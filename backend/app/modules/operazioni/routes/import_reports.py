"""Import endpoints for Operazioni field reports."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.services.import_white import import_white_reports

router = APIRouter(prefix="", tags=["operazioni/reports-import"])


@router.post("/reports/import-white", response_model=dict)
async def import_white_reports_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="È richiesto un file Excel .xlsx",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Il file caricato è vuoto",
        )

    result = import_white_reports(
        db=db,
        current_user=current_user,
        file_bytes=file_bytes,
    )
    return {
        "imported": result.imported,
        "skipped": result.skipped,
        "errors": result.errors,
        "categories_created": result.categories_created,
        "total_events_created": result.total_events_created,
    }
