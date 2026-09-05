from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    PresenzeSyncJob,
)
from app.modules.presenze.router.common import RequirePresenzeModule
from app.modules.presenze.router.helpers.access import _can_view_all_inaz_data
from app.modules.presenze.router.helpers.jobs import (
    _create_sync_job_record,
    _load_sync_job_summary,
    _normalize_employee_codes,
)
from app.modules.presenze.schemas import (
    PresenzeSyncJobCreateRequest,
    PresenzeSyncJobListResponse,
    PresenzeSyncJobResponse,
    PresenzeSyncJobRetrySelectedRequest,
)
from app.modules.presenze.services.credentials import (
    get_credential,
)
from app.modules.presenze.services.sync_runtime import (
    delete_sync_artifact_dir,
    has_running_sync_job,
    prepare_sync_job_artifacts,
    reconcile_stale_sync_jobs,
    resolve_sync_artifact_path,
    stop_sync_worker,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

router = APIRouter(prefix="/presenze")

@router.post("/sync/jobs", response_model=PresenzeSyncJobResponse)
def create_sync_job(
    payload: PresenzeSyncJobCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    if has_running_sync_job(db):
        raise HTTPException(status_code=409, detail="Another Presenze sync job is already pending or running")
    credential = get_credential(db, payload.credential_id, current_user)
    if credential is None:
        raise HTTPException(status_code=404, detail="Credenziale Presenze non trovata")
    job = _create_sync_job_record(
        db,
        requested_by_user_id=current_user.id,
        credential_id=credential.id,
        year=payload.year,
        month=payload.month,
        collaborator_limit=payload.collaborator_limit,
        employee_codes=payload.employee_codes,
        trigger="manual",
    )
    return PresenzeSyncJobResponse.model_validate(job)

@router.get("/sync/jobs", response_model=PresenzeSyncJobListResponse)
def list_sync_jobs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    limit: int | None = Query(default=None, ge=1, le=100),
) -> PresenzeSyncJobListResponse:
    reconcile_stale_sync_jobs(db)
    stmt = select(PresenzeSyncJob)
    count_stmt = select(func.count(PresenzeSyncJob.id))
    if not _can_view_all_inaz_data(current_user):
        visibility_filter = PresenzeSyncJob.requested_by_user_id == current_user.id
        stmt = stmt.where(visibility_filter)
        count_stmt = count_stmt.where(visibility_filter)
    stmt = stmt.order_by(PresenzeSyncJob.created_at.desc())
    if limit is not None:
        stmt = stmt.limit(limit)
    jobs = db.execute(stmt).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    return PresenzeSyncJobListResponse(items=[PresenzeSyncJobResponse.model_validate(job) for job in jobs], total=total)

@router.get("/sync/jobs/{job_id}", response_model=PresenzeSyncJobResponse)
def get_sync_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    reconcile_stale_sync_jobs(db)
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    return PresenzeSyncJobResponse.model_validate(job)

@router.post("/sync/jobs/{job_id}/retry", response_model=PresenzeSyncJobResponse)
def retry_sync_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    if has_running_sync_job(db):
        raise HTTPException(status_code=409, detail="Another Presenze sync job is already pending or running")

    job = db.get(PresenzeSyncJob, job_id)
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    if job.status not in {"failed", "completed"}:
        raise HTTPException(status_code=409, detail="Sync job is not retryable in the current state")
    if job.credential_id is None:
        raise HTTPException(status_code=409, detail="Questo job usa una configurazione legacy. Crea una nuova sync con una credenziale Presenze salvata.")
    checkpoint = dict((job.params_json or {}).get("checkpoint") or {})
    completed_employee_codes = checkpoint.get("completed_employee_codes")
    has_resume_checkpoint = isinstance(completed_employee_codes, list) and len(completed_employee_codes) > 0
    if job.attempt_count >= job.max_attempts and not has_resume_checkpoint:
        raise HTTPException(status_code=409, detail="Sync job reached the configured max attempts")

    job.status = "pending"
    job.error_detail = None
    job.started_at = None
    job.finished_at = None
    job.worker_pid = None
    prepare_sync_job_artifacts(job)
    db.add(job)
    db.commit()
    db.refresh(job)
    return PresenzeSyncJobResponse.model_validate(job)

@router.post("/sync/jobs/{job_id}/retry-selected", response_model=PresenzeSyncJobResponse)
def retry_sync_job_selected(
    job_id: uuid.UUID,
    payload: PresenzeSyncJobRetrySelectedRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    if has_running_sync_job(db):
        raise HTTPException(status_code=409, detail="Another Presenze sync job is already pending or running")

    source_job = db.get(PresenzeSyncJob, job_id)
    if source_job is None or (not _can_view_all_inaz_data(current_user) and source_job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    if source_job.credential_id is None:
        raise HTTPException(status_code=409, detail="Questo job usa una configurazione legacy. Crea una nuova sync con una credenziale Presenze salvata.")

    requested_codes = _normalize_employee_codes(payload.employee_codes)
    if not requested_codes:
        raise HTTPException(status_code=422, detail="At least one employee code is required")

    summary_payload = _load_sync_job_summary(str(source_job.id))
    error_items = summary_payload.get("error_items")
    failed_codes = {
        str(item.get("employee_code") or "").strip()
        for item in error_items
        if isinstance(item, dict) and str(item.get("employee_code") or "").strip()
    } if isinstance(error_items, list) else set()
    if not failed_codes:
        raise HTTPException(status_code=409, detail="No failed collaborators available in the job summary")

    invalid_codes = [code for code in requested_codes if code not in failed_codes]
    if invalid_codes:
        raise HTTPException(
            status_code=409,
            detail=f"Selected employee codes are not retryable for this job: {', '.join(invalid_codes)}",
        )

    retry_job = _create_sync_job_record(
        db,
        requested_by_user_id=current_user.id,
        credential_id=source_job.credential_id,
        year=int((source_job.params_json or {}).get("year") or source_job.period_end.year),
        month=int((source_job.params_json or {}).get("month") or source_job.period_end.month),
        collaborator_limit=None,
        employee_codes=requested_codes,
        period_start_override=source_job.period_start,
        period_end_override=source_job.period_end,
        params_overrides={
            "target_scope": (source_job.params_json or {}).get("target_scope"),
            "target_months": (source_job.params_json or {}).get("target_months"),
        },
        trigger="retry_selected",
    )
    return PresenzeSyncJobResponse.model_validate(retry_job)

@router.get("/sync/jobs/{job_id}/artifacts/{artifact_name}")
def download_sync_job_artifact(
    job_id: uuid.UUID,
    artifact_name: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> FileResponse:
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    try:
        artifact_path = resolve_sync_artifact_path(str(job.id), artifact_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="Sync job artifact not found")
    media_type = {
        "json": "application/json",
        "summary": "application/json",
        "progress": "application/json",
        "events": "application/x-ndjson",
        "log": "text/plain; charset=utf-8",
    }.get(artifact_name, "application/octet-stream")
    return FileResponse(artifact_path, media_type=media_type, filename=artifact_path.name)

@router.post("/sync/jobs/{job_id}/cancel", response_model=PresenzeSyncJobResponse)
def cancel_sync_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    if job.status not in {"pending", "running"}:
        raise HTTPException(status_code=409, detail="Sync job cannot be cancelled in the current state")
    if job.status == "running" and job.worker_pid is not None:
        try:
            stop_sync_worker(job)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    job.status = "cancelled"
    job.error_detail = "Sync job cancelled by user"
    job.finished_at = datetime.now(UTC)
    db.add(job)
    db.commit()
    db.refresh(job)
    return PresenzeSyncJobResponse.model_validate(job)

@router.delete("/sync/jobs/{job_id}", status_code=204)
def delete_sync_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> Response:
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    if job.status not in {"failed", "cancelled", "completed"}:
        raise HTTPException(status_code=409, detail="Only terminal sync jobs can be deleted")

    delete_sync_artifact_dir(str(job.id))
    db.delete(job)
    db.commit()
    return Response(status_code=204)

# fmt: on
