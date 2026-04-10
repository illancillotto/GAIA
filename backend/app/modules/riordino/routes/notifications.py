"""Notification routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.riordino.schemas import NotificationResponse
from app.modules.riordino.services import check_deadlines, list_notifications, mark_read

router = APIRouter(dependencies=[Depends(require_module("riordino")), Depends(require_section("riordino.notifications"))])


@router.get("", response_model=list[NotificationResponse])
def list_notifications_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return [NotificationResponse.model_validate(item) for item in list_notifications(db, current_user.id)]


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read_endpoint(
    notification_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        notification = mark_read(db, notification_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/check-deadlines", response_model=list[NotificationResponse])
def check_deadlines_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    notifications = check_deadlines(db)
    db.commit()
    return [NotificationResponse.model_validate(item) for item in notifications]
