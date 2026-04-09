"""Document routes."""

from __future__ import annotations

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.riordino.schemas import DocumentListResponse, DocumentResponse
from app.modules.riordino.services import get_document, list_documents, soft_delete_document, upload_document

router = APIRouter(dependencies=[Depends(require_module("riordino")), Depends(require_section("riordino.documents"))])


@router.post("/{practice_id}/documents", response_model=DocumentResponse)
def upload_document_endpoint(
    practice_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    document_type: str = Form(...),
    phase_id: UUID | None = Form(None),
    step_id: UUID | None = Form(None),
    appeal_id: UUID | None = Form(None),
    issue_id: UUID | None = Form(None),
    notes: str | None = Form(None),
):
    document = upload_document(
        db,
        practice_id,
        current_user,
        file,
        document_type=document_type,
        phase_id=phase_id,
        step_id=step_id,
        appeal_id=appeal_id,
        issue_id=issue_id,
        notes=notes,
    )
    db.commit()
    db.refresh(document)
    return document


@router.get("/{practice_id}/documents", response_model=DocumentListResponse)
def list_documents_endpoint(
    practice_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    phase_id: UUID | None = None,
    step_id: UUID | None = None,
    document_type: str | None = None,
    appeal_id: UUID | None = None,
):
    items = list_documents(db, practice_id, phase_id=phase_id, step_id=step_id, document_type=document_type, appeal_id=appeal_id)
    return DocumentListResponse(items=[DocumentResponse.model_validate(item) for item in items], total=len(items), page=1, per_page=len(items) or 1, total_pages=1)


@router.get("/documents/{document_id}/download")
def download_document_endpoint(
    document_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    document = get_document(db, document_id)
    return FileResponse(document.storage_path, filename=document.original_filename, media_type=document.mime_type)


@router.delete("/documents/{document_id}", response_model=DocumentResponse)
def delete_document_endpoint(
    document_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    document = soft_delete_document(db, document_id, current_user)
    db.commit()
    db.refresh(document)
    return document
