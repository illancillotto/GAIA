"""Characterization of GET /me/summary operazioni aggregates (slice R120)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal

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
from app.modules.me import router as me_router
from app.modules.operazioni.models.activities import ActivityCatalog, OperatorActivity
from app.modules.operazioni.models.reports import (
    FieldReport,
    FieldReportCategory,
    FieldReportSeverity,
    InternalCase,
)
from app.modules.operazioni.models.vehicles import Vehicle, VehicleAssignment, VehicleUsageSession

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
client = TestClient(app)

JUNE = "period_start=2026-06-01&period_end=2026-06-30"
OPERAZIONI_ZERO = {
    "activities_count": 0,
    "activity_minutes": 0,
    "reports_count": 0,
    "assigned_cases_count": 0,
    "open_cases_count": 0,
    "closed_cases_count": 0,
    "vehicle_sessions_count": 0,
    "vehicle_km": 0.0,
    "active_vehicle_assignments_count": 0,
}


def _override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _database() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = _override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _user(
    username: str,
    *,
    role: str = ApplicationUserRole.VIEWER.value,
    module_operazioni: bool = True,
    is_active: bool = True,
) -> int:
    db = TestingSessionLocal()
    try:
        user = ApplicationUser(
            username=username,
            email=f"{username}@example.local",
            password_hash=hash_password("secret123"),
            role=role,
            is_active=is_active,
            module_accessi=True,
            module_operazioni=module_operazioni,
            module_rete=False,
            module_presenze=False,
        )
        db.add(user)
        db.commit()
        return user.id
    finally:
        db.close()


def _headers(username: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": "secret123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _at(day: int, month: int = 6, hour: int = 8) -> datetime:
    return datetime(2026, month, day, hour, 0, tzinfo=UTC)


def _seed_operazioni(user_id: int, other_id: int, *, cases_in_period: bool = True) -> None:
    db = TestingSessionLocal()
    try:
        category = FieldReportCategory(code="GUASTO", name="Guasto", is_active=True)
        severity = FieldReportSeverity(code="ALTA", name="Alta", rank_order=1, is_active=True)
        catalog = ActivityCatalog(
            code="SOPR", name="Sopralluogo", category="Territorio", is_active=True
        )
        vehicle = Vehicle(
            code="MEZZO-01", name="Porter", vehicle_type="pickup", plate_number="GA123IA"
        )
        db.add_all([category, severity, catalog, vehicle])
        db.flush()

        def activity(
            operator: int, started: datetime, calc: int | None, declared: int | None
        ) -> OperatorActivity:
            return OperatorActivity(
                activity_catalog_id=catalog.id,
                operator_user_id=operator,
                status="submitted",
                started_at=started,
                duration_minutes_calculated=calc,
                duration_minutes_declared=declared,
            )

        db.add_all(
            [
                activity(user_id, _at(5), 120, 999),
                activity(user_id, _at(6), None, 45),
                activity(user_id, _at(7), None, None),
                activity(user_id, _at(30, 5), 500, None),
                activity(other_id, _at(5), 60, None),
            ]
        )

        def report(
            number: str, reporter: int, created: datetime, client_created: datetime | None
        ) -> FieldReport:
            return FieldReport(
                report_number=number,
                reporter_user_id=reporter,
                category_id=category.id,
                severity_id=severity.id,
                title=number,
                status="submitted",
                created_at=created,
                client_created_at=client_created,
            )

        reports = [
            report("R-IN", user_id, _at(10), _at(10)),
            report("R-OUT-NULLCLIENT", user_id, _at(1, 1), None),
            report("R-OUT", user_id, _at(1, 1), _at(1, 1)),
            report("R-OTHER", other_id, _at(10), None),
            report("R-C2", user_id, _at(1, 1), _at(1, 1)),
            report("R-C3", user_id, _at(1, 1), _at(1, 1)),
            report("R-C4", user_id, _at(1, 1), _at(1, 1)),
            report("R-C5", other_id, _at(1, 1), _at(1, 1)),
        ]
        db.add_all(reports)
        db.flush()

        case_created = _at(12) if cases_in_period else _at(1, 1)
        case_specs = [
            ("C-OPEN", user_id, "open", case_created),
            ("C-CLOSED", user_id, "closed", case_created),
            ("C-RESOLVED", user_id, "resolved", case_created),
            ("C-OLD", user_id, "in_progress", _at(1, 1)),
            ("C-OTHER", other_id, "open", _at(12)),
        ]
        db.add_all(
            [
                InternalCase(
                    case_number=number,
                    source_report_id=reports[index].id,
                    title=number,
                    status=status,
                    assigned_to_user_id=assignee,
                    created_at=created,
                )
                for index, (number, assignee, status, created) in enumerate(case_specs[:3])
            ]
            + [
                InternalCase(
                    case_number=number,
                    source_report_id=reports[index + 5].id,
                    title=number,
                    status=status,
                    assigned_to_user_id=assignee,
                    created_at=created,
                )
                for index, (number, assignee, status, created) in enumerate(case_specs[3:])
            ]
        )

        def session(
            started_by: int, driver: int | None, started: datetime, **km: object
        ) -> VehicleUsageSession:
            return VehicleUsageSession(
                vehicle_id=vehicle.id,
                started_by_user_id=started_by,
                actual_driver_user_id=driver,
                started_at=started,
                start_odometer_km=Decimal("1000.000"),
                status="closed",
                **km,
            )

        db.add_all(
            [
                session(user_id, user_id, _at(5), route_distance_km=Decimal("1.115")),
                session(other_id, user_id, _at(6), end_odometer_km=Decimal("1002.221")),
                session(user_id, other_id, _at(7), km_start=10, km_end=13),
                session(user_id, None, _at(30, 5), route_distance_km=Decimal("50.000")),
                session(other_id, other_id, _at(8), route_distance_km=Decimal("70.000")),
            ]
        )
        db.add_all(
            [
                VehicleAssignment(
                    vehicle_id=vehicle.id,
                    assignment_target_type="user",
                    operator_user_id=user_id,
                    assigned_by_user_id=user_id,
                    start_at=_at(1, 1),
                ),
                VehicleAssignment(
                    vehicle_id=vehicle.id,
                    assignment_target_type="user",
                    operator_user_id=user_id,
                    assigned_by_user_id=user_id,
                    start_at=_at(1, 1),
                    end_at=_at(15),
                ),
                VehicleAssignment(
                    vehicle_id=vehicle.id,
                    assignment_target_type="user",
                    operator_user_id=user_id,
                    assigned_by_user_id=user_id,
                    start_at=_at(1, 1),
                    end_at=_at(1, 2),
                ),
            ]
        )
        db.commit()
    finally:
        db.close()


EXPECTED_JUNE = {
    "period_start": "2026-06-01",
    "period_end": "2026-06-30",
    "presenze": {
        "ordinary_hours": 0.0,
        "extra_hours": 0.0,
        "absence_hours": 0.0,
        "worked_days": 0,
        "anomaly_days": 0,
        "km": 0.0,
    },
    "ordinary_minutes": 0,
    "extra_minutes": 0,
    "absence_minutes": 0,
    "worked_days": 0,
    "anomaly_days": 0,
    "km_from_presenze": 0.0,
    "activities_count": 3,
    "activity_minutes": 165,
    "reports_count": 2,
    "assigned_cases_count": 3,
    "open_cases_count": 1,
    "closed_cases_count": 2,
    "vehicle_sessions_count": 3,
    "vehicle_km": 6.34,
    "assigned_devices_count": 0,
    "active_vehicle_assignments_count": 2,
}


def test_a_requires_authenticated_active_user() -> None:
    _user("r120_inactive", is_active=False)
    assert client.get(f"/me/summary?{JUNE}").status_code == 401
    login = client.post("/auth/login", json={"username": "r120_inactive", "password": "secret123"})
    assert login.status_code != 200


def test_b_operazioni_disabled_keeps_zero_defaults_even_with_data() -> None:
    user_id = _user("r120_noop", module_operazioni=False)
    other_id = _user("r120_noop_other")
    _seed_operazioni(user_id, other_id)

    body = client.get(f"/me/summary?{JUNE}", headers=_headers("r120_noop")).json()

    assert {key: body[key] for key in OPERAZIONI_ZERO} == OPERAZIONI_ZERO


def test_c_full_response_snapshot_for_scoped_period_aggregates() -> None:
    user_id = _user("r120_op")
    other_id = _user("r120_other")
    _seed_operazioni(user_id, other_id)

    response = client.get(f"/me/summary?{JUNE}", headers=_headers("r120_op"))

    assert response.status_code == 200
    assert response.json() == EXPECTED_JUNE


def test_d_cases_fall_back_to_all_assigned_cases_when_none_in_period() -> None:
    user_id = _user("r120_fallback")
    other_id = _user("r120_fallback_other")
    _seed_operazioni(user_id, other_id, cases_in_period=False)

    body = client.get(f"/me/summary?{JUNE}", headers=_headers("r120_fallback")).json()

    assert body["assigned_cases_count"] == 4
    assert body["open_cases_count"] == 2
    assert body["closed_cases_count"] == 2


def test_e_super_admin_gating_and_empty_operazioni_data() -> None:
    _user("r120_super", role=ApplicationUserRole.SUPER_ADMIN.value, module_operazioni=False)

    body = client.get(f"/me/summary?{JUNE}", headers=_headers("r120_super")).json()

    assert {key: body[key] for key in OPERAZIONI_ZERO} == OPERAZIONI_ZERO


def test_f_facade_monkeypatch_reaches_summary_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = _user("r120_patch")
    other_id = _user("r120_patch_other")
    _seed_operazioni(user_id, other_id)
    monkeypatch.setattr(me_router, "_activity_duration_minutes", lambda activity: 7)
    monkeypatch.setattr(me_router, "_vehicle_session_km", lambda session: 1.0049)

    body = client.get(f"/me/summary?{JUNE}", headers=_headers("r120_patch")).json()

    assert body["activity_minutes"] == 21
    assert body["vehicle_km"] == 3.01


def test_openapi_operation_for_me_summary_is_stable() -> None:
    operation = app.openapi()["paths"]["/me/summary"]["get"]

    assert operation["operationId"] == "get_me_summary_me_summary_get"
    assert [param["name"] for param in operation["parameters"]] == ["period_start", "period_end"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/MeSummaryResponse"
    }
