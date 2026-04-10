"""Notification services."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.riordino.enums import DEADLINE_THRESHOLDS
from app.modules.riordino.models import RiordinoNotification, RiordinoStep
from app.modules.riordino.services.common import utcnow


def _notification_exists(db: Session, user_id: int, practice_id, message: str) -> bool:
    existing = db.scalar(
        select(RiordinoNotification).where(
            RiordinoNotification.user_id == user_id,
            RiordinoNotification.practice_id == practice_id,
            RiordinoNotification.message == message,
        )
    )
    return existing is not None


def check_deadlines(db: Session) -> list[RiordinoNotification]:
    now = utcnow()
    created: list[RiordinoNotification] = []
    steps = list(db.scalars(select(RiordinoStep).where(RiordinoStep.status.in_(["todo", "in_progress"]))))
    decree_by_practice = {
        step.practice_id: step.completed_at
        for step in steps
        if step.code == "F1_RISOLUZIONE" and step.completed_at
    }

    for step in steps:
        deadline = step.due_at
        thresholds = DEADLINE_THRESHOLDS["default"]
        if step.code == "F1_OSSERVAZIONI" and step.started_at:
            deadline = step.started_at + timedelta(days=90)
            thresholds = DEADLINE_THRESHOLDS["F1_OSSERVAZIONI"]
        elif step.code == "F1_TRASCRIZIONE" and decree_by_practice.get(step.practice_id):
            deadline = decree_by_practice[step.practice_id] + timedelta(days=30)
            thresholds = DEADLINE_THRESHOLDS["F1_TRASCRIZIONE"]
        if not deadline or not step.owner_user_id:
            continue
        days_left = (deadline.date() - now.date()).days
        if days_left not in thresholds:
            continue
        message = f"Scadenza step {step.code} tra {days_left} giorni"
        if _notification_exists(db, step.owner_user_id, step.practice_id, message):
            continue
        notification = RiordinoNotification(
            user_id=step.owner_user_id,
            practice_id=step.practice_id,
            type="deadline_warning",
            message=message,
        )
        db.add(notification)
        created.append(notification)
    db.flush()
    return created


def list_notifications(db: Session, user_id: int) -> list[RiordinoNotification]:
    return list(
        db.scalars(
            select(RiordinoNotification)
            .where(RiordinoNotification.user_id == user_id)
            .order_by(RiordinoNotification.is_read.asc(), RiordinoNotification.created_at.desc())
        )
    )


def mark_read(db: Session, notification_id, user_id: int) -> RiordinoNotification:
    notification = db.get(RiordinoNotification, notification_id)
    if not notification or notification.user_id != user_id:
        raise ValueError("Notification not found")
    notification.is_read = True
    db.flush()
    return notification
