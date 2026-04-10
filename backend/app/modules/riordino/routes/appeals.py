"""Appeal routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.riordino.schemas import AppealCreate, AppealResolveRequest, AppealResponse, AppealUpdate
from app.modules.riordino.services import create_appeal, list_appeals, resolve_appeal, update_appeal

router = APIRouter(dependencies=[Depends(require_module("riordino")), Depends(require_section("riordino.appeals"))])


@router.post("/{practice_id}/appeals", response_model=AppealResponse)
def create_appeal_endpoint(
    practice_id: UUID,
    payload: AppealCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    appeal = create_appeal(db, practice_id, payload.model_dump(), current_user)
    db.commit()
    db.refresh(appeal)
    return appeal


@router.get("/{practice_id}/appeals", response_model=list[AppealResponse])
def list_appeals_endpoint(
    practice_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status: str | None = None,
):
    return [AppealResponse.model_validate(item) for item in list_appeals(db, practice_id, status)]


@router.patch("/{practice_id}/appeals/{appeal_id}", response_model=AppealResponse)
def update_appeal_endpoint(
    practice_id: UUID,
    appeal_id: UUID,
    payload: AppealUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    appeal = update_appeal(db, practice_id, appeal_id, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(appeal)
    return appeal


@router.post("/{practice_id}/appeals/{appeal_id}/resolve", response_model=AppealResponse)
def resolve_appeal_endpoint(
    practice_id: UUID,
    appeal_id: UUID,
    payload: AppealResolveRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    appeal = resolve_appeal(db, practice_id, appeal_id, payload.model_dump(), current_user)
    db.commit()
    db.refresh(appeal)
    return appeal
