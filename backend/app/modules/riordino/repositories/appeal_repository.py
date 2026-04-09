"""Appeal repository helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.riordino.models import RiordinoAppeal


class AppealRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, appeal: RiordinoAppeal) -> RiordinoAppeal:
        self.db.add(appeal)
        self.db.flush()
        self.db.refresh(appeal)
        return appeal

    def get(self, practice_id: uuid.UUID, appeal_id: uuid.UUID) -> RiordinoAppeal | None:
        return self.db.scalar(
            select(RiordinoAppeal).where(RiordinoAppeal.practice_id == practice_id, RiordinoAppeal.id == appeal_id)
        )

    def list(self, practice_id: uuid.UUID, status: str | None = None) -> list[RiordinoAppeal]:
        stmt = select(RiordinoAppeal).where(RiordinoAppeal.practice_id == practice_id)
        if status:
            stmt = stmt.where(RiordinoAppeal.status == status)
        return list(self.db.scalars(stmt.order_by(RiordinoAppeal.created_at.desc())))
