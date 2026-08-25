from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SISTER_SCHEDULE_TIMEZONE = ZoneInfo("Europe/Rome")


def _minutes(value: str) -> int:
    hours, minutes = value.split(":", 1)
    return int(hours) * 60 + int(minutes)


def _weekly(schedule: dict | None) -> dict[str, list[dict[str, str]]]:
    if not isinstance(schedule, dict):
        return {}
    weekly = schedule.get("weekly")
    return weekly if isinstance(weekly, dict) else {}


def _window_contains_minute(window: dict[str, str], minute: int) -> bool:
    start, end = _minutes(window["start"]), _minutes(window["end"])
    if start == end:
        return True
    if start < end:
        return start <= minute < end
    return minute >= start


def _overnight_window_contains_tail(window: dict[str, str], minute: int) -> bool:
    start, end = _minutes(window["start"]), _minutes(window["end"])
    return start > end and minute < end


def credential_is_available(
    schedule_enabled: bool,
    schedule: dict | None,
    at: datetime | None = None,
) -> bool:
    if not schedule_enabled:
        return True
    local_now = (at or datetime.now(timezone.utc)).astimezone(SISTER_SCHEDULE_TIMEZONE)
    minute = local_now.hour * 60 + local_now.minute
    weekly = _weekly(schedule)

    if any(_window_contains_minute(window, minute) for window in weekly.get(str(local_now.weekday()), [])):
        return True

    previous_day = str((local_now.weekday() - 1) % 7)
    return any(
        _overnight_window_contains_tail(window, minute)
        for window in weekly.get(previous_day, [])
    )


def next_credential_availability(
    schedule_enabled: bool,
    schedule: dict | None,
    at: datetime | None = None,
) -> datetime | None:
    reference = at or datetime.now(timezone.utc)
    if credential_is_available(schedule_enabled, schedule, reference):
        return reference

    candidate = reference.astimezone(timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(8 * 24 * 60):
        if credential_is_available(schedule_enabled, schedule, candidate):
            return candidate
        candidate += timedelta(minutes=1)
    return None
