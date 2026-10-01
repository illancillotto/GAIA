"""Daily meal vouchers: the existing automatic rule plus an audited manual grant."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.presenze.models import PresenzeDailyRecord
from app.modules.presenze.services.meal_voucher_audit import record_manual_meal_voucher_change

AUTOMATIC_MEAL_VOUCHER_START = date(2026, 8, 26)
AUTOMATIC_MEAL_VOUCHER_EXTRA_MINUTES = 120


def meal_voucher_values(record: PresenzeDailyRecord, extra_minutes: int | None) -> dict[str, Any]:
    automatic = (
        record.work_date >= AUTOMATIC_MEAL_VOUCHER_START
        and (extra_minutes or 0) >= AUTOMATIC_MEAL_VOUCHER_EXTRA_MINUTES
    )
    manual = bool(getattr(record, "meal_voucher_manual", False))
    sources = [
        source for source, enabled in (("automatic", automatic), ("manual", manual)) if enabled
    ]
    return {
        "meal_voucher_manual": manual,
        "meal_voucher_automatic": automatic,
        "meal_voucher_count": int(automatic or manual),
        "meal_voucher_sources": sources,
    }


def apply_manual_meal_voucher(
    db: Session, record: PresenzeDailyRecord, enabled: bool | None, actor_id: int
) -> None:
    if enabled is None:
        return
    locked = lock_manual_meal_voucher_record(db, record)
    record_manual_meal_voucher_change(locked, enabled, actor_id, "gaia_web")


def lock_manual_meal_voucher_record(
    db: Session, record: PresenzeDailyRecord
) -> PresenzeDailyRecord:
    return db.scalars(
        select(PresenzeDailyRecord)
        .where(PresenzeDailyRecord.id == record.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()
