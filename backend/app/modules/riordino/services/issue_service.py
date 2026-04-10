"""Issue services."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.riordino.enums import EventType
from app.modules.riordino.models import RiordinoIssue
from app.modules.riordino.repositories import IssueRepository, PracticeRepository
from app.modules.riordino.services.common import create_event, utcnow


def create_issue(db: Session, practice_id: UUID, data: dict, current_user) -> RiordinoIssue:
    if not PracticeRepository(db).get(practice_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice not found")
    issue = RiordinoIssue(practice_id=practice_id, opened_by=current_user.id, **data)
    IssueRepository(db).add(issue)
    create_event(db, practice_id=practice_id, phase_id=issue.phase_id, step_id=issue.step_id, created_by=current_user.id, event_type=EventType.issue_opened)
    db.flush()
    return issue


def list_issues(db: Session, practice_id: UUID, *, severity: str | None = None, status_filter: str | None = None, category: str | None = None) -> list[RiordinoIssue]:
    return IssueRepository(db).list(practice_id, severity=severity, status=status_filter, category=category)


def close_issue(db: Session, practice_id: UUID, issue_id: UUID, resolution_notes: str, current_user) -> RiordinoIssue:
    issue = IssueRepository(db).get(practice_id, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    if current_user.role not in {"admin", "super_admin"} and issue.category not in {"technical", "cadastral"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Issue cannot be closed by current user")
    issue.status = "closed"
    issue.closed_at = utcnow()
    issue.resolution_notes = resolution_notes
    issue.version += 1
    create_event(db, practice_id=practice_id, phase_id=issue.phase_id, step_id=issue.step_id, created_by=current_user.id, event_type=EventType.issue_closed)
    db.flush()
    return issue
