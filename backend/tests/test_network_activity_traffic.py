"""Activity totals preserve conversion order, failures and the device traffic path."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.modules.network.router.helpers import tracking


def activity(monkeypatch, parsed, *, kind="ip", value="peer", limit=25, matched=True):
    event = SimpleNamespace(
        id=8,
        firewall_id=2,
        device_id=4,
        event_type="allow.drop",
        severity="info",
        protocol="TCP",
        src_ip="peer",
        dst_ip="remote",
        message="event",
        observed_at=datetime(2026, 11, 17, tzinfo=UTC),
    )
    subject = SimpleNamespace(entity_type=kind, value=value, normalized_value="peer", device_id=4)
    queries = []

    def scalars(query):
        queries.append(query)
        return SimpleNamespace(all=lambda: [event])

    monkeypatch.setattr(tracking, "_active_detection_watchlist_entries", lambda _db: [])
    monkeypatch.setattr(tracking, "_extract_firewall_event_parsed", lambda _event: parsed)
    monkeypatch.setattr(
        tracking,
        "_match_tracked_subject_against_event",
        lambda *_args, **_kwargs: ("src_ip", "peer") if matched else None,
    )
    monkeypatch.setattr(
        tracking,
        "event_detection_tags",
        lambda *_args, **_kwargs: ["vpn_suspected", "proxy_suspected"],
    )
    monkeypatch.setattr(
        tracking,
        "_resolve_firewall_event_endpoint_labels",
        lambda *_args, **_kwargs: ("Source", "Destination"),
    )
    summary = tracking._build_tracked_subject_activity_summary(
        SimpleNamespace(scalars=scalars), subject, window_hours=24, limit=limit
    )
    assert len(queries) == 1
    return summary


@pytest.mark.parametrize(
    "parsed,expected",
    [
        ({"bytes_sent": " 17 ", "bytes_received": " +23 "}, (23, 17)),
        ({"bytes_sent": -7, "bytes_received": "-9"}, (0, 0)),
        ({}, (0, 0)),
        ({"bytes_sent": None, "bytes_received": []}, (0, 0)),
        ({"bytes_sent": True, "bytes_received": {}}, (0, 0)),
        ({"bytes_sent": "3.5", "bytes_received": "1e2"}, (0, 0)),
        ({"bytes_sent": 12.9, "bytes_received": 6.2}, (0, 0)),
        ({"bytes_sent": 10**40, "bytes_received": "004"}, (4, 10**40)),
    ],
)
def test_totals_and_details_share_converted_nonnegative_values(monkeypatch, parsed, expected):
    result = activity(monkeypatch, parsed)
    assert (result.bytes_in, result.bytes_out) == expected
    assert (result.total_events, result.allowed_events, result.blocked_events) == (1, 1, 1)
    assert (
        result.suspicious_events
        == result.vpn_suspected_events
        == result.proxy_suspected_events
        == 1
    )
    detail = result.recent_events[0]
    assert (detail.bytes_in, detail.bytes_out) == expected
    assert (detail.src_device_label, detail.dst_device_label) == ("Source", "Destination")


def test_sent_get_and_string_conversion_precede_received(monkeypatch):
    trace = []

    class Value:
        def __init__(self, name, value):
            self.name, self.value = name, value

        def __str__(self):
            trace.append(("str", self.name))
            return self.value

    class Parsed(dict):
        def get(self, key, default=None):
            trace.append(("get", key))
            return super().get(key, default)

    parsed = Parsed(bytes_sent=Value("sent", " 13 "), bytes_received=Value("received", " 29 "))
    result = activity(monkeypatch, parsed, limit=0)
    assert (result.bytes_in, result.bytes_out) == (29, 13)
    assert result.recent_events == []
    assert trace == [
        ("get", "bytes_sent"),
        ("str", "sent"),
        ("get", "bytes_received"),
        ("str", "received"),
    ]


@pytest.mark.parametrize("error", [TypeError, ValueError])
@pytest.mark.parametrize("failing_key", ["bytes_sent", "bytes_received"])
def test_conversion_errors_are_caught_independently(monkeypatch, error, failing_key):
    class BadValue:
        def __str__(self):
            raise error("cannot stringify counter")

    parsed = {"bytes_sent": "11", "bytes_received": "19", failing_key: BadValue()}
    result = activity(monkeypatch, parsed)
    expected = (19, 0) if failing_key == "bytes_sent" else (0, 11)
    assert (result.bytes_in, result.bytes_out) == expected
    assert (result.recent_events[0].bytes_in, result.recent_events[0].bytes_out) == expected


@pytest.mark.parametrize("error", [OverflowError, RuntimeError])
@pytest.mark.parametrize("failing_key", ["bytes_sent", "bytes_received"])
def test_other_errors_propagate_without_reading_later_counters(monkeypatch, error, failing_key):
    trace = []

    class Parsed(dict):
        def get(self, key, default=None):
            trace.append(key)
            if key == failing_key:
                raise error("counter unavailable")
            return "11"

    with pytest.raises(error, match="counter unavailable"):
        activity(monkeypatch, Parsed(), limit=0)
    assert trace == (
        ["bytes_sent"] if failing_key == "bytes_sent" else ["bytes_sent", "bytes_received"]
    )


def test_device_delegates_without_reading_payload_counters_or_clamping(monkeypatch):
    calls = []

    class Parsed(dict):
        def get(self, key, default=None):
            assert key not in {"bytes_sent", "bytes_received"}
            return super().get(key, default)

    def extract(event, *, device_ip):
        calls.append((event.id, device_ip))
        return -3, 17, "outbound"

    monkeypatch.setattr(tracking, "_extract_event_traffic", extract)
    result = activity(monkeypatch, Parsed(), kind="device", value="peer")
    assert calls == [(8, "peer")]
    assert (result.bytes_in, result.bytes_out) == (-3, 17)
    assert (result.recent_events[0].bytes_in, result.recent_events[0].bytes_out) == (-3, 17)


@pytest.mark.parametrize("value", [None, "", 0, False])
def test_falsey_device_value_keeps_raw_counter_path(monkeypatch, value):
    def unexpected(*_args, **_kwargs):
        raise AssertionError("falsey subject value does not select device traffic")

    monkeypatch.setattr(tracking, "_extract_event_traffic", unexpected)
    result = activity(
        monkeypatch,
        {"bytes_sent": "7", "bytes_received": "9"},
        kind="device",
        value=value,
    )
    assert (result.bytes_in, result.bytes_out) == (9, 7)


def test_unmatched_events_do_not_read_counters_or_create_details(monkeypatch):
    class Parsed(dict):
        def get(self, *_args):
            raise AssertionError("unmatched payload counters must stay unread")

    result = activity(monkeypatch, Parsed(), matched=False)
    assert (result.total_events, result.bytes_in, result.bytes_out) == (0, 0, 0)
    assert result.recent_events == []
