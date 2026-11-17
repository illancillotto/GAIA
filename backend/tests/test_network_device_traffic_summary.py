"""Device traffic totals, stable ranking, lazy detail reads and query order."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.modules.network.router.helpers import traffic


@pytest.fixture
def traffic_case(monkeypatch):
    state = SimpleNamespace(
        anchor=datetime.now(UTC),
        events=[],
        values={},
        labels={},
        payloads={},
        subjects={},
        calls=[],
        queries=[],
        device=SimpleNamespace(id=4, ip_address="10.0.0.4"),
    )

    def now(zone):
        assert zone is UTC
        state.calls.append(("clock",))
        return state.anchor

    def get_map(db):
        assert db is state.db
        state.calls.append(("tracked_map",))
        return state.subjects

    def scalars(query):
        state.queries.append(query)
        state.calls.append(("query",))

        def all_events():
            state.calls.append(("all",))
            return state.events

        return SimpleNamespace(all=all_events)

    def extract(event, *, device_ip):
        state.calls.append(("traffic", event.key, device_ip))
        return state.values[event.key]

    def parsed(event):
        state.calls.append(("parsed", event.key))
        return state.payloads[event.key]

    def hint(event, *, peer_ip):
        state.calls.append(("hint", event.key, peer_ip))
        return state.labels[event.key]

    def find(subjects, *, entity_type, value):
        assert subjects is state.subjects
        state.calls.append(("find", entity_type, value))
        return subjects.get((entity_type, value))

    def resolve(address):
        state.calls.append(("resolve", address))
        return "Resolved " + address

    def add(*, event_type="other", peer="peer", bytes_in=1, bytes_out=2, label=None, url=None):
        key = len(state.events) + 1
        event = SimpleNamespace(
            key=key,
            id=key,
            event_type=event_type,
            severity="info",
            protocol="TCP",
            src_ip="10.0.0.4",
            dst_ip=peer,
            observed_at=state.anchor - timedelta(minutes=key),
        )
        state.events.append(event)
        state.values[key] = (bytes_in, bytes_out, peer)
        state.labels[key] = label
        state.payloads[key] = {"url": url}
        return event

    state.db = SimpleNamespace(scalars=scalars)
    state.add = add
    state.run = lambda **kwargs: traffic._build_device_traffic_summary(
        state.db, state.device, **kwargs
    )
    monkeypatch.setattr(traffic, "datetime", SimpleNamespace(now=now))
    monkeypatch.setattr(traffic, "_get_active_tracked_subject_map", get_map)
    monkeypatch.setattr(traffic, "_extract_event_traffic", extract)
    monkeypatch.setattr(traffic, "_extract_firewall_event_parsed", parsed)
    monkeypatch.setattr(traffic, "_extract_peer_hint", hint)
    monkeypatch.setattr(traffic, "_find_tracked_subject", find)
    monkeypatch.setattr(traffic, "_resolve_peer_label", resolve)
    return state


def test_empty_query_preserves_clock_map_and_materialization_order(traffic_case):
    result = traffic_case.run(window_hours=7)
    assert result.window_hours == 7
    assert result.total_events == result.allowed_events == result.blocked_events == 0
    assert result.bytes_in == result.bytes_out == 0
    assert result.last_observed_at is None
    assert result.top_peers == result.recent_events == []
    assert traffic_case.calls == [("clock",), ("tracked_map",), ("query",), ("all",)]
    query = traffic_case.queries[0]
    compiled = query.compile(dialect=postgresql.dialect())
    assert compiled.params == {
        "observed_at_1": traffic_case.anchor - timedelta(hours=7),
        "device_id_1": 4,
        "src_ip_1": "10.0.0.4",
        "dst_ip_1": "10.0.0.4",
    }
    assert "ORDER BY network_firewall_events.observed_at DESC" in str(compiled)
    assert dict(query.get_execution_options()) == {}


@pytest.mark.parametrize(
    "event_type, allowed, blocked",
    [
        ("ALLOW.rule", 1, 0),
        ("deny.rule", 0, 1),
        ("block.rule", 0, 1),
        ("drop.rule", 0, 1),
        ("ALLOW.BLOCK.DROP", 1, 1),
        ("disallowed", 1, 0),
        ("other", 0, 0),
        ("", 0, 0),
    ],
)
def test_allowed_and_blocked_are_independent_substring_counts(
    traffic_case, event_type, allowed, blocked
):
    traffic_case.add(event_type=event_type, peer=None)
    result = traffic_case.run()
    assert result.allowed_events == allowed
    assert result.blocked_events == blocked
    assert result.total_events == 1
    assert (result.bytes_in, result.bytes_out) == (1, 2)
    assert result.top_peers == []


def test_peer_totals_top_five_and_label_ties_are_stable(traffic_case):
    for peer, size, label in [
        ("B", 5, "Z"),
        ("A", 5, "A"),
        ("B", 0, "Y"),
        ("A", 0, "B"),
        ("C", 20, None),
        ("D", 15, None),
        ("E", 10, None),
        ("F", 7, None),
        ("G", 1, None),
    ]:
        traffic_case.add(peer=peer, bytes_in=size, bytes_out=0, label=label)
    result = traffic_case.run()
    assert result.total_events == 9
    assert (result.bytes_in, result.bytes_out) == (63, 0)
    assert [peer.ip_address for peer in result.top_peers] == ["C", "D", "E", "F", "B"]
    assert result.top_peers[-1].label == "Z"
    assert result.top_peers[-1].events_count == 2
    assert [item.id for item in result.recent_events] == list(range(1, 9))
    assert result.last_observed_at == traffic_case.events[0].observed_at
    assert [call for call in traffic_case.calls if call[0] == "resolve"] == [
        ("resolve", "C"),
        ("resolve", "D"),
        ("resolve", "E"),
        ("resolve", "F"),
    ]


def test_equal_byte_totals_rank_event_count_before_input_order(traffic_case):
    traffic_case.add(peer="A", bytes_in=8, bytes_out=0)
    traffic_case.add(peer="B", bytes_in=4, bytes_out=0)
    traffic_case.add(peer="B", bytes_in=4, bytes_out=0)
    result = traffic_case.run()
    assert [peer.ip_address for peer in result.top_peers] == ["B", "A"]


@pytest.mark.parametrize("peer", [None, ""])
def test_missing_peer_does_not_discard_event_bytes_or_details(traffic_case, peer):
    traffic_case.add(peer=peer, bytes_in=7, bytes_out=9, label="Domain")
    result = traffic_case.run()
    assert (result.bytes_in, result.bytes_out) == (7, 9)
    assert result.top_peers == []
    assert result.recent_events[0].peer_ip == peer
    assert result.recent_events[0].peer_label == "Domain"


def test_tracked_ids_and_double_url_get_are_preserved(traffic_case):
    reads = []

    class Payload(dict):
        def get(self, key, default=None):
            reads.append(key)
            return super().get(key, default)

    traffic_case.add(peer="P", label="Domain", url="https://url.example")
    traffic_case.payloads[1] = Payload(url="https://url.example")
    traffic_case.subjects.update(
        {
            ("ip", "P"): SimpleNamespace(id=31),
            ("domain", "Domain"): SimpleNamespace(id=32),
            ("url", "https://url.example"): SimpleNamespace(id=33),
        }
    )
    result = traffic_case.run()
    event = result.recent_events[0]
    assert (
        event.tracked_peer_ip_subject_id,
        event.tracked_peer_label_subject_id,
        event.tracked_url_subject_id,
    ) == (31, 32, 33)
    assert result.top_peers[0].tracked_subject_id == 31
    assert reads == ["url", "url"]
    assert traffic_case.calls[4:] == [
        ("traffic", 1, "10.0.0.4"),
        ("parsed", 1),
        ("find", "ip", "P"),
        ("hint", 1, "P"),
        ("find", "domain", "Domain"),
        ("find", "url", "https://url.example"),
        ("find", "ip", "P"),
    ]


def test_ninth_event_keeps_lookups_but_never_reads_detail_fields(traffic_case):
    for _ in range(9):
        traffic_case.add()

    class NinthEvent:
        key = 9
        event_type = "allow.rule"

        def __getattr__(self, name):
            raise AssertionError("unexpected detail read: " + name)

    traffic_case.events[-1] = NinthEvent()
    result = traffic_case.run()
    assert result.total_events == 9
    assert len(result.recent_events) == 8
    assert result.allowed_events == 1
    assert len([call for call in traffic_case.calls if call[0] == "find"]) == 28


def test_device_address_is_read_twice_in_query_and_again_for_each_event(traffic_case):
    reads = []
    addresses = iter(["query-source", "query-destination", "event-one", "event-two"])

    class Device:
        id = 4

        @property
        def ip_address(self):
            address = next(addresses)
            reads.append(address)
            return address

    traffic_case.device = Device()
    traffic_case.add()
    traffic_case.add()
    traffic_case.run()
    assert reads == ["query-source", "query-destination", "event-one", "event-two"]
    compiled = traffic_case.queries[0].compile(dialect=postgresql.dialect())
    assert compiled.params["src_ip_1"] == "query-source"
    assert compiled.params["dst_ip_1"] == "query-destination"
    assert [call[-1] for call in traffic_case.calls if call[0] == "traffic"] == [
        "event-one",
        "event-two",
    ]
