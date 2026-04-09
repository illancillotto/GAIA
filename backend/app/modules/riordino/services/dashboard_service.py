"""Dashboard services."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.riordino.enums import IssueSeverity
from app.modules.riordino.models import RiordinoEvent, RiordinoIssue, RiordinoPractice


def get_summary(db: Session, recent_limit: int = 10) -> dict:
    practices_by_status = {
        row[0]: row[1]
        for row in db.execute(
            select(RiordinoPractice.status, func.count(RiordinoPractice.id))
            .where(RiordinoPractice.deleted_at.is_(None))
            .group_by(RiordinoPractice.status)
        )
    }
    practices_by_phase = {
        row[0]: row[1]
        for row in db.execute(
            select(RiordinoPractice.current_phase, func.count(RiordinoPractice.id))
            .where(RiordinoPractice.deleted_at.is_(None))
            .group_by(RiordinoPractice.current_phase)
        )
    }
    blocking_issues_open = db.scalar(
        select(func.count(RiordinoIssue.id)).where(
            RiordinoIssue.severity == IssueSeverity.blocking.value,
            RiordinoIssue.status != "closed",
        )
    ) or 0
    recent_events = list(db.scalars(select(RiordinoEvent).order_by(RiordinoEvent.created_at.desc()).limit(recent_limit)))
    return {
        "practices_by_status": practices_by_status,
        "practices_by_phase": practices_by_phase,
        "blocking_issues_open": blocking_issues_open,
        "recent_events": recent_events,
    }
