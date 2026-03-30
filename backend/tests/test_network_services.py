from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.network import services
from app.modules.network.models import NetworkAlert, NetworkDevice


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
