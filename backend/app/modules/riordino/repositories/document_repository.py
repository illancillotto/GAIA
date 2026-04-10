"""Document repository helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.riordino.models import RiordinoDocument


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, document: RiordinoDocument) -> RiordinoDocument:
        self.db.add(document)
        self.db.flush()
        self.db.refresh(document)
        return document

    def get(self, document_id: uuid.UUID) -> RiordinoDocument | None:
        return self.db.get(RiordinoDocument, document_id)

    def next_version(self, practice_id: uuid.UUID, step_id: uuid.UUID | None, original_filename: str) -> int:
        max_version = self.db.scalar(
            select(func.max(RiordinoDocument.version_no)).where(
                RiordinoDocument.practice_id == practice_id,
                RiordinoDocument.step_id == step_id,
                RiordinoDocument.original_filename == original_filename,
            )
        )
        return (max_version or 0) + 1

    def list(
        self,
        practice_id: uuid.UUID,
        *,
        phase_id: uuid.UUID | None = None,
        step_id: uuid.UUID | None = None,
        document_type: str | None = None,
        appeal_id: uuid.UUID | None = None,
    ) -> list[RiordinoDocument]:
        stmt = select(RiordinoDocument).where(
            RiordinoDocument.practice_id == practice_id,
            RiordinoDocument.deleted_at.is_(None),
        )
        if phase_id:
            stmt = stmt.where(RiordinoDocument.phase_id == phase_id)
        if step_id:
            stmt = stmt.where(RiordinoDocument.step_id == step_id)
        if document_type:
            stmt = stmt.where(RiordinoDocument.document_type == document_type)
        if appeal_id:
            stmt = stmt.where(RiordinoDocument.appeal_id == appeal_id)
        return list(self.db.scalars(stmt.order_by(RiordinoDocument.created_at.desc())))
