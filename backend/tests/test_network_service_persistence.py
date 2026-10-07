from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.modules.network import services
from app.modules.network.models import NetworkAlert, NetworkDevice, NetworkScanDevice


@pytest.fixture
def network_db(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        services, "_collect_enrichment", lambda *args: services.EnrichmentMetadata()
    )
    monkeypatch.setattr(services, "_resolve_mac_address", lambda address, mac: mac)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _device(db, address="10.0.0.1", **values):
    device = NetworkDevice(ip_address=address, **values)
    db.add(device)
    db.flush()
    return device


def _alert(db, device, kind="UNKNOWN_DEVICE", **values):
    alert = NetworkAlert(device_id=device.id, alert_type=kind, title=kind, **values)
    db.add(alert)
    db.flush()
    return alert


def test_device_filters_counts_pagination_and_user_search(network_db):
    user = ApplicationUser(
        username="engineer",
        full_name="Test Operator",
        email="engineer@example.com",
        password_hash="unused",
    )
    network_db.add(user)
    network_db.flush()
    known = _device(
        network_db,
        is_known_device=True,
        assigned_user_id=user.id,
        status="online",
        vendor="Cisco",
        device_type="switch",
    )
    unknown = _device(
        network_db, "10.0.0.2", status="offline", metadata_sources='{"discovery": "arp"}'
    )
    retired = _device(network_db, "10.0.0.3", lifecycle_state="retired", status="offline")
    plan = services.create_floor_plan(network_db, name=" Main ", floor_label=" 1 ", building=" HQ ")
    services.upsert_device_position(network_db, device_id=known.id, floor_plan_id=plan.id, x=1, y=2)
    cases = [
        ({"search": " Operator "}, [known]),
        ({"status": "online"}, [known]),
        ({"lifecycle_state": "retired"}, [retired]),
        ({"assignment": "assigned"}, [known]),
        ({"assignment": "unassigned"}, [unknown]),
        ({"known": "known"}, [known]),
        ({"known": "unknown"}, [unknown, retired]),
        ({"known": "arp_unknown"}, [unknown]),
        ({"vendor": "Cisco"}, [known]),
        ({"device_type": "switch"}, [known]),
        ({"floor_plan_id": plan.id}, [known]),
        ({"search": "missing"}, []),
        ({"known": "unrecognized", "assignment": "unrecognized"}, [unknown, retired, known]),
    ]
    for filters, expected in cases:
        items, total = services.list_network_devices(network_db, **filters)
        assert items == expected
        assert total == len(expected)
    items, total = services.list_network_devices(network_db, page=2, page_size=1)
    assert items == [retired]
    assert total == 3


def test_alert_resolution_update_and_assignment_semantics(network_db):
    device = _device(network_db)
    alert = _alert(network_db, device, severity="warning")
    other = _alert(network_db, device, "MISSING_DEVICE", severity="danger")
    assert services.list_network_alerts(network_db, severity="warning", status="open") == [alert]
    assert services.list_network_alerts(network_db) == [other, alert]
    services._resolve_alerts_for_device(network_db, device_id=None, alert_types=["UNKNOWN_DEVICE"])
    assert alert.status == "open"
    assert services.update_network_alert(network_db, 999) is None
    result = services.update_network_alert(
        network_db,
        alert.id,
        status="resolved",
        verification_status="confirmed",
        verification_notes="checked",
    )
    assert result.status == "resolved"
    assert result.acknowledged_at is not None
    assert result.reviewed_at is not None
    assert result.verification_notes == "checked"
    result = services.update_network_alert(network_db, alert.id, status="open")
    assert result.acknowledged_at is None
    assert services.update_network_alert(network_db, alert.id).verification_notes == "checked"


@pytest.mark.parametrize("known,status", [(True, "online"), (False, "offline"), (False, "online")])
def test_sync_alert_state_resolves_only_relevant_alerts(network_db, known, status):
    device = _device(network_db, is_known_device=known, status=status)
    unknown = _alert(network_db, device)
    missing = _alert(network_db, device, "MISSING_DEVICE")
    services.sync_network_device_alert_state(network_db, device)
    network_db.flush()
    assert unknown.status == ("resolved" if known else "open")
    assert missing.status == ("open" if known else "resolved")
    assert len(services.list_network_alerts(network_db)) == 2


def test_floor_positions_upsert_and_read_models(network_db):
    device = _device(network_db)
    plan = services.create_floor_plan(
        network_db,
        name=" Office ",
        floor_label=" Ground ",
        svg_content="<svg/>",
        width=12,
        height=8,
    )
    assert (plan.name, plan.floor_label, plan.building) == ("Office", "Ground", None)
    position = services.upsert_device_position(
        network_db, device_id=device.id, floor_plan_id=plan.id, x=1, y=2
    )
    updated = services.upsert_device_position(
        network_db, device_id=device.id, floor_plan_id=plan.id, x=3, y=4, label="rack"
    )
    assert position.id == updated.id
    assert (updated.x, updated.y, updated.label) == (3, 4, "rack")
    assert services.get_device_positions(network_db, device.id) == [position]
    assert services.get_floor_plan_devices(network_db, plan.id) == [(position, device)]
    summary = services.get_network_dashboard_summary(network_db)
    assert summary["total_devices"] == 1
    assert summary["floor_plans"] == 1
    assert summary["latest_scan_at"] is None


def test_scan_history_deltas_and_unchanged_snapshots(network_db, monkeypatch):
    discovery = MagicMock(
        return_value=[services.DiscoveredHost("10.0.0.1", mac_address="aa:bb:cc:dd:ee:ff")]
    )
    monkeypatch.setattr(services, "discover_hosts", discovery)
    first = services.run_network_scan(network_db, scan_type="unsupported")
    assert first.scan.scan_type == "incremental"
    discovery.assert_called_once_with(services.settings.network_range, scan_type="incremental")
    second = services.run_network_scan(network_db, discovered_hosts=discovery.return_value)
    assert services.list_network_scans(network_db) == [second.scan, first.scan]
    device = network_db.scalar(select(NetworkDevice))
    history = services.get_device_scan_history(network_db, device.id, limit=1)
    assert history[0].scan_id == second.scan.id
    summary, changes = services.get_scan_diff(network_db, first.scan.id, second.scan.id)
    assert summary == {
        "new_devices_count": 0,
        "missing_devices_count": 0,
        "changed_devices_count": 0,
    }
    assert changes == []
    scan, snapshots, delta = services.get_network_scan_detail(network_db, first.scan.id)
    assert scan == first.scan
    assert len(snapshots) == 1
    assert delta["new_devices_count"] == 1
    assert services.get_network_scan_detail(network_db, 999) == (
        None,
        [],
        {"new_devices_count": 0, "missing_devices_count": 0, "changed_devices_count": 0},
    )
    assert services._latest_scan_before(network_db, second.scan.id) == first.scan.id


def test_existing_known_device_returns_online_and_resolves_alerts(network_db):
    device = _device(
        network_db, is_known_device=True, status="offline", hostname="kept", open_ports="80"
    )
    alert = _alert(network_db, device, "MISSING_DEVICE")
    result = services.run_network_scan(
        network_db, discovered_hosts=[services.DiscoveredHost(device.ip_address)]
    )
    assert result.alerts_created == 0
    assert device.status == "online"
    assert (device.hostname, device.open_ports) == ("kept", "80")
    assert alert.status == "resolved"


@pytest.mark.parametrize("recent", [False, True])
def test_repeated_offline_scan_does_not_duplicate_alerts(network_db, monkeypatch, recent):
    now = datetime.now(UTC)
    device = _device(
        network_db,
        is_known_device=True,
        status="offline",
        first_seen_at=now - timedelta(days=40),
        last_seen_at=now - timedelta(hours=2) if recent else now - timedelta(days=30),
    )
    monkeypatch.setattr(
        services,
        "_recent_bypass_signal_tags_for_device",
        lambda *args, **kwargs: ["vpn_suspected"] if recent else [],
    )
    first = services.run_network_scan(network_db, discovered_hosts=[])
    second = services.run_network_scan(network_db, discovered_hosts=[])
    assert first.alerts_created == 1
    assert second.alerts_created == 0
    assert device.status == "offline"


def test_recent_offline_device_without_bypass_resolves_transient_alert(network_db):
    now = datetime.now(UTC)
    device = _device(
        network_db,
        is_known_device=True,
        first_seen_at=now - timedelta(days=10),
        last_seen_at=now - timedelta(hours=1),
    )
    alert = _alert(network_db, device, "VPN_BYPASS_TRANSIENT_DEVICE")
    result = services.run_network_scan(network_db, discovered_hosts=[])
    assert result.alerts_created == 0
    assert alert.status == "resolved"


def test_recent_arp_disappearance_correlates_bypass_and_deduplicates(network_db, monkeypatch):
    now = datetime.now(UTC)
    device = _device(
        network_db,
        is_known_device=True,
        metadata_sources='{"discovery": "arp"}',
        first_seen_at=now - timedelta(hours=2),
        last_seen_at=now - timedelta(minutes=5),
    )
    monkeypatch.setattr(
        services,
        "_recent_bypass_signal_tags_for_device",
        lambda *args, **kwargs: ["vpn_suspected", "normal"],
    )
    services.run_network_scan(network_db, discovered_hosts=[], scan_type="arp")
    second = services.run_network_scan(network_db, discovered_hosts=[], scan_type="arp")
    assert second.alerts_created == 0
    alerts = services.list_network_alerts(network_db)
    ephemeral = next(alert for alert in alerts if alert.alert_type == "ARP_EPHEMERAL_DEVICE")
    assert ephemeral.severity == "danger"
    assert "Correlazione bypass: vpn_suspected" in ephemeral.message
    assert device.status == "offline"


def test_arp_identity_alerts_are_not_duplicated(network_db):
    hosts = [
        services.DiscoveredHost("10.0.0.1", mac_address="first"),
        services.DiscoveredHost("10.0.0.2", mac_address="second"),
    ]
    services.run_network_scan(network_db, discovered_hosts=hosts, scan_type="arp")
    hosts[0].mac_address = "second"
    services.run_network_scan(network_db, discovered_hosts=hosts, scan_type="arp")
    alerts = services.list_network_alerts(network_db)
    assert any(alert.alert_type == "ARP_MAC_CHANGE_SUSPECTED" for alert in alerts)
    assert any(alert.alert_type == "ARP_IP_ROTATION_SUSPECTED" for alert in alerts)
    for device in network_db.scalars(select(NetworkDevice)):
        device.is_monitored = False
    result = services.run_network_scan(network_db, discovered_hosts=[], scan_type="arp")
    assert result.alerts_created == 0
    assert len(services.list_network_alerts(network_db)) == len(alerts)


def test_scan_tolerates_snapshots_with_deleted_device_references(network_db, monkeypatch):
    snapshots = [NetworkScanDevice(device_id=None), NetworkScanDevice(device_id=999)]
    monkeypatch.setattr(services, "_create_or_refresh_snapshot_rows", lambda db, scan: snapshots)
    result = services.run_network_scan(network_db, discovered_hosts=[])
    assert result.devices_upserted == 0
    assert result.alerts_created == 0
    assert result.scan.status == "completed"


def test_bypass_tag_history_is_ordered_and_deduplicated(network_db, monkeypatch):
    monkeypatch.setattr(services, "_active_detection_watchlist_entries", lambda db: [])
    monkeypatch.setattr(
        services, "event_detection_tags", lambda *args, **kwargs: ["vpn_suspected", "vpn_suspected"]
    )
    fake_db = MagicMock()
    fake_db.scalars.return_value.all.return_value = [
        SimpleNamespace(
            raw_payload='{"parsed":{}}', event_type="web", message="vpn", protocol="tcp"
        )
    ]
    result = services._recent_bypass_signal_tags_for_device(
        fake_db, device_id=1, observed_since=datetime.now(UTC)
    )
    assert result == ["vpn_suspected"]
    services._ensure_detection_watchlist_seeded(network_db)
    services._ensure_detection_watchlist_seeded(network_db)
