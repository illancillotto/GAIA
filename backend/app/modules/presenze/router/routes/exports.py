from __future__ import annotations

import tempfile
import uuid
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    PresenzeSyncJob,
)
from app.modules.presenze.router.common import RequirePresenzeAdmin, RequirePresenzeModule
from app.modules.presenze.router.helpers.access import _can_view_all_inaz_data
from app.modules.presenze.router.helpers.collaborators import _serialize_collaborator
from app.modules.presenze.router.helpers.jobs import (
    _create_straordinari_export_job_record,
    _create_xlsm_export_job_record,
    _is_straordinari_export_job,
    _is_xlsm_export_job,
    _resolve_straordinari_collaborator,
)
from app.modules.presenze.schemas import (
    PresenzeStraordinariExportJobCreateRequest,
    PresenzeStraordinariPreviewItemResponse,
    PresenzeStraordinariPreviewResponse,
    PresenzeSyncJobListResponse,
    PresenzeSyncJobResponse,
    PresenzeXlsmExportJobCreateRequest,
)
from app.modules.presenze.services.straordinari_export_job import (
    build_period_end as build_straordinari_period_end,
)
from app.modules.presenze.services.straordinari_export_job import (
    build_straordinari_export_items,
    format_duration_label,
    list_straordinari_preview_items,
    previous_month_period_start,
)
from app.modules.presenze.services.sync_runtime import (
    delete_sync_artifact_dir,
    reconcile_stale_sync_jobs,
    resolve_sync_artifact_path,
)
from app.modules.presenze.services.xlsm_export_job import (
    generate_xlsm_export,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

router = APIRouter(prefix="/presenze")

@router.get("/export/giornaliere.xlsm")
def export_giornaliere_xlsm(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
    period_start: date = Query(...),
    collaborator_id: list[uuid.UUID] | None = Query(default=None),
    employee_kind: str | None = Query(default=None),
    template_path: str | None = Query(default=None),
) -> FileResponse:
    with tempfile.NamedTemporaryFile(prefix="inaz_", suffix=".xlsm", delete=False) as tmp:
        output_path = Path(tmp.name)
    try:
        generate_xlsm_export(
            db,
            period_start=period_start,
            collaborator_ids=collaborator_id,
            employee_kind=employee_kind,
            template_path=template_path,
            output_path=output_path,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(output_path, media_type="application/vnd.ms-excel.sheet.macroEnabled.12", filename=output_path.name)

@router.post("/export/jobs/xlsm", response_model=PresenzeSyncJobResponse)
def create_xlsm_export_job(
    payload: PresenzeXlsmExportJobCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    job = _create_xlsm_export_job_record(
        db,
        requested_by_user_id=current_user.id,
        period_start=payload.period_start,
        collaborator_ids=payload.collaborator_ids,
        employee_kind=payload.employee_kind,
        template_path=payload.template_path,
    )
    return PresenzeSyncJobResponse.model_validate(job)

@router.get("/export/jobs/xlsm", response_model=PresenzeSyncJobListResponse)
def list_xlsm_export_jobs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
    limit: int | None = Query(default=None, ge=1, le=100),
) -> PresenzeSyncJobListResponse:
    reconcile_stale_sync_jobs(db)
    stmt = select(PresenzeSyncJob)
    if not _can_view_all_inaz_data(current_user):
        stmt = stmt.where(PresenzeSyncJob.requested_by_user_id == current_user.id)
    jobs = db.execute(stmt.order_by(PresenzeSyncJob.created_at.desc())).scalars().all()
    filtered_jobs = [job for job in jobs if _is_xlsm_export_job(job)]
    total = len(filtered_jobs)
    if limit is not None:
        filtered_jobs = filtered_jobs[:limit]
    return PresenzeSyncJobListResponse(items=[PresenzeSyncJobResponse.model_validate(job) for job in filtered_jobs], total=total)

@router.get("/export/jobs/xlsm/{job_id}", response_model=PresenzeSyncJobResponse)
def get_xlsm_export_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    reconcile_stale_sync_jobs(db)
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or not _is_xlsm_export_job(job) or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="XLSM export job not found")
    return PresenzeSyncJobResponse.model_validate(job)

@router.delete("/export/jobs/xlsm/{job_id}", status_code=204)
def delete_xlsm_export_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> Response:
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or not _is_xlsm_export_job(job) or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="XLSM export job not found")
    if job.status not in {"failed", "cancelled", "completed"}:
        raise HTTPException(status_code=409, detail="Only terminal XLSM export jobs can be deleted")

    delete_sync_artifact_dir(str(job.id))
    db.delete(job)
    db.commit()
    return Response(status_code=204)

@router.get("/export/jobs/xlsm/{job_id}/artifacts/{artifact_name}")
def download_xlsm_export_job_artifact(
    job_id: uuid.UUID,
    artifact_name: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> FileResponse:
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or not _is_xlsm_export_job(job) or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="XLSM export job not found")
    try:
        artifact_path = resolve_sync_artifact_path(str(job.id), artifact_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="XLSM export job artifact not found")
    media_type = {
        "xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
        "summary": "application/json",
        "progress": "application/json",
        "log": "text/plain; charset=utf-8",
    }.get(artifact_name, "application/octet-stream")
    return FileResponse(artifact_path, media_type=media_type, filename=artifact_path.name)

@router.get("/export/straordinari/preview", response_model=PresenzeStraordinariPreviewResponse)
def preview_straordinari_export(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
) -> PresenzeStraordinariPreviewResponse:
    collaborator = _resolve_straordinari_collaborator(db, current_user=current_user, collaborator_id=collaborator_id)
    period_start = previous_month_period_start()
    period_end = date.fromordinal(build_straordinari_period_end(period_start).toordinal() - 1)
    _, items = list_straordinari_preview_items(db, collaborator_id=collaborator.id, period_start=period_start)
    return PresenzeStraordinariPreviewResponse(
        collaborator=_serialize_collaborator(db, collaborator),
        period_start=period_start,
        period_end=period_end,
        items=[
            PresenzeStraordinariPreviewItemResponse(
                record_id=item.record_id,
                work_date=item.work_date,
                motivation=item.motivation,
                start_time=item.start_time,
                end_time=item.end_time,
                duration_minutes=item.duration_minutes,
                duration_label=format_duration_label(item.duration_minutes),
            )
            for item in items
        ],
    )

@router.post("/export/jobs/straordinari", response_model=PresenzeSyncJobResponse)
def create_straordinari_export_job(
    payload: PresenzeStraordinariExportJobCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    collaborator = _resolve_straordinari_collaborator(db, current_user=current_user, collaborator_id=payload.collaborator_id)
    if payload.template_path and not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Solo admin e super admin possono indicare un template straordinari personalizzato")
    period_start = previous_month_period_start()
    requested_motivations = {item.record_id: item.motivation for item in payload.items}
    try:
        _, export_items = build_straordinari_export_items(
            db,
            collaborator_id=collaborator.id,
            period_start=period_start,
            requested_motivations=requested_motivations,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    job = _create_straordinari_export_job_record(
        db,
        requested_by_user_id=current_user.id,
        collaborator=collaborator,
        period_start=period_start,
        template_path=payload.template_path,
        items=[
            {
                "work_date": item.work_date.isoformat(),
                "motivation": item.motivation,
                "start_time": item.start_time,
                "end_time": item.end_time,
                "duration_minutes": item.duration_minutes,
            }
            for item in export_items
        ],
    )
    return PresenzeSyncJobResponse.model_validate(job)

@router.get("/export/jobs/straordinari", response_model=PresenzeSyncJobListResponse)
def list_straordinari_export_jobs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    limit: int | None = Query(default=None, ge=1, le=100),
) -> PresenzeSyncJobListResponse:
    reconcile_stale_sync_jobs(db)
    stmt = select(PresenzeSyncJob)
    if not _can_view_all_inaz_data(current_user):
        stmt = stmt.where(PresenzeSyncJob.requested_by_user_id == current_user.id)
    jobs = db.execute(stmt.order_by(PresenzeSyncJob.created_at.desc())).scalars().all()
    filtered_jobs = [job for job in jobs if _is_straordinari_export_job(job)]
    total = len(filtered_jobs)
    if limit is not None:
        filtered_jobs = filtered_jobs[:limit]
    return PresenzeSyncJobListResponse(items=[PresenzeSyncJobResponse.model_validate(job) for job in filtered_jobs], total=total)

@router.get("/export/jobs/straordinari/{job_id}", response_model=PresenzeSyncJobResponse)
def get_straordinari_export_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    reconcile_stale_sync_jobs(db)
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or not _is_straordinari_export_job(job) or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Straordinari export job not found")
    return PresenzeSyncJobResponse.model_validate(job)

@router.delete("/export/jobs/straordinari/{job_id}", status_code=204)
def delete_straordinari_export_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> Response:
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or not _is_straordinari_export_job(job) or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Straordinari export job not found")
    if job.status not in {"failed", "cancelled", "completed"}:
        raise HTTPException(status_code=409, detail="Only terminal straordinari export jobs can be deleted")

    delete_sync_artifact_dir(str(job.id))
    db.delete(job)
    db.commit()
    return Response(status_code=204)

@router.get("/export/jobs/straordinari/{job_id}/artifacts/{artifact_name}")
def download_straordinari_export_job_artifact(
    job_id: uuid.UUID,
    artifact_name: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> FileResponse:
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or not _is_straordinari_export_job(job) or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Straordinari export job not found")
    try:
        artifact_path = resolve_sync_artifact_path(str(job.id), artifact_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="Straordinari export job artifact not found")
    media_type = {
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "summary": "application/json",
        "progress": "application/json",
        "log": "text/plain; charset=utf-8",
    }.get(artifact_name, "application/octet-stream")
    filename = (job.params_json or {}).get("output_filename") if artifact_name == "xlsx" else artifact_path.name
    return FileResponse(artifact_path, media_type=media_type, filename=str(filename))

# fmt: on
