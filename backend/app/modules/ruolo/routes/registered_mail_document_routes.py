import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo.registered_mail_document_schemas import (
    CardMetadata,
    CardUpload,
    RegisteredMailDocumentView,
)
from app.modules.ruolo.services import registered_mail_documents as service
from app.modules.utenze.routes.support import _ensure_document_available_locally
from app.services.nas_connector import NasConnectorError

router = APIRouter(
    prefix="/tributi/raccomandate",
    tags=["ruolo-tributi"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)
Database = Annotated[Session, Depends(get_db)]
Editor = Annotated[ApplicationUser, Depends(require_section("ruolo.tributi.manage_status"))]


def card_metadata(
    tracking_number: Annotated[str, Form()],
    scanned_on: Annotated[date, Form()],
    source_reference: Annotated[str | None, Form(max_length=1024)] = None,
) -> CardMetadata:
    return CardMetadata(tracking_number, scanned_on, source_reference)


@router.get("/{mail_id}/cartoline", response_model=list[RegisteredMailDocumentView])
def list_cards(mail_id: uuid.UUID, db: Database) -> list[RegisteredMailDocumentView]:
    return [service.view(link, document) for link, document in service.documents(db, mail_id)]


@router.post(
    "/{mail_id}/cartoline",
    response_model=RegisteredMailDocumentView,
    dependencies=[Depends(require_module("utenze"))],
)
async def upload_card(
    mail_id: uuid.UUID,
    db: Database,
    current_user: Editor,
    file: Annotated[UploadFile, File()],
    metadata: Annotated[CardMetadata, Depends(card_metadata)],
) -> RegisteredMailDocumentView:
    content = await file.read(service.MAX_PDF_BYTES + 1)
    try:
        return service.upload(
            db,
            mail_id=mail_id,
            payload=CardUpload(
                filename=file.filename or "",
                content=content,
                tracking_number=metadata.tracking_number,
                scanned_on=metadata.scanned_on,
                source_reference=metadata.source_reference,
            ),
            actor_id=current_user.id,
        )
    except NasConnectorError as exc:
        db.rollback()
        raise HTTPException(
            502, "Salvataggio NAS non riuscito: nessuna cartolina collegata"
        ) from exc


@router.get("/{mail_id}/cartoline/{card_id}/download")
def download_card(mail_id: uuid.UUID, card_id: uuid.UUID, db: Database) -> FileResponse:
    for link, document in service.documents(db, mail_id):
        if link.id == card_id:
            return FileResponse(
                _ensure_document_available_locally(db, document),
                media_type="application/pdf",
                filename=document.filename,
            )
    raise HTTPException(404, "Cartolina non trovata per questa raccomandata")
