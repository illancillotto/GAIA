"""Recognize an ordinary daytime operaio shift from an explicitly resolved schedule.

This calculation does not infer shifts or authorize early work. The daily policy
supplies the approved shift, minute accounting and unpaid intervals. Raw punches
are preserved; payable extra begins after the standard hours have been completed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DayMinuteInterval:
    start: int
    end: int

    def __post_init__(self) -> None:
        if not 0 <= self.start < self.end <= 24 * 60:
            raise ValueError("Serve un intervallo completo nella stessa giornata")

    def minutes(self) -> set[int]:
        return set(range(self.start, self.end))


@dataclass(frozen=True)
class RecognizedOperaiMinutes:
    ordinary_minutes: int
    overtime_minutes: int
    ordinary_night_minutes: int
    missing_minutes: int
    excluded_early_minutes: int
    excluded_break_minutes: int
    excluded_overtime_minutes: int


def recognize_operai_day(
    punches: tuple[DayMinuteInterval, ...],
    *,
    shift: DayMinuteInterval,
    overtime_step_minutes: int,
    unpaid_intervals: tuple[DayMinuteInterval, ...],
) -> RecognizedOperaiMinutes:
    """Count complete daytime pairs; absence/authorization handling is external.

    An empty tuple means an explicitly absent employee, not missing punch data.
    A caller with incomplete punches or no attested shift must not invoke this
    calculation to manufacture a publishable daily record.
    """
    if overtime_step_minutes not in {1, 15}:
        raise ValueError("Precisare conteggio al minuto oppure a quarti interi")
    actual = _interval_minutes(punches)
    unpaid = _interval_minutes(unpaid_intervals)
    expected = len(shift.minutes() - unpaid)
    eligible = {minute for minute in actual if minute >= shift.start} - unpaid
    ordinary = set(sorted(eligible)[:expected])
    eligible_tail = eligible - ordinary
    overtime = _recognized_overtime(len(eligible_tail), overtime_step_minutes)
    night = ordinary & set(range(330, 360)) if shift.start == 330 else set()
    return RecognizedOperaiMinutes(
        ordinary_minutes=len(ordinary),
        overtime_minutes=overtime,
        ordinary_night_minutes=len(night),
        missing_minutes=max(0, expected - len(ordinary)),
        excluded_early_minutes=len({minute for minute in actual if minute < shift.start}),
        excluded_break_minutes=len(actual & unpaid),
        excluded_overtime_minutes=len(eligible_tail) - overtime,
    )


def _interval_minutes(intervals: tuple[DayMinuteInterval, ...]) -> set[int]:
    return {minute for interval in intervals for minute in interval.minutes()}


def _recognized_overtime(minutes: int, step: int) -> int:
    if minutes < 15:
        return 0
    return minutes // step * step
