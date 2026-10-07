from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.modules.elaborazioni.sister_http_health import INIT_PORTALE, init_portale_hourly_health


def event(hour, kind="http_warning", **values):
    defaults = {
        "id": uuid4(),
        "request_id": None,
        "session_id": "session",
        "occurred_at": hour,
        "event_type": kind,
        "step": "prepare_download",
        "outcome": "success",
        "duration_ms": None,
        "http_status": None,
        "endpoint": None,
    }
    if kind == "http_warning":
        defaults.update(http_status=501, endpoint=INIT_PORTALE, outcome="non_blocking")
    defaults.update(values)
    return SimpleNamespace(**defaults)


def window():
    start = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    return start, start + timedelta(hours=1), start + timedelta(hours=2)


def test_hourly_aggregation_keeps_unknown_duration_and_requires_operational_evidence():
    start, hour, end = window()
    events = [
        event(hour),
        event(hour, duration_ms=25),
        event(hour, outcome="error"),
        event(hour, "download", request_id="pdf"),
        event(hour, "download", request_id="pdf"),
        event(hour, "submit", request_id="submit", outcome="waiting"),
        event(hour, "submit", step="fill_visura_form"),
        event(start - timedelta(seconds=1)),
        event(end),
        event(start, http_status=500),
        event(start, endpoint="/other"),
    ]
    rows = init_portale_hourly_health(events, start, end, [(start, end)])
    assert len(rows) == 1
    row = rows[0]
    assert row["http_501"] == 3
    assert row["confirmed_non_blocking"] == 2
    assert row["unclassified_or_blocking"] == 1
    assert row["measured_responses"] == 1
    assert row["response_wait_ms"] == 25
    assert row["downloads"] == row["successful_submits"] == 1
    assert row["complete_hour"] and row["comparable_scheduled_hours"]
    assert row["alerts"] == []
    assert init_portale_hourly_health([event(hour)], start, end, [])[0]["response_wait_ms"] is None


def test_alerts_require_failed_login_same_session_or_comparable_operational_decline():
    start, hour, end = window()
    events = [
        event(start, "download"),
        event(start, "download"),
        event(hour),
        event(hour, "login", outcome="error"),
        event(hour, "submit", outcome="error"),
        event(hour, "execution_start"),
        event(hour, "execution_start"),
    ]
    row = init_portale_hourly_health(events, start, end, [(start, end)])[0]
    assert row["alerts"] == [
        "login_failed_with_501",
        "no_successful_submits_with_501",
        "downloads_declining_with_501",
    ]
    events[3].session_id = "other"
    assert init_portale_hourly_health(events, start, end, [])[0]["alerts"] == []
    events[3].session_id = None
    assert init_portale_hourly_health(events, start, end, [(start, end)])[0]["alerts"] == [
        "no_successful_submits_with_501",
        "downloads_declining_with_501",
    ]
    events.append(event(hour, "download"))
    assert (
        "downloads_declining_with_501"
        not in init_portale_hourly_health(events, start, end, [(start, end)])[0]["alerts"]
    )


def test_missing_submits_alert_only_with_work_and_without_resumed_polling():
    start, hour, end = window()
    events = [event(hour), event(hour, "execution_start")]
    assert init_portale_hourly_health(events, start, end, [(start, end)])[0]["alerts"] == [
        "no_successful_submits_with_501"
    ]
    events.append(event(hour, "polling", outcome="waiting"))
    assert init_portale_hourly_health(events, start, end, [(start, end)])[0]["alerts"] == []


def test_login_failure_is_correlated_across_hour_boundary_without_guessing_sessions():
    start, hour, end = window()
    events = [event(hour - timedelta(seconds=1)), event(hour, "login", outcome="error")]
    rows = init_portale_hourly_health(iter(events), start, end, [(start, end)])
    assert rows[0]["alerts"] == ["login_failed_with_501"]


def test_partial_hours_inactive_calendar_and_low_demand_do_not_raise_throughput_alerts():
    start, hour, end = window()
    events = [event(start, "download"), event(hour), event(hour, "submit", outcome="error")]
    assert init_portale_hourly_health(events, start, end, [(start, end)])[0]["alerts"] == [
        "no_successful_submits_with_501"
    ]
    row = init_portale_hourly_health(events, start, end - timedelta(minutes=1), [(start, end)])[0]
    assert not row["complete_hour"] and not row["comparable_scheduled_hours"]
    assert row["alerts"] == []
    rows = init_portale_hourly_health(
        [event(start.replace(tzinfo=None)), event(hour, session_id=None)],
        start + timedelta(minutes=1),
        end,
        [(start, end)],
    )
    assert len(rows) == 1 and rows[0]["alerts"] == []
    first = init_portale_hourly_health(
        [event(start)], start + timedelta(minutes=0), end, [(start, end)]
    )[0]
    assert not first["comparable_scheduled_hours"]
