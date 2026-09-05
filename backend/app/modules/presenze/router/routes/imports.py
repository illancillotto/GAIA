from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    PresenzeImportJob,
)
from app.modules.presenze.router.common import RequirePresenzeAdmin, RequirePresenzeModule
from app.modules.presenze.router.helpers.access import _can_view_all_inaz_data
from app.modules.presenze.schemas import (
    PresenzeImportJobListResponse,
    PresenzeImportJobResponse,
    PresenzeImportJsonResponse,
    PresenzeImportPreviewResponse,
)
from app.modules.presenze.services.import_jobs import build_preview, run_import_job
from app.modules.presenze.services.parser import (
    load_json_payload,
    parse_import_payload,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

router = APIRouter(prefix="/presenze")

@router.post("/import/preview", response_model=PresenzeImportPreviewResponse)
async def preview_import_json(
    file: UploadFile = File(...),
    _: Annotated[ApplicationUser, RequirePresenzeAdmin] = ...,
    __: Annotated[ApplicationUser, RequirePresenzeModule] = ...,
) -> PresenzeImportPreviewResponse:
    content = await file.read()
    parsed = parse_import_payload(load_json_payload(content))
    return build_preview(parsed)

@router.post("/import/json", response_model=PresenzeImportJsonResponse)
async def import_json(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, RequirePresenzeAdmin],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    file: UploadFile = File(...),
) -> PresenzeImportJsonResponse:
    content = await file.read()
    parsed = parse_import_payload(load_json_payload(content))
    try:
        return run_import_job(
            db,
            parsed=parsed,
            requested_by_user_id=current_user.id,
            filename=file.filename,
            params_json={"format": "collaboratori-json"},
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.get("/import/jobs", response_model=PresenzeImportJobListResponse)
def list_import_jobs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeImportJobListResponse:
    stmt = select(PresenzeImportJob)
    if not _can_view_all_inaz_data(current_user):
        stmt = stmt.where(PresenzeImportJob.requested_by_user_id == current_user.id)
    jobs = db.execute(stmt.order_by(PresenzeImportJob.created_at.desc())).scalars().all()
    return PresenzeImportJobListResponse(items=[PresenzeImportJobResponse.model_validate(job) for job in jobs], total=len(jobs))

@router.get("/import/jobs/{job_id}", response_model=PresenzeImportJobResponse)
def get_import_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeImportJobResponse:
    job = db.get(PresenzeImportJob, job_id)
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Import job not found")
    return PresenzeImportJobResponse.model_validate(job)

# fmt: on
