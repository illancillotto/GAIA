"""Shared service helpers for Riordino."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.riordino.enums import EventType
from app.modules.riordino.models import RiordinoEvent


ADMIN_ROLES = {"admin", "super_admin"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def require_admin_like(user: ApplicationUser) -> None:
    if user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operation requires admin role")


def create_event(
    db: Session,
    *,
    practice_id,
    created_by: int,
    event_type: str | EventType,
    phase_id=None,
    step_id=None,
    payload_json: dict | None = None,
) -> RiordinoEvent:
    event = RiordinoEvent(
        practice_id=practice_id,
        phase_id=phase_id,
        step_id=step_id,
        event_type=event_type.value if isinstance(event_type, EventType) else event_type,
        payload_json=payload_json,
        created_by=created_by,
    )
    db.add(event)
    db.flush()
    return event
