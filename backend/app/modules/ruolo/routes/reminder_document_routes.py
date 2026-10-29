"""Downloads of generated reminders; a missing local PDF is rebuilt before being served."""

import uuid
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.services import notice_pdf_regeneration as regeneration
from app.modules.ruolo.services.tributi_reminder_service import DOCX_MEDIA_TYPE, PDF_MEDIA_TYPE

router = APIRouter(
    prefix="/tributi",
    tags=["ruolo-tributi"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)


def _ensured_document(db: Session, ensure) -> Path | None:
    """A missing generated PDF is rebuilt from its saved data before being served."""
    try:
        path = ensure()
    except regeneration.RegenerationFailed as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"PDF non ricostruibile: {exc}"
        ) from exc
    db.commit()
    return path


@router.get("/solleciti/items/{item_id}/download")
def download_reminder_batch_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section("ruolo.tributi.view")),
) -> Response:
    item = repo.get_reminder_batch_item(db, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sollecito batch non trovato"
        )
    path = _ensured_document(
        db, lambda: regeneration.ensure_batch_item_document(db, item, actor_id=current_user.id)
    )
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento sollecito non trovato"
        )
    media_type = DOCX_MEDIA_TYPE if path.suffix.lower() == ".docx" else PDF_MEDIA_TYPE
    if repo.is_remote_reminder_document_path(path):
        return _remote_document_response(path, media_type=media_type)
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/reminders/{reminder_id}/download")
def download_reminder(
    reminder_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section("ruolo.tributi.view")),
) -> Response:
    reminder = repo.get_reminder(db, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sollecito non trovato")
    path = _ensured_document(
        db, lambda: regeneration.ensure_reminder_document(db, reminder, actor_id=current_user.id)
    )
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento sollecito non trovato"
        )
    if repo.is_remote_reminder_document_path(path):
        return _remote_document_response(path, media_type=DOCX_MEDIA_TYPE)
    return FileResponse(path, media_type=DOCX_MEDIA_TYPE, filename=path.name)


def _remote_document_response(path, *, media_type: str) -> Response:
    try:
        content = repo.read_remote_reminder_document(path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento sollecito non trovato"
        ) from exc

    filename = path.name
    quoted_filename = quote(filename)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted_filename}"},
    )
