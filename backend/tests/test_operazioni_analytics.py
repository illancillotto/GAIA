"""Tests for the Operazioni Analytics endpoints."""

from collections.abc import Generator
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.operazioni.models.activities import ActivityCatalog, OperatorActivity
from app.modules.operazioni.models.organizational import Team, TeamMembership
from app.modules.operazioni.models.vehicles import (
    Vehicle,
    VehicleAssignment,
    VehicleFuelLog,
    VehicleUsageSession,
    WCRefuelEvent,
)

# ─── DB setup ─────────────────────────────────────────────────────────────────

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
def setup_database() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def _seed_user(module_operazioni: bool = True) -> ApplicationUser:
    db = TestingSessionLocal()
    username = "analytics-admin" if module_operazioni else "analytics-noaccess"
    email = f"{username}@example.local"
    user = ApplicationUser(
        username=username,
        email=email,
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_operazioni=module_operazioni,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _auth_headers(module_operazioni: bool = True) -> dict[str, str]:
    _seed_user(module_operazioni=module_operazioni)
    username = "analytics-admin" if module_operazioni else "analytics-noaccess"
    response = client.post(
        "/auth/login",
        json={"username": username, "password": "secret123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─── Data helpers ─────────────────────────────────────────────────────────────

def _make_vehicle(db: Session, plate: str = "AA000AA", code: str | None = None) -> Vehicle:
    v = Vehicle(
        code=code or f"VH-{plate}",
        name=f"Mezzo {plate}",
        plate_number=plate,
        vehicle_type="autocarro",
        fuel_type="diesel",
        current_status="available",
    )
    db.add(v)
    db.flush()
    return v


def _make_user(db: Session, username: str) -> ApplicationUser:
    u = ApplicationUser(
        username=username,
        email=f"{username}@test.local",
        password_hash=hash_password("x"),
        role=ApplicationUserRole.VIEWER.value,
        is_active=True,
        module_operazioni=True,
    )
    db.add(u)
    db.flush()
    return u


def _make_session(
    db: Session,
    vehicle: Vehicle,
    driver_user_id: int,
    started_at: datetime,
    km_start: float,
    km_end: float,
    status: str = "closed",
) -> VehicleUsageSession:
    s = VehicleUsageSession(
        vehicle_id=vehicle.id,
        started_by_user_id=driver_user_id,
        actual_driver_user_id=driver_user_id,
        started_at=started_at,
        ended_at=started_at + timedelta(hours=2),
        start_odometer_km=Decimal(str(km_start)),
        end_odometer_km=Decimal(str(km_end)),
        status=status,
    )
    db.add(s)
    db.flush()
    return s


def _make_fuel_log(
    db: Session,
    vehicle: Vehicle,
    user_id: int,
    fueled_at: datetime,
    liters: float,
    cost: float,
) -> VehicleFuelLog:
    log = VehicleFuelLog(
        vehicle_id=vehicle.id,
        recorded_by_user_id=user_id,
        fueled_at=fueled_at,
        liters=Decimal(str(liters)),
        total_cost=Decimal(str(cost)),
    )
    db.add(log)
    db.flush()
    return log


def _make_activity(
    db: Session,
    catalog: ActivityCatalog,
    user_id: int,
    started_at: datetime,
    declared_min: int,
    calculated_min: int | None = None,
    team_id=None,
    status: str = "submitted",
) -> OperatorActivity:
    a = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=user_id,
        team_id=team_id,
        started_at=started_at,
        ended_at=started_at + timedelta(minutes=declared_min),
        duration_minutes_declared=declared_min,
        duration_minutes_calculated=calculated_min,
        status=status,
    )
    db.add(a)
    db.flush()
    return a


# ─── /analytics/summary ───────────────────────────────────────────────────────

def test_summary_empty_db_returns_zeros() -> None:
    response = client.get("/operazioni/analytics/summary", headers=_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["total_km"] == 0.0
    assert data["total_liters"] == 0.0
    assert data["total_fuel_cost"] == 0.0
    assert data["total_work_hours"] == 0.0
    assert data["active_sessions"] == 0
    assert data["anomaly_count"] == 0
    assert data["avg_consumption_l_per_100km"] is None


def test_summary_aggregates_km_fuel_and_hours() -> None:
    db = TestingSessionLocal()
    vehicle = _make_vehicle(db, "AB001CD")
    user = _make_user(db, "driver-summary")

    base = datetime(2026, 3, 15, 8, 0)

    _make_session(db, vehicle, user.id, base, 1000, 1150)      # 150 km
    _make_session(db, vehicle, user.id, base + timedelta(days=5), 1150, 1250)  # 100 km

    _make_fuel_log(db, vehicle, user.id, base, 40.0, 60.0)
    _make_fuel_log(db, vehicle, user.id, base + timedelta(days=5), 60.0, 90.0)  # 100L total, €150

    catalog = ActivityCatalog(code="SUM-ACT", name="Attività test", category="manutenzione")
    db.add(catalog)
    db.flush()
    _make_activity(db, catalog, user.id, base, declared_min=120, calculated_min=120)
    _make_activity(db, catalog, user.id, base + timedelta(days=5), declared_min=60, calculated_min=60)
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/summary",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_km"] == pytest.approx(250.0, abs=0.5)
    assert data["total_liters"] == pytest.approx(100.0, abs=0.1)
    assert data["total_fuel_cost"] == pytest.approx(150.0, abs=0.1)
    assert data["total_work_hours"] == pytest.approx(3.0, abs=0.1)
    assert data["avg_consumption_l_per_100km"] == pytest.approx(40.0, abs=1.0)


def test_summary_requires_operazioni_module() -> None:
    response = client.get(
        "/operazioni/analytics/summary",
        headers=_auth_headers(module_operazioni=False),
    )
    assert response.status_code == 403


def test_summary_date_filter_excludes_out_of_range() -> None:
    db = TestingSessionLocal()
    vehicle = _make_vehicle(db, "ZZ999ZZ")
    user = _make_user(db, "driver-filter")

    # Session in February — must be excluded when filtering March
    _make_session(db, vehicle, user.id, datetime(2026, 2, 10), 0, 200)
    _make_fuel_log(db, vehicle, user.id, datetime(2026, 2, 10), 80.0, 120.0)
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/summary",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_km"] == 0.0
    assert data["total_liters"] == 0.0


# ─── /analytics/fuel ──────────────────────────────────────────────────────────

def test_fuel_time_series_groups_by_month() -> None:
    db = TestingSessionLocal()
    vehicle = _make_vehicle(db, "FU001EL")
    user = _make_user(db, "driver-fuel")

    _make_fuel_log(db, vehicle, user.id, datetime(2026, 1, 10), 50.0, 75.0)
    _make_fuel_log(db, vehicle, user.id, datetime(2026, 1, 20), 30.0, 45.0)
    _make_fuel_log(db, vehicle, user.id, datetime(2026, 2, 5), 70.0, 105.0)
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/fuel",
        params={"from_date": "2026-01-01", "to_date": "2026-02-28", "granularity": "month"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    periods = {p["period"]: p["value"] for p in data["time_series"]}
    assert "2026-01" in periods
    assert periods["2026-01"] == pytest.approx(80.0, abs=0.1)
    assert "2026-02" in periods
    assert periods["2026-02"] == pytest.approx(70.0, abs=0.1)
    assert data["total_liters"] == pytest.approx(150.0, abs=0.1)
    assert data["total_cost"] == pytest.approx(225.0, abs=0.1)


def test_fuel_time_series_groups_by_week() -> None:
    db = TestingSessionLocal()
    vehicle = _make_vehicle(db, "FU002EL")
    user = _make_user(db, "driver-fuel-week")

    # 2026-W04: Jan 19-25
    _make_fuel_log(db, vehicle, user.id, datetime(2026, 1, 19), 40.0, 60.0)
    _make_fuel_log(db, vehicle, user.id, datetime(2026, 1, 21), 20.0, 30.0)
    # 2026-W05: Jan 26 - Feb 1
    _make_fuel_log(db, vehicle, user.id, datetime(2026, 1, 26), 55.0, 82.5)
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/fuel",
        params={"from_date": "2026-01-19", "to_date": "2026-01-31", "granularity": "week"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    periods = {p["period"]: p["value"] for p in data["time_series"]}
    assert "2026-W04" in periods
    assert periods["2026-W04"] == pytest.approx(60.0, abs=0.1)
    assert "2026-W05" in periods
    assert periods["2026-W05"] == pytest.approx(55.0, abs=0.1)


def test_fuel_top_vehicles_ordered_by_liters() -> None:
    db = TestingSessionLocal()
    v1 = _make_vehicle(db, "AA001BB", "VH-HI")
    v2 = _make_vehicle(db, "CC002DD", "VH-LO")
    user = _make_user(db, "driver-topv")

    base = datetime(2026, 3, 1)
    _make_fuel_log(db, v1, user.id, base, 200.0, 300.0)
    _make_fuel_log(db, v1, user.id, base + timedelta(days=1), 100.0, 150.0)
    _make_fuel_log(db, v2, user.id, base, 50.0, 75.0)
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/fuel",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    top = data["top_vehicles"]
    assert len(top) >= 2
    assert top[0]["total_liters"] >= top[1]["total_liters"]
    assert top[0]["label"] == "AA001BB"
    assert top[0]["total_liters"] == pytest.approx(300.0, abs=0.1)
    assert top[0]["refuel_count"] == 2


def test_fuel_empty_period_returns_empty_series() -> None:
    response = client.get(
        "/operazioni/analytics/fuel",
        params={"from_date": "2026-06-01", "to_date": "2026-06-30"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["time_series"] == []
    assert data["top_vehicles"] == []
    assert data["total_liters"] == 0.0


# ─── /analytics/km ────────────────────────────────────────────────────────────

def test_km_time_series_uses_odometer_diff() -> None:
    db = TestingSessionLocal()
    vehicle = _make_vehicle(db, "KM001AA")
    user = _make_user(db, "driver-km")

    _make_session(db, vehicle, user.id, datetime(2026, 3, 5, 8), 5000, 5180)   # 180 km
    _make_session(db, vehicle, user.id, datetime(2026, 3, 15, 8), 5180, 5280)  # 100 km
    _make_session(db, vehicle, user.id, datetime(2026, 4, 2, 8), 5280, 5380)   # 100 km (April)
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/km",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31", "granularity": "month"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_km"] == pytest.approx(280.0, abs=0.5)
    assert data["avg_km_per_session"] == pytest.approx(140.0, abs=0.5)
    periods = {p["period"]: p["value"] for p in data["time_series"]}
    assert "2026-03" in periods
    assert "2026-04" not in periods


def test_km_top_vehicles_ordered() -> None:
    db = TestingSessionLocal()
    v1 = _make_vehicle(db, "KM002BB", "VH-KM-HI")
    v2 = _make_vehicle(db, "KM003CC", "VH-KM-LO")
    user = _make_user(db, "driver-km2")

    base = datetime(2026, 3, 1, 8)
    _make_session(db, v1, user.id, base, 0, 500)
    _make_session(db, v2, user.id, base + timedelta(days=1), 0, 100)
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/km",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    top = data["top_vehicles"]
    assert top[0]["label"] == "KM002BB"
    assert top[0]["total_km"] == pytest.approx(500.0, abs=0.5)


def test_km_excludes_open_sessions() -> None:
    db = TestingSessionLocal()
    vehicle = _make_vehicle(db, "KM004DD")
    user = _make_user(db, "driver-km-open")

    # Open session — should not count in km totals
    _make_session(db, vehicle, user.id, datetime(2026, 3, 10, 8), 0, 999, status="open")
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/km",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    assert response.json()["total_km"] == 0.0


def test_km_longest_and_shortest_session_are_returned() -> None:
    db = TestingSessionLocal()
    vehicle = _make_vehicle(db, "KMEXT01")
    user = _make_user(db, "driver-km-extremes")

    base = datetime(2026, 3, 10, 8, 0)

    # Short: 30 min
    s1 = VehicleUsageSession(
        vehicle_id=vehicle.id,
        started_by_user_id=user.id,
        actual_driver_user_id=user.id,
        started_at=base,
        ended_at=base + timedelta(minutes=30),
        start_odometer_km=Decimal("1000"),
        end_odometer_km=Decimal("1010"),
        status="closed",
    )
    # Long: 3h 15m
    s2 = VehicleUsageSession(
        vehicle_id=vehicle.id,
        started_by_user_id=user.id,
        actual_driver_user_id=user.id,
        started_at=base + timedelta(days=1),
        ended_at=base + timedelta(days=1, hours=3, minutes=15),
        start_odometer_km=Decimal("1010"),
        end_odometer_km=Decimal("1100"),
        status="closed",
    )
    db.add_all([s1, s2])
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/km",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["longest_session"]["duration_minutes"] == 195
    assert data["shortest_session"]["duration_minutes"] == 30
    assert data["longest_session"]["vehicle_label"] == "KMEXT01"
    assert data["shortest_session"]["vehicle_label"] == "KMEXT01"


# ─── /analytics/work-hours ────────────────────────────────────────────────────

def test_work_hours_aggregates_declared_minutes() -> None:
    db = TestingSessionLocal()
    catalog = ActivityCatalog(code="WH-ACT", name="Manutenzione", category="manutenzione")
    db.add(catalog)
    db.flush()
    user = _make_user(db, "driver-wh")

    base = datetime(2026, 3, 10, 8)
    _make_activity(db, catalog, user.id, base, declared_min=120)          # 2h
    _make_activity(db, catalog, user.id, base + timedelta(days=1), declared_min=90)   # 1.5h
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/work-hours",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_hours"] == pytest.approx(3.5, abs=0.1)
    assert data["avg_hours_per_operator"] == pytest.approx(3.5, abs=0.1)


def test_work_hours_prefers_calculated_over_declared() -> None:
    db = TestingSessionLocal()
    catalog = ActivityCatalog(code="WH-CALC", name="Calcolo", category="test")
    db.add(catalog)
    db.flush()
    user = _make_user(db, "driver-wh-calc")

    # declared=120 but calculated=90 → should use 90
    _make_activity(db, catalog, user.id, datetime(2026, 3, 5, 8), declared_min=120, calculated_min=90)
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/work-hours",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_hours"] == pytest.approx(1.5, abs=0.1)


def test_work_hours_groups_by_team() -> None:
    db = TestingSessionLocal()
    catalog = ActivityCatalog(code="WH-TEAM", name="Lavoro team", category="squadra")
    db.add(catalog)
    team = Team(code="SQUAD-A", name="Squadra A")
    db.add(team)
    db.flush()

    user1 = _make_user(db, "driver-team1")
    user2 = _make_user(db, "driver-team2")

    base = datetime(2026, 3, 1, 8)
    _make_activity(db, catalog, user1.id, base, declared_min=60, team_id=team.id)
    _make_activity(db, catalog, user2.id, base + timedelta(days=1), declared_min=120, team_id=team.id)
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/work-hours",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    teams = {t["team_name"]: t for t in data["by_team"]}
    assert "Squadra A" in teams
    assert teams["Squadra A"]["total_hours"] == pytest.approx(3.0, abs=0.1)
    assert teams["Squadra A"]["operator_count"] == 2


def test_work_hours_by_category_breakdown() -> None:
    db = TestingSessionLocal()
    cat1 = ActivityCatalog(code="WH-CAT1", name="Irrigazione", category="irrigazione")
    cat2 = ActivityCatalog(code="WH-CAT2", name="Manutenzione", category="manutenzione")
    db.add_all([cat1, cat2])
    db.flush()
    user = _make_user(db, "driver-cats")

    base = datetime(2026, 3, 1, 8)
    _make_activity(db, cat1, user.id, base, declared_min=180)
    _make_activity(db, cat2, user.id, base + timedelta(days=1), declared_min=60)
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/work-hours",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    cats = {c["category"]: c["total_hours"] for c in response.json()["by_category"]}
    assert "irrigazione" in cats
    assert cats["irrigazione"] == pytest.approx(3.0, abs=0.1)
    assert "manutenzione" in cats
    assert cats["manutenzione"] == pytest.approx(1.0, abs=0.1)


def test_work_hours_excludes_draft_activities() -> None:
    db = TestingSessionLocal()
    catalog = ActivityCatalog(code="WH-DRAFT", name="Bozza", category="test")
    db.add(catalog)
    db.flush()
    user = _make_user(db, "driver-draft")

    _make_activity(db, catalog, user.id, datetime(2026, 3, 5, 8), declared_min=240, status="draft")
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/work-hours",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    assert response.json()["total_hours"] == 0.0


# ─── /analytics/anomalies ─────────────────────────────────────────────────────

def test_anomalies_detects_excessive_fuel() -> None:
    db = TestingSessionLocal()
    vehicle = _make_vehicle(db, "AN001AA")
    user = _make_user(db, "driver-excess")

    # Normal refuel
    _make_fuel_log(db, vehicle, user.id, datetime(2026, 3, 10), 50.0, 75.0)
    # Excessive refuel (> 120L threshold)
    _make_fuel_log(db, vehicle, user.id, datetime(2026, 3, 15), 150.0, 225.0)
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/anomalies",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31", "type": "excessive_fuel"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["type"] == "excessive_fuel"
    assert item["severity"] == "medium"
    assert "150" in item["description"]
    assert item["entity_label"] == "AN001AA"


def test_anomalies_detects_unmatched_refuel_events() -> None:
    db = TestingSessionLocal()
    vehicle = _make_vehicle(db, "AN002BB")

    ev1 = WCRefuelEvent(
        wc_id=1001,
        vehicle_code="VH-AN002BB",
        operator_name="Mario Rossi",
        fueled_at=datetime(2026, 3, 12, 10, 0),
        matched_fuel_log_id=None,
    )
    ev2 = WCRefuelEvent(
        wc_id=1002,
        vehicle_code="VH-AN002BB",
        operator_name="Luigi Bianchi",
        fueled_at=datetime(2026, 3, 14, 14, 0),
        matched_fuel_log_id=None,
    )
    db.add_all([ev1, ev2])
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/anomalies",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31", "type": "unmatched_refuel"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["by_type"].get("unmatched_refuel") == 2
    assert all(i["type"] == "unmatched_refuel" for i in data["items"])
    assert all(i["severity"] == "low" for i in data["items"])


def test_anomalies_detects_hours_discrepancy() -> None:
    db = TestingSessionLocal()
    catalog = ActivityCatalog(code="AN-DISC", name="Discrepanza", category="test")
    db.add(catalog)
    db.flush()
    user = _make_user(db, "driver-disc")

    # Discrepancy > 60 min
    a = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=user.id,
        started_at=datetime(2026, 3, 10, 8),
        ended_at=datetime(2026, 3, 10, 12),
        duration_minutes_declared=240,
        duration_minutes_calculated=90,  # 150 min diff
        status="submitted",
    )
    # Small discrepancy — below threshold (30 min diff, not > 60)
    b = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=user.id,
        started_at=datetime(2026, 3, 11, 8),
        ended_at=datetime(2026, 3, 11, 10),
        duration_minutes_declared=120,
        duration_minutes_calculated=90,  # 30 min diff — below threshold
        status="submitted",
    )
    db.add_all([a, b])
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/anomalies",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31", "type": "hours_discrepancy"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["type"] == "hours_discrepancy"
    assert item["details"]["diff_min"] == 150
    assert item["details"]["declared_min"] == 240
    assert item["details"]["calculated_min"] == 90


def test_anomalies_detects_driver_mismatch() -> None:
    db = TestingSessionLocal()
    vehicle = _make_vehicle(db, "AN003CC")
    assigned_user = _make_user(db, "driver-assigned")
    other_user = _make_user(db, "driver-other")

    base = datetime(2026, 3, 10, 8)

    # Assign vehicle to assigned_user
    assignment = VehicleAssignment(
        vehicle_id=vehicle.id,
        operator_user_id=assigned_user.id,
        assignment_target_type="operator",
        start_at=base - timedelta(days=1),
        end_at=base + timedelta(days=10),
        assigned_by_user_id=assigned_user.id,
    )
    db.add(assignment)
    db.flush()

    # Session driven by other_user — mismatch
    s = VehicleUsageSession(
        vehicle_id=vehicle.id,
        started_by_user_id=other_user.id,
        actual_driver_user_id=other_user.id,
        started_at=base,
        ended_at=base + timedelta(hours=3),
        start_odometer_km=Decimal("1000"),
        end_odometer_km=Decimal("1100"),
        status="closed",
    )
    db.add(s)
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/anomalies",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31", "type": "driver_mismatch"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["type"] == "driver_mismatch"
    assert item["severity"] == "high"
    assert item["entity_label"] == "AN003CC"


def test_anomalies_no_mismatch_when_driver_is_assigned() -> None:
    db = TestingSessionLocal()
    vehicle = _make_vehicle(db, "AN004DD")
    user = _make_user(db, "driver-correct")

    base = datetime(2026, 3, 10, 8)
    assignment = VehicleAssignment(
        vehicle_id=vehicle.id,
        operator_user_id=user.id,
        assignment_target_type="operator",
        start_at=base - timedelta(days=1),
        end_at=base + timedelta(days=10),
        assigned_by_user_id=user.id,
    )
    db.add(assignment)
    db.flush()

    s = VehicleUsageSession(
        vehicle_id=vehicle.id,
        started_by_user_id=user.id,
        actual_driver_user_id=user.id,
        started_at=base,
        ended_at=base + timedelta(hours=2),
        start_odometer_km=Decimal("2000"),
        end_odometer_km=Decimal("2050"),
        status="closed",
    )
    db.add(s)
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/anomalies",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31", "type": "driver_mismatch"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_anomalies_all_types_returned_without_filter() -> None:
    db = TestingSessionLocal()
    vehicle = _make_vehicle(db, "AN005EE")
    user = _make_user(db, "driver-all")

    base = datetime(2026, 3, 10, 8)

    # Excessive fuel
    _make_fuel_log(db, vehicle, user.id, base, 200.0, 300.0)
    # Unmatched refuel
    db.add(WCRefuelEvent(wc_id=9001, vehicle_code="X", fueled_at=base, matched_fuel_log_id=None))
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/anomalies",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    types_found = {i["type"] for i in data["items"]}
    assert "excessive_fuel" in types_found
    assert "unmatched_refuel" in types_found
    assert data["total"] >= 2


def test_anomalies_sorted_high_severity_first() -> None:
    db = TestingSessionLocal()
    vehicle = _make_vehicle(db, "AN006FF")
    assigned_user = _make_user(db, "driver-sev-assigned")
    other_user = _make_user(db, "driver-sev-other")

    base = datetime(2026, 3, 10, 8)

    # High: driver mismatch
    assignment = VehicleAssignment(
        vehicle_id=vehicle.id,
        operator_user_id=assigned_user.id,
        assignment_target_type="operator",
        start_at=base - timedelta(days=1),
        end_at=base + timedelta(days=10),
        assigned_by_user_id=assigned_user.id,
    )
    db.add(assignment)
    db.flush()
    db.add(VehicleUsageSession(
        vehicle_id=vehicle.id,
        started_by_user_id=other_user.id,
        actual_driver_user_id=other_user.id,
        started_at=base,
        ended_at=base + timedelta(hours=2),
        start_odometer_km=Decimal("0"),
        end_odometer_km=Decimal("50"),
        status="closed",
    ))

    # Low: unmatched refuel
    db.add(WCRefuelEvent(wc_id=9002, vehicle_code="X", fueled_at=base, matched_fuel_log_id=None))
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/anomalies",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    items = response.json()["items"]
    severities = [i["severity"] for i in items]
    sev_order = {"high": 0, "medium": 1, "low": 2}
    assert severities == sorted(severities, key=lambda s: sev_order.get(s, 3))


def test_anomalies_by_severity_counts_correct() -> None:
    db = TestingSessionLocal()
    vehicle = _make_vehicle(db, "AN007GG")
    user = _make_user(db, "driver-sev-count")

    base = datetime(2026, 3, 10, 8)
    # 2 excessive fuel (medium)
    _make_fuel_log(db, vehicle, user.id, base, 130.0, 195.0)
    _make_fuel_log(db, vehicle, user.id, base + timedelta(days=1), 150.0, 225.0)
    # 1 unmatched (low)
    db.add(WCRefuelEvent(wc_id=9003, vehicle_code="X", fueled_at=base, matched_fuel_log_id=None))
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/anomalies",
        params={"from_date": "2026-03-01", "to_date": "2026-03-31"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["by_severity"].get("medium", 0) == 2
    assert data["by_severity"].get("low", 0) == 1
    assert data["by_type"].get("excessive_fuel", 0) == 2
    assert data["by_type"].get("unmatched_refuel", 0) == 1


# ─── Granularity edge cases ────────────────────────────────────────────────────

def test_fuel_granularity_day() -> None:
    db = TestingSessionLocal()
    vehicle = _make_vehicle(db, "GR001AA")
    user = _make_user(db, "driver-day")

    _make_fuel_log(db, vehicle, user.id, datetime(2026, 3, 1, 9), 40.0, 60.0)
    _make_fuel_log(db, vehicle, user.id, datetime(2026, 3, 1, 17), 20.0, 30.0)  # same day
    _make_fuel_log(db, vehicle, user.id, datetime(2026, 3, 3, 10), 50.0, 75.0)
    db.commit()
    db.close()

    response = client.get(
        "/operazioni/analytics/fuel",
        params={"from_date": "2026-03-01", "to_date": "2026-03-05", "granularity": "day"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    periods = {p["period"]: p["value"] for p in response.json()["time_series"]}
    assert "2026-03-01" in periods
    assert periods["2026-03-01"] == pytest.approx(60.0, abs=0.1)
    assert "2026-03-03" in periods
    assert periods["2026-03-03"] == pytest.approx(50.0, abs=0.1)
    assert "2026-03-02" not in periods


def test_km_granularity_invalid_returns_422() -> None:
    response = client.get(
        "/operazioni/analytics/km",
        params={"granularity": "quarter"},
        headers=_auth_headers(),
    )
    assert response.status_code == 422
