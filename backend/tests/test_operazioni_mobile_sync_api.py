from __future__ import annotations

import base64
import sys
import types
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from uuid import UUID

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
        gaia_user_id=gaia_user.id,
        wc_synced_at=datetime.now(UTC),
    )
    db.add(operator)
    db.flush()
    return operator, gaia_user


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
    db.add(
        CatMeterReading(
            anno=2026,
            punto_consegna="CNT-001",
            matricola="MTR-001",
            record_kind="meter_reading",
            source="mobile",
            mobile_operator_id=str(operator.id),
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

    catalogs_response = client.get("/api/mobile-sync/catalogs", headers=headers)
    assert catalogs_response.status_code == 200
    catalog_types = {item["catalog_type"] for item in catalogs_response.json()["catalogs"]}
    assert {"activity_types", "report_types", "report_severities", "vehicles", "meters"} <= catalog_types
    report_types = next(item for item in catalogs_response.json()["catalogs"] if item["catalog_type"] == "report_types")
    assert report_types["payload"]["items"][0]["id"] == "3"
    meters_catalog = next(item for item in catalogs_response.json()["catalogs"] if item["catalog_type"] == "meters")
    assert meters_catalog["payload"]["items"][0] == {
        "id": meters_catalog["payload"]["items"][0]["id"],
        "delivery_point_id": meters_catalog["payload"]["items"][0]["delivery_point_id"],
        "label": "CNT-001 · MTR-001 · Idrante",
        "code": "CNT-001",
        "punto_consegna": "CNT-001",
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
        "reading_id": meters_catalog["payload"]["items"][0]["reading_id"],
        "reading_year": 2026,
        "operational_state": None,
    }

    worksets_response = client.get("/api/mobile-sync/worksets", headers=headers, params={"operator_id": operator_id})
    assert worksets_response.status_code == 200
    worksets = {item["workset_type"]: item for item in worksets_response.json()["worksets"]}
    assert worksets["assigned_activities"]["items"][0]["payload"]["team_label"] == "Squadra Nord"
    assert worksets["available_vehicles"]["items"][0]["payload"]["plate"] == "AB123CD"
    assert worksets["assigned_meters"]["items"][0]["payload"]["punto_consegna"] == "CNT-001"


def test_mobile_sync_requires_connector_token() -> None:
    response = client.get("/api/mobile-sync/mobile-operators")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid connector token"


def test_mobile_sync_connector_handshake_returns_capabilities() -> None:
    response = client.get("/api/mobile-sync/connector/handshake", headers=_connector_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "gaia-mobile-sync"
    assert payload["authenticated"] is True
    assert payload["auth_scheme"] == "header_token"
    assert "catalogs.read" in payload["capabilities"]
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
    assert payload["outbound_scope"] == ["operators"]
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
            report=GateMobileSyncReport(requested_tasks=[{"type": "operators"}], operators_pushed=17),
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
    db.commit()
    catalog_id = str(catalog.id)
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
            "meter_number": "A1234",
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
    assert reading.matricola == "A1234"
    assert float(reading.lettura_finale) == 258.0
    assert str(reading.mobile_operator_id) == operator_id
    assert reading.device_id == payload["device_id"]
    assert reading.mobile_session_id == body["gaia_entity_id"]
    assert reading.photo_url is not None
    assert Path(reading.photo_url).exists()

    attachment = db.query(Attachment).one()
    assert Path(attachment.storage_path).exists()
    assert attachment.metadata_json["upload_origin"] == "gaia_mobile_connector_inline"
    assert attachment.metadata_json["linked_activity_id"] == body["gaia_entity_id"]
    assert db.query(MobileSyncEvent).count() == 1
    db.close()


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
