"""Activity summaries preserve aggregation order and query selection."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.modules.network.router.helpers import tracking


def event(index, *, kind="allow", tags=(), matched=True, observed_at=None):
    return SimpleNamespace(
        id=index,
        firewall_id=2,
        device_id=4,
        event_type=kind,
        severity="info",
        protocol="TCP",
        src_ip="peer",
        dst_ip="remote",
        message="event",
        observed_at=observed_at,
        tags=tags,
        matched=matched,
        parsed={"bytes_sent": str(index), "bytes_received": str(index * 2)},
    )


def summarize(monkeypatch, events, *, limit=25, kind="ip", device_id=4, value="peer"):
    queries, labels = [], []

    def scalars(query):
        queries.append(str(query.compile(compile_kwargs={"literal_binds": True})))
        return SimpleNamespace(all=lambda: events)

    monkeypatch.setattr(tracking, "_active_detection_watchlist_entries", lambda _db: [])
    monkeypatch.setattr(tracking, "_extract_firewall_event_parsed", lambda item: item.parsed)
    monkeypatch.setattr(
        tracking,
        "_match_tracked_subject_against_event",
        lambda _subject, item, **_kwargs: ("src_ip", "peer") if item.matched else None,
    )
    tags = iter(item.tags for item in events if item.matched)
    monkeypatch.setattr(tracking, "event_detection_tags", lambda *_args, **_kwargs: next(tags))

    def endpoint_labels(_db, **kwargs):
        labels.append(kwargs)
        return "Source", "Destination"

    monkeypatch.setattr(tracking, "_resolve_firewall_event_endpoint_labels", endpoint_labels)
    subject = SimpleNamespace(
        entity_type=kind, device_id=device_id, value=value, normalized_value="normalized.example"
    )
    summary = tracking._build_tracked_subject_activity_summary(
        SimpleNamespace(scalars=scalars), subject, window_hours=24, limit=limit
    )
    assert len(queries) == 1
    return summary, queries[0], labels


def test_mixed_events_keep_totals_after_detail_limit_and_stable_tag_ranking(monkeypatch):
    now = datetime.now(UTC)
    rows = [
        event(
            1, kind="allow.drop", tags=["vpn_suspected", "vpn_suspected", "other"], observed_at=now
        ),
        event(2, kind="DENIED", tags=["proxy_suspected"], observed_at=now - timedelta(hours=1)),
        event(3, kind="block", matched=False, observed_at=now - timedelta(hours=2)),
        event(
            4,
            kind="other",
            tags=["tor_suspected", "encrypted_dns"],
            observed_at=now - timedelta(hours=3),
        ),
    ]
    result, _, labels = summarize(monkeypatch, rows, limit=1)
    assert (result.total_events, result.allowed_events, result.blocked_events) == (3, 1, 2)
    assert (result.bytes_in, result.bytes_out) == (14, 7)
    assert result.last_observed_at == now
    assert (result.suspicious_events, result.vpn_suspected_events) == (3, 1)
    assert (
        result.proxy_suspected_events
        == result.tor_suspected_events
        == result.encrypted_dns_events
        == 1
    )
    assert result.top_detection_tags == [
        "vpn_suspected",
        "other",
        "proxy_suspected",
        "tor_suspected",
    ]
    assert [item.id for item in result.recent_events] == [1]
    assert len(labels) == 1


@pytest.mark.parametrize("limit", [-1, 0])
def test_no_details_still_count_every_match_and_read_first_non_none_timestamp(monkeypatch, limit):
    now = datetime.now(UTC)
    rows = [event(1), event(2, observed_at=now), event(3, observed_at=now + timedelta(hours=1))]
    result, _, labels = summarize(monkeypatch, rows, limit=limit)
    assert (result.total_events, result.bytes_in, result.bytes_out) == (3, 12, 6)
    assert result.last_observed_at == now
    assert result.recent_events == []
    assert labels == []


def test_empty_summaries_do_not_share_counter_state(monkeypatch):
    now = datetime.now(UTC)
    populated, _, _ = summarize(monkeypatch, [event(1, tags=["vpn_suspected"], observed_at=now)])
    empty, _, _ = summarize(monkeypatch, [])
    assert populated.top_detection_tags == ["vpn_suspected"]
    assert empty.model_dump() == {
        "window_hours": 24,
        "total_events": 0,
        "allowed_events": 0,
        "blocked_events": 0,
        "suspicious_events": 0,
        "vpn_suspected_events": 0,
        "proxy_suspected_events": 0,
        "tor_suspected_events": 0,
        "encrypted_dns_events": 0,
        "bytes_in": 0,
        "bytes_out": 0,
        "last_observed_at": None,
        "top_detection_tags": [],
        "recent_events": [],
    }


def test_tag_truth_iteration_and_membership_keep_their_order(monkeypatch):
    trace = []

    class Tags(list):
        def __bool__(self):
            trace.append("bool")
            return True

        def __iter__(self):
            trace.append("iter")
            return super().__iter__()

        def __contains__(self, value):
            trace.append(value)
            return super().__contains__(value)

    result, _, _ = summarize(monkeypatch, [event(1, tags=Tags(["vpn_suspected"]))], limit=0)
    assert result.top_detection_tags == ["vpn_suspected"]
    assert trace == [
        "bool",
        "iter",
        "vpn_suspected",
        "proxy_suspected",
        "tor_suspected",
        "encrypted_dns",
    ]


def test_falsey_nonempty_tags_skip_all_detection_totals(monkeypatch):
    class Tags(list):
        def __bool__(self):
            return False

    result, _, _ = summarize(monkeypatch, [event(1, tags=Tags(["vpn_suspected"]))], limit=0)
    assert result.suspicious_events == result.vpn_suspected_events == 0
    assert result.top_detection_tags == []


@pytest.mark.parametrize(
    "kind,device_id,value,fragment",
    [
        ("device", 4, "peer", "network_firewall_events.device_id = 4 OR"),
        ("device", 0, "peer", None),
        ("device", 4, "", None),
        ("ip", 4, "peer", "network_firewall_events.src_ip = 'normalized.example' OR"),
        ("domain", 4, "peer", "lower(network_firewall_events.raw_payload) LIKE"),
        ("url", 4, "peer", "lower(network_firewall_events.raw_payload) LIKE"),
        ("other", None, "", None),
    ],
)
def test_query_scope_guard_and_descending_order_are_preserved(
    monkeypatch, kind, device_id, value, fragment
):
    _, query, _ = summarize(monkeypatch, [], kind=kind, device_id=device_id, value=value)
    assert "observed_at >=" in query
    assert query.endswith("ORDER BY network_firewall_events.observed_at DESC")
    if fragment is not None:
        assert fragment in query
    else:
        assert " OR " not in query and " LIKE " not in query
