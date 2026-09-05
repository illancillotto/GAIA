import io
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.application_user import ApplicationUser
from app.modules.network.models import (
    NetworkAlert,
    NetworkDevice,
    NetworkFirewallEvent,
    NetworkScan,
    NetworkScanDevice,
)
from app.modules.network.router import common
from app.modules.network.router.helpers import (
    devices,
    endpoints,
    firewalls,
    inference,
    scans,
    tracking,
    traffic,
)


class JsonResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def test_device_label_and_rdap_edge_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    assigned = ApplicationUser(username="fallback-user", full_name=None)
    device = NetworkDevice(ip_address="10.0.0.1", assigned_user=assigned)
    assert devices._resolve_device_label(device) == ("fallback-user", "application_user")
    device.assigned_user = None
    device.display_name = "Display"
    assert devices._resolve_device_label(device) == ("Display", "device")
    device.display_name = None
    device.hostname = "host"
    assert devices._resolve_device_label(device) == ("host", "hostname")
    device.hostname = None
    assert devices._resolve_device_label(device) == ("10.0.0.1", "ip_address")

    assert devices._extract_rdap_entity_names({}) == []
    assert (
        devices._extract_rdap_entity_names(
            {"entities": [None, {}, {"vcardArray": ["vcard", [None]]}]}
        )
        == []
    )
    names = devices._extract_rdap_entity_names(
        {
            "entities": [
                {"vcardArray": ["vcard", [["fn", {}, "text", " Example Org "]]]},
                {"vcardArray": ["vcard", [["org", {}, "text", "Example Org"]]]},
            ]
        }
    )
    assert names == ["Example Org"]

    with pytest.raises(HTTPException) as invalid:
        devices._summarize_ip_whois("invalid")
    assert invalid.value.status_code == 422

    fake_loopback = SimpleNamespace(is_private=False, is_loopback=True, is_link_local=False)
    monkeypatch.setattr(devices.ipaddress, "ip_address", lambda _value: fake_loopback)
    assert devices._summarize_ip_whois("127.0.0.1").scope == "Loopback locale"
    fake_link_local = SimpleNamespace(is_private=False, is_loopback=False, is_link_local=True)
    monkeypatch.setattr(devices.ipaddress, "ip_address", lambda _value: fake_link_local)
    assert devices._summarize_ip_whois("169.254.1.1").scope == "Link-local"


def test_rdap_unavailable_and_malformed_range(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        devices.urllib.request, "urlopen", MagicMock(side_effect=OSError("offline"))
    )
    assert devices._summarize_ip_whois("8.8.4.4").rdap_status == "unavailable"

    payload = {
        "startAddress": "bad",
        "endAddress": "worse",
        "name": 123,
        "handle": None,
        "country": [],
        "entities": [],
    }
    monkeypatch.setattr(
        devices.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: JsonResponse(json.dumps(payload).encode()),
    )
    result = devices._summarize_ip_whois("8.8.8.8")
    assert result.rdap_status == "ok"
    assert result.cidr == []
    assert result.label is None

    monkeypatch.setattr(
        devices.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: JsonResponse(b"{}"),
    )
    assert devices._summarize_ip_whois("1.1.1.1").cidr == []


def test_endpoint_label_and_traffic_helpers() -> None:
    device = NetworkDevice(id=4, ip_address="10.0.0.4", display_name="Linked")
    db = MagicMock()
    db.scalar.side_effect = [None, None, None, None, None]
    db.get.side_effect = [None, device]

    assert endpoints._resolve_label_for_ip(db, None) is None
    assert endpoints._resolve_label_for_ip(db, "10.0.0.9") is None
    assert endpoints._resolve_firewall_event_endpoint_labels(
        db, device_id=99, src_ip="10.0.0.1", dst_ip="10.0.0.2"
    ) == (None, None)
    assert endpoints._resolve_firewall_event_endpoint_labels(
        db, device_id=4, src_ip="10.0.0.4", dst_ip="10.0.0.8"
    ) == ("Linked", None)

    event = NetworkFirewallEvent(
        src_ip="10.0.0.4",
        dst_ip="8.8.8.8",
        raw_payload=json.dumps({"parsed": {"bytes_sent": "10", "bytes_received": "-2"}}),
    )
    assert endpoints._extract_event_traffic(event, device_ip="10.0.0.4") == (0, 10, "8.8.8.8")
    event.raw_payload = json.dumps({"parsed": {"bytes_sent": "bad", "bytes_received": None}})
    assert endpoints._extract_event_traffic(event, device_ip="8.8.8.8") == (0, 0, "10.0.0.4")
    event.src_ip = None
    event.dst_ip = None
    assert endpoints._extract_event_traffic(event, device_ip="other") == (0, 0, None)

    both = MagicMock()
    both.scalar.side_effect = [device, device]
    assert endpoints._resolve_firewall_event_endpoint_labels(
        both, device_id=4, src_ip="10.0.0.4", dst_ip="10.0.0.4"
    ) == ("Linked", "Linked")

    destination = MagicMock()
    destination.scalar.side_effect = [None, None]
    destination.get.return_value = device
    assert endpoints._resolve_firewall_event_endpoint_labels(
        destination, device_id=4, src_ip="10.0.0.8", dst_ip="10.0.0.4"
    ) == (None, "Linked")


def test_tracking_normalization_matching_and_labels() -> None:
    assert tracking._normalize_tracked_value("domain", "HTTPS://Example.COM/path") == "example.com"
    assert tracking._normalize_tracked_value("domain", " Example.COM. ") == "example.com"
    assert (
        tracking._normalize_tracked_value("url", " https://example.test/a ")
        == "https://example.test/a"
    )
    assert tracking._normalize_tracked_value("other", " value ") == "value"
    with pytest.raises(HTTPException):
        tracking._normalize_tracked_value("ip", "bad")
    with pytest.raises(HTTPException):
        tracking._normalize_tracked_value("domain", "")
    with pytest.raises(HTTPException):
        tracking._normalize_tracked_value("url", "  ")

    event = NetworkFirewallEvent(device_id=1, src_ip="10.0.0.1", dst_ip="8.8.8.8")
    subjects = [
        NetworkScan,
        SimpleNamespace(entity_type="device", device_id=1, value="10.0.0.1", normalized_value="1"),
        SimpleNamespace(entity_type="device", device_id=2, value="10.0.0.2", normalized_value="2"),
        SimpleNamespace(entity_type="ip", normalized_value="10.0.0.1"),
        SimpleNamespace(entity_type="ip", normalized_value="8.8.8.8"),
        SimpleNamespace(entity_type="ip", normalized_value="1.1.1.1"),
        SimpleNamespace(entity_type="domain", normalized_value="example.test"),
        SimpleNamespace(entity_type="url", normalized_value="https://example.test/a"),
    ]
    assert tracking._match_tracked_subject_against_event(subjects[1], event, parsed={}) == (
        "device",
        "10.0.0.1",
    )
    assert tracking._match_tracked_subject_against_event(subjects[2], event, parsed={}) is None
    assert (
        tracking._match_tracked_subject_against_event(subjects[3], event, parsed={})[0] == "src_ip"
    )
    assert (
        tracking._match_tracked_subject_against_event(subjects[4], event, parsed={})[0] == "dst_ip"
    )
    assert tracking._match_tracked_subject_against_event(subjects[5], event, parsed={}) is None
    assert tracking._match_tracked_subject_against_event(
        subjects[6], event, parsed={"url": "https://example.test/path"}
    ) == ("domain", "example.test")
    assert (
        tracking._match_tracked_subject_against_event(
            subjects[7], event, parsed={"url": "https://example.test/a"}
        )[0]
        == "url"
    )
    assert tracking._find_tracked_subject({}, entity_type="ip", value=None) is None
    assert tracking._find_tracked_subject({}, entity_type="ip", value="bad") is None

    direct_domain = SimpleNamespace(entity_type="domain", normalized_value="direct.example")
    assert tracking._match_tracked_subject_against_event(
        direct_domain, event, parsed={"domain": " Direct.Example "}
    ) == ("domain", "direct.example")
    assert tracking._match_tracked_subject_against_event(direct_domain, event, parsed={}) is None
    assert (
        tracking._match_tracked_subject_against_event(
            SimpleNamespace(entity_type="url", normalized_value="other"), event, parsed={"url": 3}
        )
        is None
    )
    assert (
        tracking._match_tracked_subject_against_event(
            SimpleNamespace(entity_type="other", normalized_value="other"), event, parsed={}
        )
        is None
    )

    labeled = SimpleNamespace(label="Label", device_id=None, value="value")
    assert tracking._resolve_tracked_subject_label(labeled, MagicMock()) == "Label"
    linked = SimpleNamespace(label=None, device_id=1, value="fallback")
    linked_db = MagicMock()
    linked_db.get.return_value = NetworkDevice(ip_address="10.0.0.1", display_name="Linked")
    assert tracking._resolve_tracked_subject_label(linked, linked_db) == "Linked"
    linked_db.get.return_value = None
    assert tracking._resolve_tracked_subject_label(linked, linked_db) == "fallback"
    assert inference._find_internal_device_by_ip(MagicMock(), None) is None

    from app.modules.network.router.routes import tracking as tracking_routes
    from app.modules.network.schemas import NetworkTrackedSubjectCreateRequest

    payload = NetworkTrackedSubjectCreateRequest.model_construct(
        entity_type="domain", value=None, device_id=None, label=None, notes=None
    )
    with pytest.raises(HTTPException) as missing:
        tracking_routes.create_tracked_subject(
            payload,
            SimpleNamespace(module_rete=True, is_super_admin=False, id=1),
            MagicMock(),
        )
    assert missing.value.status_code == 422


def test_tracking_reconciliation_and_arp_timeline(monkeypatch: pytest.MonkeyPatch) -> None:
    db = MagicMock()
    assert (
        tracking._find_matching_device_for_legacy_ip_subject(
            db, SimpleNamespace(entity_type="domain", device_id=None, value="example.test")
        )
        is None
    )
    assert (
        tracking._find_matching_device_for_legacy_ip_subject(
            db, SimpleNamespace(entity_type="ip", device_id=None, value="bad")
        )
        is None
    )
    assert (
        tracking._find_matching_device_for_legacy_ip_subject(
            db, SimpleNamespace(entity_type="ip", device_id=None, value="8.8.8.8")
        )
        is None
    )

    device = NetworkDevice(id=7, ip_address="10.0.0.7", display_name="Seven")
    legacy = SimpleNamespace(
        id=1,
        entity_type="ip",
        device_id=None,
        normalized_value="10.0.0.7",
        value="10.0.0.7",
        label="Legacy",
        notes="Notes",
        is_active=True,
    )
    canonical = SimpleNamespace(
        id=2,
        label=None,
        notes=None,
        is_active=False,
        device_id=None,
        value="",
    )
    monkeypatch.setattr(
        tracking, "_find_matching_device_for_legacy_ip_subject", lambda *_args: device
    )
    db.scalar.return_value = canonical
    result, changed = tracking._reconcile_legacy_ip_tracked_subject(db, legacy)
    assert changed is True
    assert result is canonical
    assert canonical.label == "Legacy"
    assert canonical.notes == "Notes"
    db.delete.assert_called_once_with(legacy)

    canonical.label = "Existing"
    canonical.notes = "Existing notes"
    db.delete.reset_mock()
    result, changed = tracking._reconcile_legacy_ip_tracked_subject(db, legacy)
    assert changed is True
    assert result.label == "Existing"
    assert result.notes == "Existing notes"

    monkeypatch.setattr(
        tracking, "_find_matching_device_for_legacy_ip_subject", lambda *_args: None
    )
    assert tracking._reconcile_legacy_ip_tracked_subject(db, legacy) == (legacy, False)

    empty_db = MagicMock()
    empty_db.scalars.return_value.all.return_value = []
    assert tracking._build_arp_timeline(empty_db, window_hours=24, limit=10) == []

    now = datetime.now(UTC)
    rows = [
        NetworkScanDevice(
            id=1,
            scan_id=1,
            device_id=None,
            ip_address="",
            mac_address="",
            status="offline",
            observed_at=now.replace(tzinfo=None),
        ),
        NetworkScanDevice(
            id=2,
            scan_id=2,
            device_id=5,
            ip_address="10.0.0.2",
            mac_address="aa",
            status="online",
            observed_at=now,
        ),
        NetworkScanDevice(
            id=3,
            scan_id=3,
            device_id=5,
            ip_address="10.0.0.3",
            mac_address="bb",
            status="online",
            observed_at=now,
        ),
        NetworkScanDevice(
            id=4,
            scan_id=4,
            device_id=5,
            ip_address="10.0.0.3",
            mac_address="bb",
            status="online",
            observed_at=now,
        ),
    ]
    timeline_db = MagicMock()
    timeline_db.scalars.side_effect = [
        SimpleNamespace(all=lambda: rows),
        SimpleNamespace(all=lambda: []),
    ]
    timeline = tracking._build_arp_timeline(timeline_db, window_hours=24, limit=10)
    assert timeline
    assert any("same_ip_multiple_macs" in item.suspicious_reasons for item in timeline)
    assert any(item.primary_ip_address is None for item in timeline)


def test_inferred_tracking_filters_and_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(UTC)
    device = NetworkDevice(
        id=1,
        ip_address="10.0.0.1",
        display_name="Internal",
        first_seen_at=now,
        last_seen_at=now,
    )
    events = []
    for index in range(12):
        events.append(
            NetworkFirewallEvent(
                id=index + 1,
                firewall_id=1,
                device_id=1 if index < 11 else None,
                event_type="allow.vpn" if index != 11 else "none",
                severity="info",
                protocol="TCP",
                message="vpn proxy tor encrypted dns",
                src_ip="10.0.0.1" if index % 2 == 0 else "bad-peer",
                dst_ip="8.8.8.8" if index % 2 == 0 else "10.0.0.1",
                raw_payload=json.dumps(
                    {"parsed": {"domain": "vpn.example", "url": "https://vpn.example/a"}}
                    if index % 3 == 0
                    else {"parsed": {}}
                ),
                observed_at=now,
            )
        )

    db = MagicMock()
    db.scalars.return_value.all.return_value = events
    db.get.side_effect = lambda _model, key: device if key == 1 else None
    monkeypatch.setattr(inference, "_active_detection_watchlist_entries", lambda _db: [])
    monkeypatch.setattr(
        inference,
        "_get_active_tracked_subject_map",
        lambda _db: {("domain", "skip.example"): object()},
    )
    monkeypatch.setattr(
        inference,
        "_find_internal_device_by_ip",
        lambda _db, value: device if value == "10.0.0.1" else None,
    )
    monkeypatch.setattr(inference, "get_device_scan_history", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        inference, "_resolve_firewall_event_endpoint_labels", lambda *_args, **_kwargs: (None, None)
    )
    monkeypatch.setattr(
        inference, "_extract_event_traffic", lambda *_args, **_kwargs: (1, 2, "8.8.8.8")
    )
    monkeypatch.setattr(
        inference,
        "event_detection_tags",
        lambda event_type, *_args, **_kwargs: (
            []
            if event_type == "none"
            else [
                "vpn_suspected",
                "proxy_suspected",
                "tor_suspected",
                "encrypted_dns",
            ]
        ),
    )

    items = inference._build_inferred_tracked_subjects(db, window_hours=24)
    assert {item.entity_type for item in items} >= {"device", "domain", "url", "ip"}
    assert (
        inference._build_inferred_tracked_subjects(
            db, window_hours=24, entity_type="domain", search="missing"
        )
        == []
    )
    assert inference._find_internal_device_by_ip(db, None) is None


def test_inferred_tracking_external_and_active_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(UTC)
    events = [
        NetworkFirewallEvent(
            id=1,
            firewall_id=1,
            device_id=None,
            event_type="vpn",
            severity="info",
            protocol="TCP",
            message="vpn",
            src_ip=None,
            dst_ip="not-an-ip",
            raw_payload=json.dumps({"parsed": {"domain": "active.example"}}),
            observed_at=now,
        ),
        NetworkFirewallEvent(
            id=2,
            firewall_id=1,
            device_id=None,
            event_type="vpn",
            severity="info",
            protocol="TCP",
            message="vpn",
            src_ip=None,
            dst_ip=None,
            raw_payload="{}",
            observed_at=now,
        ),
    ]
    db = MagicMock()
    db.scalars.return_value.all.return_value = events
    db.get.return_value = None
    monkeypatch.setattr(inference, "_active_detection_watchlist_entries", lambda _db: [])
    monkeypatch.setattr(
        inference,
        "_get_active_tracked_subject_map",
        lambda _db: {("domain", "active.example"): object()},
    )
    monkeypatch.setattr(inference, "_find_internal_device_by_ip", lambda *_args: None)
    monkeypatch.setattr(
        inference, "event_detection_tags", lambda *_args, **_kwargs: ["vpn_suspected"]
    )

    assert inference._build_inferred_tracked_subjects(db, window_hours=24) == []
    assert inference._find_internal_device_by_ip(MagicMock(), None) is None


def test_inferred_tracking_false_detection_flags_and_matching_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FlippingTags(list):
        def __init__(self):
            super().__init__(["other"])
            self.bool_calls = 0

        def __bool__(self):
            self.bool_calls += 1
            return self.bool_calls != 2

    now = datetime.now(UTC)
    device = NetworkDevice(
        id=1, ip_address="10.0.0.1", display_name="Internal", first_seen_at=now, last_seen_at=now
    )
    events = [
        NetworkFirewallEvent(
            id=1,
            firewall_id=1,
            device_id=1,
            event_type="deny.rule",
            severity="info",
            protocol="TCP",
            message="suspicious",
            src_ip="4.4.4.4",
            dst_ip="5.5.5.5",
            raw_payload=json.dumps({"parsed": {"domain": "match.example"}}),
            observed_at=now,
        )
    ]
    db = MagicMock()
    db.scalars.return_value.all.return_value = events
    db.get.return_value = device
    monkeypatch.setattr(inference, "_active_detection_watchlist_entries", lambda _db: [])
    monkeypatch.setattr(inference, "_get_active_tracked_subject_map", lambda _db: {})
    monkeypatch.setattr(inference, "_find_internal_device_by_ip", lambda *_args: None)
    monkeypatch.setattr(inference, "get_device_scan_history", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        inference, "_resolve_firewall_event_endpoint_labels", lambda *_args, **_kwargs: (None, None)
    )
    monkeypatch.setattr(inference, "_extract_event_traffic", lambda *_args, **_kwargs: (0, 0, None))
    monkeypatch.setattr(inference, "event_detection_tags", lambda *_args, **_kwargs: FlippingTags())

    items = inference._build_inferred_tracked_subjects(db, window_hours=24, search="match.example")
    assert any(item.entity_type == "domain" for item in items)


def test_activity_summary_malformed_bytes_all_tags_and_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    matching = NetworkFirewallEvent(
        id=1,
        firewall_id=1,
        event_type="allow.drop",
        severity="info",
        protocol="TCP",
        message="all tags",
        src_ip="8.8.8.8",
        dst_ip="1.1.1.1",
        raw_payload=json.dumps({"parsed": {"bytes_sent": "bad", "bytes_received": []}}),
        observed_at=now,
    )
    skipped = NetworkFirewallEvent(
        id=2,
        firewall_id=1,
        event_type="other",
        severity="info",
        protocol="TCP",
        message="skip",
        src_ip="2.2.2.2",
        dst_ip="3.3.3.3",
        raw_payload="{}",
        observed_at=now,
    )
    db = MagicMock()
    db.scalars.return_value.all.return_value = [skipped, matching]
    monkeypatch.setattr(tracking, "_active_detection_watchlist_entries", lambda _db: [])
    monkeypatch.setattr(
        tracking,
        "event_detection_tags",
        lambda *_args, **_kwargs: [
            "vpn_suspected",
            "proxy_suspected",
            "tor_suspected",
            "encrypted_dns",
        ],
    )
    subject = SimpleNamespace(
        entity_type="ip", device_id=None, value="8.8.8.8", normalized_value="8.8.8.8"
    )
    summary = tracking._build_tracked_subject_activity_summary(
        db, subject, window_hours=24, limit=0
    )
    assert summary.total_events == 1
    assert summary.recent_events == []
    assert summary.proxy_suspected_events == 1
    assert summary.tor_suspected_events == 1
    assert summary.encrypted_dns_events == 1

    db.scalars.return_value.all.return_value = []
    other = SimpleNamespace(entity_type="other", device_id=None, value="x", normalized_value="x")
    assert tracking._build_tracked_subject_activity_summary(db, other).total_events == 0

    db.scalars.return_value.all.return_value = [matching]
    monkeypatch.setattr(
        tracking, "event_detection_tags", lambda *_args, **_kwargs: ["proxy_suspected"]
    )
    proxy_only = tracking._build_tracked_subject_activity_summary(
        db, subject, window_hours=24, limit=0
    )
    assert proxy_only.vpn_suspected_events == 0
    assert proxy_only.proxy_suspected_events == 1


def test_inferred_assigned_arp_subject_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    assert (
        inference._build_inferred_assigned_arp_subjects(
            MagicMock(), active_subjects={}, window_hours=24, entity_type="domain"
        )
        == []
    )

    now = datetime.now(UTC)
    assigned = ApplicationUser(username="assigned", full_name="Assigned Person")
    ignored = NetworkDevice(
        id=1,
        ip_address="10.0.0.1",
        metadata_sources="{}",
        assigned_user=assigned,
        assigned_user_id=1,
        status="online",
        first_seen_at=now,
        last_seen_at=now,
    )
    active = NetworkDevice(
        id=2,
        ip_address="10.0.0.2",
        metadata_sources='{"discovery":"arp"}',
        assigned_user=assigned,
        assigned_user_id=1,
        status="online",
        first_seen_at=now,
        last_seen_at=now,
    )
    candidate = NetworkDevice(
        id=3,
        ip_address="10.0.0.3",
        metadata_sources='{"discovery":"arp"}',
        assigned_user=assigned,
        assigned_user_id=1,
        status="online",
        first_seen_at=now,
        last_seen_at=now,
    )
    db = MagicMock()
    db.scalars.return_value.all.return_value = [ignored, active, candidate]
    monkeypatch.setattr(
        inference,
        "_build_tracked_subject_activity_summary",
        lambda *_args, **kwargs: tracking.NetworkTrackedSubjectActivitySummary(
            window_hours=kwargs["window_hours"]
        ),
    )
    monkeypatch.setattr(inference, "get_device_scan_history", lambda *_args, **_kwargs: [])

    result = inference._build_inferred_assigned_arp_subjects(
        db,
        active_subjects={("device", "2"): object()},
        window_hours=24,
        search="Assigned",
    )
    assert [item.device_id for item in result] == [3]
    assert (
        inference._build_inferred_assigned_arp_subjects(
            db, active_subjects={}, window_hours=24, search="not-found"
        )
        == []
    )


def test_peer_resolution_and_statistics_item_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    traffic._resolve_peer_label.cache_clear()
    assert traffic._resolve_peer_label(None) is None
    assert traffic._resolve_peer_label("bad") is None
    monkeypatch.setattr(
        traffic.socket, "gethostbyaddr", lambda _ip: (" resolved.example. ", [], [])
    )
    assert traffic._resolve_peer_label("8.8.8.8") == "resolved.example"

    traffic._resolve_peer_label.cache_clear()
    monkeypatch.setattr(traffic.socket, "gethostbyaddr", MagicMock(side_effect=OSError))
    assert traffic._resolve_peer_label("10.0.0.1") is None
    monkeypatch.setattr(traffic.urllib.request, "urlopen", MagicMock(side_effect=OSError))
    assert traffic._resolve_peer_label("8.8.4.4") is None

    event = NetworkFirewallEvent(
        raw_payload=json.dumps({"parsed": {"url": "https://peer.example/a"}})
    )
    assert traffic._extract_peer_hint(event, peer_ip="8.8.8.8") == "peer.example"
    event.raw_payload = json.dumps({"parsed": {"domain": " domain.example "}})
    assert traffic._extract_peer_hint(event, peer_ip=None) == "domain.example"
    event.raw_payload = "{}"
    monkeypatch.setattr(traffic, "_resolve_peer_label", lambda _ip: "rdap-label")
    assert traffic._extract_peer_hint(event, peer_ip="8.8.8.8") == "rdap-label"
    assert traffic._extract_peer_hint(event, peer_ip=None) is None

    event.raw_payload = json.dumps({"parsed": {"url": "not-a-url"}})
    monkeypatch.setattr(traffic, "_resolve_peer_label", lambda _ip: "fallback")
    assert traffic._extract_peer_hint(event, peer_ip="8.8.8.8") == "fallback"

    items = traffic._counter_to_items(traffic.Counter({"": 3, "x": 2}), labels={"x": "X"})
    assert [(item.key, item.label) for item in items] == [("x", "X")]
    mapped = traffic._traffic_map_to_items(
        {
            "8.8.8.8": {
                "label": None,
                "ip_address": "8.8.8.8",
                "device_id": None,
                "events_count": 1,
                "bytes_in": 2,
                "bytes_out": 3,
                "bytes_total": 5,
            }
        }
    )
    assert mapped[0].label == "8.8.8.8"


def test_peer_rdap_payload_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(traffic.socket, "gethostbyaddr", lambda _ip: (" . ", [], []))
    traffic._resolve_peer_label.cache_clear()
    assert traffic._resolve_peer_label("10.0.0.1") is None

    payloads = [
        {"name": "Network Name"},
        {
            "entities": [
                None,
                {},
                {
                    "vcardArray": [
                        "vcard",
                        [None, ["role", {}, "text", "x"], ["fn", {}, "text", "Entity Name"]],
                    ]
                },
            ]
        },
        {
            "entities": [{"vcardArray": ["vcard", [["role", {}, "text", "x"]]]}, None],
            "handle": "Handle",
        },
        {},
    ]
    for expected, payload in zip(
        ["Network Name", "Entity Name", "Handle", None], payloads, strict=True
    ):
        traffic._resolve_peer_label.cache_clear()
        monkeypatch.setattr(
            traffic.urllib.request,
            "urlopen",
            lambda *_args, payload=payload, **_kwargs: JsonResponse(json.dumps(payload).encode()),
        )
        assert traffic._resolve_peer_label("8.8.8.8") == expected


def test_device_traffic_summary_rich_events(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(UTC)
    device = NetworkDevice(id=1, ip_address="10.0.0.1", display_name="Source")
    events = [
        NetworkFirewallEvent(
            id=index + 1,
            event_type="allow.rule"
            if index % 3 == 0
            else "drop.rule"
            if index % 3 == 1
            else "other",
            severity="info",
            protocol="TCP",
            src_ip="10.0.0.1",
            dst_ip=None if index == 8 else f"8.8.8.{index}",
            raw_payload="{}",
            observed_at=now,
        )
        for index in range(9)
    ]
    db = MagicMock()
    db.scalars.return_value.all.return_value = events
    monkeypatch.setattr(traffic, "_get_active_tracked_subject_map", lambda _db: {})
    monkeypatch.setattr(
        traffic,
        "_extract_event_traffic",
        lambda event, **_kwargs: (1, 2, event.dst_ip),
    )
    monkeypatch.setattr(traffic, "_extract_firewall_event_parsed", lambda _event: {})
    monkeypatch.setattr(
        traffic,
        "_extract_peer_hint",
        lambda event, **_kwargs: "peer-label" if event.id == 1 else None,
    )
    monkeypatch.setattr(traffic, "_resolve_peer_label", lambda _ip: "resolved")

    result = traffic._build_device_traffic_summary(db, device)
    assert result.total_events == 9
    assert len(result.recent_events) == 8
    assert result.allowed_events == 3
    assert result.blocked_events == 3
    assert any(peer.label == "peer-label" for peer in result.top_peers)
    assert any(peer.label == "resolved" for peer in result.top_peers)


def test_network_statistics_rich_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(UTC)
    placeholder = ApplicationUser(
        id=1,
        username="placeholder",
        email="placeholder@users.local",
        full_name=None,
        office_location="HQ",
        is_active=False,
    )
    active = NetworkDevice(
        id=1,
        ip_address="10.0.0.1",
        display_name="Active",
        lifecycle_state="active",
        status="online",
        is_known_device=False,
        is_monitored=True,
        assigned_user_id=1,
        assigned_user=placeholder,
        device_type="workstation",
        vendor="Vendor",
    )
    retired = NetworkDevice(
        id=2,
        ip_address="10.0.0.2",
        lifecycle_state="retired",
        status="offline",
        is_known_device=True,
        is_monitored=False,
    )
    plain = NetworkDevice(
        id=3,
        ip_address="10.0.0.3",
        lifecycle_state="active",
        status="offline",
        is_known_device=True,
        is_monitored=False,
        location_hint="Branch",
    )
    rows = [
        {
            "event_type": "allow.rule",
            "severity": None,
            "protocol": None,
            "raw_payload": json.dumps(
                {
                    "parsed": {
                        "bytes_sent": "bad",
                        "bytes_received": "bad",
                        "fw_rule_name": " Allow ",
                        "domain": "Example.COM",
                    }
                }
            ),
            "src_ip": "10.0.0.1",
            "dst_ip": "8.8.8.8",
            "device_id": 1,
            "observed_at": now,
        },
        {
            "event_type": "drop.rule",
            "severity": "danger",
            "protocol": "tcp",
            "raw_payload": json.dumps(
                {
                    "parsed": {
                        "bytes_sent": "5",
                        "bytes_received": "7",
                        "url": "https://url.example/path",
                    }
                }
            ),
            "src_ip": "unknown",
            "dst_ip": "bad-peer",
            "device_id": None,
            "observed_at": now,
        },
        {
            "event_type": "other",
            "severity": "info",
            "protocol": "udp",
            "raw_payload": json.dumps({"parsed": {"bytes_sent": None, "bytes_received": []}}),
            "src_ip": None,
            "dst_ip": None,
            "device_id": None,
            "observed_at": now,
        },
    ]
    db = MagicMock()
    db.scalars.return_value.all.return_value = [active, retired, plain]
    db.execute.return_value.mappings.return_value = rows
    monkeypatch.setattr(traffic, "_get_active_tracked_subject_map", lambda _db: {})
    monkeypatch.setattr(
        traffic, "list_network_firewalls", lambda _db: [SimpleNamespace(status="online")]
    )
    monkeypatch.setattr(
        traffic,
        "list_network_alerts",
        lambda *_args, **_kwargs: [SimpleNamespace(severity="danger")],
    )

    result = traffic._build_network_statistics_summary(db)
    assert result.total_devices == 3
    assert result.retired_devices == 1
    assert result.placeholder_profiles == 1
    assert result.allowed_events == 1
    assert result.blocked_events == 1
    assert result.unique_domains == 2
    assert result.unique_external_peers == 1


def test_statistics_covers_destination_device_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    class ChangingIpDevice:
        id = 1
        lifecycle_state = "active"
        status = "online"
        is_known_device = True
        is_monitored = False
        assigned_user_id = None
        assigned_user = None
        device_type = None
        vendor = None
        location_hint = None

        def __init__(self, *, match_destination: bool = True):
            self.calls = 0
            self.match_destination = match_destination

        @property
        def ip_address(self):
            self.calls += 1
            third = "destination" if self.match_destination else "also-different"
            return ["source-key", "different", third, "stable", "stable"][min(self.calls - 1, 4)]

    device = ChangingIpDevice()
    row = {
        "event_type": "other",
        "severity": "info",
        "protocol": "tcp",
        "raw_payload": "{}",
        "src_ip": "source-key",
        "dst_ip": "destination",
        "device_id": 1,
        "observed_at": datetime.now(UTC),
    }
    db = MagicMock()
    db.scalars.return_value.all.return_value = [device]
    db.execute.return_value.mappings.return_value = [row]
    monkeypatch.setattr(traffic, "_get_active_tracked_subject_map", lambda _db: {})
    monkeypatch.setattr(traffic, "list_network_firewalls", lambda _db: [])
    monkeypatch.setattr(traffic, "list_network_alerts", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(traffic, "_resolve_device_label", lambda _device: ("Changing", "device"))

    result = traffic._build_network_statistics_summary(db)

    assert result.bytes_in == 0

    nonmatching = ChangingIpDevice(match_destination=False)
    db.scalars.return_value.all.return_value = [nonmatching]
    second = traffic._build_network_statistics_summary(db)
    assert second.total_events == 1


def test_firewall_classification_serializers_and_common(monkeypatch: pytest.MonkeyPatch) -> None:
    cases = {
        "firewall.rule": "firewall",
        "remote.vpn": "vpn",
        "network.ips": "ips",
        "user.auth": "authentication",
        "system_health.cpu": "system",
        "content_filtering.web": "content_filtering",
        "anti-virus.scan": "anti-virus",
        "custom.event": "custom",
        "": "other",
    }
    for event_type, expected in cases.items():
        assert (
            firewalls._classify_sophos_log_family_from_values(event_type=event_type, parsed=None)
            == expected
        )
    assert (
        firewalls._classify_sophos_log_family_from_values(
            event_type="other", parsed={"log_type": "VPN"}
        )
        == "vpn"
    )

    user = SimpleNamespace(module_rete=False, is_super_admin=False)
    with pytest.raises(HTTPException):
        common._require_network_module(user)
    common._require_network_module(SimpleNamespace(module_rete=False, is_super_admin=True))

    alert = NetworkAlert(
        id=1,
        alert_type="test",
        severity="info",
        status="open",
        verification_status="unverified",
        title="Title",
        message="Message",
        assigned_to_user=ApplicationUser(username="assigned"),
        created_at=datetime.now(UTC),
    )
    serialized = firewalls._serialize_alert(alert)
    assert serialized.assigned_to_username == "assigned"

    policy = SimpleNamespace(
        syslog_enabled=True,
        snmp_enabled=False,
        operation_window_enabled=False,
        operation_start_hour=0,
        operation_end_hour=24,
        operation_timezone="Europe/Rome",
        is_within_window=True,
        syslog_should_ingest=True,
        snmp_should_poll=False,
    )
    monkeypatch.setattr(common, "build_sophos_runtime_policy", lambda _config: policy)
    result = common._serialize_sophos_config(SimpleNamespace(updated_at=None))
    assert result.syslog_effective_enabled is True

    event = NetworkFirewallEvent(
        event_type="firewall.rule", raw_payload='{"parsed":{"log_type":"Firewall"}}'
    )
    assert firewalls._classify_sophos_log_family(event) == "firewall"


def test_firewall_coverage_caps_examples_and_updates_latest() -> None:
    now = datetime.now(UTC)
    rows = [
        {"event_type": f"custom.{index}", "events_count": index, "last_observed_at": now}
        for index in range(5)
    ]
    rows.append({"event_type": "custom.0", "events_count": 1, "last_observed_at": now})
    db = MagicMock()
    db.execute.return_value.mappings.return_value = rows

    result = firewalls._build_firewall_log_coverage_summary(
        db, firewall=SimpleNamespace(id=9), window_hours=24
    )
    custom = next(item for item in result.additional_families if item.family_key == "custom")
    assert len(custom.examples) == 3
    assert custom.observed_count == 11


def test_scan_serializers_cover_reference_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    scan = NetworkScan(
        id=1,
        network_range="10.0.0.0/24",
        scan_type="incremental",
        status="completed",
        hosts_scanned=0,
        active_hosts=0,
        discovered_devices=0,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    monkeypatch.setattr(
        scans,
        "get_scan_delta",
        lambda _db, _id: {
            "new_devices_count": 0,
            "missing_devices_count": 0,
            "changed_devices_count": 0,
        },
    )
    assert scans._serialize_scan(1, scan, MagicMock()).id == 1

    snapshot = NetworkScanDevice(
        id=2,
        scan_id=1,
        device_id=None,
        ip_address="10.0.0.9",
        hostname="snapshot-host",
        metadata_sources="{}",
        status="online",
        observed_at=datetime.now(UTC),
    )
    db = MagicMock()
    db.scalar.return_value = None
    assert scans._serialize_scan_device(snapshot, db).resolved_label == "snapshot-host"
