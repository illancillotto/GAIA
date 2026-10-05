"""Shared classified-day result for ordinary schedules and CCNL shifts."""

from dataclasses import dataclass

from app.modules.presenze.services.operai_recognized_minutes import RecognizedOperaiMinutes
from app.modules.presenze.services.operai_schedule_policy import OperaiDayPolicy


@dataclass(frozen=True)
class DayClassification:
    special_day: bool
    ordinary_minutes: int | None
    extra_minutes: int | None
    holiday_kind: str | None
    grants_recovery_day: bool
    source: str
    night_minutes: int = 0
    festive_minutes: int = 0
    festive_night_minutes: int = 0
    ordinary_night_minutes: int = 0
    overtime_day_minutes: int = 0
    overtime_night_minutes: int = 0
    overtime_festive_minutes: int = 0
    overtime_festive_night_minutes: int = 0
    shift_festive_day_minutes: int = 0
    shift_night_minutes: int = 0
    shift_festive_night_minutes: int = 0
    recognized_minutes: RecognizedOperaiMinutes | None = None
    operai_day_policy: OperaiDayPolicy | None = None
    shift_calendar: list[bool] | None = None
    shift_ccnl: dict | None = None
