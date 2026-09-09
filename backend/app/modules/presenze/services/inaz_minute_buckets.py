"""Keep INAZ's accounted minutes authoritative over raw punch durations."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from app.modules.presenze.services.contract_profile import resolve_contract_profile

if TYPE_CHECKING:
    from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyRecord
    from app.modules.presenze.services.schedule_engine import WorkedMinuteBuckets


def inaz_special_day(
    record: PresenzeDailyRecord,
    collaborator: PresenzeCollaborator,
    special_day: bool,
    holiday_kind: str | None,
) -> bool:
    """An ordinary, scheduled operaio Saturday is not automatically festive."""
    profile = resolve_contract_profile(
        collaborator.contract_kind, None, schedule_codes=[record.schedule_code]
    )
    scheduled_saturday = (
        record.work_date.weekday() == 5
        and profile.contract_kind == "operaio"
        and (record.ordinary_minutes or 0) > 0
        and (record.schedule_code or "").strip().upper() not in {"", "SAB", "DOM", "RIPTURN"}
        and holiday_kind != "ordinary"
    )
    return special_day and not scheduled_saturday


def reconcile_inaz_minute_buckets(
    buckets: WorkedMinuteBuckets,
    ordinary_minutes: int | None,
    extra_minutes: int | None,
    *,
    special_day: bool,
) -> WorkedMinuteBuckets:
    """Use a timed breakdown only when it agrees with INAZ's accounted totals.

    Early punches and missing local schedules cannot create extra paid minutes
    or night premiums. Without a matching breakdown, retain the imported totals
    in the day's ordinary/extra category, without inventing night attribution.
    """
    ordinary = ordinary_minutes or 0
    extra = extra_minutes or 0
    if (buckets.ordinary_minutes, buckets.extra_minutes) == (ordinary, extra):
        return buckets
    return replace(
        buckets,
        ordinary_minutes=ordinary,
        extra_minutes=extra,
        night_minutes=0,
        festive_minutes=ordinary + extra if special_day else 0,
        festive_night_minutes=0,
        ordinary_night_minutes=0,
        overtime_day_minutes=0 if special_day else extra,
        overtime_night_minutes=0,
        overtime_festive_minutes=extra if special_day else 0,
        overtime_festive_night_minutes=0,
        shift_festive_day_minutes=ordinary if special_day else 0,
        shift_night_minutes=0,
        shift_festive_night_minutes=0,
    )
