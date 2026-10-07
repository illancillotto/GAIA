from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from typing import Any

UTC = timezone.utc  # noqa: UP017 - Imported by the Python 3.10 worker report.
INIT_PORTALE = "/portale-rest/rs/initPortale"
SUBMIT_STEPS = {"prepare_download", "captcha_submit", "subject_search"}


def _hour(value: datetime) -> datetime:
    return (
        value.replace(tzinfo=value.tzinfo or UTC)
        .astimezone(UTC)
        .replace(minute=0, second=0, microsecond=0)
    )


def _init_errors(events: list[Any]) -> list[Any]:
    return [
        event
        for event in events
        if getattr(event, "http_status", None) == 501
        and getattr(event, "endpoint", None) == INIT_PORTALE
    ]


def _successes(events: list[Any], kind: str) -> set[Any]:
    return {
        event.request_id or event.id
        for event in events
        if event.event_type == kind and event.outcome == "success"
    }


def _submits(events: list[Any], *, successful: bool = False) -> set[Any]:
    return {
        event.request_id or event.id
        for event in events
        if event.event_type == "submit"
        and event.step in SUBMIT_STEPS
        and (not successful or event.outcome in {"success", "waiting"})
    }


def _login_failed(events: list[Any], failed_sessions: set[Any]) -> bool:
    sessions = {event.session_id for event in _init_errors(events) if event.session_id}
    return bool(sessions & failed_sessions)


def _downloads_declining(events: list[Any], previous: list[Any]) -> bool:
    previous_downloads = len(_successes(previous, "download"))
    executions = sum(event.event_type == "execution_start" for event in events)
    return bool(
        previous_downloads
        and executions >= previous_downloads
        and len(_successes(events, "download")) * 2 < previous_downloads
    )


def _submit_stalled(events: list[Any]) -> bool:
    if _submits(events, successful=True) or _successes(events, "download"):
        return False
    if _submits(events):
        return True
    kinds = {event.event_type for event in events}
    return "execution_start" in kinds and "polling" not in kinds


def _hour_alerts(
    events: list[Any], previous: list[Any], comparable: bool, failed_sessions: set[Any]
) -> list[str]:
    alerts = []
    if _login_failed(events, failed_sessions):
        alerts.append("login_failed_with_501")
    if comparable and _submit_stalled(events):
        alerts.append("no_successful_submits_with_501")
    if comparable and _downloads_declining(events, previous):
        alerts.append("downloads_declining_with_501")
    return alerts


def _comparable_hours(
    hour: datetime,
    start: datetime,
    end: datetime,
    intervals: list[tuple[datetime, datetime]],
) -> tuple[bool, bool]:
    previous_hour = hour - timedelta(hours=1)
    complete = start <= hour and hour + timedelta(hours=1) <= end
    comparable = (
        complete
        and previous_hour >= start
        and all(
            any(left <= point and right >= point + timedelta(hours=1) for left, right in intervals)
            for point in (previous_hour, hour)
        )
    )
    return complete, comparable


def _hour_summary(
    hour: datetime,
    values: list[Any],
    previous: list[Any],
    window: tuple[datetime, datetime],
    intervals: list[tuple[datetime, datetime]],
    failed_sessions: set[Any],
) -> dict[str, Any] | None:
    errors = _init_errors(values)
    if not errors:
        return None
    complete, comparable = _comparable_hours(hour, *window, intervals)
    durations = [event.duration_ms for event in errors if event.duration_ms is not None]
    return {
        "hour_utc": hour.isoformat(),
        "http_501": len(errors),
        "confirmed_non_blocking": sum(event.outcome == "non_blocking" for event in errors),
        "unclassified_or_blocking": sum(event.outcome != "non_blocking" for event in errors),
        "measured_responses": len(durations),
        "response_wait_ms": sum(durations) if durations else None,
        "successful_submits": len(_submits(values, successful=True)),
        "downloads": len(_successes(values, "download")),
        "complete_hour": complete,
        "comparable_scheduled_hours": comparable,
        "alerts": _hour_alerts(values, previous, comparable, failed_sessions),
    }


def init_portale_hourly_health(
    events: Iterable[Any],
    start: datetime,
    end: datetime,
    scheduled: Iterable[tuple[datetime, datetime]],
) -> list[dict[str, Any]]:
    grouped: dict[datetime, list[Any]] = defaultdict(list)
    failed_sessions = set()
    for event in events:
        occurred_at = event.occurred_at.replace(tzinfo=event.occurred_at.tzinfo or UTC)
        if start <= occurred_at < end:
            grouped[_hour(occurred_at)].append(event)
            if event.event_type == "login" and event.outcome == "error":
                failed_sessions.add(event.session_id)
    intervals = list(scheduled)
    rows = []
    for hour, values in sorted(grouped.items()):
        row = _hour_summary(
            hour,
            values,
            grouped.get(hour - timedelta(hours=1), []),
            (start, end),
            intervals,
            failed_sessions,
        )
        if row is not None:
            rows.append(row)
    return rows
