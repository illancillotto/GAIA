"""Routes storiche del workspace Ruolo."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_module
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo import repositories as repo
from app.modules.ruolo.schemas import (
    RuoloImportJobListResponse,
    RuoloImportJobResponse,
    RuoloImportYearDetectionResponse,
)

router = APIRouter(tags=["ruolo-import"])

_DMP_DISMISSED_DETAIL = (
    "L'import file Ruolo basato su DMP/PDF e dismesso. "
    "Usa il workflow Elaborazioni > Capacitas > inCASS avvisi per la raccolta del ruolo."
)


@router.post("/import/upload")
async def upload_ruolo(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_module("ruolo")),
) -> None:
    """Upload DMP/PDF dismesso: il ruolo si raccoglie via inCASS."""
    del file, db, current_user
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_DMP_DISMISSED_DETAIL)


@router.post("/import/detect-year", response_model=RuoloImportYearDetectionResponse)
async def detect_import_year(
    file: UploadFile,
    current_user: ApplicationUser = Depends(require_module("ruolo")),
) -> RuoloImportYearDetectionResponse:
    del file, current_user
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_DMP_DISMISSED_DETAIL)


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
