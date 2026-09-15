"""Persistent retry scope and quarantine for attempts with an uncertain outcome."""

from collections.abc import Iterable
from datetime import date
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.modules.presenze.services.punch_reminders import ReminderDayInput, reminder_day
from app.modules.presenze.whatsapp_models import (
    PresenzeWhatsAppMessage,
    PresenzeWhatsAppPendingDay,
)

UNCERTAIN_STATUSES = {"SENDING", "UNKNOWN"}


def pending_keys(db: Session) -> set[tuple[UUID, date]]:
    return set(
        db.execute(
            select(PresenzeWhatsAppPendingDay.collaborator_id, PresenzeWhatsAppPendingDay.work_date)
        ).all()
    )


def blocked_days(db: Session) -> set[tuple[UUID, date]]:
    return set(
        db.execute(
            select(PresenzeWhatsAppPendingDay.collaborator_id, PresenzeWhatsAppPendingDay.work_date)
            .join(
                PresenzeWhatsAppMessage,
                PresenzeWhatsAppMessage.id == PresenzeWhatsAppPendingDay.last_message_id,
            )
            .where(PresenzeWhatsAppMessage.status.in_(UNCERTAIN_STATUSES))
        ).all()
    )


def remember_days(db: Session, keys: Iterable[tuple[UUID, date]]) -> None:
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert
    for collaborator_id, work_date in keys:
        db.execute(
            insert(PresenzeWhatsAppPendingDay)
            .values(collaborator_id=collaborator_id, work_date=work_date)
            .on_conflict_do_nothing()
        )


def reconcile_pending(
    db: Session,
    items: Iterable[ReminderDayInput],
    *,
    include_missing: bool,
    notified: frozenset[tuple[UUID, date]],
) -> None:
    eligible = {
        (item.collaborator_id, item.work_date)
        for item in items
        if reminder_day(item, include_missing_punches=include_missing) is not None
    } - notified
    for collaborator_id, work_date in pending_keys(db) - eligible - blocked_days(db):
        db.execute(
            delete(PresenzeWhatsAppPendingDay).where(
                PresenzeWhatsAppPendingDay.collaborator_id == collaborator_id,
                PresenzeWhatsAppPendingDay.work_date == work_date,
            )
        )
    remember_days(db, eligible)
    db.commit()


def link_attempt(db: Session, message: PresenzeWhatsAppMessage) -> None:
    keys = [
        (message.collaborator_id, date.fromisoformat(day["work_date"])) for day in message.days_json
    ]
    remember_days(db, keys)
    for key in keys:
        pending = db.get(PresenzeWhatsAppPendingDay, key)
        pending.last_message_id = message.id


def forget_message_days(db: Session, message_id: UUID) -> None:
    db.execute(
        delete(PresenzeWhatsAppPendingDay).where(
            PresenzeWhatsAppPendingDay.last_message_id == message_id
        )
    )
