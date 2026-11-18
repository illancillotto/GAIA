"""Daily meal vouchers from recognized overtime, dated profiles and audited grants."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.modules.presenze.models import PresenzeDailyRecord
from app.modules.presenze.services.manual_presence import lock_for_manual_benefit
from app.modules.presenze.services.meal_voucher_audit import record_manual_meal_voucher_change
from app.modules.presenze.services.shift_voucher_policy import shift_voucher_profile
from app.modules.presenze.services.shift_worker_rules import (
    shift_meal_voucher,
    shift_record_values,
)

AUTOMATIC_MEAL_VOUCHER_START = date(2026, 8, 26)


def meal_voucher_values(record: PresenzeDailyRecord, classification: Any) -> dict[str, Any]:
    automatic_source = automatic_meal_voucher_source(record, classification)
    manual = bool(getattr(record, "meal_voucher_manual", False))
    sources = ((automatic_source, bool(automatic_source)), ("manual", manual))
    return {
        **shift_record_values(record),
        "meal_voucher_shift": automatic_source == "shift",
        "meal_voucher_manual": manual,
        "meal_voucher_automatic": automatic_source is not None,
        "meal_voucher_count": int(automatic_source is not None or manual),
        "meal_voucher_sources": [source for source, enabled in sources if enabled],
    }


def automatic_meal_voucher_source(record: PresenzeDailyRecord, classification: Any) -> str | None:
    """Shift entitlement replaces the extra-hours rule; it never falls back to it."""
    if shift_voucher_profile(record):
        return "shift" if shift_meal_voucher(record) else None
    qualifies = all((
        record.work_date >= AUTOMATIC_MEAL_VOUCHER_START,
        (getattr(classification, "ordinary_minutes", None) or 0) > 0,
        (getattr(classification, "extra_minutes", None) or 0) >= 120,
    ))
    return "automatic" if qualifies else None


def apply_manual_meal_voucher(
    db: Session, record: PresenzeDailyRecord, enabled: bool | None, actor_id: int
) -> None:
    """Preserve the GAIA web API while sharing the locked operation with GATE."""
    apply_audited_manual_meal_voucher(db, record, enabled, actor_id, "gaia_web")


def apply_audited_manual_meal_voucher(
    db: Session, record: PresenzeDailyRecord, enabled: bool | None, actor_id: int, source: str
) -> None:
    if enabled is None:
        return
    locked = lock_for_manual_benefit(db, record, require_punch=enabled)
    record_manual_meal_voucher_change(locked, enabled, actor_id, source)
