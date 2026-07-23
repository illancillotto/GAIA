from __future__ import annotations

import base64
import sys
import types
import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from uuid import UUID

import pytest

if "shapely" not in sys.modules:
    shapely_module = types.ModuleType("shapely")
    shapely_geometry = types.ModuleType("shapely.geometry")
    shapely_geometry.shape = lambda value: value
    shapely_module.geometry = shapely_geometry
    sys.modules["shapely"] = shapely_module
    sys.modules["shapely.geometry"] = shapely_geometry

if "geoalchemy2" not in sys.modules:
    geoalchemy2_module = types.ModuleType("geoalchemy2")
    geoalchemy2_shape = types.ModuleType("geoalchemy2.shape")
    geoalchemy2_shape.to_shape = lambda value: value
    geoalchemy2_module.shape = geoalchemy2_shape
    sys.modules["geoalchemy2"] = geoalchemy2_module
    sys.modules["geoalchemy2.shape"] = geoalchemy2_shape

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.catasto_phase1 import CatDeliveryPoint, CatMeterReading
from app.modules.operazioni.routes import mobile_sync as mobile_sync_routes
from app.modules.operazioni.routes import mobile_gateway_sync as mobile_gateway_sync_routes
from app.modules.operazioni.models.activities import ActivityCatalog, OperatorActivity
from app.modules.operazioni.models.attachments import Attachment
from app.modules.operazioni.models.gate_mobile_sync_run import GateMobileSyncRun
from app.modules.operazioni.models.mobile_sync import MobileSyncEvent
from app.modules.operazioni.models.organizational import OperatorProfile, Team, TeamMembership
from app.modules.operazioni.models.reports import (
    FieldReport,
    FieldReportAttachment,
    FieldReportCategory,
    FieldReportSeverity,
    InternalCaseAttachment,
)
from app.modules.operazioni.models.vehicles import Vehicle, VehicleAssignment
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyRecord
from app.services import gate_mobile_sync as gate_mobile_sync_service
from app.services.gate_mobile_sync import GateMobileSyncExecutionResult, GateMobileSyncReport


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
client = TestClient(app)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_function() -> None:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_function() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _seed_admin() -> dict[str, str]:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username="mobile-sync-admin",
        email="mobile-sync-admin@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_operazioni=True,
    )
    db.add(user)
    db.commit()
    db.close()

    response = client.post("/auth/login", json={"username": "mobile-sync-admin", "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _connector_headers() -> dict[str, str]:
    return {settings.mobile_connector_header_name: settings.mobile_connector_token}


def _seed_mobile_operator(db: Session) -> tuple[WCOperator, ApplicationUser]:
    gaia_user = ApplicationUser(
        username="field.operator",
        email="field.operator@example.local",
        password_hash=hash_password("operator123"),
        role=ApplicationUserRole.OPERATOR.value,
        is_active=True,
        module_operazioni=True,
    )
    db.add(gaia_user)
    db.flush()

    db.add(
        OperatorProfile(
            user_id=gaia_user.id,
            phone="+39000000001",
            can_drive_vehicles=True,
            is_active=True,
        )
    )

    operator = WCOperator(
        wc_id=101,
        username="field.operator",
        email="field.operator@example.local",
        first_name="Mario",
        last_name="Rossi",
        enabled=True,
        gate_mobile_console_enabled=True,
        gate_mobile_console_role="console_admin",
        gaia_user_id=gaia_user.id,
        wc_synced_at=datetime.now(UTC),
    )
    db.add(operator)
    db.flush()
    return operator, gaia_user


def test_gate_mobile_operator_push_payload_includes_console_permissions() -> None:
    db = TestingSessionLocal()
    _seed_mobile_operator(db)
    db.commit()

    payload = gate_mobile_sync_service.build_mobile_operator_push_payload(db)

    assert payload["operators"][0]["gate_mobile_console_enabled"] is True
    assert payload["operators"][0]["gate_mobile_console_role"] == "console_admin"
    db.close()


def test_enable_gate_mobile_console_for_first_giornaliere_worker() -> None:
    db = TestingSessionLocal()
    users: list[ApplicationUser] = []
    operators: list[WCOperator] = []
    for index, contract_kind in enumerate(("operaio", "impiegato"), start=1):
        user = ApplicationUser(
            username=f"giornaliera-user-{index}",
            email=f"giornaliera-user-{index}@example.local",
            password_hash=hash_password("operator123"),
            role=ApplicationUserRole.OPERATOR.value,
            is_active=True,
            module_presenze=True,
        )
        db.add(user)
        db.flush()
        operator = WCOperator(
            wc_id=200 + index,
            username=user.username,
            email=user.email,
            first_name=f"Nome{index}",
            last_name=f"Cognome{index}",
            enabled=True,
            gaia_user_id=user.id,
            gate_mobile_console_enabled=False,
        )
        collaborator = PresenzeCollaborator(
            application_user_id=user.id,
            employee_code=f"E{index:03d}",
            name=f"Collaboratore {index}",
            contract_kind=contract_kind,
            is_active=True,
        )
        db.add_all([operator, collaborator])
        db.flush()
        db.add(PresenzeDailyRecord(collaborator_id=collaborator.id, application_user_id=user.id, work_date=date(2026, 7, index)))
        if index == 1:
            db.add(
                PresenzeDailyRecord(
                    collaborator_id=collaborator.id,
                    application_user_id=user.id,
                    work_date=date(2026, 7, 10),
                )
            )
        users.append(user)
        operators.append(operator)
    db.commit()

    with pytest.raises(ValueError, match="limit must be greater than zero"):
        gate_mobile_sync_service.enable_gate_mobile_console_for_giornaliere_workers(db, limit=0)

    dry_run = gate_mobile_sync_service.enable_gate_mobile_console_for_giornaliere_workers(db, limit=1, dry_run=True)

    assert dry_run.candidates_total == 2
    assert dry_run.enabled_total == 1
    assert dry_run.items[0].username == "giornaliera-user-1"
    assert db.get(WCOperator, operators[0].id).gate_mobile_console_enabled is False

    result = gate_mobile_sync_service.enable_gate_mobile_console_for_giornaliere_workers(
        db,
        limit=1,
        role="viewer",
        dry_run=False,
    )

    assert result.candidates_total == 2
    assert result.enabled_total == 1
    assert result.items[0].gaia_user_id == users[0].id
    assert db.get(WCOperator, operators[0].id).gate_mobile_console_enabled is True
    assert db.get(WCOperator, operators[0].id).gate_mobile_console_role == "viewer"
    assert db.get(WCOperator, operators[1].id).gate_mobile_console_enabled is False
    db.close()


def test_mobile_sync_exports_operators_catalogs_and_worksets() -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, gaia_user = _seed_mobile_operator(db)
    operator_id = str(operator.id)
    gaia_user_id = gaia_user.id

    team = Team(code="TEAM-NORD", name="Squadra Nord", is_active=True)
    db.add(team)
    db.flush()
    db.add(
        TeamMembership(
            team_id=team.id,
            user_id=gaia_user.id,
            valid_from=datetime.now(UTC) - timedelta(days=1),
            is_primary=True,
        )
    )

    catalog = ActivityCatalog(code="SOPR", name="Sopralluogo", category="rete", is_active=True)
    category = FieldReportCategory(code="LOSS", name="Perdita", wc_id=3, is_active=True)
    severity = FieldReportSeverity(code="MED", name="Media", rank_order=1, is_active=True)
    vehicle = Vehicle(
        code="VH-001",
        name="Pickup Nord",
        plate_number="AB123CD",
        vehicle_type="pickup",
        current_status="available",
        is_active=True,
    )
    db.add_all([catalog, category, severity, vehicle])
    db.flush()

    db.add(
        VehicleAssignment(
            vehicle_id=vehicle.id,
            assignment_target_type="team",
            team_id=team.id,
            assigned_by_user_id=gaia_user.id,
            start_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    db.add(
        OperatorActivity(
            activity_catalog_id=catalog.id,
            operator_user_id=gaia_user.id,
            team_id=team.id,
            vehicle_id=vehicle.id,
            status="in_progress",
            started_at=datetime.now(UTC) - timedelta(hours=1),
            text_note="Attivita assegnata",
        )
    )
    db.add(
        CatDeliveryPoint(
            distretto_code="D01",
            punto_consegna_code="CNT-001",
            tipologia="Idrante",
            tipo="Punto presa",
            cod_cont="MTR-001",
            has_meter=True,
            source_dataset="test",
            source_x=8.591234,
            source_y=39.903456,
            is_active=True,
        )
    )
    db.flush()
    delivery_point_id = db.query(CatDeliveryPoint).filter(CatDeliveryPoint.punto_consegna_code == "CNT-001").one().id
    db.add(
        CatDeliveryPoint(
            distretto_code="D01",
            punto_consegna_code="NO-METER-001",
            tipologia="Punto senza contatore",
            tipo="Punto presa",
            cod_cont=None,
            has_meter=False,
            source_dataset="test",
            source_x=8.592000,
            source_y=39.904000,
            is_active=True,
        )
    )
    db.add(
        CatDeliveryPoint(
            distretto_code="D01",
            punto_consegna_code="NO-CODE-001",
            tipologia="Colonnina flangiata",
            tipo="FLANGIA",
            cod_cont=None,
            has_meter=True,
            source_dataset="test",
            source_x=8.593000,
            source_y=39.905000,
            is_active=True,
        )
    )
    db.add(
        CatDeliveryPoint(
            distretto_code="D01",
            punto_consegna_code="PLACEHOLDER-CODE-001",
            tipologia="Idrometro non letto",
            tipo="CONT_NO_TES",
            cod_cont="0",
            has_meter=True,
            source_dataset="test",
            source_x=8.594000,
            source_y=39.906000,
            is_active=True,
        )
    )
    db.add(
        CatMeterReading(
            anno=2026,
            punto_consegna="CNT-001",
            matricola="MTR-001",
            record_kind="meter_reading",
            source="mobile",
            delivery_point_id=delivery_point_id,
            mobile_operator_id=str(operator.id),
        )
    )
    db.add(
        CatMeterReading(
            anno=2026,
            punto_consegna="ORPHAN-001",
            matricola="ORPHAN-MTR-001",
            record_kind="meter_reading",
            source="excel",
        )
    )
    db.commit()
    db.close()

    operators_response = client.get("/api/mobile-sync/mobile-operators", headers=headers)
    assert operators_response.status_code == 200
    operators_payload = operators_response.json()
    assert operators_payload["operators"][0]["operator_id"] == operator_id
    assert operators_payload["operators"][0]["status"] == "ACTIVE"
    assert operators_payload["operators"][0]["gaia_user_id"] == str(gaia_user_id)
    assert operators_payload["operators"][0]["gaia_username"] == "field.operator"
    assert operators_payload["operators"][0]["gate_mobile_console_enabled"] is True
    assert operators_payload["operators"][0]["gate_mobile_console_role"] == "console_admin"

    catalogs_response = client.get("/api/mobile-sync/catalogs", headers=headers)
    assert catalogs_response.status_code == 200
    catalog_types = {item["catalog_type"] for item in catalogs_response.json()["catalogs"]}
    assert {"activity_types", "report_types", "report_severities", "vehicles", "meters"} <= catalog_types
    report_types = next(item for item in catalogs_response.json()["catalogs"] if item["catalog_type"] == "report_types")
    assert report_types["payload"]["items"][0]["id"] == "3"
    meters_catalog = next(item for item in catalogs_response.json()["catalogs"] if item["catalog_type"] == "meters")
    meter_items = meters_catalog["payload"]["items"]
    assert [item["punto_consegna"] for item in meter_items] == ["CNT-001", "NO-CODE-001", "PLACEHOLDER-CODE-001"]
    assert meter_items[0] == {
        "id": meter_items[0]["id"],
        "delivery_point_id": meter_items[0]["delivery_point_id"],
        "label": "CNT-001 · MTR-001 · Idrante",
        "code": "CNT-001",
        "punto_consegna": "CNT-001",
        "meter_number": "MTR-001",
        "matricola": "MTR-001",
        "cod_cont": "MTR-001",
        "distretto_code": "D01",
        "tipologia": "Idrante",
        "tipo": "Punto presa",
        "has_meter": True,
        "gps_lat": 39.903,
        "gps_lng": 8.591,
        "lat": 39.903,
        "lng": 8.591,
        "source_dataset": "test",
        "reading_id": meter_items[0]["reading_id"],
        "reading_year": 2026,
        "operational_state": None,
    }
    assert meter_items[1] == {
        "id": meter_items[1]["id"],
        "delivery_point_id": meter_items[1]["delivery_point_id"],
        "label": "NO-CODE-001 · Colonnina flangiata",
        "code": "NO-CODE-001",
        "punto_consegna": "NO-CODE-001",
        "meter_number": None,
        "matricola": None,
        "cod_cont": None,
        "distretto_code": "D01",
        "tipologia": "Colonnina flangiata",
        "tipo": "FLANGIA",
        "has_meter": True,
        "gps_lat": 39.905,
        "gps_lng": 8.593,
        "lat": 39.905,
        "lng": 8.593,
        "source_dataset": "test",
        "reading_id": None,
        "reading_year": None,
        "operational_state": None,
    }
    assert meter_items[2] == {
        "id": meter_items[2]["id"],
        "delivery_point_id": meter_items[2]["delivery_point_id"],
        "label": "PLACEHOLDER-CODE-001 · Idrometro non letto",
        "code": "PLACEHOLDER-CODE-001",
        "punto_consegna": "PLACEHOLDER-CODE-001",
        "meter_number": None,
        "matricola": None,
        "cod_cont": None,
        "distretto_code": "D01",
        "tipologia": "Idrometro non letto",
        "tipo": "CONT_NO_TES",
        "has_meter": True,
        "gps_lat": 39.906,
        "gps_lng": 8.594,
        "lat": 39.906,
        "lng": 8.594,
        "source_dataset": "test",
        "reading_id": None,
        "reading_year": None,
        "operational_state": None,
    }

    worksets_response = client.get("/api/mobile-sync/worksets", headers=headers, params={"operator_id": operator_id})
    assert worksets_response.status_code == 200
    worksets = {item["workset_type"]: item for item in worksets_response.json()["worksets"]}
    assert worksets["assigned_activities"]["items"][0]["payload"]["team_label"] == "Squadra Nord"
    assert worksets["available_vehicles"]["items"][0]["payload"]["plate"] == "AB123CD"
    assert worksets["assigned_meters"]["items"][0]["payload"]["punto_consegna"] == "CNT-001"


def test_mobile_sync_worksets_return_empty_and_include_direct_vehicle_assignments() -> None:
    headers = _connector_headers()
    empty_response = client.get("/api/mobile-sync/worksets", headers=headers, params={"operator_id": str(uuid4())})
    assert empty_response.status_code == 200
    assert empty_response.json()["worksets"] == []

    db = TestingSessionLocal()
    operator, gaia_user = _seed_mobile_operator(db)
    vehicle = Vehicle(
        code="VH-DIRECT",
        name="Furgone diretto",
        plate_number="CD456EF",
        vehicle_type="van",
        current_status="assigned",
        is_active=True,
    )
    inactive_vehicle = Vehicle(
        code="VH-INACTIVE",
        name="Mezzo fermo",
        vehicle_type="van",
        current_status="assigned",
        is_active=False,
    )
    db.add_all([vehicle, inactive_vehicle])
    db.flush()
    db.add_all(
        [
            VehicleAssignment(
                vehicle_id=vehicle.id,
                assignment_target_type="operator",
                operator_user_id=gaia_user.id,
                assigned_by_user_id=gaia_user.id,
                start_at=datetime.now(UTC) - timedelta(days=1),
            ),
            VehicleAssignment(
                vehicle_id=inactive_vehicle.id,
                assignment_target_type="operator",
                operator_user_id=gaia_user.id,
                assigned_by_user_id=gaia_user.id,
                start_at=datetime.now(UTC) - timedelta(days=1),
            ),
        ]
    )
    db.commit()
    operator_id = str(operator.id)
    db.close()

    response = client.get("/api/mobile-sync/worksets", headers=headers, params={"operator_id": operator_id})
    assert response.status_code == 200
    worksets = {item["workset_type"]: item for item in response.json()["worksets"]}
    vehicle_items = worksets["available_vehicles"]["items"]
    assert [item["payload"]["code"] for item in vehicle_items] == ["VH-DIRECT"]


def test_mobile_sync_exports_presenze_snapshots_for_lan_connector(monkeypatch) -> None:
    headers = _connector_headers()
    monkeypatch.setattr(
        gate_mobile_sync_service,
        "build_presenze_teams_push_payload",
        lambda _db: {"schema_version": 1, "source": "gaia", "teams": [{"team_id": "team-1"}]},
    )
    monkeypatch.setattr(
        gate_mobile_sync_service,
        "build_presenze_months_push_payload",
        lambda _db: {"schema_version": 1, "source": "gaia", "months": [{"month": "2026-07"}]},
    )
    monkeypatch.setattr(
        gate_mobile_sync_service,
        "build_presenze_giornaliere_push_payload",
        lambda _db, month: {"schema_version": 1, "source": "gaia", "month": month, "records": [{"record_id": "rec-1"}]},
    )
    monkeypatch.setattr(
        gate_mobile_sync_service,
        "build_presenze_anomalie_push_payload",
        lambda _db, month: {"schema_version": 1, "source": "gaia", "month": month, "anomalies": [{"record_id": "rec-1"}]},
    )
    monkeypatch.setattr(
        gate_mobile_sync_service,
        "build_presenze_rules_push_payload",
        lambda: {"schema_version": 1, "source": "gaia", "rules_version": "2026.07", "rules": {}},
    )

    teams = client.get("/api/mobile-sync/presenze/teams/snapshot", headers=headers)
    months = client.get("/api/mobile-sync/presenze/months/snapshot", headers=headers)
    giornaliere = client.get("/api/mobile-sync/presenze/giornaliere/snapshot?month=2026-07", headers=headers)
    anomalie = client.get("/api/mobile-sync/presenze/anomalie/snapshot?month=2026-07", headers=headers)
    rules = client.get("/api/mobile-sync/presenze/rules/snapshot", headers=headers)

    assert teams.status_code == 200
    assert teams.json()["teams"] == [{"team_id": "team-1"}]
    assert months.status_code == 200
    assert months.json()["months"] == [{"month": "2026-07"}]
    assert giornaliere.status_code == 200
    assert giornaliere.json()["month"] == "2026-07"
    assert giornaliere.json()["records"] == [{"record_id": "rec-1"}]
    assert anomalie.status_code == 200
    assert anomalie.json()["anomalies"] == [{"record_id": "rec-1"}]
    assert rules.status_code == 200
    assert rules.json()["rules_version"] == "2026.07"


def test_mobile_meter_code_normalizes_empty_and_placeholder_values() -> None:
    assert mobile_sync_routes._mobile_meter_code(None) is None
    assert mobile_sync_routes._mobile_meter_code("   ") is None
    assert mobile_sync_routes._mobile_meter_code(" n.l. ") is None
    assert mobile_sync_routes._mobile_meter_code("  A1234  ") == "A1234"


def test_delivery_point_payload_uses_optional_meter_code_and_coordinates() -> None:
    point = CatDeliveryPoint(
        distretto_code="D01",
        punto_consegna_code="PDR-100",
        tipologia="Idrante",
        tipo="Punto presa",
        cod_cont="0",
        has_meter=True,
        source_dataset="test",
        is_active=True,
    )
    reading = CatMeterReading(
        anno=2026,
        punto_consegna="PDR-100",
        matricola=" A1234 ",
        record_kind="meter_reading",
        source="mobile",
    )

    payload = mobile_sync_routes._delivery_point_payload(point, (None, None), reading)

    assert payload["delivery_point_id"] == str(point.id)
    assert payload["label"] == "PDR-100 · A1234 · Idrante"
    assert payload["meter_number"] == "A1234"
    assert payload["matricola"] == "A1234"
    assert payload["cod_cont"] is None
    assert payload["gps_lat"] is None
    assert payload["gps_lng"] is None


def test_delivery_point_coordinates_fallback_uses_only_valid_source_coordinates() -> None:
    valid_point = CatDeliveryPoint(
        distretto_code="D01",
        punto_consegna_code="VALID-POINT",
        source_x=8.61,
        source_y=39.91,
        is_active=True,
    )
    invalid_point = CatDeliveryPoint(
        distretto_code="D01",
        punto_consegna_code="INVALID-POINT",
        source_x=999,
        source_y=999,
        is_active=True,
    )

    coordinates = mobile_sync_routes._delivery_point_coordinates(TestingSessionLocal(), [valid_point, invalid_point])

    assert coordinates == {valid_point.id: (39.91, 8.61)}


def test_mobile_sync_coordinate_helpers_cover_empty_and_postgresql_paths() -> None:
    assert mobile_sync_routes._delivery_point_coordinates(TestingSessionLocal(), []) == {}

    delivery_point = CatDeliveryPoint(
        distretto_code="D01",
        punto_consegna_code="PG-POINT",
        is_active=True,
    )
    delivery_point.id = uuid4()
    meter = CatMeterReading(
        id=uuid4(),
        anno=2026,
        punto_consegna="PG-POINT",
        matricola="MTR-PG",
        record_kind="meter_reading",
        source="mobile",
        subject_id=123,
    )
    point_rows = [types.SimpleNamespace(id=delivery_point.id, lat=39.9, lng=8.6)]
    meter_rows = [
        types.SimpleNamespace(meter_id=meter.id, lat=91.0, lng=8.6),
        types.SimpleNamespace(meter_id=meter.id, lat=39.91, lng=8.61),
        types.SimpleNamespace(meter_id=meter.id, lat=39.92, lng=8.62),
    ]

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class FakeDb:
        bind = types.SimpleNamespace(dialect=types.SimpleNamespace(name="postgresql"))

        def __init__(self, rows):
            self.rows = rows

        def execute(self, _statement):
            return FakeResult(self.rows)

    assert mobile_sync_routes._delivery_point_coordinates(FakeDb(point_rows), [delivery_point]) == {
        delivery_point.id: (39.9, 8.6)
    }
    assert mobile_sync_routes._meter_parcel_coordinates(TestingSessionLocal(), []) == {}
    assert mobile_sync_routes._meter_parcel_coordinates(FakeDb(meter_rows), [meter]) == {meter.id: (39.91, 8.61)}


def test_mobile_sync_helper_fallbacks_and_validation_errors() -> None:
    user = ApplicationUser(username="gaia.user", email="gaia@example.local", password_hash="hash", is_active=True)
    unnamed_operator = WCOperator(enabled=True)
    username_operator = WCOperator(username="mobile.user", enabled=True)

    assert mobile_sync_routes._operator_display_name(unnamed_operator, user) == "gaia.user"
    assert mobile_sync_routes._operator_display_name(username_operator, None) == "mobile.user"
    assert mobile_sync_routes._operator_display_name(unnamed_operator, None) == str(unnamed_operator.id)
    assert mobile_sync_routes._stable_catalog_id(uuid_value=uuid4(), wc_id=42) == "42"
    assert mobile_sync_routes._as_float(None) is None
    assert mobile_sync_routes._valid_wgs84_point(-91, 8) is False

    meter = CatMeterReading(
        anno=2026,
        punto_consegna="PDR-200",
        matricola="MTR-200",
        record_kind="meter_reading",
        source="mobile",
        gps_lat=Decimal("39.91"),
        gps_lng=Decimal("8.61"),
        intervento_da_eseguire="Verifica",
    )
    direct_payload = mobile_sync_routes._meter_catalog_payload(meter, parcel_coordinates=(40.0, 9.0))
    assert direct_payload["position_source"] == "meter_gps"
    assert direct_payload["lat"] == 39.91

    meter.gps_lat = Decimal("999")
    parcel_payload = mobile_sync_routes._meter_catalog_payload(meter, parcel_coordinates=(40.0, 9.0))
    assert parcel_payload["position_source"] == "parcel"
    assert parcel_payload["lat"] == 40.0


def test_mobile_sync_resolvers_reject_invalid_operator_category_and_severity() -> None:
    db = TestingSessionLocal()
    inactive_user = ApplicationUser(
        username="inactive.operator",
        email="inactive.operator@example.local",
        password_hash="hash",
        is_active=False,
        module_operazioni=True,
    )
    db.add(inactive_user)
    db.flush()
    operator_without_user = WCOperator(
        wc_id=909,
        username="detached",
        email="detached@example.local",
        enabled=True,
        gaia_user_id=None,
    )
    operator_missing_user = WCOperator(
        wc_id=910,
        username="missing-user",
        email="missing-user@example.local",
        enabled=True,
        gaia_user_id=999999,
    )
    operator_inactive_user = WCOperator(
        wc_id=911,
        username="inactive.operator",
        email="inactive.operator@example.local",
        enabled=True,
        gaia_user_id=inactive_user.id,
    )
    active_category = FieldReportCategory(code="ACTIVE", name="Active", is_active=True)
    inactive_category = FieldReportCategory(code="OLD", name="Old", wc_id=7, is_active=False)
    active_severity = FieldReportSeverity(code="ACTIVE", name="Active", rank_order=1, is_active=True)
    inactive_severity = FieldReportSeverity(code="OLD", name="Old", rank_order=9, is_active=False)
    db.add_all(
        [
            operator_without_user,
            operator_missing_user,
            operator_inactive_user,
            active_category,
            inactive_category,
            active_severity,
            inactive_severity,
        ]
    )
    db.commit()

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as missing_operator:
        mobile_sync_routes._resolve_mobile_operator(db, uuid4())
    assert missing_operator.value.status_code == 404

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as detached_operator:
        mobile_sync_routes._resolve_mobile_operator(db, operator_without_user.id)
    assert detached_operator.value.status_code == 422

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as missing_user:
        mobile_sync_routes._resolve_mobile_operator(db, operator_missing_user.id)
    assert missing_user.value.status_code == 422

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as inactive_user_error:
        mobile_sync_routes._resolve_mobile_operator(db, operator_inactive_user.id)
    assert inactive_user_error.value.status_code == 403

    assert mobile_sync_routes._resolve_report_category(db, str(active_category.id)) == active_category
    assert mobile_sync_routes._resolve_report_severity(db, "ACTIVE") == active_severity

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as invalid_category:
        mobile_sync_routes._resolve_report_category(db, "not-a-category")
    assert invalid_category.value.details == {"field": "category_id"}

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as inactive_category_error:
        mobile_sync_routes._resolve_report_category(db, "7")
    assert inactive_category_error.value.status_code == 422

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as inactive_severity_error:
        mobile_sync_routes._resolve_report_severity(db, str(inactive_severity.id))
    assert inactive_severity_error.value.details == {"field": "severity_id"}

    active_category.is_active = False
    active_severity.is_active = False
    db.commit()

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as teti_category_error:
        mobile_sync_routes._resolve_teti_category(db)
    assert teti_category_error.value.details == {"field": "payload"}

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as teti_severity_error:
        mobile_sync_routes._resolve_teti_severity(db, "HIGH")
    assert teti_severity_error.value.details == {"field": "payload.severity"}

    db.close()


def test_mobile_sync_teti_severity_uses_rank_buckets_when_code_is_not_configured() -> None:
    db = TestingSessionLocal()
    severities = [
        FieldReportSeverity(code="S1", name="Bassa", rank_order=1, is_active=True),
        FieldReportSeverity(code="S2", name="Media", rank_order=2, is_active=True),
        FieldReportSeverity(code="S3", name="Alta", rank_order=3, is_active=True),
        FieldReportSeverity(code="S4", name="Critica", rank_order=4, is_active=True),
    ]
    db.add_all(severities)
    db.commit()

    assert mobile_sync_routes._resolve_teti_severity(db, "LOW").code == "S1"
    assert mobile_sync_routes._resolve_teti_severity(db, "MEDIUM").code == "S2"
    assert mobile_sync_routes._resolve_teti_severity(db, "HIGH").code == "S3"
    assert mobile_sync_routes._resolve_teti_severity(db, "CRITICAL").code == "S4"
    db.close()


def test_mobile_sync_teti_category_uses_first_active_fallback_category() -> None:
    db = TestingSessionLocal()
    fallback = FieldReportCategory(code="OTHER", name="Altro", is_active=True)
    db.add(fallback)
    db.commit()

    assert mobile_sync_routes._resolve_teti_category(db) == fallback
    db.close()


def test_mobile_sync_resolve_event_rejects_reused_client_event_for_different_type() -> None:
    db = TestingSessionLocal()
    event = MobileSyncEvent(
        client_event_id=uuid4(),
        event_type="FIELD_REPORT_CREATED",
        operator_id=uuid4(),
        device_id="device-1",
        payload_version=1,
        payload_hash="same-hash",
        gaia_entity_type="field_report",
        gaia_entity_id=str(uuid4()),
        payload_json={},
    )
    db.add(event)
    db.commit()

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as reused_event:
        mobile_sync_routes._resolve_mobile_event(
            db,
            client_event_id=event.client_event_id,
            event_type="ACTIVITY_START_REQUESTED",
            payload_hash="same-hash",
        )
    assert reused_event.value.details == {"field": "client_event_id"}
    db.close()


def test_mobile_sync_attachment_validation_helpers(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPERAZIONI_STORAGE_PATH", str(tmp_path / "operazioni-storage"))
    operator_id = uuid4()
    client_attachment_id = uuid4()
    valid_bytes = b"inline-attachment"
    valid_checksum = mobile_sync_routes.compute_checksum(valid_bytes)
    valid_attachment = mobile_sync_routes.MobileSyncAttachmentRef(
        client_attachment_id=client_attachment_id,
        filename="foto.jpg",
        mime_type="image/jpeg",
        size_bytes=len(valid_bytes),
        sha256=valid_checksum,
        content_base64=base64.b64encode(valid_bytes).decode("ascii"),
    )

    assert mobile_sync_routes._decode_mobile_attachment_content(valid_attachment) == valid_bytes

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as missing_content:
        mobile_sync_routes._decode_mobile_attachment_content(
            mobile_sync_routes.MobileSyncAttachmentRef(filename="foto.jpg", mime_type="image/jpeg")
        )
    assert missing_content.value.status_code == 422

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as invalid_base64:
        mobile_sync_routes._decode_mobile_attachment_content(
            mobile_sync_routes.MobileSyncAttachmentRef(
                client_attachment_id=uuid4(),
                filename="foto.jpg",
                mime_type="image/jpeg",
                content_base64="not-valid-base64",
            )
        )
    assert invalid_base64.value.status_code == 422

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as invalid_size:
        mobile_sync_routes._decode_mobile_attachment_content(
            valid_attachment.model_copy(update={"size_bytes": len(valid_bytes) + 1})
        )
    assert invalid_size.value.status_code == 409

    db = TestingSessionLocal()
    created = mobile_sync_routes._create_inline_mobile_attachment(
        db,
        operator_id=operator_id,
        device_id="device-1",
        attachment=valid_attachment,
    )
    db.flush()
    assert Path(created.storage_path).exists()
    assert mobile_sync_routes._resolve_existing_mobile_attachment(
        [created],
        operator_id=operator_id,
        client_attachment_id=client_attachment_id,
    ) == created

    reused = mobile_sync_routes._create_inline_mobile_attachment(
        db,
        operator_id=operator_id,
        device_id="device-1",
        attachment=valid_attachment,
    )
    assert reused == created

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as missing_client_id:
        mobile_sync_routes._create_inline_mobile_attachment(
            db,
            operator_id=operator_id,
            device_id="device-1",
            attachment=valid_attachment.model_copy(update={"client_attachment_id": None}),
        )
    assert missing_client_id.value.status_code == 422

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as checksum_mismatch:
        mobile_sync_routes._create_inline_mobile_attachment(
            db,
            operator_id=operator_id,
            device_id="device-1",
            attachment=valid_attachment.model_copy(update={"sha256": "0" * 64}),
        )
    assert checksum_mismatch.value.status_code == 409

    different_bytes = b"different-inline-attachment"
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as existing_checksum_mismatch:
        mobile_sync_routes._create_inline_mobile_attachment(
            db,
            operator_id=operator_id,
            device_id="device-1",
            attachment=valid_attachment.model_copy(
                update={
                    "content_base64": base64.b64encode(different_bytes).decode("ascii"),
                    "size_bytes": len(different_bytes),
                    "sha256": mobile_sync_routes.compute_checksum(different_bytes),
                }
            ),
        )
    assert existing_checksum_mismatch.value.status_code == 409
    db.close()


def test_mobile_sync_uploaded_attachment_helpers_reject_missing_and_conflicting_refs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPERAZIONI_STORAGE_PATH", str(tmp_path / "operazioni-storage"))
    operator_id = uuid4()
    client_attachment_id = uuid4()
    db = TestingSessionLocal()
    stored = mobile_sync_routes.create_attachment_record(
        db,
        storage_path=str(tmp_path / "stored.jpg"),
        filename="stored.jpg",
        mime_type="image/jpeg",
        file_size=6,
        source_context="mobile_sync_attachment",
        checksum="a" * 64,
    )
    stored.metadata_json = {
        "client_attachment_id": str(client_attachment_id),
        "operator_id": str(operator_id),
    }
    db.commit()

    refs = [
        mobile_sync_routes.MobileSyncAttachmentRef(
            client_attachment_id=None,
            filename="ignored.jpg",
            mime_type="image/jpeg",
        ),
        mobile_sync_routes.MobileSyncAttachmentRef(
            client_attachment_id=client_attachment_id,
            filename="stored.jpg",
            mime_type="image/jpeg",
            sha256="a" * 64,
        ),
    ]
    assert mobile_sync_routes._fetch_mobile_uploaded_attachments(db, operator_id=operator_id, attachments=refs) == [stored]

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as missing_upload:
        mobile_sync_routes._fetch_mobile_uploaded_attachments(
            db,
            operator_id=operator_id,
            attachments=[
                mobile_sync_routes.MobileSyncAttachmentRef(
                    client_attachment_id=uuid4(),
                    filename="missing.jpg",
                    mime_type="image/jpeg",
                )
            ],
        )
    assert missing_upload.value.status_code == 422

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as uploaded_checksum_mismatch:
        mobile_sync_routes._fetch_mobile_uploaded_attachments(
            db,
            operator_id=operator_id,
            attachments=[
                mobile_sync_routes.MobileSyncAttachmentRef(
                    client_attachment_id=client_attachment_id,
                    filename="stored.jpg",
                    mime_type="image/jpeg",
                    sha256="b" * 64,
                )
            ],
        )
    assert uploaded_checksum_mismatch.value.status_code == 409

    assert mobile_sync_routes._resolve_mobile_attachments(
        db,
        operator_id=operator_id,
        device_id="device-1",
        attachments=[
            mobile_sync_routes.MobileSyncAttachmentRef(
                client_attachment_id=client_attachment_id,
                filename="stored.jpg",
                mime_type="image/jpeg",
                sha256="a" * 64,
            )
        ],
    ) == [stored]

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as missing_resolved_client_id:
        mobile_sync_routes._resolve_mobile_attachments(
            db,
            operator_id=operator_id,
            device_id="device-1",
            attachments=[mobile_sync_routes.MobileSyncAttachmentRef(filename="missing.jpg", mime_type="image/jpeg")],
        )
    assert missing_resolved_client_id.value.status_code == 422
    db.close()


def test_mobile_sync_requires_connector_token() -> None:
    response = client.get("/api/mobile-sync/mobile-operators")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid connector token"


def test_mobile_sync_returns_503_when_no_connector_token_is_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mobile_connector_token", "")
    monkeypatch.setattr(settings, "gate_mobile_connector_token", "")

    response = client.get("/api/mobile-sync/connector/handshake")

    assert response.status_code == 503
    assert response.json()["detail"] == "Mobile connector auth not configured"


def test_mobile_sync_accepts_gate_connector_token_as_fallback(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mobile_connector_token", "")
    monkeypatch.setattr(settings, "gate_mobile_connector_token", "gate-token")

    response = client.get(
        "/api/mobile-sync/connector/handshake",
        headers={settings.mobile_connector_header_name: "gate-token"},
    )

    assert response.status_code == 200
    assert response.json()["authenticated"] is True


def test_mobile_sync_upload_attachment_maps_value_error_and_unexpected_error(monkeypatch) -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    operator_id = str(operator.id)
    db.commit()
    db.close()

    def raise_value_error(_file_bytes: bytes) -> str:
        raise ValueError("invalid file")

    monkeypatch.setattr(mobile_sync_routes, "compute_checksum", raise_value_error)
    value_error_response = client.post(
        "/api/mobile-sync/attachments/upload",
        headers=headers,
        data={
            "operator_id": operator_id,
            "device_id": str(uuid4()),
            "client_attachment_id": str(uuid4()),
        },
        files={"file": ("foto.jpg", b"fake-image-content", "image/jpeg")},
    )
    assert value_error_response.status_code == 422
    assert value_error_response.json()["details"] == {"field": "file"}

    def raise_runtime_error(_file_bytes: bytes) -> str:
        raise RuntimeError("temporary failure")

    monkeypatch.setattr(mobile_sync_routes, "compute_checksum", raise_runtime_error)
    retryable_response = client.post(
        "/api/mobile-sync/attachments/upload",
        headers=headers,
        data={
            "operator_id": operator_id,
            "device_id": str(uuid4()),
            "client_attachment_id": str(uuid4()),
        },
        files={"file": ("foto.jpg", b"fake-image-content", "image/jpeg")},
    )
    assert retryable_response.status_code == 500
    assert retryable_response.json()["retryable"] is True


def test_mobile_sync_connector_handshake_returns_capabilities() -> None:
    response = client.get("/api/mobile-sync/connector/handshake", headers=_connector_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "gaia-mobile-sync"
    assert payload["authenticated"] is True
    assert payload["auth_scheme"] == "header_token"
    assert "catalogs.read" in payload["capabilities"]
    assert "presenze_giornaliere.read" in payload["capabilities"]
    assert "presenze_rules.read" in payload["capabilities"]
    assert "teti_fault_work_requests.create" in payload["capabilities"]
    assert payload["connector_header"] == settings.mobile_connector_header_name


def test_mobile_gateway_sync_status_returns_config_and_recent_runs(monkeypatch) -> None:
    monkeypatch.setattr(settings, "gate_mobile_gateway_base_url", "https://gateway.example.test")
    monkeypatch.setattr(settings, "gate_mobile_connector_token", "gate-token")
    monkeypatch.setattr(settings, "gate_mobile_sync_enabled", True)
    headers = _seed_admin()
    db = TestingSessionLocal()
    db.add(
        GateMobileSyncRun(
            trigger_source="systemd_timer_or_manual",
            status="failed",
            requested_tasks_count=1,
            operators_pushed=0,
            error_kind="http_status_error",
            error_message="status=503 method=POST path=/api/mobile/connector/sync/plan",
        )
    )
    db.commit()
    db.close()

    response = client.get("/operazioni/mobile-gateway-sync/status", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["outbound_scope"] == [
        "catalogs",
        "operators",
        "worksets",
        "presenze_teams",
        "presenze_months",
        "presenze_giornaliere",
        "presenze_anomalie",
        "presenze_rules",
        "presenze_pending_actions",
    ]
    assert payload["internal_connector_api"]["path_prefix"] == "/api/mobile-sync"
    assert payload["token_configured"] is True
    assert payload["last_run"]["status"] == "failed"
    assert payload["recent_runs"][0]["error_kind"] == "http_status_error"


def test_mobile_gateway_sync_run_triggers_manual_execution(monkeypatch) -> None:
    monkeypatch.setattr(settings, "gate_mobile_gateway_base_url", "https://gateway.example.test")
    monkeypatch.setattr(settings, "gate_mobile_connector_token", "gate-token")
    monkeypatch.setattr(settings, "gate_mobile_sync_enabled", True)
    headers = _seed_admin()

    async def fake_execute_gate_mobile_sync(db: Session, **kwargs) -> GateMobileSyncExecutionResult:
        run = GateMobileSyncRun(
            trigger_source=kwargs.get("trigger_source", "manual_api"),
            status="succeeded",
            requested_tasks_count=1,
            operators_pushed=17,
            requested_tasks_json=[{"type": "operators"}],
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return GateMobileSyncExecutionResult(
            status="succeeded",
            run_id=run.id,
            report=GateMobileSyncReport(
                requested_tasks=[{"type": "operators"}],
                catalogs_pushed=5,
                operators_pushed=17,
                worksets_pushed=2,
            ),
        )

    monkeypatch.setattr(mobile_gateway_sync_routes, "execute_gate_mobile_sync", fake_execute_gate_mobile_sync)

    response = client.post("/operazioni/mobile-gateway-sync/run", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["trigger_source"] == "manual_api"
    assert payload["job"]["status"] == "succeeded"
    assert payload["job"]["operators_pushed"] == 17


def test_mobile_gateway_sync_run_rejects_when_another_run_is_running() -> None:
    headers = _seed_admin()
    db = TestingSessionLocal()
    db.add(
        GateMobileSyncRun(
            trigger_source="systemd_timer",
            status="running",
            requested_tasks_count=0,
            operators_pushed=0,
        )
    )
    db.commit()
    db.close()

    response = client.post("/operazioni/mobile-gateway-sync/run", headers=headers)

    assert response.status_code == 409
    assert "già in esecuzione" in response.json()["detail"]


def test_mobile_sync_field_reports_are_idempotent_and_conflict_on_hash_mismatch(tmp_path: Path) -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    operator_id = str(operator.id)
    category = FieldReportCategory(code="LOSS", name="Perdita", wc_id=3, is_active=True)
    severity = FieldReportSeverity(code="MED", name="Media", rank_order=1, is_active=True)
    db.add_all([category, severity])
    db.commit()
    db.close()
    os.environ["OPERAZIONI_STORAGE_PATH"] = str(tmp_path / "operazioni-storage")

    attachment_upload = client.post(
        "/api/mobile-sync/attachments/upload",
        headers=headers,
        data={
            "operator_id": operator_id,
            "device_id": str(uuid4()),
            "client_attachment_id": str(uuid4()),
        },
        files={"file": ("foto.jpg", b"fake-image-content", "image/jpeg")},
    )
    assert attachment_upload.status_code == 201
    attachment_payload = attachment_upload.json()
    attachment_path = tmp_path / "operazioni-storage"
    assert attachment_path.exists()

    duplicate_upload = client.post(
        "/api/mobile-sync/attachments/upload",
        headers=headers,
        data={
            "operator_id": operator_id,
            "device_id": str(uuid4()),
            "client_attachment_id": attachment_payload["client_attachment_id"],
        },
        files={"file": ("foto.jpg", b"fake-image-content", "image/jpeg")},
    )
    assert duplicate_upload.status_code == 201
    assert duplicate_upload.json()["attachment_id"] == attachment_payload["attachment_id"]

    checksum_mismatch_upload = client.post(
        "/api/mobile-sync/attachments/upload",
        headers=headers,
        data={
            "operator_id": operator_id,
            "device_id": str(uuid4()),
            "client_attachment_id": str(uuid4()),
            "checksum_sha256": "0" * 64,
        },
        files={"file": ("foto.jpg", b"fake-image-content", "image/jpeg")},
    )
    assert checksum_mismatch_upload.status_code == 409
    assert checksum_mismatch_upload.json()["details"] == {"field": "checksum_sha256"}

    duplicate_conflict_upload = client.post(
        "/api/mobile-sync/attachments/upload",
        headers=headers,
        data={
            "operator_id": operator_id,
            "device_id": str(uuid4()),
            "client_attachment_id": attachment_payload["client_attachment_id"],
        },
        files={"file": ("foto.jpg", b"different-image-content", "image/jpeg")},
    )
    assert duplicate_conflict_upload.status_code == 409
    assert duplicate_conflict_upload.json()["details"] == {"field": "client_attachment_id"}

    client_event_id = str(uuid4())
    payload = {
        "client_event_id": client_event_id,
        "operator_id": operator_id,
        "device_id": str(uuid4()),
        "payload_version": 1,
        "payload_hash": "a" * 64,
        "payload": {
            "title": "Perdita su condotta",
            "description": "Descrizione operatore",
            "category_id": "3",
            "occurred_at_device": "2026-05-18T08:00:00Z",
            "gps_position": {"lat": 45.0, "lng": 9.0, "accuracy_m": 8},
        },
        "attachments": [
            {
                "client_attachment_id": attachment_payload["client_attachment_id"],
                "filename": "foto.jpg",
                "mime_type": "image/jpeg",
                "size_bytes": len(b"fake-image-content"),
                "sha256": attachment_payload["checksum_sha256"],
            }
        ],
    }

    first = client.post("/api/mobile-sync/field-reports", headers=headers, json=payload)
    assert first.status_code == 201
    first_id = first.json()["gaia_entity_id"]

    second = client.post("/api/mobile-sync/field-reports", headers=headers, json=payload)
    assert second.status_code == 201
    assert second.json()["gaia_entity_id"] == first_id

    conflict_payload = payload | {"payload_hash": "b" * 64}
    conflict = client.post("/api/mobile-sync/field-reports", headers=headers, json=conflict_payload)
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "GAIA_CONFLICT_ERROR"
    assert conflict.json()["retryable"] is False

    db = TestingSessionLocal()
    assert db.query(FieldReport).count() == 1
    assert db.query(MobileSyncEvent).count() == 1
    assert db.query(Attachment).count() == 1
    assert db.query(FieldReportAttachment).count() == 1
    assert db.query(InternalCaseAttachment).count() == 1
    stored_attachment = db.query(Attachment).first()
    assert stored_attachment is not None
    assert Path(stored_attachment.storage_path).exists()
    db.close()


def test_mobile_sync_activity_start_and_stop_are_idempotent() -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, gaia_user = _seed_mobile_operator(db)
    operator_id = str(operator.id)
    catalog = ActivityCatalog(code="SOPR", name="Sopralluogo", category="rete", is_active=True)
    team = Team(code="TEAM-SUD", name="Squadra Sud", is_active=True)
    vehicle = Vehicle(code="VH-002", name="Jeep Sud", vehicle_type="jeep", current_status="available", is_active=True)
    db.add_all([catalog, team, vehicle])
    db.flush()
    catalog_id = str(catalog.id)
    team_id = str(team.id)
    vehicle_id = str(vehicle.id)
    db.add(
        TeamMembership(
            team_id=team.id,
            user_id=gaia_user.id,
            valid_from=datetime.now(UTC) - timedelta(days=1),
            is_primary=True,
        )
    )
    db.commit()
    db.close()

    start_payload = {
        "client_event_id": str(uuid4()),
        "operator_id": operator_id,
        "device_id": str(uuid4()),
        "payload_version": 1,
        "payload_hash": "c" * 64,
        "payload": {
            "activity_catalog_id": catalog_id,
            "team_id": team_id,
            "vehicle_id": vehicle_id,
            "notes": "Avvio mobile",
            "started_at_device": "2026-05-18T08:00:00Z",
            "gps_start": {"lat": 45.0, "lng": 9.0, "accuracy_m": 5},
        },
        "attachments": [],
    }

    start_response = client.post("/api/mobile-sync/activity-starts", headers=headers, json=start_payload)
    assert start_response.status_code == 201
    assert start_response.json()["gaia_entity_type"] == "activity"
    activity_id = start_response.json()["gaia_entity_id"]

    start_retry = client.post("/api/mobile-sync/activity-starts", headers=headers, json=start_payload)
    assert start_retry.status_code == 201
    assert start_retry.json()["gaia_entity_id"] == activity_id

    stop_payload = {
        "client_event_id": str(uuid4()),
        "operator_id": operator_id,
        "device_id": str(uuid4()),
        "payload_version": 1,
        "payload_hash": "d" * 64,
        "payload": {
            "client_started_event_id": start_payload["client_event_id"],
            "stopped_at_device": "2026-05-18T09:15:00Z",
            "notes": "Chiusura mobile",
            "gps_end": {"lat": 45.1, "lng": 9.1, "accuracy_m": 7},
        },
        "attachments": [],
    }

    stop_response = client.post("/api/mobile-sync/activity-stops", headers=headers, json=stop_payload)
    assert stop_response.status_code == 201
    assert stop_response.json()["gaia_entity_type"] == "activity"
    assert stop_response.json()["gaia_entity_id"] == activity_id

    stop_retry = client.post("/api/mobile-sync/activity-stops", headers=headers, json=stop_payload)
    assert stop_retry.status_code == 201
    assert stop_retry.json()["gaia_entity_id"] == activity_id

    db = TestingSessionLocal()
    activity = db.get(OperatorActivity, UUID(start_response.json()["gaia_entity_id"]))
    assert activity is not None
    assert activity.status == "submitted"
    assert activity.duration_minutes_calculated == 75
    assert db.query(MobileSyncEvent).count() == 2
    db.close()


def test_mobile_sync_activity_start_persists_meter_reading_and_inline_attachments(tmp_path: Path) -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    operator_id = str(operator.id)
    catalog = ActivityCatalog(code="LETT_CONT", name="Lettura contatori", category="catasto", is_active=True)
    db.add(catalog)
    delivery_point = CatDeliveryPoint(
        distretto_code="D01",
        punto_consegna_code="PDR-001",
        tipologia="Idrante",
        tipo="Punto presa",
        cod_cont="A1234",
        has_meter=True,
        source_dataset="test",
        source_x=8.5880152,
        source_y=39.9071572,
        is_active=True,
    )
    db.add(delivery_point)
    db.commit()
    catalog_id = str(catalog.id)
    delivery_point_id = str(delivery_point.id)
    db.close()
    os.environ["OPERAZIONI_STORAGE_PATH"] = str(tmp_path / "operazioni-storage")

    attachment_bytes = b"fake-inline-image"
    attachment_b64 = base64.b64encode(attachment_bytes).decode("ascii")
    attachment_client_id = str(uuid4())
    payload = {
        "client_event_id": str(uuid4()),
        "operator_id": operator_id,
        "device_id": str(uuid4()),
        "payload_version": 1,
        "payload_hash": "9" * 64,
        "payload": {
            "activity_catalog_id": catalog_id,
            "delivery_point_id": delivery_point_id,
            "meter_reading_value": "258",
            "notes": "Numero contatore: A1234\nValore lettura: 258\nNote operatore",
            "started_at_device": "2026-06-22T13:08:42.132Z",
            "gps_start": {"lat": 39.9071572, "lng": 8.5880152, "accuracy_m": 20},
        },
        "attachments": [
            {
                "client_attachment_id": attachment_client_id,
                "filename": "foto.jpg",
                "mime_type": "image/jpeg",
                "size_bytes": len(attachment_bytes),
                "sha256": "5e4cea5dc899a0f10929cda794ca4fc16fcec9e7136e5116b4f87a0bba07a3e9",
                "content_base64": attachment_b64,
            }
        ],
    }

    response = client.post("/api/mobile-sync/activity-starts", headers=headers, json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["gaia_entity_type"] == "activity"
    assert UUID(body["gaia_entity_id"])
    assert UUID(body["extra"]["meter_reading_id"])

    db = TestingSessionLocal()
    activity = db.get(OperatorActivity, UUID(body["gaia_entity_id"]))
    assert activity is not None
    assert activity.text_note == payload["payload"]["notes"]

    reading = db.get(CatMeterReading, UUID(body["extra"]["meter_reading_id"]))
    assert reading is not None
    assert reading.source == "mobile"
    assert reading.sync_status == "applied_to_gaia"
    assert str(reading.delivery_point_id) == delivery_point_id
    assert reading.punto_consegna == "PDR-001"
    assert reading.matricola == "A1234"
    assert float(reading.lettura_finale) == 258.0
    assert str(reading.mobile_operator_id) == operator_id
    assert reading.device_id == payload["device_id"]
    assert reading.mobile_session_id == body["gaia_entity_id"]
    assert reading.photo_url is not None
    assert Path(reading.photo_url).exists()
    assert reading.import_payload_json["delivery_point_id"] == delivery_point_id

    attachment = db.query(Attachment).one()
    assert Path(attachment.storage_path).exists()
    assert attachment.metadata_json["upload_origin"] == "gaia_mobile_connector_inline"
    assert attachment.metadata_json["linked_activity_id"] == body["gaia_entity_id"]
    assert db.query(MobileSyncEvent).count() == 1
    db.close()


def test_mobile_sync_activity_start_rejects_unknown_delivery_point() -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    catalog = ActivityCatalog(code="LETT_CONT", name="Lettura contatori", category="catasto", is_active=True)
    db.add(catalog)
    db.commit()
    operator_id = str(operator.id)
    catalog_id = str(catalog.id)
    db.close()

    response = client.post(
        "/api/mobile-sync/activity-starts",
        headers=headers,
        json={
            "client_event_id": str(uuid4()),
            "operator_id": operator_id,
            "device_id": str(uuid4()),
            "payload_version": 1,
            "payload_hash": "9" * 64,
            "payload": {
                "activity_catalog_id": catalog_id,
                "delivery_point_id": str(uuid4()),
                "meter_reading_value": "258",
                "started_at_device": "2026-06-22T13:08:42.132Z",
            },
            "attachments": [],
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "GAIA_VALIDATION_ERROR"
    assert body["details"]["field"] == "delivery_point_id"


def test_mobile_sync_field_report_rejects_unknown_linked_activity() -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    category = FieldReportCategory(code="LOSS", name="Perdita", wc_id=3, is_active=True)
    severity = FieldReportSeverity(code="MED", name="Media", rank_order=1, is_active=True)
    db.add_all([category, severity])
    db.commit()
    operator_id = str(operator.id)
    db.close()

    response = client.post(
        "/api/mobile-sync/field-reports",
        headers=headers,
        json={
            "client_event_id": str(uuid4()),
            "operator_id": operator_id,
            "device_id": str(uuid4()),
            "payload_version": 1,
            "payload_hash": "6" * 64,
            "payload": {
                "title": "Perdita su condotta",
                "description": "Descrizione operatore",
                "category_id": "3",
                "linked_gaia_activity_id": str(uuid4()),
                "occurred_at_device": "2026-05-18T08:00:00Z",
            },
            "attachments": [],
        },
    )

    assert response.status_code == 422
    assert response.json()["details"] == {"field": "linked_gaia_activity_id"}


def test_mobile_sync_field_report_returns_retryable_on_unexpected_error(monkeypatch) -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    category = FieldReportCategory(code="LOSS", name="Perdita", wc_id=3, is_active=True)
    severity = FieldReportSeverity(code="MED", name="Media", rank_order=1, is_active=True)
    db.add_all([category, severity])
    db.commit()
    operator_id = str(operator.id)
    db.close()

    def _boom(*args, **kwargs):
        raise RuntimeError("temporary db failure")

    monkeypatch.setattr(mobile_sync_routes, "_create_mobile_event", _boom)
    response = client.post(
        "/api/mobile-sync/field-reports",
        headers=headers,
        json={
            "client_event_id": str(uuid4()),
            "operator_id": operator_id,
            "device_id": str(uuid4()),
            "payload_version": 1,
            "payload_hash": "7" * 64,
            "payload": {
                "title": "Perdita su condotta",
                "description": "Descrizione operatore",
                "category_id": "3",
                "occurred_at_device": "2026-05-18T08:00:00Z",
            },
            "attachments": [],
        },
    )

    assert response.status_code == 500
    assert response.json()["retryable"] is True


def test_mobile_sync_activity_start_rejects_invalid_catalog_team_and_vehicle() -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    inactive_catalog = ActivityCatalog(code="OLD", name="Old", category="rete", is_active=False)
    active_catalog = ActivityCatalog(code="SOPR", name="Sopralluogo", category="rete", is_active=True)
    inactive_vehicle = Vehicle(code="VH-OLD", name="Vecchio", vehicle_type="pickup", current_status="available", is_active=False)
    db.add_all([inactive_catalog, active_catalog, inactive_vehicle])
    db.commit()
    operator_id = str(operator.id)
    inactive_catalog_id = str(inactive_catalog.id)
    active_catalog_id = str(active_catalog.id)
    inactive_vehicle_id = str(inactive_vehicle.id)
    db.close()

    base_payload = {
        "client_event_id": str(uuid4()),
        "operator_id": operator_id,
        "device_id": str(uuid4()),
        "payload_version": 1,
        "payload_hash": "7" * 64,
        "payload": {
            "activity_catalog_id": inactive_catalog_id,
            "started_at_device": "2026-05-18T08:00:00Z",
        },
        "attachments": [],
    }

    invalid_catalog = client.post("/api/mobile-sync/activity-starts", headers=headers, json=base_payload)
    assert invalid_catalog.status_code == 422
    assert invalid_catalog.json()["details"] == {"field": "activity_catalog_id"}

    invalid_team = client.post(
        "/api/mobile-sync/activity-starts",
        headers=headers,
        json=base_payload
        | {
            "client_event_id": str(uuid4()),
            "payload_hash": "8" * 64,
            "payload": base_payload["payload"] | {"activity_catalog_id": active_catalog_id, "team_id": str(uuid4())},
        },
    )
    assert invalid_team.status_code == 422
    assert invalid_team.json()["details"] == {"field": "team_id"}

    invalid_vehicle = client.post(
        "/api/mobile-sync/activity-starts",
        headers=headers,
        json=base_payload
        | {
            "client_event_id": str(uuid4()),
            "payload_hash": "a" * 64,
            "payload": base_payload["payload"]
            | {"activity_catalog_id": active_catalog_id, "vehicle_id": inactive_vehicle_id},
        },
    )
    assert invalid_vehicle.status_code == 422
    assert invalid_vehicle.json()["details"] == {"field": "vehicle_id"}


def test_mobile_sync_activity_start_returns_retryable_on_unexpected_error(monkeypatch) -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    catalog = ActivityCatalog(code="SOPR", name="Sopralluogo", category="rete", is_active=True)
    db.add(catalog)
    db.commit()
    operator_id = str(operator.id)
    catalog_id = str(catalog.id)
    db.close()

    def _boom(*args, **kwargs):
        raise RuntimeError("temporary db failure")

    monkeypatch.setattr(mobile_sync_routes, "_create_mobile_event", _boom)
    response = client.post(
        "/api/mobile-sync/activity-starts",
        headers=headers,
        json={
            "client_event_id": str(uuid4()),
            "operator_id": operator_id,
            "device_id": str(uuid4()),
            "payload_version": 1,
            "payload_hash": "f" * 64,
            "payload": {
                "activity_catalog_id": catalog_id,
                "started_at_device": "2026-05-18T08:00:00Z",
            },
            "attachments": [],
        },
    )

    assert response.status_code == 500
    assert response.json()["retryable"] is True


def test_mobile_sync_activity_stop_rejects_missing_foreign_or_closed_activity() -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, gaia_user = _seed_mobile_operator(db)
    other_user = ApplicationUser(
        username="other.operator",
        email="other.operator@example.local",
        password_hash=hash_password("operator123"),
        role=ApplicationUserRole.OPERATOR.value,
        is_active=True,
        module_operazioni=True,
    )
    catalog = ActivityCatalog(code="SOPR", name="Sopralluogo", category="rete", is_active=True)
    db.add_all([other_user, catalog])
    db.flush()
    foreign_activity = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=other_user.id,
        status="in_progress",
        started_at=datetime.now(UTC) - timedelta(hours=1),
    )
    closed_activity = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=gaia_user.id,
        status="submitted",
        started_at=datetime.now(UTC) - timedelta(hours=1),
    )
    bad_start_event_id = uuid4()
    db.add_all([foreign_activity, closed_activity])
    db.flush()
    db.add(
        MobileSyncEvent(
            client_event_id=bad_start_event_id,
            event_type="ACTIVITY_START_REQUESTED",
            operator_id=operator.id,
            device_id="device-1",
            payload_version=1,
            payload_hash="bad-start",
            gaia_entity_type="activity",
            gaia_entity_id="not-a-uuid",
            payload_json={},
        )
    )
    db.commit()
    operator_id = str(operator.id)
    foreign_activity_id = str(foreign_activity.id)
    closed_activity_id = str(closed_activity.id)
    db.close()

    base_payload = {
        "client_event_id": str(uuid4()),
        "operator_id": operator_id,
        "device_id": str(uuid4()),
        "payload_version": 1,
        "payload_hash": "b" * 64,
        "payload": {
            "gaia_activity_id": str(uuid4()),
            "stopped_at_device": "2026-05-18T09:15:00Z",
        },
        "attachments": [],
    }

    missing_activity = client.post("/api/mobile-sync/activity-stops", headers=headers, json=base_payload)
    assert missing_activity.status_code == 422
    assert missing_activity.json()["details"] == {"field": "gaia_activity_id"}

    invalid_start_event = client.post(
        "/api/mobile-sync/activity-stops",
        headers=headers,
        json=base_payload
        | {
            "client_event_id": str(uuid4()),
            "payload_hash": "c" * 64,
            "payload": {
                "client_started_event_id": str(bad_start_event_id),
                "stopped_at_device": "2026-05-18T09:15:00Z",
            },
        },
    )
    assert invalid_start_event.status_code == 422
    assert invalid_start_event.json()["details"] == {"field": "gaia_activity_id"}

    foreign = client.post(
        "/api/mobile-sync/activity-stops",
        headers=headers,
        json=base_payload
        | {
            "client_event_id": str(uuid4()),
            "payload_hash": "d" * 64,
            "payload": {
                "gaia_activity_id": foreign_activity_id,
                "stopped_at_device": "2026-05-18T09:15:00Z",
            },
        },
    )
    assert foreign.status_code == 422
    assert foreign.json()["message"] == "Attivita non valida per l'operatore"

    already_closed = client.post(
        "/api/mobile-sync/activity-stops",
        headers=headers,
        json=base_payload
        | {
            "client_event_id": str(uuid4()),
            "payload_hash": "e" * 64,
            "payload": {
                "gaia_activity_id": closed_activity_id,
                "stopped_at_device": "2026-05-18T09:15:00Z",
            },
        },
    )
    assert already_closed.status_code == 409
    assert already_closed.json()["message"] == "Attivita non in corso"


def test_mobile_sync_activity_stop_returns_retryable_on_unexpected_error(monkeypatch) -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, gaia_user = _seed_mobile_operator(db)
    catalog = ActivityCatalog(code="SOPR", name="Sopralluogo", category="rete", is_active=True)
    db.add(catalog)
    db.flush()
    activity = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=gaia_user.id,
        status="in_progress",
        started_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db.add(activity)
    db.commit()
    operator_id = str(operator.id)
    activity_id = str(activity.id)
    db.close()

    def _boom(*args, **kwargs):
        raise RuntimeError("temporary db failure")

    monkeypatch.setattr(mobile_sync_routes, "_create_mobile_event", _boom)
    response = client.post(
        "/api/mobile-sync/activity-stops",
        headers=headers,
        json={
            "client_event_id": str(uuid4()),
            "operator_id": operator_id,
            "device_id": str(uuid4()),
            "payload_version": 1,
            "payload_hash": "f" * 64,
            "payload": {
                "gaia_activity_id": activity_id,
                "stopped_at_device": "2026-05-18T09:15:00Z",
            },
            "attachments": [],
        },
    )

    assert response.status_code == 500
    assert response.json()["retryable"] is True


def test_mobile_sync_teti_fault_work_request_requires_connector_token() -> None:
    response = client.post(
        "/api/mobile-sync/teti/fault-work-requests",
        json={
            "cloud_event_id": str(uuid4()),
            "client_event_id": str(uuid4()),
            "operator_id": str(uuid4()),
            "device_id": str(uuid4()),
            "payload_version": 1,
            "payload_hash": "e" * 64,
            "teti_fault_id": "TETI-001",
            "payload": {
                "plantId": str(uuid4()),
                "title": "Guasto",
                "description": "Test",
                "severity": "HIGH",
            },
            "attachments": [],
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid connector token"


def test_mobile_sync_teti_fault_work_request_creates_case_and_is_idempotent() -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    operator_id = str(operator.id)
    category = FieldReportCategory(code="TETI_FAULT", name="Fault TETI", is_active=True)
    low = FieldReportSeverity(code="LOW", name="Bassa", rank_order=1, is_active=True)
    high = FieldReportSeverity(code="HIGH", name="Alta", rank_order=3, is_active=True)
    critical = FieldReportSeverity(code="CRITICAL", name="Critica", rank_order=4, is_active=True)
    db.add_all([category, low, high, critical])
    db.commit()
    db.close()

    client_event_id = str(uuid4())
    payload = {
        "cloud_event_id": str(uuid4()),
        "client_event_id": client_event_id,
        "operator_id": operator_id,
        "device_id": str(uuid4()),
        "payload_version": 1,
        "payload_hash": "f" * 64,
        "teti_fault_id": "TETI-FAULT-001",
        "payload": {
            "plantId": str(uuid4()),
            "assetId": str(uuid4()),
            "title": "Guasto gruppo di pompaggio",
            "description": "Anomalia rilevata su pressione mandata",
            "severity": "CRITICAL",
            "latitude": 45.1234,
            "longitude": 9.4567,
        },
        "attachments": [],
    }

    first = client.post("/api/mobile-sync/teti/fault-work-requests", headers=headers, json=payload)
    assert first.status_code == 201
    body = first.json()
    assert body["gaia_entity_type"] == "gaia_work"
    assert body["extra"]["status"] == "created"
    assert body["extra"]["teti_fault_id"] == "TETI-FAULT-001"

    second = client.post("/api/mobile-sync/teti/fault-work-requests", headers=headers, json=payload)
    assert second.status_code == 201
    assert second.json()["gaia_entity_id"] == body["gaia_entity_id"]
    assert second.json()["extra"]["status"] == "already_exists"

    replay_with_new_client_event = client.post(
        "/api/mobile-sync/teti/fault-work-requests",
        headers=headers,
        json=payload | {"client_event_id": str(uuid4())},
    )
    assert replay_with_new_client_event.status_code == 201
    assert replay_with_new_client_event.json()["gaia_entity_id"] == body["gaia_entity_id"]
    assert replay_with_new_client_event.json()["extra"]["status"] == "already_exists"

    db = TestingSessionLocal()
    assert db.query(FieldReport).count() == 1
    assert db.query(MobileSyncEvent).count() == 1
    event = db.query(MobileSyncEvent).first()
    assert event is not None
    assert event.external_reference == "TETI-FAULT-001"
    assert event.cloud_event_id is not None
    db.close()


def test_mobile_sync_teti_fault_work_request_conflicts_on_hash_mismatch() -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    operator_id = str(operator.id)
    db.add(FieldReportCategory(code="TETI_FAULT", name="Fault TETI", is_active=True))
    db.add(FieldReportSeverity(code="HIGH", name="Alta", rank_order=3, is_active=True))
    db.commit()
    db.close()

    base_payload = {
        "cloud_event_id": str(uuid4()),
        "client_event_id": str(uuid4()),
        "operator_id": operator_id,
        "device_id": str(uuid4()),
        "payload_version": 1,
        "payload_hash": "1" * 64,
        "teti_fault_id": "TETI-FAULT-002",
        "payload": {
            "plantId": str(uuid4()),
            "title": "Guasto rete",
            "description": "Descrizione",
            "severity": "HIGH",
        },
        "attachments": [],
    }

    first = client.post("/api/mobile-sync/teti/fault-work-requests", headers=headers, json=base_payload)
    assert first.status_code == 201

    conflict = client.post(
        "/api/mobile-sync/teti/fault-work-requests",
        headers=headers,
        json=base_payload | {"payload_hash": "2" * 64},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "GAIA_CONFLICT"
    assert conflict.json()["retryable"] is False

    conflict_on_fault = client.post(
        "/api/mobile-sync/teti/fault-work-requests",
        headers=headers,
        json=base_payload | {"client_event_id": str(uuid4()), "payload_hash": "3" * 64},
    )
    assert conflict_on_fault.status_code == 409
    assert conflict_on_fault.json()["error_code"] == "GAIA_CONFLICT"


def test_mobile_sync_teti_fault_work_request_rejects_invalid_payload() -> None:
    headers = _connector_headers()
    response = client.post(
        "/api/mobile-sync/teti/fault-work-requests",
        headers=headers,
        json={
            "cloud_event_id": str(uuid4()),
            "client_event_id": str(uuid4()),
            "operator_id": str(uuid4()),
            "device_id": str(uuid4()),
            "payload_version": 1,
            "payload_hash": "4" * 64,
            "teti_fault_id": "TETI-FAULT-003",
            "payload": {
                "plantId": str(uuid4()),
                "title": "Guasto",
                "description": "Test",
                "severity": "INVALID",
            },
            "attachments": [],
        },
    )

    assert response.status_code == 422


def test_mobile_sync_teti_fault_work_request_returns_retryable_on_temporary_error(
    monkeypatch,
) -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    operator_id = str(operator.id)
    db.add(FieldReportCategory(code="TETI_FAULT", name="Fault TETI", is_active=True))
    db.add(FieldReportSeverity(code="HIGH", name="Alta", rank_order=3, is_active=True))
    db.commit()
    db.close()

    from app.modules.operazioni.routes import mobile_sync as mobile_sync_module

    original_create_mobile_event = mobile_sync_module._create_mobile_event

    def _boom(*args, **kwargs):
        raise RuntimeError("temporary db failure")

    monkeypatch.setattr(mobile_sync_module, "_create_mobile_event", _boom)
    response = client.post(
        "/api/mobile-sync/teti/fault-work-requests",
        headers=headers,
        json={
            "cloud_event_id": str(uuid4()),
            "client_event_id": str(uuid4()),
            "operator_id": operator_id,
            "device_id": str(uuid4()),
            "payload_version": 1,
            "payload_hash": "5" * 64,
            "teti_fault_id": "TETI-FAULT-004",
            "payload": {
                "plantId": str(uuid4()),
                "title": "Guasto transitorio",
                "description": "Test",
                "severity": "HIGH",
            },
            "attachments": [],
        },
    )
    monkeypatch.setattr(mobile_sync_module, "_create_mobile_event", original_create_mobile_event)

    assert response.status_code == 500
    assert response.json()["error_code"] == "GAIA_RETRYABLE_ERROR"
    assert response.json()["retryable"] is True
