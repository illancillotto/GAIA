"""Issue routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.riordino.schemas import IssueCloseRequest, IssueCreate, IssueResponse
from app.modules.riordino.services import close_issue, create_issue, list_issues

router = APIRouter(dependencies=[Depends(require_module("riordino")), Depends(require_section("riordino.issues"))])


@router.post("/{practice_id}/issues", response_model=IssueResponse)
def create_issue_endpoint(
    practice_id: UUID,
    payload: IssueCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    issue = create_issue(db, practice_id, payload.model_dump(), current_user)
    db.commit()
    db.refresh(issue)
    return issue


@router.get("/{practice_id}/issues", response_model=list[IssueResponse])
def list_issues_endpoint(
    practice_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    severity: str | None = None,
    status_filter: str | None = None,
    category: str | None = None,
):
    return [IssueResponse.model_validate(item) for item in list_issues(db, practice_id, severity=severity, status_filter=status_filter, category=category)]


@router.post("/{practice_id}/issues/{issue_id}/close", response_model=IssueResponse)
def close_issue_endpoint(
    practice_id: UUID,
    issue_id: UUID,
    payload: IssueCloseRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    issue = close_issue(db, practice_id, issue_id, payload.resolution_notes, current_user)
    db.commit()
    db.refresh(issue)
    return issue
