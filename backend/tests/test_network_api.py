from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.network import (
    DevicePosition,
    FloorPlan,
    NetworkAlert,
    NetworkDevice,
    NetworkFirewall,
    NetworkFirewallEvent,
    NetworkFirewallMetric,
    NetworkScan,
    NetworkScanDevice,
    NetworkTrackedSubject,
)


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    user = ApplicationUser(
        username="network-admin",
        email="network@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_accessi=True,
        module_rete=True,
    )
    db.add(user)
    db.flush()

    mapped_user = ApplicationUser(
        username="operatore.ced",
        email="operatore.ced@example.local",
        full_name="Operatore CED",
        office_location="CED piano terra",
        phone_extension="301",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.VIEWER.value,
        is_active=True,
        module_accessi=True,
        module_rete=True,
    )
    db.add(mapped_user)
    db.flush()

    scan = NetworkScan(
        network_range="192.168.1.0/24",
        scan_type="incremental",
        status="completed",
        hosts_scanned=2,
        active_hosts=2,
        discovered_devices=2,
        initiated_by="seed",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db.add(scan)
    db.flush()

    device_one = NetworkDevice(
        last_scan_id=scan.id,
        assigned_user_id=mapped_user.id,
        ip_address="192.168.1.10",
        mac_address="aa:bb:cc:dd:ee:01",
        hostname="switch-core",
        hostname_source="snmp",
        display_name="Core Switch",
        asset_label="SW-CORE-01",
        vendor="Cisco",
        model_name="CBS350",
        metadata_sources='{"snmp":"public","dns":"switch-core.local"}',
        device_type="network-service",
        dns_name="switch-core.local",
        location_hint="CED piano terra",
        notes="Switch principale edificio A",
        is_known_device=True,
        status="online",
        open_ports="22,443",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    device_two = NetworkDevice(
        last_scan_id=scan.id,
        ip_address="192.168.1.20",
        mac_address="aa:bb:cc:dd:ee:02",
        hostname="pc-contabilita",
        vendor="Dell",
        device_type="workstation",
        is_known_device=True,
        status="offline",
        open_ports="3389",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC) - timedelta(days=20),
    )
    db.add_all([device_one, device_two])
    db.flush()

    db.add_all(
        [
            NetworkScanDevice(
                scan_id=scan.id,
                device_id=device_one.id,
                ip_address=device_one.ip_address,
                mac_address=device_one.mac_address,
                hostname=device_one.hostname,
                hostname_source=device_one.hostname_source,
                display_name=device_one.display_name,
                asset_label=device_one.asset_label,
                vendor=device_one.vendor,
                model_name=device_one.model_name,
                device_type=device_one.device_type,
                operating_system=device_one.operating_system,
                dns_name=device_one.dns_name,
                location_hint=device_one.location_hint,
                metadata_sources=device_one.metadata_sources,
                status=device_one.status,
                open_ports=device_one.open_ports,
                observed_at=datetime.now(UTC),
            ),
            NetworkScanDevice(
                scan_id=scan.id,
                device_id=device_two.id,
                ip_address=device_two.ip_address,
                mac_address=device_two.mac_address,
                hostname=device_two.hostname,
                vendor=device_two.vendor,
                device_type=device_two.device_type,
                status=device_two.status,
                open_ports=device_two.open_ports,
                observed_at=datetime.now(UTC),
            ),
        ]
    )

    db.add(
        NetworkAlert(
            device_id=device_two.id,
            scan_id=scan.id,
            alert_type="MISSING_DEVICE",
            severity="danger",
            status="open",
            title="Dispositivo conosciuto assente dalla rete",
            message="Host assente oltre soglia",
        )
    )

    firewall = NetworkFirewall(
        vendor="Sophos",
        name="Sophos XGS87",
        model_name="XGS87",
        management_ip="192.168.1.1",
        status="online",
        metadata_sources='{"ingest":"seed"}',
        last_seen_at=datetime.now(UTC),
    )
    db.add(firewall)
    db.flush()
    db.add(
        NetworkFirewallEvent(
            firewall_id=firewall.id,
            device_id=device_one.id,
            source="sophos_syslog",
            event_type="firewall.firewall_rule.drop",
            severity="danger",
            log_id="010101600001",
            message="Traffico bloccato verso Internet",
            src_ip=device_one.ip_address,
            dst_ip="8.8.8.8",
            protocol="TCP",
            raw_payload='{"parsed":{"log_type":"Firewall"}}',
            observed_at=datetime.now(UTC),
        )
    )
    db.add(
        NetworkFirewallMetric(
            firewall_id=firewall.id,
            metric_key="sys_uptime_ticks",
            metric_value=12345,
            unit="ticks",
            severity="info",
            raw_payload='{"source":"seed"}',
            observed_at=datetime.now(UTC),
        )
    )

    floor_plan = FloorPlan(
        name="Palazzina A - Piano Terra",
        building="Sede centrale",
        floor_label="PT",
        svg_content="<svg viewBox='0 0 100 100'></svg>",
        width=100,
        height=100,
    )
    db.add(floor_plan)
    db.flush()
    db.add(
        DevicePosition(
            device_id=device_one.id,
            floor_plan_id=floor_plan.id,
            x=25,
            y=40,
            label="Rack principale",
        )
    )

    db.commit()
    db.close()

    def fake_run_network_scan(
        db: Session,
        initiated_by: str | None = None,
        network_range: str | None = None,
        scan_type: str = "incremental",
    ):
        new_scan = NetworkScan(
            network_range=network_range or "192.168.1.0/24",
            scan_type=scan_type,
            status="completed",
            hosts_scanned=1,
            active_hosts=1,
            discovered_devices=1,
            initiated_by=initiated_by,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db.add(new_scan)
        db.commit()
        db.refresh(new_scan)

        class Result:
            scan = new_scan
            devices_upserted = 1
            alerts_created = 0

        return Result()

    monkeypatch.setattr("app.modules.network.router.run_network_scan", fake_run_network_scan)

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def auth_headers() -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "network-admin", "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_network_dashboard_summary() -> None:
    response = client.get("/network/dashboard", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_devices"] == 2
    assert payload["online_devices"] == 1
    assert payload["offline_devices"] == 1
    assert payload["open_alerts"] == 1
    assert payload["firewalls_online"] == 1
    assert payload["floor_plans"] == 1


def test_network_devices_support_filters() -> None:
    response = client.get("/network/devices?search=pc&status=offline", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["hostname"] == "pc-contabilita"
    assert payload["items"][0]["status"] == "offline"
    assert payload["items"][0]["is_known_device"] is True


def test_network_device_detail_prefers_assigned_application_user_label() -> None:
    response = client.get("/network/devices/1", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["resolved_label"] == "Operatore CED"
    assert payload["label_source"] == "application_user"
    assert payload["assigned_user"]["username"] == "operatore.ced"
    assert payload["assigned_user"]["phone_extension"] == "301"


def test_network_device_assignees_endpoint_returns_assignable_users() -> None:
    response = client.get("/network/device-assignees", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert any(item["username"] == "operatore.ced" for item in payload)


def test_network_statistics_summary_returns_traffic_and_device_aggregates() -> None:
    response = client.get("/network/statistics?window_hours=24", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_devices"] == 2
    assert payload["active_devices"] == 2
    assert payload["online_devices"] == 1
    assert payload["total_events"] == 1
    assert payload["blocked_events"] == 1
    assert payload["top_source_devices"][0]["ip_address"] == "192.168.1.10"
    assert payload["top_event_types"][0]["key"] == "firewall.firewall_rule.drop"


def test_network_device_metadata_can_be_updated() -> None:
    response = client.patch(
        "/network/devices/2",
        headers=auth_headers(),
        json={
            "display_name": "PC Contabilita 01",
            "asset_label": "PC-ACC-01",
            "location_hint": "Ufficio contabilita",
            "notes": "Postazione fissa piano primo",
            "is_known_device": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["display_name"] == "PC Contabilita 01"
    assert payload["asset_label"] == "PC-ACC-01"
    assert payload["location_hint"] == "Ufficio contabilita"
    assert payload["notes"] == "Postazione fissa piano primo"
    assert payload["is_known_device"] is False


def test_network_device_can_be_assigned_to_application_user() -> None:
    response = client.patch(
        "/network/devices/2",
        headers=auth_headers(),
        json={"assigned_user_id": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assigned_user_id"] == 2
    assert payload["resolved_label"] == "Operatore CED"
    assert payload["label_source"] == "application_user"


def test_network_device_can_be_unassigned_from_application_user() -> None:
    response = client.patch(
        "/network/devices/1",
        headers=auth_headers(),
        json={"assigned_user_id": None},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assigned_user_id"] is None
    assert payload["assigned_user"] is None
    assert payload["resolved_label"] == "Core Switch"
    assert payload["label_source"] == "device"


def test_network_device_can_be_marked_retired() -> None:
    response = client.patch(
        "/network/devices/2",
        headers=auth_headers(),
        json={"assigned_user_id": 2, "lifecycle_state": "retired"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["lifecycle_state"] == "retired"
    assert payload["assigned_user_id"] is None
    assert payload["is_monitored"] is False
    assert payload["retired_at"] is not None

    dashboard_response = client.get("/network/dashboard", headers=auth_headers())
    assert dashboard_response.status_code == 200
    dashboard_payload = dashboard_response.json()
    assert dashboard_payload["total_devices"] == 1
    assert dashboard_payload["online_devices"] == 1
    assert dashboard_payload["offline_devices"] == 0


def test_network_devices_can_be_bulk_updated() -> None:
    response = client.post(
        "/network/devices/bulk-update",
        headers=auth_headers(),
        json={
            "device_ids": [1, 2],
            "is_known_device": True,
            "location_hint": "Censimento ARP",
            "notes_append": "Verifica operatore CED",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["updated_count"] == 2
    assert len(payload["items"]) == 2
    assert all(item["is_known_device"] is True for item in payload["items"])
    assert all(item["location_hint"] == "Censimento ARP" for item in payload["items"])
    assert all("Verifica operatore CED" in (item["notes"] or "") for item in payload["items"])


def test_network_device_can_toggle_known_state_and_create_unknown_alert() -> None:
    response = client.patch(
        "/network/devices/1",
        headers=auth_headers(),
        json={"is_known_device": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_known_device"] is False

    alerts_response = client.get("/network/alerts", headers=auth_headers())
    assert alerts_response.status_code == 200
    alerts = alerts_response.json()
    assert any(item["alert_type"] == "UNKNOWN_DEVICE" and item["device_id"] == 1 for item in alerts)


def test_network_floor_plan_returns_positions() -> None:
    floor_plan_response = client.get("/network/floor-plans", headers=auth_headers())
    floor_plan_id = floor_plan_response.json()[0]["id"]

    response = client.get(f"/network/floor-plans/{floor_plan_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["floor_label"] == "PT"
    assert len(payload["positions"]) == 1
    assert payload["positions"][0]["label"] == "Rack principale"


def test_network_scan_detail_includes_snapshot_devices() -> None:
    response = client.get("/network/scans/1", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == 1
    assert len(payload["devices"]) == 2
    assert payload["delta"]["new_devices_count"] == 2


def test_network_alert_can_be_resolved() -> None:
    response = client.patch("/network/alerts/1", headers=auth_headers(), json={"status": "resolved"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "resolved"
    assert payload["acknowledged_at"] is not None


def test_network_floor_plan_can_be_created() -> None:
    response = client.post(
        "/network/floor-plans",
        headers=auth_headers(),
        json={
            "name": "Palazzina B - Primo Piano",
            "floor_label": "P1",
            "building": "Sede distaccata",
            "svg_content": "<svg viewBox='0 0 200 200'></svg>",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Palazzina B - Primo Piano"
    assert payload["floor_label"] == "P1"


def test_network_device_position_can_be_upserted() -> None:
    response = client.put(
        "/network/devices/2/position",
        headers=auth_headers(),
        json={"floor_plan_id": 1, "x": 60, "y": 75, "label": "Scrivania contabilita"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["floor_plan_id"] == 1
    assert payload["device_id"] == 2
    assert payload["label"] == "Scrivania contabilita"


def test_network_floor_plan_devices_returns_device_pairs() -> None:
    response = client.get("/network/floor-plans/1/devices", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["device"]["hostname"] == "switch-core"


def test_network_scan_can_be_triggered() -> None:
    response = client.post("/network/scans", headers=auth_headers())

    assert response.status_code == 201
    payload = response.json()
    assert payload["devices_upserted"] == 1
    assert payload["scan"]["initiated_by"] == "network-admin"
    assert "delta" in payload["scan"]


def test_network_arp_scan_can_be_triggered() -> None:
    response = client.post(
        "/network/scans",
        headers=auth_headers(),
        json={"scan_type": "arp", "network_range": "192.168.1.0/24"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["scan"]["scan_type"] == "arp"
    assert payload["scan"]["network_range"] == "192.168.1.0/24"


def test_network_firewalls_are_listed() -> None:
    response = client.get("/network/firewalls", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["vendor"] == "Sophos"
    assert payload[0]["name"] == "Sophos XGS87"


def test_network_firewall_events_are_listed() -> None:
    response = client.get("/network/firewalls/1/events", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["event_type"] == "firewall.firewall_rule.drop"
    assert payload[0]["device_id"] == 1
    assert payload[0]["src_device_label"] == "Operatore CED"
    assert payload[0]["dst_device_label"] is None


def test_network_tracked_subject_can_be_created_for_device() -> None:
    response = client.post(
        "/network/tracking",
        headers=auth_headers(),
        json={"entity_type": "device", "device_id": 1, "label": "Monitoraggio core"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["entity_type"] == "device"
    assert payload["device_id"] == 1
    assert payload["value"] == "192.168.1.10"
    assert payload["resolved_label"] == "Monitoraggio core"


def test_network_tracked_subject_list_and_activity_summary_are_returned() -> None:
    db = TestingSessionLocal()
    db.add(
        NetworkTrackedSubject(
            entity_type="domain",
            normalized_value="google.com",
            value="google.com",
            label="Google",
            is_active=True,
        )
    )
    db.add(
        NetworkTrackedSubject(
            entity_type="ip",
            normalized_value="8.8.8.8",
            value="8.8.8.8",
            is_active=True,
        )
    )
    db.commit()
    db.close()

    response = client.get("/network/tracking", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert {item["entity_type"] for item in payload} == {"domain", "ip"}
    assert all("activity_summary" in item for item in payload)


def test_network_tracked_subject_activities_match_firewall_events() -> None:
    db = TestingSessionLocal()
    subject = NetworkTrackedSubject(
        entity_type="ip",
        normalized_value="8.8.8.8",
        value="8.8.8.8",
        is_active=True,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    subject_id = subject.id
    db.close()

    response = client.get(f"/network/tracking/{subject_id}/activities", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_events"] == 1
    assert payload["blocked_events"] == 1
    assert payload["recent_events"][0]["matched_on"] == "dst_ip"
    assert payload["recent_events"][0]["dst_ip"] == "8.8.8.8"


def test_network_firewall_events_include_tracked_subject_ids() -> None:
    db = TestingSessionLocal()
    tracked_ip = NetworkTrackedSubject(
        entity_type="ip",
        normalized_value="8.8.8.8",
        value="8.8.8.8",
        is_active=True,
    )
    db.add(tracked_ip)
    db.commit()
    db.refresh(tracked_ip)
    tracked_ip_id = tracked_ip.id
    db.close()

    response = client.get("/network/firewalls/1/events", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["tracked_dst_ip_subject_id"] == tracked_ip_id


def test_network_firewall_metrics_are_listed() -> None:
    response = client.get("/network/firewalls/1/metrics", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["metric_key"] == "sys_uptime_ticks"
    assert payload[0]["metric_value"] == 12345


def test_sophos_syslog_can_be_ingested_via_api() -> None:
    response = client.post(
        "/network/firewalls/sophos/syslog",
        headers=auth_headers(),
        json={
            "firewall_id": 1,
            "message": 'device_name="XGS87" log_type="Firewall" log_component="Firewall Rule" log_subtype="Drop" priority="Critical" src_ip=192.168.1.10 dst_ip=1.1.1.1 message="Tentativo bloccato"',
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["firewall_id"] == 1
    assert payload["severity"] == "critical"
    assert payload["device_id"] == 1


def test_sophos_snmp_metrics_can_be_polled_via_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.network.router.poll_sophos_firewall_metrics", lambda db: [
        NetworkFirewallMetric(
            id=99,
            firewall_id=1,
            metric_key="if_number",
            metric_value=9,
            metric_text=None,
            unit="count",
            severity="info",
            raw_payload='{"source":"snmp"}',
            observed_at=datetime.now(UTC),
        )
    ])

    response = client.post("/network/firewalls/1/metrics/poll", headers=auth_headers())

    assert response.status_code == 201
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["metric_key"] == "if_number"
