from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.core.capacitas_autosync_settings import CapacitasAutoSyncSettings
from app.modules.elaborazioni import domande_irrigue_autosync_scheduler as scheduler
from app.modules.elaborazioni.autosync_windows import window_context


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [
        ("2026-10-07T02:59:59", False),
        ("2026-10-07T03:00:00", True),
        ("2026-10-07T05:29:59", True),
        ("2026-10-07T05:30:00", False),
        ("2026-10-07T14:59:59", False),
        ("2026-10-07T15:00:00", True),
        ("2026-10-07T16:59:59", True),
        ("2026-10-07T17:00:00", False),
        ("2026-11-07T04:00:00", True),
        ("2026-11-07T06:30:00", False),
    ],
)
def test_split_windows_in_rome(monkeypatch, timestamp, expected):
    monkeypatch.setattr(
        scheduler.settings, "capacitas_domande_irrigue_autosync_windows", "05:00-07:30,17:00-19:00"
    )
    monkeypatch.setattr(
        scheduler.settings, "capacitas_domande_irrigue_autosync_window_enabled", True
    )
    monkeypatch.setattr(
        scheduler.settings, "capacitas_domande_irrigue_autosync_timezone", "Europe/Rome"
    )
    assert scheduler._window_context(datetime.fromisoformat(timestamp).replace(tzinfo=UTC)) == (
        expected,
        timestamp[:10],
    )


@pytest.mark.parametrize(
    ("windows", "hour", "expected"),
    [
        ("18:00-07:00", 20, (True, "2026-10-07")),
        ("18:00-07:00", 3, (True, "2026-10-06")),
        ("18:00-07:00", 12, (False, "2026-10-07")),
        ("00:00-00:00", 12, (True, "2026-10-07")),
    ],
)
def test_legacy_overnight_and_all_day(windows, hour, expected):
    assert window_context(datetime(2026, 10, 7, hour), windows) == expected


@pytest.mark.parametrize("windows", ["", "05:00-07:30,17:00-19:00", "18:00-07:00"])
def test_settings_accept_valid_windows(windows):
    config = CapacitasAutoSyncSettings(CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_WINDOWS=windows)
    assert config.capacitas_domande_irrigue_autosync_windows == windows


@pytest.mark.parametrize(
    "windows", ["25:00-07:30", "05:60-07:30", "05:00", "5:00-7:30", "05:00-07:30,"]
)
def test_settings_reject_invalid_windows(windows):
    with pytest.raises(ValidationError):
        CapacitasAutoSyncSettings(CAPACITAS_DOMANDE_IRRIGUE_AUTOSYNC_WINDOWS=windows)
