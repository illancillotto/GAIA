from __future__ import annotations

import pytest

from app.modules.presenze.services.operai_recognized_minutes import (
    DayMinuteInterval,
    recognize_operai_day,
)


@pytest.mark.parametrize(("start", "end"), [(60, 60), (120, 60), (-1, 60), (0, 1441)])
def test_rejects_invalid_or_overnight_intervals(start: int, end: int) -> None:
    with pytest.raises(ValueError, match="intervallo completo"):
        DayMinuteInterval(start, end)


@pytest.mark.parametrize("step", [0, 5, 30])
def test_requires_an_explicit_supported_rounding_rule(step: int) -> None:
    with pytest.raises(ValueError, match="quarti interi"):
        recognize_operai_day(
            (), shift=DayMinuteInterval(420, 840), overtime_step_minutes=step, unpaid_intervals=()
        )


@pytest.mark.parametrize(("exit_minute", "extra"), [(840, 0), (850, 0), (854, 0), (855, 15)])
def test_exit_examples_do_not_credit_early_arrival(exit_minute: int, extra: int) -> None:
    punches = (DayMinuteInterval(400, exit_minute),)
    result = recognize_operai_day(
        punches,
        shift=DayMinuteInterval(420, 840),
        overtime_step_minutes=1,
        unpaid_intervals=(),
    )
    assert result.ordinary_minutes == 420
    assert result.overtime_minutes == extra
    assert result.excluded_early_minutes == 20
    assert result.excluded_overtime_minutes == exit_minute - 840 - extra
    assert result.ordinary_night_minutes == 0
    assert punches == (DayMinuteInterval(400, exit_minute),)


@pytest.mark.parametrize(("step", "extra"), [(1, 20), (15, 15)])
def test_1420_is_controlled_by_the_supplied_rounding_rule(step: int, extra: int) -> None:
    result = recognize_operai_day(
        (DayMinuteInterval(420, 860),),
        shift=DayMinuteInterval(420, 840),
        overtime_step_minutes=step,
        unpaid_intervals=(),
    )
    assert result.overtime_minutes == extra


@pytest.mark.parametrize(
    ("shift_start", "entry", "night", "early"), [(330, 315, 30, 15), (360, 347, 0, 13)]
)
def test_night_depends_on_the_shift_not_the_early_punch(
    shift_start: int, entry: int, night: int, early: int
) -> None:
    result = recognize_operai_day(
        (DayMinuteInterval(entry, shift_start + 420),),
        shift=DayMinuteInterval(shift_start, shift_start + 420),
        overtime_step_minutes=1,
        unpaid_intervals=(),
    )
    assert result.ordinary_night_minutes == night
    assert result.excluded_early_minutes == early
    assert result.ordinary_minutes == 420
    assert result.overtime_minutes == 0


@pytest.mark.parametrize("timbrata", [False, True])
def test_three_hour_extension_excludes_lunch_exactly_once(timbrata: bool) -> None:
    punches = (
        (DayMinuteInterval(420, 840), DayMinuteInterval(870, 1020))
        if timbrata
        else (DayMinuteInterval(420, 1020),)
    )
    result = recognize_operai_day(
        punches,
        shift=DayMinuteInterval(420, 840),
        overtime_step_minutes=1,
        unpaid_intervals=(DayMinuteInterval(840, 870),),
    )
    assert result.ordinary_minutes == 420
    assert result.overtime_minutes == 150
    assert result.missing_minutes == 0
    assert result.excluded_break_minutes == (0 if timbrata else 30)


def test_overlapping_pairs_do_not_duplicate_paid_minutes() -> None:
    result = recognize_operai_day(
        (DayMinuteInterval(420, 720), DayMinuteInterval(600, 855)),
        shift=DayMinuteInterval(420, 840),
        overtime_step_minutes=1,
        unpaid_intervals=(),
    )
    assert result.ordinary_minutes == 420
    assert result.overtime_minutes == 15


def test_early_arrival_cannot_cover_an_early_exit() -> None:
    result = recognize_operai_day(
        (DayMinuteInterval(400, 820),),
        shift=DayMinuteInterval(420, 840),
        overtime_step_minutes=1,
        unpaid_intervals=(),
    )
    assert result.ordinary_minutes == 400
    assert result.missing_minutes == 20
    assert result.excluded_early_minutes == 20
    assert result.overtime_minutes == 0


def test_explicit_absence_is_not_credited_as_presence() -> None:
    result = recognize_operai_day(
        (),
        shift=DayMinuteInterval(420, 840),
        overtime_step_minutes=1,
        unpaid_intervals=(),
    )
    assert result.ordinary_minutes == result.overtime_minutes == 0
    assert result.missing_minutes == 420
