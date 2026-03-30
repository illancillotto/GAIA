from collections.abc import Generator
from datetime import UTC, datetime

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
from app.models.network import DevicePosition, FloorPlan, NetworkAlert, NetworkDevice, NetworkScan, NetworkScanDevice


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
        status="offline",
        open_ports="3389",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
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
            alert_type="device_offline",
            severity="danger",
            status="open",
            title="Dispositivo non raggiungibile",
            message="Host offline",
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

    def fake_run_network_scan(db: Session, initiated_by: str | None = None):
        new_scan = NetworkScan(
            network_range="192.168.1.0/24",
            scan_type="incremental",
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
    assert payload["floor_plans"] == 1


def test_network_devices_support_filters() -> None:
    response = client.get("/network/devices?search=pc&status=offline", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["hostname"] == "pc-contabilita"
    assert payload["items"][0]["status"] == "offline"


def test_network_device_metadata_can_be_updated() -> None:
    response = client.patch(
        "/network/devices/2",
        headers=auth_headers(),
        json={
            "display_name": "PC Contabilita 01",
            "asset_label": "PC-ACC-01",
            "location_hint": "Ufficio contabilita",
            "notes": "Postazione fissa piano primo",
            "is_monitored": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["display_name"] == "PC Contabilita 01"
    assert payload["asset_label"] == "PC-ACC-01"
    assert payload["location_hint"] == "Ufficio contabilita"
    assert payload["notes"] == "Postazione fissa piano primo"
    assert payload["is_monitored"] is False


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
