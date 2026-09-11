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
from app.modules.presenze.services.parser import (
    extract_detail_payload,
    parse_schedule_code_from_detail,
)

# Nominal starts from the effective INAZ schedule. An unambiguous assignment
# is used when the imported day does not attest its own effective schedule.
SCHEDULE_STARTS = {
    "OPE0714": 420,
    "OPE0613": 360,
    "OPEF0613": 360,
    "OPE0736": 380,
    "OP_5.3_12.3": 330,
    "OPESAB": 420,
    "OSAB5.3_12.3": 330,
    "OPESACE": 360,
    "OPSABE": 360,
    "OSAB5.3_11.3": 330,
}


def assigned_daily_start(record, rule, starts):
    # The effective schedule of this imported day supersedes a generic
    # seasonal template (which may still contain the 05:30 summer shift).
    payload = record.raw_payload_json
    if isinstance(payload, dict):
        detail = extract_detail_payload(payload)
        effective_code = parse_schedule_code_from_detail(detail.get("effective_schedule"))
        if effective_code == rule.formula_code:
            return None
    return next(iter(starts)) if len(starts) == 1 else None


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
    pairs = _complete_day_pairs(punches)
    start = _effective_summer_start(start, rule.formula_code, pairs)
    end = start + rule.expected_minutes
    if not pairs or end > 1440:
        return None
    unpaid = _lunch_intervals(pairs, start, rule.expected_minutes)
    return recognize_operai_day(
        pairs,
        shift=DayMinuteInterval(start, end),
        overtime_step_minutes=1,
        unpaid_intervals=unpaid,
    )


def _effective_summer_start(start, code, pairs):
    # Operationally confirmed 07-14 -> 06-13 switch: the nominal INAZ code
    # can remain unchanged, as in the summer cases confirmed by the operator.
    if not pairs or code != "OPE0714" or start != 420:
        return start
    first = min(pair.start for pair in pairs)
    last = max(pair.end for pair in pairs)
    return 360 if 330 < first <= 360 and 780 <= last <= 1320 else start


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


# INAZ leaves a day unaccounted while a punch insertion awaits approval (RIC):
# the complete punches then carry the worked minutes shown and exported.
PENDING_PUNCH_REQUEST_SOURCE = "pending_punch_request"


def effective_extra_values(record: PresenzeDailyRecord, classification: object) -> dict:
    if getattr(classification, "recognized_minutes", None) is not None:
        straordinario = max(0, record.override_straordinario_minutes or 0)
        return _classified_extra_values(classification, straordinario, recognized=True)
    straordinario = _adjusted(record.straordinario_minutes, record.override_straordinario_minutes)
    if getattr(classification, "source", None) == PENDING_PUNCH_REQUEST_SOURCE:
        return _classified_extra_values(classification, straordinario or 0, recognized=False)
    mpe = _adjusted(record.mpe_minutes, record.override_mpe_minutes)
    return {
        "effective_straordinario_minutes": straordinario,
        "effective_mpe_minutes": mpe,
        "effective_extra_minutes": (straordinario or 0) + (mpe or 0) or None,
    }


def _adjusted(imported: int | None, override: int | None) -> int | None:
    return imported if override is None else override


def _classified_extra_values(classification: object, straordinario: int, *, recognized: bool) -> dict:
    extra = classification.extra_minutes
    values = {
        "effective_straordinario_minutes": straordinario,
        "effective_mpe_minutes": extra - straordinario,
        "effective_extra_minutes": extra,
        "ordinary_minutes": classification.ordinary_minutes,
    }
    if recognized:
        values["operational_mpe_minutes"] = extra - straordinario
    return values


def classified_extra_minutes(imported: int, classification: object) -> int:
    if getattr(classification, "recognized_minutes", None) is not None:
        return classification.extra_minutes or 0
    return max(imported, classification.extra_minutes or 0)
