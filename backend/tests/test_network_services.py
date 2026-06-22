import json
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.network import services
from app.modules.network.models import (
    NetworkAlert,
    NetworkDetectionWatchlist,
    NetworkDevice,
    NetworkFirewall,
    NetworkFirewallEvent,
    NetworkSophosConfig,
)
from app.modules.network.sophos import ingest_sophos_syslog, parse_sophos_syslog_message, strip_syslog_prefix
from app.modules.network.sophos_runtime import clear_sophos_runtime_policy_cache
from app.modules.network.sophos_snmp import poll_sophos_firewall_metrics
from app.modules.network.sophos_syslog_listener import SophosSyslogListener


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _build_session() -> Session:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


class _FakeHostState(dict):
    def state(self) -> str:
        return self.get("status", "down")


class _FakePortScanner:
    scan_calls: list[tuple[str, str]] = []

    def __init__(self) -> None:
        self._scan_result: dict[str, dict] = {"scan": {}}
        self._hosts: list[str] = []

    def scan(self, hosts: str, arguments: str) -> None:
        self.scan_calls.append((hosts, arguments))
        if "-sn" in arguments:
            self._hosts = ["192.168.1.10", "192.168.1.20"]
            self._scan_result = {
                "scan": {
                    "192.168.1.10": {
                        "status": "up",
                        "addresses": {"mac": "AA-BB-CC-DD-EE-10"},
                        "hostnames": [{"name": "switch-core"}],
                        "vendor": {"AA:BB:CC:DD:EE:10": "Cisco"},
                    },
                    "192.168.1.20": {
                        "status": "up",
                        "addresses": {"mac": "AA-BB-CC-DD-EE-20"},
                        "hostnames": [{"name": "pc-amministrazione"}],
                        "vendor": {"AA:BB:CC:DD:EE:20": "Dell"},
                    },
                }
            }
            return

        self._hosts = ["192.168.1.10"]
        self._scan_result = {
            "scan": {
                "192.168.1.10": {
                    "tcp": {
                        22: {"state": "open"},
                        443: {"state": "open"},
                    }
                }
            }
        }

    def all_hosts(self) -> list[str]:
        return self._hosts

    def __getitem__(self, host: str) -> _FakeHostState:
        return _FakeHostState(self._scan_result["scan"][host])


def test_run_nmap_scan_keeps_hosts_without_open_ports(monkeypatch) -> None:
    _FakePortScanner.scan_calls = []
    monkeypatch.setattr(services, "nmap", type("FakeNmapModule", (), {"PortScanner": _FakePortScanner}))
    monkeypatch.setattr(services.shutil, "which", lambda value: "/usr/bin/nmap" if value == "nmap" else None)
    monkeypatch.setattr(services, "_collect_enrichment", lambda ip_address, open_ports: services.EnrichmentMetadata())

    hosts = services._run_nmap_scan("192.168.1.0/24", "22,443")

    assert len(hosts) == 2
    assert hosts[0].ip_address == "192.168.1.10"
    assert hosts[0].hostname == "switch-core"
    assert hosts[0].open_ports == [22, 443]
    assert hosts[1].ip_address == "192.168.1.20"
    assert hosts[1].hostname == "pc-amministrazione"
    assert hosts[1].open_ports == []
    assert hosts[1].vendor == "Dell"


def test_run_nmap_arp_scan_discovers_hosts_with_mac_addresses(monkeypatch) -> None:
    _FakePortScanner.scan_calls = []
    monkeypatch.setattr(services, "nmap", type("FakeNmapModule", (), {"PortScanner": _FakePortScanner}))
    monkeypatch.setattr(services.shutil, "which", lambda value: "/usr/bin/nmap" if value == "nmap" else None)
    monkeypatch.setattr(services, "_collect_enrichment", lambda ip_address, open_ports: services.EnrichmentMetadata())

    hosts = services._run_nmap_arp_scan("192.168.1.0/24")

    assert len(hosts) == 2
    assert hosts[0].ip_address == "192.168.1.10"
    assert hosts[0].mac_address == "aa:bb:cc:dd:ee:10"
    assert hosts[0].device_type == "unknown-host"
    assert hosts[1].ip_address == "192.168.1.20"
    assert hosts[1].mac_address == "aa:bb:cc:dd:ee:20"
    assert _FakePortScanner.scan_calls == [("192.168.1.0/24", f"-sn -PR -n --host-timeout {services.settings.network_scan_ping_timeout_ms}ms")]


def test_parse_netbios_name_returns_active_workstation_name() -> None:
    output = """
Looking up status of 192.168.1.50
        OFFICE-PC      <00> -         B <ACTIVE>
        WORKGROUP      <00> - <GROUP> B <ACTIVE>
        OFFICE-PC      <20> -         B <ACTIVE>
    """

    assert services._parse_netbios_name(output) == "OFFICE-PC"


def test_classify_snmp_descr_extracts_vendor_model_and_os() -> None:
    vendor, model_name, operating_system = services._classify_snmp_descr(
        "MikroTik RouterOS CRS326-24G-2S+ version 7.18.2"
    )

    assert vendor == "MikroTik"
    assert model_name == "MikroTik RouterOS CRS326-24G-2S+ version 7.18.2"
    assert operating_system == "RouterOS"


def test_snmp_profile_communities_match_subnet(monkeypatch) -> None:
    monkeypatch.setattr(
        services.settings,
        "network_snmp_community_profiles",
        '[{"cidr":"192.168.1.0/24","communities":["private","public-site"]},{"cidr":"10.0.0.0/8","communities":["lab"]}]',
    )
    monkeypatch.setattr(services.settings, "network_snmp_communities", "public")

    communities = services._snmp_profile_communities("192.168.1.50")

    assert communities == ["private", "public-site", "public"]


def test_classify_http_identity_extracts_canon_printer_metadata() -> None:
    vendor, model_name, operating_system = services._classify_http_identity(
        "Canon iR-ADV C5840 Remote UI",
        "Canon HTTP Server",
        "Canon iR-ADV C5840 - PROTOCOLLO",
    )

    assert vendor == "Canon"
    assert "Canon iR-ADV C5840" in (model_name or "")
    assert operating_system == "Embedded/Web appliance"


def test_extract_meta_refresh_target_and_device_name() -> None:
    html = """
    <html>
      <head><meta http-equiv=Refresh content="0; URL=http://192.168.1.113:8000/rps/"></head>
      <body><span id="deviceName">Canon iR-ADV C3520 - PROTOCOLLO</span></body>
    </html>
    """

    assert services._extract_meta_refresh_target(html) == "http://192.168.1.113:8000/rps/"
    assert services._extract_device_name(html) == "Canon iR-ADV C3520 - PROTOCOLLO"


def test_extract_mac_from_text_supports_ip_neigh_output() -> None:
    output = "192.168.1.113 dev eth0 lladdr 84:ba:3b:13:ae:0d REACHABLE"

    assert services._extract_mac_from_text(output) == "84:ba:3b:13:ae:0d"


def test_resolve_mac_via_arp_helper_uses_helper_response(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class _FakeResponse:
        status_code = 200

        @staticmethod
        def json() -> dict[str, str]:
            return {"mac_address": "84-BA-3B-13-AE-0D"}

    class _FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            return

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, url: str, headers: dict[str, str]) -> _FakeResponse:
            captured["url"] = url
            return _FakeResponse()

    monkeypatch.setattr(services, "httpx", type("FakeHttpxModule", (), {"Client": _FakeClient}))
    monkeypatch.setattr(services.settings, "network_arp_helper_base_url", "http://host.docker.internal:9105")

    mac_address = services._resolve_mac_via_arp_helper("192.168.1.113")

    assert captured["url"] == "http://host.docker.internal:9105/lookup?ip=192.168.1.113"
    assert mac_address == "84:ba:3b:13:ae:0d"


def test_build_diff_counts_new_missing_and_changed_entries() -> None:
    previous = [
        services.NetworkScanDevice(
            scan_id=1,
            ip_address="192.168.1.10",
            mac_address="aa:bb:cc:dd:ee:10",
            hostname="switch-old",
            status="online",
            observed_at=services.datetime.now(services.UTC),
        ),
        services.NetworkScanDevice(
            scan_id=1,
            ip_address="192.168.1.20",
            mac_address="aa:bb:cc:dd:ee:20",
            hostname="printer-1",
            status="online",
            observed_at=services.datetime.now(services.UTC),
        ),
    ]
    current = [
        services.NetworkScanDevice(
            scan_id=2,
            ip_address="192.168.1.10",
            mac_address="aa:bb:cc:dd:ee:10",
            hostname="switch-new",
            status="online",
            observed_at=services.datetime.now(services.UTC),
        ),
        services.NetworkScanDevice(
            scan_id=2,
            ip_address="192.168.1.30",
            mac_address="aa:bb:cc:dd:ee:30",
            hostname="camera-1",
            status="online",
            observed_at=services.datetime.now(services.UTC),
        ),
    ]

    summary, changes = services._build_diff(previous, current)

    assert summary == {
        "new_devices_count": 1,
        "missing_devices_count": 1,
        "changed_devices_count": 1,
    }
    assert len(changes) == 3


def test_run_network_scan_creates_unknown_device_alert_for_unregistered_host(monkeypatch) -> None:
    db = _build_session()
    monkeypatch.setattr(services, "_collect_enrichment", lambda ip_address, open_ports: services.EnrichmentMetadata())

    result = services.run_network_scan(
        db,
        initiated_by="tester",
        discovered_hosts=[
            services.DiscoveredHost(
                ip_address="192.168.1.50",
                mac_address="AA-BB-CC-DD-EE-50",
                hostname="printer-lab",
                open_ports=[80],
            )
        ],
    )

    alerts = db.scalars(select(NetworkAlert).order_by(NetworkAlert.id.asc())).all()
    device = db.scalar(select(NetworkDevice).where(NetworkDevice.ip_address == "192.168.1.50"))

    assert result.alerts_created == 1
    assert device is not None
    assert device.is_known_device is False
    assert len(alerts) == 1
    assert alerts[0].alert_type == "UNKNOWN_DEVICE"

    db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_network_scan_persists_arp_scan_type_and_discovery_metadata(monkeypatch) -> None:
    db = _build_session()
    monkeypatch.setattr(services, "_collect_enrichment", lambda ip_address, open_ports: services.EnrichmentMetadata(metadata_sources={"dns": "pc-ufficio.local"}))

    result = services.run_network_scan(
        db,
        initiated_by="tester",
        scan_type="arp",
        discovered_hosts=[
            services.DiscoveredHost(
                ip_address="192.168.1.77",
                mac_address="AA-BB-CC-DD-EE-77",
                hostname="pc-ufficio",
                open_ports=[],
            )
        ],
    )

    device = db.scalar(select(NetworkDevice).where(NetworkDevice.ip_address == "192.168.1.77"))

    assert result.scan.scan_type == "arp"
    assert device is not None
    assert services.metadata_sources_to_dict(device.metadata_sources) == {"dns": "pc-ufficio.local", "discovery": "arp"}

    db.close()
    Base.metadata.drop_all(bind=engine)


def test_parse_sophos_syslog_message_extracts_key_values() -> None:
    parsed = parse_sophos_syslog_message(
        'device_name="XGS87" log_type="Firewall" log_component="Firewall Rule" log_subtype="Drop" priority="Error" src_ip=192.168.1.50 dst_ip=8.8.8.8 message="Blocked by policy"'
    )

    assert parsed["device_name"] == "XGS87"
    assert parsed["log_type"] == "Firewall"
    assert parsed["src_ip"] == "192.168.1.50"
    assert parsed["message"] == "Blocked by policy"


def test_strip_syslog_prefix_returns_body_and_host() -> None:
    body, host = strip_syslog_prefix(
        '<134>2026-06-04T09:20:00+02:00 sophos-xgs87 log_type="Firewall" log_component="Firewall Rule" src_ip=192.168.1.50'
    )

    assert host == "sophos-xgs87"
    assert body == 'log_type="Firewall" log_component="Firewall Rule" src_ip=192.168.1.50'


def test_ingest_sophos_syslog_creates_event_and_alert() -> None:
    db = _build_session()
    device = NetworkDevice(
        ip_address="192.168.1.50",
        mac_address="aa:bb:cc:dd:ee:50",
        hostname="printer-lab",
        is_known_device=True,
        status="online",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    event = ingest_sophos_syslog(
        db,
        message='device_name="XGS87" log_type="Firewall" log_component="Firewall Rule" log_subtype="Drop" priority="Error" src_ip=192.168.1.50 dst_ip=8.8.8.8 message="Blocked by policy"',
        firewall_name="Sophos XGS87",
        management_ip="192.168.1.1",
    )

    alerts = db.scalars(select(NetworkAlert).where(NetworkAlert.alert_type == "FIREWALL_EVENT")).all()

    assert event.firewall_id is not None
    assert event.device_id == device.id
    assert event.event_type == "firewall.firewall_rule.drop"
    assert event.severity == "danger"
    assert len(alerts) == 1

    db.close()
    Base.metadata.drop_all(bind=engine)


def test_ingest_sophos_syslog_creates_vpn_bypass_alert_when_watchlist_matches() -> None:
    db = _build_session()
    device = NetworkDevice(
        ip_address="192.168.1.60",
        mac_address="aa:bb:cc:dd:ee:60",
        hostname="pc-amministrazione",
        is_known_device=True,
        status="online",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    for index in range(3):
        ingest_sophos_syslog(
            db,
            message=f'device_name="XGS87" log_type="Web Server" log_component="HTTPS" log_subtype="Allowed" priority="Info" src_ip=192.168.1.60 dst_ip=104.18.0.{index + 1} domain=api.nordvpn.com url=https://api.nordvpn.com/v1/servers message="Allowed HTTPS"',
            firewall_name="Sophos XGS87",
            management_ip="192.168.1.1",
        )

    alerts = db.scalars(select(NetworkAlert).where(NetworkAlert.alert_type == "VPN_BYPASS_SUSPECTED")).all()

    assert len(alerts) == 1
    assert "vpn_suspected" in (alerts[0].message or "")

    db.close()
    Base.metadata.drop_all(bind=engine)


def test_ingest_sophos_syslog_allowlist_suppresses_false_positive_alert() -> None:
    db = _build_session()
    device = NetworkDevice(
        ip_address="192.168.1.61",
        mac_address="aa:bb:cc:dd:ee:61",
        hostname="pc-allowlist",
        is_known_device=True,
        status="online",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db.add(device)
    db.add(
        NetworkDetectionWatchlist(
            category="vpn",
            rule_mode="allow",
            match_type="domain",
            pattern="api.nordvpn.com",
            label="False positive known service",
            is_active=True,
        )
    )
    db.commit()
    db.refresh(device)

    for index in range(3):
        ingest_sophos_syslog(
            db,
            message=f'device_name="XGS87" log_type="Web Server" log_component="HTTPS" log_subtype="Allowed" priority="Info" src_ip=192.168.1.61 dst_ip=104.18.1.{index + 1} domain=api.nordvpn.com url=https://api.nordvpn.com/v1/servers message="Allowed HTTPS"',
            firewall_name="Sophos XGS87",
            management_ip="192.168.1.1",
        )

    alerts = db.scalars(select(NetworkAlert).where(NetworkAlert.alert_type == "VPN_BYPASS_SUSPECTED")).all()

    assert len(alerts) == 0

    db.close()
    Base.metadata.drop_all(bind=engine)


def test_sophos_syslog_listener_handles_message_with_client_ip() -> None:
    db = _build_session()
    db.add(
        NetworkSophosConfig(
            id=1,
            syslog_enabled=True,
            snmp_enabled=True,
            operation_window_enabled=False,
            operation_start_hour=19,
            operation_end_hour=4,
            operation_timezone="Europe/Rome",
        )
    )
    db.commit()
    db.close()
    clear_sophos_runtime_policy_cache()

    services.settings.network_sophos_firewall_management_ip = None
    listener = SophosSyslogListener(session_factory=TestingSessionLocal, firewall_name="Sophos XGS87")
    listener.handle_message(
        '<134>2026-06-04T09:20:00+02:00 xgs87 log_type="Firewall" log_component="Firewall Rule" log_subtype="Drop" priority="Critical" src_ip=192.168.1.99 dst_ip=8.8.8.8 message="Drop test"',
        "192.168.1.1",
    )

    verification_db = TestingSessionLocal()
    event = verification_db.scalar(select(services.NetworkFirewallEvent).order_by(services.NetworkFirewallEvent.id.desc()))
    firewall = verification_db.scalar(select(services.NetworkFirewall).order_by(services.NetworkFirewall.id.desc()))

    assert event is not None
    assert event.event_type == "firewall.firewall_rule.drop"
    assert firewall is not None
    assert firewall.management_ip == "192.168.1.1"

    verification_db.close()
    Base.metadata.drop_all(bind=engine)


def test_sophos_syslog_listener_queue_workers_process_messages() -> None:
    db = _build_session()
    db.add(
        NetworkSophosConfig(
            id=1,
            syslog_enabled=True,
            snmp_enabled=True,
            operation_window_enabled=False,
            operation_start_hour=19,
            operation_end_hour=4,
            operation_timezone="Europe/Rome",
        )
    )
    db.commit()
    db.close()
    clear_sophos_runtime_policy_cache()

    listener = SophosSyslogListener(
        session_factory=TestingSessionLocal,
        firewall_name="Sophos XGS87",
        worker_count=1,
        queue_size=10,
    )
    listener.start()
    try:
        listener.enqueue_message(
            'device_name="XGS87" log_type="Firewall" log_component="Firewall Rule" log_subtype="Drop" priority="Critical" src_ip=192.168.1.77 dst_ip=8.8.8.8 message="Queued drop test"',
            "192.168.1.1",
        )
        deadline = time.time() + 2.0
        verification_db = TestingSessionLocal()
        try:
            while time.time() < deadline:
                event = verification_db.scalar(select(NetworkFirewallEvent).where(NetworkFirewallEvent.src_ip == "192.168.1.77"))
                if event is not None:
                    break
                verification_db.expire_all()
                time.sleep(0.05)
            else:
                raise AssertionError("Queued syslog message was not ingested in time")
        finally:
            verification_db.close()
    finally:
        listener.stop()

    Base.metadata.drop_all(bind=engine)


def test_poll_sophos_firewall_metrics_records_standard_metrics(monkeypatch) -> None:
    db = _build_session()
    monkeypatch.setattr(services.settings, "network_sophos_snmp_host", "192.168.1.1")
    monkeypatch.setattr(services.settings, "network_sophos_firewall_management_ip", "192.168.1.1")
    monkeypatch.setattr(services.settings, "network_sophos_snmp_community", "public")
    monkeypatch.setattr(
        "app.modules.network.sophos_snmp._snmp_get_values",
        lambda host, port, community, oids: {
            "sys_name": "Sophos-XGS87",
            "sys_descr": "Sophos Firewall",
            "sys_uptime_ticks": "12345",
            "if_number": "9",
        },
    )

    metrics = poll_sophos_firewall_metrics(db)

    assert len(metrics) == 4
    assert any(item.metric_key == "sys_name" and item.metric_text == "Sophos-XGS87" for item in metrics)
    assert any(item.metric_key == "if_number" and item.metric_value == 9 for item in metrics)

    db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_network_scan_creates_missing_alert_only_after_threshold(monkeypatch) -> None:
    db = _build_session()
    monkeypatch.setattr(services, "_collect_enrichment", lambda ip_address, open_ports: services.EnrichmentMetadata())
    monkeypatch.setattr(services.settings, "network_missing_device_alert_days", 15)

    known_device = NetworkDevice(
        ip_address="192.168.1.60",
        mac_address="aa:bb:cc:dd:ee:60",
        hostname="switch-remoto",
        is_known_device=True,
        status="online",
        is_monitored=True,
        first_seen_at=datetime.now(UTC) - timedelta(days=40),
        last_seen_at=datetime.now(UTC) - timedelta(days=16),
    )
    db.add(known_device)
    db.commit()

    result = services.run_network_scan(
        db,
        initiated_by="tester",
        discovered_hosts=[],
    )

    db.refresh(known_device)
    alerts = db.scalars(select(NetworkAlert).order_by(NetworkAlert.id.asc())).all()

    assert result.alerts_created == 1
    assert known_device.status == "offline"
    assert len(alerts) == 1
    assert alerts[0].alert_type == "MISSING_DEVICE"

    db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_network_scan_creates_transient_bypass_alert_when_device_disappears_after_suspicious_events(monkeypatch) -> None:
    db = _build_session()
    monkeypatch.setattr(services, "_collect_enrichment", lambda ip_address, open_ports: services.EnrichmentMetadata())
    monkeypatch.setattr(services.settings, "network_missing_device_alert_days", 15)

    now = datetime.now(UTC)
    known_device = NetworkDevice(
        ip_address="192.168.1.62",
        mac_address="aa:bb:cc:dd:ee:62",
        hostname="pc-bypass-transient",
        is_known_device=True,
        status="online",
        is_monitored=True,
        first_seen_at=now - timedelta(days=5),
        last_seen_at=now - timedelta(hours=2),
    )
    firewall = NetworkFirewall(
        vendor="Sophos",
        name="Sophos XGS87",
        model_name="XGS87",
        management_ip="192.168.1.1",
        status="online",
        metadata_sources='{"ingest":"seed"}',
        last_seen_at=now,
    )
    db.add_all([known_device, firewall])
    db.commit()
    db.refresh(known_device)
    db.refresh(firewall)

    db.add(
        NetworkFirewallEvent(
            firewall_id=firewall.id,
            device_id=known_device.id,
            source="sophos_syslog",
            event_type="web.server.allowed",
            severity="info",
            log_id="vpn-transient-001",
            message="Allowed HTTPS",
            src_ip=known_device.ip_address,
            dst_ip="104.18.0.10",
            protocol="HTTPS",
            raw_payload=json.dumps(
                {
                    "parsed": {
                        "domain": "api.nordvpn.com",
                        "url": "https://api.nordvpn.com/v1/servers",
                        "dst_port": "443",
                    }
                }
            ),
            observed_at=now - timedelta(hours=1),
        )
    )
    db.commit()

    result = services.run_network_scan(
        db,
        initiated_by="tester",
        discovered_hosts=[],
    )

    alerts = db.scalars(
        select(NetworkAlert).where(NetworkAlert.alert_type == "VPN_BYPASS_TRANSIENT_DEVICE").order_by(NetworkAlert.id.asc())
    ).all()

    assert result.alerts_created == 1
    assert len(alerts) == 1
    assert alerts[0].device_id == known_device.id
    assert "vpn_suspected" in (alerts[0].message or "")

    db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_network_scan_creates_arp_ephemeral_alert_for_recent_arp_device(monkeypatch) -> None:
    db = _build_session()
    monkeypatch.setattr(services, "_collect_enrichment", lambda ip_address, open_ports: services.EnrichmentMetadata())
    monkeypatch.setattr(services.settings, "network_missing_device_alert_days", 15)

    now = datetime.now(UTC)
    arp_device = NetworkDevice(
        ip_address="192.168.1.63",
        mac_address="aa:bb:cc:dd:ee:63",
        hostname="arp-host",
        is_known_device=False,
        status="online",
        is_monitored=True,
        metadata_sources='{"discovery": "arp"}',
        first_seen_at=now - timedelta(hours=1),
        last_seen_at=now - timedelta(minutes=20),
    )
    db.add(arp_device)
    db.commit()

    result = services.run_network_scan(
        db,
        initiated_by="tester",
        discovered_hosts=[],
    )

    alerts = db.scalars(
        select(NetworkAlert).where(NetworkAlert.alert_type == "ARP_EPHEMERAL_DEVICE").order_by(NetworkAlert.id.asc())
    ).all()

    assert result.alerts_created == 1
    assert len(alerts) == 1
    assert alerts[0].severity == "warning"
    assert "ARP" in alerts[0].title

    db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_network_scan_creates_arp_mac_change_alert_when_same_ip_has_multiple_macs(monkeypatch) -> None:
    db = _build_session()
    monkeypatch.setattr(services, "_collect_enrichment", lambda ip_address, open_ports: services.EnrichmentMetadata())

    services.run_network_scan(
        db,
        initiated_by="tester",
        scan_type="arp",
        discovered_hosts=[
            services.DiscoveredHost(
                ip_address="192.168.1.64",
                mac_address="aa:bb:cc:dd:ee:64",
                hostname="arp-mac-a",
                open_ports=[],
            )
        ],
    )

    services.run_network_scan(
        db,
        initiated_by="tester",
        scan_type="arp",
        discovered_hosts=[
            services.DiscoveredHost(
                ip_address="192.168.1.64",
                mac_address="aa:bb:cc:dd:ee:99",
                hostname="arp-mac-b",
                open_ports=[],
            )
        ],
    )

    alerts = db.scalars(
        select(NetworkAlert).where(NetworkAlert.alert_type == "ARP_MAC_CHANGE_SUSPECTED").order_by(NetworkAlert.id.asc())
    ).all()

    assert len(alerts) == 1
    assert "MAC" in (alerts[0].message or "")
    assert "aa:bb:cc:dd:ee:64" in (alerts[0].message or "")
    assert "aa:bb:cc:dd:ee:99" in (alerts[0].message or "")

    db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_network_scan_creates_arp_ip_rotation_alert_when_same_mac_has_multiple_ips(monkeypatch) -> None:
    db = _build_session()
    monkeypatch.setattr(services, "_collect_enrichment", lambda ip_address, open_ports: services.EnrichmentMetadata())

    services.run_network_scan(
        db,
        initiated_by="tester",
        scan_type="arp",
        discovered_hosts=[
            services.DiscoveredHost(
                ip_address="192.168.1.71",
                mac_address="aa:bb:cc:dd:ee:70",
                hostname="arp-ip-a",
                open_ports=[],
            )
        ],
    )

    services.run_network_scan(
        db,
        initiated_by="tester",
        scan_type="arp",
        discovered_hosts=[
            services.DiscoveredHost(
                ip_address="192.168.1.72",
                mac_address="aa:bb:cc:dd:ee:70",
                hostname="arp-ip-b",
                open_ports=[],
            )
        ],
    )

    alerts = db.scalars(
        select(NetworkAlert).where(NetworkAlert.alert_type == "ARP_IP_ROTATION_SUSPECTED").order_by(NetworkAlert.id.asc())
    ).all()

    assert len(alerts) >= 1
    assert "aa:bb:cc:dd:ee:70" in (alerts[0].message or "")
    assert "192.168.1.71" in (alerts[0].message or "")
    assert "192.168.1.72" in (alerts[0].message or "")

    db.close()
    Base.metadata.drop_all(bind=engine)
