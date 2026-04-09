"""Practice repository helpers."""

from __future__ import annotations

import math
import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.riordino.models import (
    RiordinoAppeal,
    RiordinoDocument,
    RiordinoIssue,
    RiordinoPhase,
    RiordinoPractice,
)


class PracticeRepository:
    def __init__(self, db: Session):
        self.db = db

    def next_code(self, year: int) -> str:
        prefix = f"RIO-{year}-"
        max_code = self.db.scalar(
            select(func.max(RiordinoPractice.code)).where(RiordinoPractice.code.like(f"{prefix}%"))
        )
        next_no = 1
        if max_code:
            next_no = int(max_code.rsplit("-", 1)[1]) + 1
        return f"{prefix}{next_no:04d}"

    def add(self, practice: RiordinoPractice) -> RiordinoPractice:
        self.db.add(practice)
        self.db.flush()
        self.db.refresh(practice)
        return practice

    def get(self, practice_id: uuid.UUID, include_deleted: bool = False) -> RiordinoPractice | None:
        stmt = (
            select(RiordinoPractice)
            .options(
                selectinload(RiordinoPractice.phases).selectinload(RiordinoPhase.steps),
                selectinload(RiordinoPractice.documents),
                selectinload(RiordinoPractice.issues),
                selectinload(RiordinoPractice.appeals),
                selectinload(RiordinoPractice.events),
            )
            .where(RiordinoPractice.id == practice_id)
        )
        if not include_deleted:
            stmt = stmt.where(RiordinoPractice.deleted_at.is_(None))
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        status: str | None,
        municipality: str | None,
        phase: str | None,
        owner: int | None,
        page: int,
        per_page: int,
    ) -> tuple[list[RiordinoPractice], int]:
        stmt: Select[tuple[RiordinoPractice]] = select(RiordinoPractice).where(RiordinoPractice.deleted_at.is_(None))
        if status:
            stmt = stmt.where(RiordinoPractice.status == status)
        if municipality:
            stmt = stmt.where(RiordinoPractice.municipality == municipality)
        if phase:
            stmt = stmt.where(RiordinoPractice.current_phase == phase)
        if owner:
            stmt = stmt.where(RiordinoPractice.owner_user_id == owner)

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        items = list(
            self.db.scalars(
                stmt.order_by(RiordinoPractice.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
        )
        return items, total

    def detail_counts(self, practice_id: uuid.UUID) -> tuple[int, int, int]:
        issues_count = self.db.scalar(select(func.count(RiordinoIssue.id)).where(RiordinoIssue.practice_id == practice_id)) or 0
        appeals_count = self.db.scalar(select(func.count(RiordinoAppeal.id)).where(RiordinoAppeal.practice_id == practice_id)) or 0
        documents_count = self.db.scalar(
            select(func.count(RiordinoDocument.id)).where(
                RiordinoDocument.practice_id == practice_id,
                RiordinoDocument.deleted_at.is_(None),
            )
        ) or 0
        return issues_count, appeals_count, documents_count
