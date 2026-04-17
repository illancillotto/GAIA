"""Routes per import del file Ruolo."""
from __future__ import annotations

import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, Form, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_module
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo import repositories as repo
from app.modules.ruolo.schemas import (
    RuoloImportJobListResponse,
    RuoloImportJobResponse,
    RuoloImportUploadResponse,
    RuoloImportYearDetectionResponse,
)
from app.modules.ruolo.services.import_service import (
    check_anno_already_imported,
    create_import_job,
    run_import_job,
)
from app.modules.ruolo.services.parser import detect_anno_tributario

router = APIRouter(tags=["ruolo-import"])

_background_tasks_set: set[asyncio.Task] = set()


@router.post("/import/upload", response_model=RuoloImportUploadResponse)
async def upload_ruolo(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    anno_tributario: Annotated[int | None, Form()] = None,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_module("ruolo")),
) -> RuoloImportUploadResponse:
    """Upload file Ruolo (PDF o DMP) e avvia job di import asincrono."""
    raw_content = await file.read()
    filename = file.filename or "unknown"

    resolved_anno = anno_tributario or detect_anno_tributario(raw_content, filename=filename)
    if resolved_anno is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anno tributario non rilevato automaticamente. Inseriscilo manualmente e riprova.",
        )

    existing_count = check_anno_already_imported(db, resolved_anno)
    warning_existing = existing_count > 0

    job = create_import_job(
        db,
        anno_tributario=resolved_anno,
        filename=filename,
        triggered_by=current_user.id,
    )
    db.commit()

    job_id = job.id

    task = asyncio.create_task(
        run_import_job(job_id, raw_content, resolved_anno, filename=filename)
    )
    _background_tasks_set.add(task)
    task.add_done_callback(_background_tasks_set.discard)

    return RuoloImportUploadResponse(
        job_id=str(job_id),
        status="pending",
        anno_tributario=resolved_anno,
        warning_existing=warning_existing,
        existing_count=existing_count,
    )


@router.post("/import/detect-year", response_model=RuoloImportYearDetectionResponse)
async def detect_import_year(
    file: UploadFile,
    current_user: ApplicationUser = Depends(require_module("ruolo")),
) -> RuoloImportYearDetectionResponse:
    raw_content = await file.read()
    filename = file.filename or "unknown"
    return RuoloImportYearDetectionResponse(
        detected_year=detect_anno_tributario(raw_content, filename=filename)
    )


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
