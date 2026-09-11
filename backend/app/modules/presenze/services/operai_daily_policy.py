"""Daily operaio payroll policy, separate from imported INAZ punch data."""

from __future__ import annotations

from datetime import time

from app.modules.presenze.models import PresenzeDailyPunch, PresenzeDailyRecord
from app.modules.presenze.services.operai_recognized_minutes import (
    DayMinuteInterval,
    RecognizedOperaiMinutes,
    recognize_operai_day,
)
from app.modules.presenze.services.operai_rules import ResolvedOperaiRule

# Nominal starts from the INAZ schedule definitions. An assigned daily rule
# takes precedence, including seasonal shifts. Duration comes from operai_group.
SCHEDULE_STARTS = {
    "OPE0714": 420,
    "OPE0613": 360,
    "OPE0736": 380,
    "OP_5.3_12.3": 330,
    "OPESAB": 420,
    "OSAB5.3_12.3": 330,
}


def recognized_daily_minutes(
    punches: list[PresenzeDailyPunch],
    rule: ResolvedOperaiRule,
    *,
    scheduled_start: time | None = None,
) -> RecognizedOperaiMinutes | None:
    start = (
        _minute(scheduled_start)
        if scheduled_start is not None
        else SCHEDULE_STARTS.get(rule.formula_code)
    )
    if start is None or rule.expected_minutes <= 0:
        return None
    end = start + rule.expected_minutes
    pairs = _complete_day_pairs(punches)
    if not pairs or end > 1440:
        return None
    unpaid = _lunch_intervals(pairs, start, rule.expected_minutes)
    return recognize_operai_day(
        pairs,
        shift=DayMinuteInterval(start, end),
        overtime_step_minutes=1,
        unpaid_intervals=unpaid,
    )


def _minute(value: time) -> int:
    return value.hour * 60 + value.minute


def _complete_day_pairs(punches: list[PresenzeDailyPunch]) -> tuple[DayMinuteInterval, ...]:
    pairs = []
    for punch in punches:
        if punch.entry_time is None or punch.exit_time is None:
            return ()
        start, end = _minute(punch.entry_time), _minute(punch.exit_time)
        if end <= start:
            return ()
        pairs.append(DayMinuteInterval(start, end))
    return tuple(pairs)


def _lunch_intervals(
    punches: tuple[DayMinuteInterval, ...], shift_start: int, expected: int
) -> tuple[DayMinuteInterval, ...]:
    worked = sorted(
        {minute for pair in punches for minute in pair.minutes() if minute >= shift_start}
    )
    if len(worked) <= expected:
        return ()
    standard_end = worked[expected - 1] + 1
    # The agreed trigger is the fixed local exit time 16:00, inclusive,
    # regardless of the shift end. The unpaid interval still follows the
    # completion of standard hours and is excluded exactly once.
    if max(pair.end for pair in punches) < 16 * 60:
        return ()
    return (DayMinuteInterval(standard_end, min(standard_end + 30, 1440)),)


def recognized_extra_minutes(record: PresenzeDailyRecord, minutes: RecognizedOperaiMinutes) -> int:
    # Explicit adjustments are the existing administrative authorization path.
    # Imported STR/MPE values cannot restore excluded early/unpaid minutes.
    mpe = record.override_mpe_minutes
    return max(0, minutes.overtime_minutes if mpe is None else mpe) + max(
        0, record.override_straordinario_minutes or 0
    )


def effective_extra_values(record: PresenzeDailyRecord, classification: object) -> dict:
    straordinario = (
        record.straordinario_minutes
        if record.override_straordinario_minutes is None
        else record.override_straordinario_minutes
    )
    mpe = record.mpe_minutes if record.override_mpe_minutes is None else record.override_mpe_minutes
    if getattr(classification, "recognized_minutes", None) is not None:
        extra = classification.extra_minutes
        straordinario = max(0, record.override_straordinario_minutes or 0)
        mpe = extra - straordinario
    else:
        extra = (straordinario or 0) + (mpe or 0) or None
    values = {
        "effective_straordinario_minutes": straordinario,
        "effective_mpe_minutes": mpe,
        "effective_extra_minutes": extra,
    }
    if getattr(classification, "recognized_minutes", None) is not None:
        values["operational_mpe_minutes"] = mpe
        values["ordinary_minutes"] = classification.ordinary_minutes
    return values


def classified_extra_minutes(imported: int, classification: object) -> int:
    if getattr(classification, "recognized_minutes", None) is not None:
        return classification.extra_minutes or 0
    return max(imported, classification.extra_minutes or 0)
