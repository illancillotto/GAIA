"""Routes storiche del workspace Ruolo."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_module
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo import repositories as repo
from app.modules.ruolo.schemas import (
    RuoloImportJobListResponse,
    RuoloImportJobResponse,
)

router = APIRouter(tags=["ruolo-import"])


@router.get("/import/jobs", response_model=RuoloImportJobListResponse)
def list_import_jobs(
    anno: int | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_module("ruolo")),
) -> RuoloImportJobListResponse:
    items, total = repo.list_jobs(db, anno=anno, page=page, page_size=page_size)
    return RuoloImportJobListResponse(
        items=[RuoloImportJobResponse.model_validate(j) for j in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/import/jobs/{job_id}", response_model=RuoloImportJobResponse)
def get_import_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_module("ruolo")),
) -> RuoloImportJobResponse:
    job = repo.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")
    return RuoloImportJobResponse.model_validate(job)
