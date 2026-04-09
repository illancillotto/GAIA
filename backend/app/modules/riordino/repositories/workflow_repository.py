"""Workflow repository helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.riordino.enums import IssueSeverity
from app.modules.riordino.models import (
    RiordinoChecklistItem,
    RiordinoDocument,
    RiordinoIssue,
    RiordinoPhase,
    RiordinoPractice,
    RiordinoStep,
)


class WorkflowRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_phase(self, practice_id: uuid.UUID, phase_id: uuid.UUID) -> RiordinoPhase | None:
        return self.db.scalar(
            select(RiordinoPhase)
            .options(selectinload(RiordinoPhase.steps))
            .where(RiordinoPhase.id == phase_id, RiordinoPhase.practice_id == practice_id)
        )

    def get_step(self, practice_id: uuid.UUID, step_id: uuid.UUID) -> RiordinoStep | None:
        return self.db.scalar(
            select(RiordinoStep)
            .options(
                selectinload(RiordinoStep.issues),
                selectinload(RiordinoStep.documents),
                selectinload(RiordinoStep.checklist_items),
                selectinload(RiordinoStep.phase),
                selectinload(RiordinoStep.practice),
            )
            .where(RiordinoStep.id == step_id, RiordinoStep.practice_id == practice_id)
        )

    def has_documents_for_step(self, step_id: uuid.UUID) -> bool:
        count = self.db.scalar(
            select(func.count(RiordinoDocument.id)).where(
                RiordinoDocument.step_id == step_id,
                RiordinoDocument.deleted_at.is_(None),
            )
        ) or 0
        return count > 0

    def open_blocking_issues_for_step(self, step_id: uuid.UUID) -> list[RiordinoIssue]:
        return list(
            self.db.scalars(
                select(RiordinoIssue).where(
                    RiordinoIssue.step_id == step_id,
                    RiordinoIssue.severity == IssueSeverity.blocking.value,
                    RiordinoIssue.status != "closed",
                )
            )
        )

    def open_blocking_issues_for_phase(self, phase_id: uuid.UUID) -> list[RiordinoIssue]:
        return list(
            self.db.scalars(
                select(RiordinoIssue).where(
                    RiordinoIssue.phase_id == phase_id,
                    RiordinoIssue.severity == IssueSeverity.blocking.value,
                    RiordinoIssue.status != "closed",
                )
            )
        )

    def blocking_checklist_for_step(self, step_id: uuid.UUID) -> list[RiordinoChecklistItem]:
        return list(
            self.db.scalars(
                select(RiordinoChecklistItem).where(
                    RiordinoChecklistItem.step_id == step_id,
                    RiordinoChecklistItem.is_blocking.is_(True),
                    RiordinoChecklistItem.is_checked.is_(False),
                )
            )
        )

    def auto_skip_branch(self, practice_id: uuid.UUID, branch: str, reason: str) -> list[RiordinoStep]:
        steps = list(
            self.db.scalars(
                select(RiordinoStep).where(
                    RiordinoStep.practice_id == practice_id,
                    RiordinoStep.branch == branch,
                    RiordinoStep.status.in_(["todo", "in_progress", "blocked"]),
                )
            )
        )
        for step in steps:
            step.status = "skipped"
            step.skip_reason = reason
            step.version += 1
        return steps

    def phase_steps(self, phase_id: uuid.UUID) -> list[RiordinoStep]:
        return list(
            self.db.scalars(select(RiordinoStep).where(RiordinoStep.phase_id == phase_id).order_by(RiordinoStep.sequence_no))
        )
