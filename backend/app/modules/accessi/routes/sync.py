from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.sync_job import SyncJob
from app.schemas.sync import (
    SyncApplyResponse,
    SyncCapabilitiesResponse,
    SyncJobCreateRequest,
    SyncJobResponse,
    SyncPreviewRequest,
    SyncPreviewResponse,
)
from app.services.nas_connector import get_sync_capabilities
from app.services.sync import apply_sync_payload, build_sync_preview
from app.services.sync_runtime import (
    get_sync_job_artifact_dir,
    has_running_sync_job,
    launch_sync_worker,
    reconcile_stale_sync_jobs,
    stop_sync_worker,
)
from app.services.sync_runs import create_sync_run

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/capabilities", response_model=SyncCapabilitiesResponse)
def sync_capabilities(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
) -> SyncCapabilitiesResponse:
    return get_sync_capabilities()


@router.post("/preview", response_model=SyncPreviewResponse)
def sync_preview(
    payload: SyncPreviewRequest,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
) -> SyncPreviewResponse:
    return build_sync_preview(payload)


@router.post("/apply", response_model=SyncApplyResponse)
def sync_apply(
    payload: SyncPreviewRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SyncApplyResponse:
    started_at = datetime.now(timezone.utc)
    result = apply_sync_payload(db, payload)
    create_sync_run(
        db,
        mode="payload",
        trigger_type="api",
        status="succeeded",
        attempts_used=1,
        snapshot_id=result.snapshot_id,
        initiated_by=current_user.username,
        source_label="api:payload",
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
    )
    return result


def _serialize_sync_job(job: SyncJob) -> SyncJobResponse:
    return SyncJobResponse.model_validate(job)


@router.post("/jobs", response_model=SyncJobResponse, status_code=status.HTTP_201_CREATED)
def create_sync_job(
    current_user: Annotated[ApplicationUser, Depends(require_section("accessi.sync"))],
    db: Annotated[Session, Depends(get_db)],
    payload: SyncJobCreateRequest,
) -> SyncJobResponse:
    profile = payload.profile if payload.profile in {"quick", "full"} else "quick"
    if has_running_sync_job(db):
        raise HTTPException(status_code=409, detail="Another NAS sync job is already pending or running")

    job = SyncJob(
        requested_by_user_id=current_user.id,
        profile=profile,
        trigger_type="api",
        status="pending",
        max_attempts=3,
        source_label=f"api:ssh:{profile}",
    )
    db.add(job)
    db.flush()
    job.worker_log_path = str(get_sync_job_artifact_dir(job.id) / "worker.log")

    try:
        job.worker_pid = launch_sync_worker(job)
    except Exception as exc:
        job.status = "failed"
        job.error_detail = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Unable to start NAS sync worker: {exc}") from exc

    db.add(job)
    db.commit()
    db.refresh(job)
    return _serialize_sync_job(job)


@router.post("/live-apply", response_model=SyncJobResponse, status_code=status.HTTP_201_CREATED)
def sync_live_apply(
    current_user: Annotated[ApplicationUser, Depends(require_section("accessi.sync"))],
    db: Annotated[Session, Depends(get_db)],
    payload: SyncJobCreateRequest | None = None,
) -> SyncJobResponse:
    request_payload = payload or SyncJobCreateRequest()
    return create_sync_job(current_user=current_user, db=db, payload=request_payload)


@router.get("/jobs", response_model=list[SyncJobResponse])
def list_sync_jobs(
    current_user: Annotated[ApplicationUser, Depends(require_section("accessi.sync"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[SyncJobResponse]:
    reconcile_stale_sync_jobs(db)
    stmt = select(SyncJob)
    if current_user.role not in {"admin", "super_admin"}:
        stmt = stmt.where(SyncJob.requested_by_user_id == current_user.id)
    jobs = db.execute(stmt.order_by(SyncJob.created_at.desc())).scalars().all()
    return [_serialize_sync_job(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=SyncJobResponse)
def get_sync_job(
    job_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_section("accessi.sync"))],
    db: Annotated[Session, Depends(get_db)],
) -> SyncJobResponse:
    reconcile_stale_sync_jobs(db)
    job = db.get(SyncJob, job_id)
    if job is None or (current_user.role not in {"admin", "super_admin"} and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    return _serialize_sync_job(job)


@router.post("/jobs/{job_id}/retry", response_model=SyncJobResponse)
def retry_sync_job(
    job_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_section("accessi.sync"))],
    db: Annotated[Session, Depends(get_db)],
) -> SyncJobResponse:
    if has_running_sync_job(db):
        raise HTTPException(status_code=409, detail="Another NAS sync job is already pending or running")
    job = db.get(SyncJob, job_id)
    if job is None or (current_user.role not in {"admin", "super_admin"} and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    if job.status not in {"failed", "succeeded", "cancelled"}:
        raise HTTPException(status_code=409, detail="Sync job is not retryable in the current state")
    job.status = "pending"
    job.snapshot_id = None
    job.persisted_users = 0
    job.persisted_groups = 0
    job.persisted_shares = 0
    job.persisted_permission_entries = 0
    job.persisted_effective_permissions = 0
    job.share_acl_pairs_used = 0
    job.error_detail = None
    job.started_at = None
    job.finished_at = None
    try:
        job.worker_pid = launch_sync_worker(job)
    except Exception as exc:
        job.status = "failed"
        job.error_detail = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Unable to restart NAS sync worker: {exc}") from exc
    db.add(job)
    db.commit()
    db.refresh(job)
    return _serialize_sync_job(job)


@router.post("/jobs/{job_id}/cancel", response_model=SyncJobResponse)
def cancel_sync_job(
    job_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_section("accessi.sync"))],
    db: Annotated[Session, Depends(get_db)],
) -> SyncJobResponse:
    job = db.get(SyncJob, job_id)
    if job is None or (current_user.role not in {"admin", "super_admin"} and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    if job.status not in {"pending", "running"}:
        raise HTTPException(status_code=409, detail="Sync job cannot be cancelled in the current state")
    try:
        stop_sync_worker(job)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    job.status = "cancelled"
    job.error_detail = "Sync job cancelled by user"
    job.finished_at = datetime.now(timezone.utc)
    db.add(job)
    db.commit()
    db.refresh(job)
    return _serialize_sync_job(job)
