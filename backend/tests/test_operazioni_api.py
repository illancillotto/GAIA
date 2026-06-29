from collections.abc import Generator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.catasto_phase1 import CatMeterReading
from app.modules.operazioni.models.activities import (
    ActivityCatalog,
    OperatorActivity,
    OperatorActivityAttachment,
)
from app.modules.operazioni.models.attachments import Attachment
from app.modules.operazioni.models.gps import GpsTrackSummary
from app.modules.operazioni.models.reports import (
    FieldReport,
    FieldReportCategory,
    FieldReportSeverity,
    InternalCase,
)
from app.modules.operazioni.models.vehicles import Vehicle, WCRefuelEvent
from app.models.wc_sync_job import WCSyncJob


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


def seed_operazioni_user() -> ApplicationUser:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username="operazioni-admin",
        email="operazioni-admin@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_operazioni=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def auth_headers() -> dict[str, str]:
    seed_operazioni_user()
    response = client.post(
        "/auth/login",
        json={"username": "operazioni-admin", "password": "secret123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def auth_headers_without_operazioni() -> dict[str, str]:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username="no-operazioni",
        email="no-operazioni@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_operazioni=False,
    )
    db.add(user)
    db.commit()
    db.close()

    response = client.post(
        "/auth/login",
        json={"username": "no-operazioni", "password": "secret123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_activity_gps_viewer_extracts_track_points() -> None:
    db = TestingSessionLocal()
    catalog = ActivityCatalog(code="GPS-VIEW", name="GPS viewer activity", category="test")
    db.add(catalog)
    db.flush()

    track = GpsTrackSummary(
        source_type="provider_import",
        provider_name="test_provider",
        provider_track_id="TRACK-001",
        started_at=datetime.fromisoformat("2026-04-09T08:00:00"),
        ended_at=datetime.fromisoformat("2026-04-09T08:45:00"),
        start_latitude=Decimal("39.9031000"),
        start_longitude=Decimal("8.5923000"),
        end_latitude=Decimal("39.9112000"),
        end_longitude=Decimal("8.6014000"),
        total_distance_km=Decimal("6.250"),
        total_duration_seconds=2700,
        raw_payload_json={
            "track": {
                "points": [
                    {
                        "latitude": 39.9031,
                        "longitude": 8.5923,
                        "timestamp": "2026-04-09T08:00:00",
                    },
                    {
                        "latitude": 39.9075,
                        "longitude": 8.5961,
                        "timestamp": "2026-04-09T08:18:00",
                    },
                    {
                        "latitude": 39.9112,
                        "longitude": 8.6014,
                        "timestamp": "2026-04-09T08:45:00",
                    },
                ]
            }
        },
    )
    db.add(track)
    db.flush()

    activity = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=1,
        started_at=datetime.fromisoformat("2026-04-09T08:00:00"),
        ended_at=datetime.fromisoformat("2026-04-09T08:45:00"),
        status="submitted",
        gps_track_summary_id=track.id,
    )
    db.add(activity)
    db.commit()

    response = client.get(
        f"/operazioni/activities/{activity.id}/gps-viewer",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["viewer_mode"] == "track"
    assert payload["point_count"] == 3
    assert payload["uses_raw_payload"] is True
    assert payload["summary"]["provider_track_id"] == "TRACK-001"
    assert payload["points"][1]["latitude"] == pytest.approx(39.9075)
    assert payload["bounds"]["max_longitude"] == pytest.approx(8.6014)

    db.close()


def test_attachment_download_returns_file(tmp_path: Path) -> None:
    db = TestingSessionLocal()
    file_path = tmp_path / "operazioni-note.txt"
    file_path.write_text("contenuto allegato test", encoding="utf-8")

    attachment = Attachment(
        storage_path=str(file_path),
        original_filename="operazioni-note.txt",
        mime_type="text/plain",
        extension="txt",
        attachment_type="note",
        file_size_bytes=file_path.stat().st_size,
        source_context="operator_activity",
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    response = client.get(
        f"/operazioni/attachments/{attachment.id}/download",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.text == "contenuto allegato test"
    assert "operazioni-note.txt" in response.headers["content-disposition"]
    assert response.headers["content-type"].startswith("text/plain")

    db.close()


def test_operazioni_module_requires_module_flag() -> None:
    response = client.get(
        "/operazioni/dashboard/summary",
        headers=auth_headers_without_operazioni(),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Module access denied"


def test_operazioni_dashboard_quick_search_matches_content_across_entities() -> None:
    db = TestingSessionLocal()

    vehicle = Vehicle(
        code="VH-SEARCH-001",
        name="Motopompa reparto nord",
        vehicle_type="attrezzatura",
        notes="Contenuto speciale motopompa",
        current_status="available",
    )
    db.add(vehicle)

    catalog = ActivityCatalog(code="SEARCH-ACT", name="Ispezione canale", description="Attività di sopralluogo")
    db.add(catalog)
    db.flush()

    activity = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=1,
        started_at=datetime.fromisoformat("2026-04-14T08:00:00"),
        status="submitted",
        text_note="Contenuto speciale attività",
    )
    db.add(activity)

    category = FieldReportCategory(code="SEARCH-CAT", name="Ricerca", description="Categoria ricerca")
    severity = FieldReportSeverity(code="SEARCH-SEV", name="Media", rank_order=1)
    db.add(category)
    db.add(severity)
    db.flush()

    report = FieldReport(
        report_number="REP-SEARCH-001",
        reporter_user_id=1,
        category_id=category.id,
        severity_id=severity.id,
        title="Segnalazione ricerca",
        description="Contenuto speciale segnalazione",
        status="submitted",
    )
    db.add(report)
    db.flush()

    case = InternalCase(
        case_number="CAS-SEARCH-001",
        source_report_id=report.id,
        title="Pratica ricerca",
        description="Contenuto speciale pratica",
        status="open",
    )
    db.add(case)
    db.commit()

    headers = auth_headers()

    vehicles_response = client.get("/operazioni/vehicles?search=speciale&page_size=5", headers=headers)
    activities_response = client.get("/operazioni/activities?search=speciale&page_size=5", headers=headers)
    reports_response = client.get("/operazioni/reports?search=speciale&page_size=5", headers=headers)
    cases_response = client.get("/operazioni/cases?search=speciale&page_size=5", headers=headers)

    assert vehicles_response.status_code == 200
    assert activities_response.status_code == 200
    assert reports_response.status_code == 200
    assert cases_response.status_code == 200

    vehicles_payload = vehicles_response.json()
    activities_payload = activities_response.json()
    reports_payload = reports_response.json()
    cases_payload = cases_response.json()

    assert vehicles_payload["total"] == 1
    assert vehicles_payload["items"][0]["code"] == "VH-SEARCH-001"

    assert activities_payload["total"] == 1
    assert activities_payload["items"][0]["catalog_name"] == "Ispezione canale"
    assert activities_payload["items"][0]["text_note"] == "Contenuto speciale attività"

    assert reports_payload["total"] == 1
    assert reports_payload["items"][0]["report_number"] == "REP-SEARCH-001"
    assert reports_payload["items"][0]["description"] == "Contenuto speciale segnalazione"

    assert cases_payload["total"] == 1
    assert cases_payload["items"][0]["case_number"] == "CAS-SEARCH-001"
    assert cases_payload["items"][0]["description"] == "Contenuto speciale pratica"

    db.close()


def test_activities_list_and_detail_include_linked_mobile_meter_reading() -> None:
    db = TestingSessionLocal()
    catalog = ActivityCatalog(code="LETT_CONT", name="Lettura contatori", category="catasto", is_active=True)
    db.add(catalog)
    db.flush()

    activity = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=1,
        started_at=datetime.fromisoformat("2026-06-29T08:00:00"),
        status="in_progress",
        text_note="Attività mobile contatore",
    )
    db.add(activity)
    db.flush()

    reading = CatMeterReading(
        anno=2026,
        punto_consegna="CNT-001",
        matricola="MAT-001",
        record_type="CONT_NO_TES",
        record_kind="meter_reading",
        operational_state="active",
        lettura_finale=Decimal("258"),
        data_lettura=date.fromisoformat("2026-06-29"),
        operatore_lettura="Operatore Test",
        source="mobile",
        mobile_session_id=str(activity.id),
        sync_status="applied_to_gaia",
    )
    db.add(reading)
    db.commit()

    headers = auth_headers()
    list_response = client.get("/operazioni/activities?page_size=10", headers=headers)
    detail_response = client.get(f"/operazioni/activities/{activity.id}", headers=headers)

    assert list_response.status_code == 200
    assert detail_response.status_code == 200

    list_payload = list_response.json()
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["catalog_name"] == "Lettura contatori"
    assert list_payload["items"][0]["linked_meter_reading"] == {
        "id": str(reading.id),
        "punto_consegna": "CNT-001",
        "matricola": "MAT-001",
        "lettura_finale": "258.000",
        "data_lettura": "2026-06-29",
        "photo_url": None,
        "source": "mobile",
        "record_kind": "meter_reading",
    }

    detail_payload = detail_response.json()
    assert detail_payload["catalog_name"] == "Lettura contatori"
    assert detail_payload["linked_meter_reading"]["id"] == str(reading.id)
    assert detail_payload["linked_meter_reading"]["punto_consegna"] == "CNT-001"

    db.close()


def test_activities_list_can_filter_only_mobile_meter_activities() -> None:
    db = TestingSessionLocal()
    catalog = ActivityCatalog(code="LETT_CONT", name="Lettura contatori", category="catasto", is_active=True)
    db.add(catalog)
    db.flush()

    linked_activity = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=1,
        started_at=datetime.fromisoformat("2026-06-29T08:00:00"),
        status="in_progress",
    )
    plain_activity = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=1,
        started_at=datetime.fromisoformat("2026-06-29T09:00:00"),
        status="submitted",
    )
    db.add(linked_activity)
    db.add(plain_activity)
    db.flush()

    db.add(
        CatMeterReading(
            anno=2026,
            punto_consegna="CNT-001",
            matricola="MAT-001",
            record_type="CONT_NO_TES",
            record_kind="meter_reading",
            operational_state="active",
            lettura_finale=Decimal("258"),
            data_lettura=date.fromisoformat("2026-06-29"),
            operatore_lettura="Operatore Test",
            source="mobile",
            mobile_session_id=str(linked_activity.id),
            sync_status="applied_to_gaia",
        )
    )
    db.commit()

    response = client.get("/operazioni/activities?mobile_meter_only=true&page_size=10", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == str(linked_activity.id)

    db.close()


def test_list_wc_refuel_events_returns_unmatched_items_with_search() -> None:
    db = TestingSessionLocal()

    vehicle = Vehicle(
        code="VH-WHITE-001",
        name="Escavatore bonifica",
        vehicle_type="equipment",
        plate_number="GC898SX",
        current_status="available",
    )
    db.add(vehicle)
    db.flush()

    unmatched = WCRefuelEvent(
        wc_id=5561,
        vehicle_id=vehicle.id,
        vehicle_code="GC898SX",
        operator_name="Franco Piras",
        fueled_at=datetime.fromisoformat("2026-04-16T10:37:00"),
        odometer_km=Decimal("98300"),
        source_issue="WhiteCompany non espone litri e costo nel dettaglio.",
    )
    matched = WCRefuelEvent(
        wc_id=6001,
        vehicle_id=vehicle.id,
        vehicle_code="GC898SX",
        operator_name="Mario Rossi",
        fueled_at=datetime.fromisoformat("2026-04-15T09:00:00"),
        matched_fuel_log_id=vehicle.id,
    )
    db.add(unmatched)
    db.add(matched)
    db.commit()

    response = client.get(
        "/operazioni/vehicles/refuel-events?matched=false&search=5561",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["wc_id"] == 5561
    assert payload["items"][0]["vehicle_display_name"] == "Escavatore bonifica"
    assert payload["items"][0]["matched_fuel_log_id"] is None

    db.close()


def test_update_vehicle_persists_autodoc_link() -> None:
    db = TestingSessionLocal()

    vehicle = Vehicle(
        code="VH-AUTODOC-001",
        name="Fiat Panda servizio",
        vehicle_type="auto",
        plate_number="AB123CD",
        current_status="available",
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    response = client.patch(
        f"/operazioni/vehicles/{vehicle.id}",
        headers=auth_headers(),
        json={
            "autodoc_url": "https://www.auto-doc.it/ricambi-auto/fiat/panda/panda-169/19057-1-2",
            "autodoc_title": "FIAT PANDA (169) 1.2",
            "autodoc_data": {
                "Potenza [kW]": "44",
                "Carburante": "Benzina",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["autodoc_url"] == "https://www.auto-doc.it/ricambi-auto/fiat/panda/panda-169/19057-1-2"
    assert payload["autodoc_title"] == "FIAT PANDA (169) 1.2"
    assert payload["autodoc_data"]["Carburante"] == "Benzina"

    db.expire_all()
    refreshed = db.get(Vehicle, vehicle.id)
    assert refreshed is not None
    assert refreshed.autodoc_url == payload["autodoc_url"]
    assert refreshed.autodoc_title == payload["autodoc_title"]
    assert refreshed.autodoc_data == payload["autodoc_data"]

    db.close()


def test_queue_vehicle_autodoc_sync_job() -> None:
    db = TestingSessionLocal()
    vehicle = Vehicle(
        code="VH-AUTODOC-002",
        name="Citroen Saxo test",
        vehicle_type="auto",
        plate_number="ZZ999ZZ",
        autodoc_url="https://www.auto-doc.it/ricambi-auto/citroen/saxo/saxo-s0-s1/5616-1-5-d",
        current_status="available",
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    response = client.post(
        "/operazioni/vehicles/autodoc-sync",
        headers=auth_headers(),
        json={"vehicle_ids": [str(vehicle.id)], "only_with_autodoc_url": True, "force_refresh": True},
    )

    assert response.status_code == 202
    payload = response.json()["job"]
    assert payload["entity"] == "autodoc_vehicle_details"
    assert payload["status"] in {"queued", "running"}

    job = db.get(WCSyncJob, uuid.UUID(payload["job_id"]))
    assert job is not None
    assert job.entity == "autodoc_vehicle_details"
    assert job.params_json["vehicle_ids"] == [str(vehicle.id)]

    db.close()


def test_queue_vehicle_autodoc_sync_job_includes_vehicle_without_saved_url() -> None:
    db = TestingSessionLocal()
    vehicle = Vehicle(
        code="VH-AUTODOC-003",
        name="Fiat Punto discovery",
        vehicle_type="auto",
        plate_number="AA111AA",
        current_status="available",
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    response = client.post(
        "/operazioni/vehicles/autodoc-sync",
        headers=auth_headers(),
        json={"vehicle_ids": [str(vehicle.id)], "force_refresh": True},
    )

    assert response.status_code == 202
    payload = response.json()["job"]
    job = db.get(WCSyncJob, uuid.UUID(payload["job_id"]))
    assert job is not None
    assert job.params_json["vehicle_ids"] == [str(vehicle.id)]
    assert job.params_json["only_with_autodoc_url"] is False

    db.close()
