"""Issue repository helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.riordino.models import RiordinoIssue


class IssueRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, issue: RiordinoIssue) -> RiordinoIssue:
        self.db.add(issue)
        self.db.flush()
        self.db.refresh(issue)
        return issue

    def get(self, practice_id: uuid.UUID, issue_id: uuid.UUID) -> RiordinoIssue | None:
        return self.db.scalar(select(RiordinoIssue).where(RiordinoIssue.practice_id == practice_id, RiordinoIssue.id == issue_id))

    def list(
        self,
        practice_id: uuid.UUID,
        *,
        severity: str | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> list[RiordinoIssue]:
        stmt = select(RiordinoIssue).where(RiordinoIssue.practice_id == practice_id)
        if severity:
            stmt = stmt.where(RiordinoIssue.severity == severity)
        if status:
            stmt = stmt.where(RiordinoIssue.status == status)
        if category:
            stmt = stmt.where(RiordinoIssue.category == category)
        return list(self.db.scalars(stmt.order_by(RiordinoIssue.created_at.desc())))
