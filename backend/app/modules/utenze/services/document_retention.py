import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo.registered_mail_document_models import RegisteredMailDocument


def ensure_cartolina_retention(db: Session, document_id: uuid.UUID | None = None) -> None:
    query = select(RegisteredMailDocument.id).limit(1)
    if document_id is not None:
        query = query.where(RegisteredMailDocument.document_id == document_id)
    if db.scalar(query):
        raise HTTPException(
            status_code=409,
            detail="Cartoline collegate a raccomandate: revisione necessaria prima di cancellare o resettare",
        )
