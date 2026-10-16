"""R130 characterization of the live network statistics summary.

Pins how the live path derives domain keys and destination labels from the
parsed firewall payload (``domain`` first, then the ``url`` hostname) and
checks that the live and rollup summary paths keep agreeing on the data where
they already agreed.

R135: the live path now mirrors the rollup rules for ``*.denied`` event types
(counted as blocked) and for lowercased destination labels.
"""

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.network.models import (
    NetworkDevice,
    NetworkFirewall,
    NetworkFirewallEvent,
    NetworkTrackedSubject,
)
from app.modules.network.router.helpers import traffic
from app.modules.network.telemetry_rollups import (
    build_network_statistics_summary_from_rollups,
    refresh_network_firewall_hourly_rollups,
)

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _no_reverse_dns(monkeypatch):
    traffic._resolve_peer_label.cache_clear()
    monkeypatch.setattr(traffic, "_resolve_peer_label", lambda _ip: None)


def _firewall(db) -> NetworkFirewall:
    firewall = NetworkFirewall(
        vendor="Sophos", name="Sophos XGS87", management_ip="192.168.1.126", status="online"
    )
    db.add(firewall)
    db.flush()
    return firewall


def _event(
    firewall, *, parsed, dst_ip, src_ip="192.168.1.50", minutes_ago=5, event_type="web.allowed"
):
    return NetworkFirewallEvent(
        firewall_id=firewall.id,
        source="sophos_syslog",
        event_type=event_type,
        severity="info",
        src_ip=src_ip,
        dst_ip=dst_ip,
        protocol="TCP",
        raw_payload=json.dumps({"parsed": parsed}),
        observed_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
    )


def _traffic_rows(items):
    return [
        (
            item.label,
            item.ip_address,
            item.events_count,
            item.bytes_in,
            item.bytes_out,
            item.bytes_total,
            item.tracked_subject_id,
        )
        for item in items
    ]


def test_live_summary_derives_domain_keys_and_destination_labels(db) -> None:
    firewall = _firewall(db)
    db.add(
        NetworkTrackedSubject(
            entity_type="domain",
            normalized_value="mixed.example",
            value="mixed.example",
            label="Tracked domain",
            is_active=True,
        )
    )
    db.add_all(
        [
            # domain wins over url; domain key and destination label are lowercased (R135)
            _event(
                firewall,
                parsed={
                    "domain": " Mixed.Example ",
                    "url": "https://other.example/x",
                    "bytes_sent": "10",
                },
                dst_ip="1.1.1.1",
            ),
            # blank domain falls back to the url hostname for both
            _event(
                firewall,
                parsed={
                    "domain": "   ",
                    "url": " https://Url.Example:8443/p ",
                    "bytes_received": "4",
                },
                dst_ip="2.2.2.2",
            ),
            # non-string domain falls back to the url hostname
            _event(firewall, parsed={"domain": 7, "url": "http://num.example"}, dst_ip="3.3.3.3"),
            # url without hostname: no domain, destination label is the peer ip
            _event(firewall, parsed={"url": "not-a-url"}, dst_ip="4.4.4.4"),
            # blank domain and blank url: no domain, label is the peer ip
            _event(firewall, parsed={"domain": " ", "url": "  "}, dst_ip="5.5.5.5"),
            # non-string url: no domain, label is the peer ip
            _event(firewall, parsed={"url": ["x"]}, dst_ip="6.6.6.6"),
            # no destination: peer falls back to the source ip
            _event(firewall, parsed={"domain": "src.example"}, dst_ip=None, src_ip="7.7.7.7"),
        ]
    )
    db.commit()

    summary = traffic._build_network_statistics_summary(db)

    assert summary.total_events == 7
    assert summary.unique_domains == 4
    domains = {item.label: item for item in summary.top_domains}
    assert set(domains) == {"mixed.example", "url.example", "num.example", "src.example"}
    assert domains["mixed.example"].tracked_subject_id is not None
    assert domains["mixed.example"].bytes_out == 10
    assert domains["url.example"].bytes_in == 4
    assert domains["url.example"].tracked_subject_id is None
    destinations = {item.ip_address: item.label for item in summary.top_destinations}
    assert destinations == {
        "1.1.1.1": "mixed.example",
        "2.2.2.2": "url.example",
        "3.3.3.3": "num.example",
        "4.4.4.4": "4.4.4.4",
        "5.5.5.5": "5.5.5.5",
        "6.6.6.6": "6.6.6.6",
        "7.7.7.7": "src.example",
    }
    assert summary.unique_external_peers == 7


def test_extract_peer_hint_prefers_domain_then_url_hostname(monkeypatch) -> None:
    monkeypatch.setattr(traffic, "_resolve_peer_label", lambda ip: f"rdap:{ip}")
    event = NetworkFirewallEvent(
        raw_payload=json.dumps({"parsed": {"domain": " ", "url": " https://Hint.Example/a "}})
    )
    assert traffic._extract_peer_hint(event, peer_ip="8.8.8.8") == "hint.example"
    event.raw_payload = json.dumps({"parsed": {"domain": 3, "url": "https://num.example"}})
    assert traffic._extract_peer_hint(event, peer_ip="8.8.8.8") == "num.example"
    event.raw_payload = json.dumps(
        {"parsed": {"domain": " Keep.Case ", "url": "https://x.example"}}
    )
    assert traffic._extract_peer_hint(event, peer_ip="8.8.8.8") == "Keep.Case"
    event.raw_payload = json.dumps({"parsed": {"domain": " ", "url": ["x"]}})
    assert traffic._extract_peer_hint(event, peer_ip="8.8.8.8") == "rdap:8.8.8.8"
    event.raw_payload = json.dumps({"parsed": "not-a-dict"})
    assert traffic._extract_peer_hint(event, peer_ip=None) is None


def test_live_and_rollup_summaries_agree_on_shared_dimensions(db) -> None:
    firewall = _firewall(db)
    device = NetworkDevice(
        ip_address="192.168.1.10",
        hostname="pc-ced",
        lifecycle_state="active",
        is_known_device=True,
        status="online",
        is_monitored=True,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db.add(device)
    db.flush()
    db.add(
        NetworkTrackedSubject(
            entity_type="ip",
            normalized_value="8.8.8.8",
            value="8.8.8.8",
            label="DNS",
            is_active=True,
        )
    )
    db.add_all(
        [
            _event(
                firewall,
                src_ip=device.ip_address,
                dst_ip="8.8.8.8",
                parsed={
                    "domain": "dns.google",
                    "bytes_sent": "100",
                    "bytes_received": "300",
                    "fw_rule_name": "Web",
                },
            ),
            _event(
                firewall,
                src_ip=device.ip_address,
                dst_ip="8.8.8.8",
                parsed={"url": "https://dns.google/q", "bytes_sent": "1", "bytes_received": "2"},
                minutes_ago=6,
            ),
            _event(
                firewall,
                src_ip=device.ip_address,
                dst_ip="9.9.9.9",
                parsed={"url": "not-a-url", "bytes_sent": "5"},
                event_type="firewall.drop",
                minutes_ago=7,
            ),
            _event(
                firewall,
                src_ip="192.168.1.99",
                dst_ip="1.0.0.1",
                parsed={"domain": "one.one", "bytes_sent": "7", "bytes_received": "11"},
                minutes_ago=8,
            ),
            # R135: "*.denied" counts as blocked and a mixed-case domain yields a
            # lowercased destination label on both paths
            _event(
                firewall,
                src_ip=device.ip_address,
                dst_ip="4.4.4.4",
                parsed={"domain": " Mixed.Case.Example ", "bytes_sent": "3"},
                event_type="web.denied",
                minutes_ago=9,
            ),
        ]
    )
    db.commit()
    assert refresh_network_firewall_hourly_rollups(db, lookback_hours=2) > 0

    live = traffic._build_network_statistics_summary(db, window_hours=1)
    rollup = build_network_statistics_summary_from_rollups(db, window_hours=1)

    assert rollup is not None
    shared_scalars = (
        "total_events",
        "allowed_events",
        "blocked_events",
        "bytes_in",
        "bytes_out",
        "unique_domains",
        "unique_external_peers",
        "devices_with_traffic",
    )
    assert {name: getattr(live, name) for name in shared_scalars} == {
        name: getattr(rollup, name) for name in shared_scalars
    }
    assert live.total_events == 5
    assert live.unique_domains == 3
    assert live.blocked_events == 2
    assert _traffic_rows(live.top_domains) == _traffic_rows(rollup.top_domains)
    assert _traffic_rows(live.top_destinations) == _traffic_rows(rollup.top_destinations)
    assert [(item.key, item.count) for item in live.top_firewall_rules] == [
        (item.key, item.count) for item in rollup.top_firewall_rules
    ]
    destinations = {item.ip_address: item for item in live.top_destinations}
    assert destinations["8.8.8.8"].label == "dns.google"
    assert destinations["8.8.8.8"].tracked_subject_id is not None
    assert destinations["9.9.9.9"].label == "9.9.9.9"
    assert destinations["4.4.4.4"].label == "mixed.case.example"


def test_live_summary_counts_denied_event_types_as_blocked(db) -> None:
    firewall = _firewall(db)
    event_types = (
        "web.allowed",
        "firewall.deny",
        "Web.DENIED",
        "firewall.block",
        "firewall.drop",
        "system.info",
    )
    db.add_all(
        [
            _event(firewall, parsed={}, dst_ip="10.0.0.1", event_type=event_type)
            for event_type in event_types
        ]
    )
    db.commit()

    summary = traffic._build_network_statistics_summary(db)

    assert summary.total_events == 6
    assert summary.allowed_events == 1
    assert summary.blocked_events == 4


def test_device_traffic_summary_counts_denied_event_types_as_blocked(db) -> None:
    firewall = _firewall(db)
    device = NetworkDevice(
        ip_address="192.168.1.50",
        hostname="pc-denied",
        lifecycle_state="active",
        is_known_device=True,
        status="online",
        is_monitored=True,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db.add(device)
    db.flush()
    event_types = (
        "web.allowed",
        "firewall.deny",
        "firewall.invalid_traffic.denied",
        "Web.DENIED",
        "firewall.block",
        "firewall.drop",
        "system.info",
    )
    db.add_all(
        [
            _event(firewall, parsed={}, dst_ip="10.0.0.1", event_type=event_type)
            for event_type in event_types
        ]
    )
    db.commit()

    summary = traffic._build_device_traffic_summary(db, device)

    assert summary.total_events == 7
    assert summary.allowed_events == 1
    assert summary.blocked_events == 5
