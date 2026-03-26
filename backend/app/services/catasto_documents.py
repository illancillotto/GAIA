from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoDocument, CatastoVisuraRequest


class CatastoDocumentNotFoundError(Exception):
    pass


def list_documents_for_user(
    db: Session,
    user_id: int,
    *,
    search: str | None = None,
    comune: str | None = None,
    foglio: str | None = None,
    particella: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> list[CatastoDocument]:
    statement = select(CatastoDocument).where(CatastoDocument.user_id == user_id)

    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                CatastoDocument.comune.ilike(term),
                CatastoDocument.filename.ilike(term),
                CatastoDocument.foglio.ilike(term),
                CatastoDocument.particella.ilike(term),
                CatastoDocument.subalterno.ilike(term),
            )
        )
    if comune:
        statement = statement.where(CatastoDocument.comune.ilike(f"%{comune.strip()}%"))
    if foglio:
        statement = statement.where(CatastoDocument.foglio == foglio.strip())
    if particella:
        statement = statement.where(CatastoDocument.particella == particella.strip())
    if created_from:
        statement = statement.where(CatastoDocument.created_at >= created_from)
    if created_to:
        statement = statement.where(CatastoDocument.created_at <= created_to)

    statement = statement.order_by(CatastoDocument.created_at.desc())
    return list(db.scalars(statement).all())


def list_documents_for_batch(db: Session, user_id: int, batch_id: UUID) -> list[CatastoDocument]:
    statement = (
        select(CatastoDocument)
        .join(CatastoVisuraRequest, CatastoVisuraRequest.id == CatastoDocument.request_id)
        .where(
            CatastoDocument.user_id == user_id,
            CatastoVisuraRequest.batch_id == batch_id,
        )
        .order_by(CatastoVisuraRequest.row_index.asc(), CatastoDocument.created_at.asc())
    )
    return list(db.scalars(statement).all())


def list_documents_by_ids_for_user(db: Session, user_id: int, document_ids: list[UUID]) -> list[CatastoDocument]:
    if not document_ids:
        return []

    statement = (
        select(CatastoDocument)
        .where(
            CatastoDocument.user_id == user_id,
            CatastoDocument.id.in_(document_ids),
        )
        .order_by(CatastoDocument.created_at.desc())
    )
    return list(db.scalars(statement).all())


def get_document_for_user(db: Session, user_id: int, document_id: UUID) -> CatastoDocument:
    document = db.scalar(
        select(CatastoDocument).where(
            CatastoDocument.id == document_id,
            CatastoDocument.user_id == user_id,
        ),
    )
    if document is None:
        raise CatastoDocumentNotFoundError(f"Document {document_id} not found")
    return document
