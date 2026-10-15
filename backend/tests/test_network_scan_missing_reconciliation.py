"""Characterization of the missing-monitored-device reconciliation in run_network_scan."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.network import services
from app.modules.network.models import NetworkAlert, NetworkDevice

ALL_PRESENCE_ALERTS = [
    "MISSING_DEVICE",
    "device_offline",
    "VPN_BYPASS_TRANSIENT_DEVICE",
    "ARP_EPHEMERAL_DEVICE",
    "ARP_MAC_CHANGE_SUSPECTED",
    "ARP_IP_ROTATION_SUSPECTED",
]


class _Recorder:
    def __init__(self, monkeypatch, tags_by_device=None):
        self.events: list[tuple] = []
        self.tags_by_device = tags_by_device or {}
        self.commits = 0
        real_create = services._create_alert
        real_resolve = services._resolve_alerts_for_device
        real_snapshot = services._create_or_refresh_snapshot_rows

        def create(db, **kwargs):
            created = real_create(db, **kwargs)
            self.events.append(("create", kwargs["device_id"], kwargs["alert_type"], created))
            return created

        def resolve(db, *, device_id, alert_types):
            self.events.append(("resolve", device_id, tuple(alert_types)))
            return real_resolve(db, device_id=device_id, alert_types=alert_types)

        def bypass(db, *, device_id, observed_since):
            self.events.append(("bypass", device_id, observed_since))
            return list(self.tags_by_device.get(device_id, []))

        def snapshot(db, scan):
            self.events.append(("snapshot",))
            return real_snapshot(db, scan)

        monkeypatch.setattr(services, "_create_alert", create)
        monkeypatch.setattr(services, "_resolve_alerts_for_device", resolve)
        monkeypatch.setattr(services, "_recent_bypass_signal_tags_for_device", bypass)
        monkeypatch.setattr(services, "_create_or_refresh_snapshot_rows", snapshot)

    def reconciliation(self):
        return self.events[: self.events.index(("snapshot",))]

    def count_commits(self, db, monkeypatch):
        real_commit = db.commit

        def commit():
            self.commits += 1
            return real_commit()

        monkeypatch.setattr(db, "commit", commit)


FROZEN_NOW = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
LOOKBACK_SINCE = FROZEN_NOW - timedelta(hours=6)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FROZEN_NOW if tz is not None else FROZEN_NOW.replace(tzinfo=None)


@pytest.fixture
def frozen_now(monkeypatch):
    monkeypatch.setattr(services, "datetime", _FrozenDatetime)
    return FROZEN_NOW


def _session_factory(autoflush: bool):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=autoflush)


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(
        services,
        "_collect_enrichment",
        lambda ip_address, open_ports: services.EnrichmentMetadata(),
    )
    monkeypatch.setattr(services.settings, "network_missing_device_alert_days", 15)
    engine, factory = _session_factory(autoflush=False)
    session = factory()
    yield session
    session.close()
    engine.dispose()


def _device(
    db,
    ip,
    *,
    known=True,
    arp=False,
    first_seen=None,
    last_seen=None,
    status="online",
    monitored=True,
):
    now = datetime.now(UTC)
    device = NetworkDevice(
        ip_address=ip,
        is_known_device=known,
        status=status,
        is_monitored=monitored,
        metadata_sources='{"discovery": "arp"}' if arp else None,
        first_seen_at=first_seen or now - timedelta(days=30),
        last_seen_at=last_seen or now - timedelta(days=20),
    )
    db.add(device)
    db.commit()
    return device


def _open_alert(db, device, alert_type):
    db.add(
        NetworkAlert(
            device_id=device.id,
            alert_type=alert_type,
            title=alert_type,
            severity="warning",
            status="open",
        )
    )
    db.commit()


def _alerts(db, alert_type=None):
    query = select(NetworkAlert).order_by(NetworkAlert.id.asc())
    if alert_type:
        query = query.where(NetworkAlert.alert_type == alert_type)
    return db.scalars(query).all()


def test_known_device_missing_past_threshold_creates_missing_alert_and_marks_offline(
    db, monkeypatch
) -> None:
    recorder = _Recorder(monkeypatch)
    device = _device(db, "10.1.0.1", last_seen=datetime.now(UTC) - timedelta(days=16))

    result = services.run_network_scan(db, discovered_hosts=[])

    db.refresh(device)
    assert result.alerts_created == 1
    assert device.status == "offline"
    assert device.last_scan_id == result.scan.id
    [alert] = _alerts(db, "MISSING_DEVICE")
    assert (alert.severity, alert.status, alert.scan_id) == ("danger", "open", result.scan.id)
    assert alert.title == "Dispositivo conosciuto assente dalla rete: 10.1.0.1"
    assert alert.message.startswith("Ultimo avvistamento: ")
    assert recorder.reconciliation() == [
        ("resolve", device.id, ("ARP_EPHEMERAL_DEVICE",)),
        ("create", device.id, "MISSING_DEVICE", True),
        ("resolve", device.id, ("VPN_BYPASS_TRANSIENT_DEVICE",)),
    ]


def test_known_device_missing_within_threshold_resolves_missing_alerts(db, monkeypatch) -> None:
    recorder = _Recorder(monkeypatch)
    device = _device(db, "10.1.0.2", last_seen=datetime.now(UTC) - timedelta(days=2))
    _open_alert(db, device, "MISSING_DEVICE")
    _open_alert(db, device, "device_offline")

    result = services.run_network_scan(db, discovered_hosts=[])

    assert result.alerts_created == 0
    assert {alert.status for alert in _alerts(db)} == {"resolved"}
    assert recorder.reconciliation() == [
        ("resolve", device.id, ("ARP_EPHEMERAL_DEVICE",)),
        ("resolve", device.id, ("MISSING_DEVICE", "device_offline")),
        ("resolve", device.id, ("VPN_BYPASS_TRANSIENT_DEVICE",)),
    ]


def test_known_device_offline_beyond_transient_window_skips_bypass_lookup(db, monkeypatch) -> None:
    recorder = _Recorder(monkeypatch)
    device = _device(db, "10.1.0.3", last_seen=datetime.now(UTC) - timedelta(hours=13))
    _open_alert(db, device, "VPN_BYPASS_TRANSIENT_DEVICE")

    result = services.run_network_scan(db, discovered_hosts=[])

    assert result.alerts_created == 0
    assert [alert.status for alert in _alerts(db, "VPN_BYPASS_TRANSIENT_DEVICE")] == ["resolved"]
    assert not [event for event in recorder.reconciliation() if event[0] == "bypass"]


def test_known_device_recently_seen_with_suspicious_signals_creates_transient_alert_once(
    db, monkeypatch
) -> None:
    device = _device(db, "10.1.0.4", last_seen=datetime.now(UTC) - timedelta(hours=2))
    recorder = _Recorder(
        monkeypatch, {device.id: ["web_allowed", "vpn_suspected", "tor_suspected", "geo"]}
    )

    first = services.run_network_scan(db, discovered_hosts=[])
    second = services.run_network_scan(db, discovered_hosts=[])

    assert (first.alerts_created, second.alerts_created) == (1, 0)
    [alert] = _alerts(db, "VPN_BYPASS_TRANSIENT_DEVICE")
    assert (alert.severity, alert.status, alert.scan_id) == ("danger", "open", first.scan.id)
    assert alert.title == "Device sparito dopo segnali bypass: 10.1.0.4"
    assert alert.message.endswith(" | Segnali recenti: vpn_suspected, tor_suspected")
    bypass_calls = [event for event in recorder.events if event[0] == "bypass"]
    assert len(bypass_calls) == 2
    assert recorder.events.count(("create", device.id, "VPN_BYPASS_TRANSIENT_DEVICE", False)) == 1


def test_known_device_recently_seen_without_suspicious_signals_resolves_transient_alert(
    db, monkeypatch, frozen_now
) -> None:
    device = _device(db, "10.1.0.5", last_seen=frozen_now - timedelta(hours=1))
    _open_alert(db, device, "VPN_BYPASS_TRANSIENT_DEVICE")
    recorder = _Recorder(monkeypatch, {device.id: ["web_allowed", "geo"]})

    result = services.run_network_scan(db, discovered_hosts=[])

    assert result.alerts_created == 0
    assert [alert.status for alert in _alerts(db)] == ["resolved"]
    assert recorder.reconciliation() == [
        ("resolve", device.id, ("ARP_EPHEMERAL_DEVICE",)),
        ("resolve", device.id, ("MISSING_DEVICE", "device_offline")),
        ("bypass", device.id, LOOKBACK_SINCE),
        ("resolve", device.id, ("VPN_BYPASS_TRANSIENT_DEVICE",)),
    ]


def test_known_arp_ephemeral_device_with_signals_is_danger_and_looks_up_signals_twice(
    db, monkeypatch, frozen_now
) -> None:
    now = frozen_now
    device = _device(
        db,
        "10.1.0.6",
        arp=True,
        first_seen=now - timedelta(hours=3),
        last_seen=now - timedelta(hours=1),
    )
    recorder = _Recorder(monkeypatch, {device.id: ["proxy_suspected", "noise", "wireguard_port"]})

    result = services.run_network_scan(db, discovered_hosts=[])

    assert result.alerts_created == 2
    [arp_alert] = _alerts(db, "ARP_EPHEMERAL_DEVICE")
    assert (arp_alert.severity, arp_alert.status) == ("danger", "open")
    assert arp_alert.title == "Presenza ARP effimera: 10.1.0.6"
    assert arp_alert.message.startswith(
        "Device scoperto via ARP e sparito rapidamente | Primo seen: "
    )
    assert arp_alert.message.endswith(" | Correlazione bypass: proxy_suspected, wireguard_port")
    events = recorder.reconciliation()
    assert [event[:3] for event in events] == [
        ("bypass", device.id, LOOKBACK_SINCE),
        ("create", device.id, "ARP_EPHEMERAL_DEVICE"),
        ("resolve", device.id, ("MISSING_DEVICE", "device_offline")),
        ("bypass", device.id, LOOKBACK_SINCE),
        ("create", device.id, "VPN_BYPASS_TRANSIENT_DEVICE"),
    ]


def test_arp_device_outside_ephemeral_window_resolves_arp_ephemeral_alert(db, monkeypatch) -> None:
    now = datetime.now(UTC)
    device = _device(
        db,
        "10.1.0.7",
        arp=True,
        first_seen=now - timedelta(hours=13),
        last_seen=now - timedelta(days=3),
    )
    _open_alert(db, device, "ARP_EPHEMERAL_DEVICE")
    recorder = _Recorder(monkeypatch)

    result = services.run_network_scan(db, discovered_hosts=[])

    assert result.alerts_created == 0
    assert [alert.status for alert in _alerts(db, "ARP_EPHEMERAL_DEVICE")] == ["resolved"]
    assert recorder.reconciliation()[0] == ("resolve", device.id, ("ARP_EPHEMERAL_DEVICE",))
    assert not [event for event in recorder.reconciliation() if event[0] == "bypass"]


@pytest.mark.parametrize(("autoflush", "expected_status"), [(False, "open"), (True, "resolved")])
def test_unknown_arp_ephemeral_device_alert_is_counted_then_resolved_in_same_pass(
    monkeypatch, frozen_now, autoflush, expected_status
) -> None:
    monkeypatch.setattr(
        services,
        "_collect_enrichment",
        lambda ip_address, open_ports: services.EnrichmentMetadata(),
    )
    monkeypatch.setattr(services.settings, "network_missing_device_alert_days", 15)
    engine, factory = _session_factory(autoflush=autoflush)
    db = factory()
    now = frozen_now
    device = _device(
        db, "10.1.0.8", known=False, arp=True, first_seen=now - timedelta(hours=1), last_seen=now
    )
    recorder = _Recorder(monkeypatch)

    result = services.run_network_scan(db, discovered_hosts=[])

    assert result.alerts_created == 1
    [alert] = _alerts(db, "ARP_EPHEMERAL_DEVICE")
    assert (alert.severity, alert.status) == ("warning", expected_status)
    events = recorder.reconciliation()
    assert [event[:3] for event in events] == [
        ("bypass", device.id, LOOKBACK_SINCE),
        ("create", device.id, "ARP_EPHEMERAL_DEVICE"),
        ("resolve", device.id, tuple(ALL_PRESENCE_ALERTS)),
    ]
    db.close()
    engine.dispose()


def test_reconciliation_skips_seen_and_unmonitored_devices_in_order_with_single_commit(
    db, monkeypatch
) -> None:
    now = datetime.now(UTC)
    seen = _device(db, "10.1.0.9", last_seen=now - timedelta(days=30))
    unmonitored = _device(db, "10.1.0.10", monitored=False, last_seen=now - timedelta(days=30))
    unknown = _device(db, "10.1.0.11", known=False, status="offline")
    known = _device(db, "10.1.0.12", last_seen=now - timedelta(days=30))
    monkeypatch.setattr(
        services, "_resolve_mac_address", lambda ip_address, mac_address: mac_address
    )
    recorder = _Recorder(monkeypatch)
    recorder.count_commits(db, monkeypatch)

    result = services.run_network_scan(
        db, discovered_hosts=[services.DiscoveredHost(ip_address="10.1.0.9")]
    )

    assert recorder.commits == 1
    assert result.alerts_created == 1
    db.refresh(unmonitored)
    db.refresh(unknown)
    assert (unmonitored.status, unmonitored.last_scan_id) == ("online", None)
    assert (unknown.status, unknown.last_scan_id) == ("offline", result.scan.id)
    missing_phase = [
        event for event in recorder.reconciliation() if event[1] in {unknown.id, known.id}
    ]
    assert missing_phase == [
        ("resolve", unknown.id, ("ARP_EPHEMERAL_DEVICE",)),
        ("resolve", unknown.id, tuple(ALL_PRESENCE_ALERTS)),
        ("resolve", known.id, ("ARP_EPHEMERAL_DEVICE",)),
        ("create", known.id, "MISSING_DEVICE", True),
        ("resolve", known.id, ("VPN_BYPASS_TRANSIENT_DEVICE",)),
    ]
    assert [alert.device_id for alert in _alerts(db, "MISSING_DEVICE")] == [known.id]
    assert seen.id not in {event[1] for event in recorder.reconciliation() if event[0] == "create"}


def test_missing_alert_threshold_boundary_is_strictly_less_than(
    db, monkeypatch, frozen_now
) -> None:
    at_threshold = _device(db, "10.2.0.1", last_seen=frozen_now - timedelta(days=15))
    just_inside = _device(
        db, "10.2.0.2", last_seen=frozen_now - timedelta(days=15) + timedelta(microseconds=1)
    )
    _Recorder(monkeypatch)

    result = services.run_network_scan(db, discovered_hosts=[])

    assert result.alerts_created == 1
    assert [alert.device_id for alert in _alerts(db, "MISSING_DEVICE")] == [at_threshold.id]
    assert just_inside.id not in {alert.device_id for alert in _alerts(db)}


@pytest.mark.parametrize("configured_days", [0, -3])
def test_missing_alert_threshold_is_floored_to_one_day(
    db, monkeypatch, frozen_now, configured_days
) -> None:
    monkeypatch.setattr(services.settings, "network_missing_device_alert_days", configured_days)
    one_day = _device(db, "10.2.0.3", last_seen=frozen_now - timedelta(days=1))
    under_one_day = _device(db, "10.2.0.4", last_seen=frozen_now - timedelta(hours=23))
    _Recorder(monkeypatch)

    result = services.run_network_scan(db, discovered_hosts=[])

    assert result.alerts_created == 1
    assert [alert.device_id for alert in _alerts(db, "MISSING_DEVICE")] == [one_day.id]
    assert under_one_day.id not in {alert.device_id for alert in _alerts(db)}


def test_transient_window_boundary_still_looks_up_bypass_signals(
    db, monkeypatch, frozen_now
) -> None:
    at_window = _device(db, "10.2.0.5", last_seen=frozen_now - timedelta(hours=12))
    past_window = _device(
        db, "10.2.0.6", last_seen=frozen_now - timedelta(hours=12, microseconds=1)
    )
    recorder = _Recorder(monkeypatch, {at_window.id: ["vpn_port"], past_window.id: ["vpn_port"]})

    result = services.run_network_scan(db, discovered_hosts=[])

    assert result.alerts_created == 1
    [alert] = _alerts(db, "VPN_BYPASS_TRANSIENT_DEVICE")
    assert alert.device_id == at_window.id
    assert alert.message.endswith(" | Segnali recenti: vpn_port")
    assert [event for event in recorder.reconciliation() if event[0] == "bypass"] == [
        ("bypass", at_window.id, LOOKBACK_SINCE)
    ]


def test_arp_ephemeral_window_boundary_is_inclusive(db, monkeypatch, frozen_now) -> None:
    at_window = _device(
        db, "10.2.0.7", arp=True, first_seen=frozen_now - timedelta(hours=12), last_seen=frozen_now
    )
    past_window = _device(
        db,
        "10.2.0.8",
        arp=True,
        first_seen=frozen_now - timedelta(hours=12, microseconds=1),
        last_seen=frozen_now,
    )
    recorder = _Recorder(monkeypatch)

    result = services.run_network_scan(db, discovered_hosts=[])

    assert result.alerts_created == 1
    [alert] = _alerts(db, "ARP_EPHEMERAL_DEVICE")
    assert (alert.device_id, alert.severity) == (at_window.id, "warning")
    events = recorder.reconciliation()
    assert events[0] == ("bypass", at_window.id, LOOKBACK_SINCE)
    assert ("resolve", past_window.id, ("ARP_EPHEMERAL_DEVICE",)) in events


def test_repeat_scans_do_not_duplicate_missing_device_alert(db, monkeypatch, frozen_now) -> None:
    device = _device(db, "10.2.0.9", last_seen=frozen_now - timedelta(days=20))
    recorder = _Recorder(monkeypatch)

    counts = [services.run_network_scan(db, discovered_hosts=[]).alerts_created for _ in range(3)]

    assert counts == [1, 0, 0]
    [alert] = _alerts(db, "MISSING_DEVICE")
    assert (alert.device_id, alert.status) == (device.id, "open")
    assert recorder.events.count(("create", device.id, "MISSING_DEVICE", False)) == 2


def test_repeat_scans_do_not_duplicate_arp_ephemeral_alert(db, monkeypatch, frozen_now) -> None:
    device = _device(
        db, "10.2.0.10", arp=True, first_seen=frozen_now - timedelta(hours=2), last_seen=frozen_now
    )
    recorder = _Recorder(monkeypatch)

    counts = [services.run_network_scan(db, discovered_hosts=[]).alerts_created for _ in range(3)]

    assert counts == [1, 0, 0]
    [alert] = _alerts(db, "ARP_EPHEMERAL_DEVICE")
    assert (alert.device_id, alert.status) == (device.id, "open")
    assert recorder.events.count(("create", device.id, "ARP_EPHEMERAL_DEVICE", False)) == 2
