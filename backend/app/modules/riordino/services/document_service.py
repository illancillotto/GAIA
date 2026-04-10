"""Document services."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.riordino.enums import ALLOWED_MIME_TYPES, DOCUMENT_STORAGE_ROOT, EventType, MAX_FILE_SIZE
from app.modules.riordino.models import RiordinoDocument, RiordinoPhase, RiordinoStep
from app.modules.riordino.repositories import DocumentRepository, PracticeRepository
from app.modules.riordino.services.common import create_event, require_admin_like, utcnow


def _storage_root() -> Path:
    return Path(os.getenv("GAIA_RIORDINO_STORAGE_ROOT", DOCUMENT_STORAGE_ROOT))


def upload_document(
    db: Session,
    practice_id: UUID,
    current_user,
    file: UploadFile,
    *,
    document_type: str,
    phase_id: UUID | None = None,
    step_id: UUID | None = None,
    appeal_id: UUID | None = None,
    issue_id: UUID | None = None,
    notes: str | None = None,
) -> RiordinoDocument:
    practice = PracticeRepository(db).get(practice_id)
    if not practice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice not found")
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unsupported MIME type")
    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="File too large")

    phase_code = "_general"
    if phase_id:
        phase = db.get(RiordinoPhase, phase_id)
        phase_code = phase.phase_code if phase else phase_code
    step_code = "_general"
    if step_id:
        step = db.get(RiordinoStep, step_id)
        step_code = step.code if step else step_code

    extension = Path(file.filename or "upload.bin").suffix or ".bin"
    filename = f"{uuid.uuid4()}{extension}"
    target_dir = _storage_root() / str(practice_id) / phase_code / step_code
    target_dir.mkdir(parents=True, exist_ok=True)
    full_path = target_dir / filename
    full_path.write_bytes(content)

    version_no = DocumentRepository(db).next_version(practice_id, step_id, file.filename or filename)
    document = RiordinoDocument(
        practice_id=practice_id,
        phase_id=phase_id,
        step_id=step_id,
        issue_id=issue_id,
        appeal_id=appeal_id,
        document_type=document_type,
        version_no=version_no,
        storage_path=str(full_path),
        original_filename=file.filename or filename,
        mime_type=file.content_type,
        file_size_bytes=len(content),
        uploaded_by=current_user.id,
        notes=notes,
    )
    DocumentRepository(db).add(document)
    create_event(db, practice_id=practice_id, phase_id=phase_id, step_id=step_id, created_by=current_user.id, event_type=EventType.document_uploaded, payload_json={"document_id": str(document.id)})
    db.flush()
    return document


def list_documents(
    db: Session,
    practice_id: UUID,
    *,
    phase_id: UUID | None = None,
    step_id: UUID | None = None,
    document_type: str | None = None,
    appeal_id: UUID | None = None,
) -> list[RiordinoDocument]:
    return DocumentRepository(db).list(practice_id, phase_id=phase_id, step_id=step_id, document_type=document_type, appeal_id=appeal_id)


def get_document(db: Session, document_id: UUID) -> RiordinoDocument:
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def soft_delete_document(db: Session, document_id: UUID, current_user) -> RiordinoDocument:
    require_admin_like(current_user)
    document = get_document(db, document_id)
    document.deleted_at = utcnow()
    create_event(db, practice_id=document.practice_id, phase_id=document.phase_id, step_id=document.step_id, created_by=current_user.id, event_type=EventType.document_deleted, payload_json={"document_id": str(document.id)})
    db.flush()
    return document
