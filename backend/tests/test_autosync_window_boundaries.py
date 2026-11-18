from datetime import datetime

import pytest

from app.modules.elaborazioni.autosync_windows import window_context


@pytest.mark.parametrize(
    ("timestamp", "windows", "expected"),
    [
        ("2026-01-01T17:59:59.999999", "18:00-07:00", (False, "2026-01-01")),
        ("2026-01-01T18:00:00", "18:00-07:00", (True, "2026-01-01")),
        ("2026-01-01T23:59:59.999999", "18:00-07:00", (True, "2026-01-01")),
        ("2026-01-01T00:00:00", "18:00-07:00", (True, "2025-12-31")),
        ("2026-01-01T06:59:59.999999", "18:00-07:00", (True, "2025-12-31")),
        ("2026-01-01T07:00:00", "18:00-07:00", (False, "2026-01-01")),
        ("2024-03-01T01:00:00", "18:00-07:00", (True, "2024-02-29")),
        ("2026-10-07T04:59:59.999999", "05:00-07:30", (False, "2026-10-07")),
        ("2026-10-07T05:00:00", "05:00-07:30", (True, "2026-10-07")),
        ("2026-10-07T07:29:59.999999", "05:00-07:30", (True, "2026-10-07")),
        ("2026-10-07T07:30:00", "05:00-07:30", (False, "2026-10-07")),
        ("2026-10-07T00:00:00", "07:30-07:30", (True, "2026-10-07")),
        ("2026-10-07T07:30:00", "07:30-07:30", (True, "2026-10-07")),
        ("2026-10-07T23:59:59.999999", "07:30-07:30", (True, "2026-10-07")),
        ("2026-10-07T06:00:00", "05:00-07:00,18:00-07:00", (True, "2026-10-07")),
        ("2026-10-07T06:00:00", "18:00-07:00,05:00-07:00", (True, "2026-10-06")),
        ("2026-10-07T20:00:00", "05:00-07:00,18:00-07:00", (True, "2026-10-07")),
        ("2026-10-07T02:00:00", "05:00-07:00,18:00-07:00", (True, "2026-10-06")),
        ("2026-10-07T12:00:00", "05:00-07:00,18:00-07:00", (False, "2026-10-07")),
        ("2026-10-07T12:00:00", "18:00-07:00,11:00-13:00", (True, "2026-10-07")),
        ("2026-10-07T12:00:00+02:00", "11:00-13:00", (True, "2026-10-07")),
        ("2026-10-07T06:00:00", "05:00-07:00,invalid", (True, "2026-10-07")),
        ("2026-10-07T06:00:00", "05:00-07:00,", (True, "2026-10-07")),
    ],
)
def test_window_boundaries_and_first_matching_cycle(timestamp, windows, expected):
    assert window_context(datetime.fromisoformat(timestamp), windows) == expected


@pytest.mark.parametrize("windows", ["", "invalid", "25:00-07:00", "05:00-07:00,invalid"])
def test_window_parsing_errors_remain_visible(windows):
    with pytest.raises(ValueError):
        window_context(datetime(2026, 10, 7, 12), windows)


def test_overnight_cycle_before_minimum_date_propagates_overflow():
    with pytest.raises(OverflowError):
        window_context(datetime.min, "18:00-07:00")
