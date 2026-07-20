from collections.abc import Generator
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from uuid import UUID, uuid4
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

if "shapely.geometry" not in sys.modules:
    shapely_module = ModuleType("shapely")
    shapely_geometry_module = ModuleType("shapely.geometry")

    def _shape(_geometry: object) -> SimpleNamespace:
        return SimpleNamespace(bounds=(8.0, 39.0, 9.0, 40.0))

    shapely_geometry_module.shape = _shape
    shapely_module.geometry = shapely_geometry_module
    sys.modules["shapely"] = shapely_module
    sys.modules["shapely.geometry"] = shapely_geometry_module

if "geoalchemy2.shape" not in sys.modules:
    geoalchemy2_module = ModuleType("geoalchemy2")
    geoalchemy2_shape_module = ModuleType("geoalchemy2.shape")

    def _to_shape(_geometry: object) -> SimpleNamespace:
        return SimpleNamespace(__geo_interface__={"type": "Point", "coordinates": [8.0, 39.0]})

    geoalchemy2_shape_module.to_shape = _to_shape
    geoalchemy2_module.shape = geoalchemy2_shape_module
    sys.modules["geoalchemy2"] = geoalchemy2_module
    sys.modules["geoalchemy2.shape"] = geoalchemy2_shape_module

if "shapefile" not in sys.modules:
    shapefile_module = ModuleType("shapefile")
    shapefile_module.Reader = object
    sys.modules["shapefile"] = shapefile_module

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.section_permission import Section
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloPartita, RuoloTributiReminder


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
client = TestClient(app)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    db.add(
        ApplicationUser(
            username="ruolo-tributi-admin",
            email="ruolo-tributi@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
            module_ruolo=True,
        )
    )
    db.add_all(
        [
            Section(key="ruolo.tributi.view", label="Ruolo Tributi view", module="ruolo", min_role="viewer"),
            Section(
                key="ruolo.tributi.manage_payments",
                label="Ruolo Tributi pagamenti",
                module="ruolo",
                min_role="admin",
            ),
            Section(
                key="ruolo.tributi.manage_status",
                label="Ruolo Tributi stati",
                module="ruolo",
                min_role="admin",
            ),
            Section(
                key="ruolo.tributi.manage_notes",
                label="Ruolo Tributi note",
                module="ruolo",
                min_role="reviewer",
            ),
            Section(
                key="ruolo.tributi.generate_reminders",
                label="Ruolo Tributi solleciti",
                module="ruolo",
                min_role="reviewer",
            ),
        ]
    )
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def auth_headers() -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "ruolo-tributi-admin", "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def seed_avviso(*, amount: float | None = 100.0) -> str:
    db = TestingSessionLocal()
    job = RuoloImportJob(anno_tributario=2024, filename="ruolo_tributi_2024", status="completed")
    db.add(job)
    db.flush()
    avviso = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc=f"CNC-{uuid4()}",
        anno_tributario=2024,
        codice_fiscale_raw="RSSMRA80A01H501Z",
        nominativo_raw="ROSSI MARIO",
        domicilio_raw="VIA TEST 1",
        residenza_raw="ORISTANO",
        codice_utenza="UT-TRIBUTI",
        importo_totale_euro=amount,
    )
    db.add(avviso)
    db.commit()
    avviso_id = str(avviso.id)
    db.close()
    return avviso_id


def test_tributi_avviso_lifecycle_tracks_payments_status_notes_and_capacitas_link() -> None:
    avviso_id = seed_avviso(amount=100.0)
    headers = auth_headers()

    list_response = client.get("/ruolo/tributi/avvisi?open_only=true", headers=headers)
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["payment_status"] == "unpaid"
    assert list_payload["items"][0]["saldo_amount"] == 100.0

    payment_response = client.post(
        f"/ruolo/tributi/avvisi/{avviso_id}/payments",
        headers=headers,
        json={
            "amount": 40.0,
            "paid_at": datetime(2026, 7, 17, tzinfo=timezone.utc).isoformat(),
            "payment_reference": "PAY-001",
            "payment_method": "bonifico",
        },
    )
    assert payment_response.status_code == 200
    payment_payload = payment_response.json()
    assert payment_payload["amount"] == 40.0
    assert payment_payload["codice_utenza_raw"] == "UT-TRIBUTI"

    detail_response = client.get(f"/ruolo/tributi/avvisi/{avviso_id}", headers=headers)
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["payment_status"] == "partial"
    assert detail_payload["paid_amount"] == 40.0
    assert detail_payload["saldo_amount"] == 60.0
    assert len(detail_payload["payments"]) == 1

    status_response = client.patch(
        f"/ruolo/tributi/avvisi/{avviso_id}/status",
        headers=headers,
        json={
            "workflow_status": "contestato",
            "capacitas_url": "https://incass3.servizicapacitas.com/pages/dettaglioAvviso.aspx?avviso=1",
            "capacitas_avviso_code": "020210002922120",
        },
    )
    assert status_response.status_code == 200
    assert status_response.json()["workflow_status"] == "contestato"

    note_response = client.post(
        f"/ruolo/tributi/avvisi/{avviso_id}/notes",
        headers=headers,
        json={"body": "Utente contattato, attende verifica.", "visibility": "internal"},
    )
    assert note_response.status_code == 200
    assert note_response.json()["body"] == "Utente contattato, attende verifica."

    second_payment_response = client.post(
        f"/ruolo/tributi/avvisi/{avviso_id}/payments",
        headers=headers,
        json={"amount": 60.0, "payment_reference": "PAY-002", "payment_method": "bonifico"},
    )
    assert second_payment_response.status_code == 200

    paid_filter_response = client.get("/ruolo/tributi/avvisi?payment_status=paid", headers=headers)
    assert paid_filter_response.status_code == 200
    paid_payload = paid_filter_response.json()
    assert paid_payload["total"] == 1
    assert paid_payload["items"][0]["payment_status"] == "paid"
    assert paid_payload["items"][0]["workflow_status"] == "contestato"
    assert paid_payload["items"][0]["notes_count"] == 1
    assert paid_payload["items"][0]["capacitas_avviso_code"] == "020210002922120"


def test_tributi_rejects_duplicate_payment_reference_and_invalid_capacitas_url() -> None:
    avviso_id = seed_avviso(amount=100.0)
    headers = auth_headers()

    first_response = client.post(
        f"/ruolo/tributi/avvisi/{avviso_id}/payments",
        headers=headers,
        json={"amount": 10.0, "payment_reference": "PAY-DUP"},
    )
    assert first_response.status_code == 200

    duplicate_response = client.post(
        f"/ruolo/tributi/avvisi/{avviso_id}/payments",
        headers=headers,
        json={"amount": 10.0, "payment_reference": "PAY-DUP"},
    )
    assert duplicate_response.status_code == 409

    invalid_status_response = client.patch(
        f"/ruolo/tributi/avvisi/{avviso_id}/status",
        headers=headers,
        json={"workflow_status": "moroso", "capacitas_url": "not-a-url"},
    )
    assert invalid_status_response.status_code == 422


def test_tributi_marks_missing_due_amount_as_to_review() -> None:
    seed_avviso(amount=None)

    response = client.get("/ruolo/tributi/avvisi?payment_status=to_review", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["payment_status"] == "to_review"
    assert payload["items"][0]["saldo_amount"] is None


def test_tributi_generates_lists_and_downloads_reminder_docx() -> None:
    avviso_id = seed_avviso(amount=100.0)
    headers = auth_headers()

    payment_response = client.post(
        f"/ruolo/tributi/avvisi/{avviso_id}/payments",
        headers=headers,
        json={"amount": 40.0, "payment_reference": "PAY-REMINDER"},
    )
    assert payment_response.status_code == 200

    create_response = client.post(
        f"/ruolo/tributi/avvisi/{avviso_id}/reminders",
        headers=headers,
        json={"notes": "Primo sollecito morosita"},
    )
    assert create_response.status_code == 200
    reminder_payload = create_response.json()
    assert reminder_payload["status"] == "generated"
    assert reminder_payload["download_url"].endswith("/download")
    assert reminder_payload["payload_json"]["codice_cnc"].startswith("CNC-")
    assert reminder_payload["payload_json"]["codice_utenza"] == "UT-TRIBUTI"
    assert reminder_payload["payload_json"]["saldo_amount"] == "60.00 EUR"

    list_response = client.get(f"/ruolo/tributi/avvisi/{avviso_id}/reminders", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == reminder_payload["id"]

    download_response = client.get(reminder_payload["download_url"], headers=headers)
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    archive = ZipFile(BytesIO(download_response.content))
    document_xml = archive.read("word/document.xml").decode("utf-8")
    assert "Avviso di sollecito pagamento" in document_xml
    assert "UT-TRIBUTI" in document_xml
    assert "60.00 EUR" in document_xml


def test_tributi_reminder_endpoints_return_404_for_missing_resources() -> None:
    missing_id = uuid4()
    headers = auth_headers()

    create_response = client.post(
        f"/ruolo/tributi/avvisi/{missing_id}/reminders",
        headers=headers,
        json={},
    )
    assert create_response.status_code == 404

    list_response = client.get(f"/ruolo/tributi/avvisi/{missing_id}/reminders", headers=headers)
    assert list_response.status_code == 404

    download_response = client.get(f"/ruolo/tributi/reminders/{missing_id}/download", headers=headers)
    assert download_response.status_code == 404


def test_tributi_reminder_download_returns_404_when_document_file_is_missing() -> None:
    avviso_id = seed_avviso(amount=None)
    headers = auth_headers()

    db = TestingSessionLocal()
    avviso = db.get(RuoloAvviso, UUID(avviso_id))
    assert avviso is not None
    avviso.codice_utenza = None
    avviso.domicilio_raw = ""
    avviso.residenza_raw = None
    db.commit()
    db.close()

    create_response = client.post(
        f"/ruolo/tributi/avvisi/{avviso_id}/reminders",
        headers=headers,
        json={},
    )
    assert create_response.status_code == 200
    reminder_payload = create_response.json()
    assert reminder_payload["payload_json"]["importo_totale"] is None
    assert reminder_payload["payload_json"]["codice_utenza"] is None

    document_path = Path(reminder_payload["generated_document_path"])
    assert document_path.exists()
    document_path.unlink()

    download_response = client.get(reminder_payload["download_url"], headers=headers)
    assert download_response.status_code == 404
    assert download_response.json()["detail"] == "Documento sollecito non trovato"

    db = TestingSessionLocal()
    avviso = db.get(RuoloAvviso, UUID(avviso_id))
    assert avviso is not None
    draft_reminder = RuoloTributiReminder(avviso_id=avviso.id, status="draft")
    db.add(draft_reminder)
    db.commit()
    draft_id = draft_reminder.id
    db.close()

    draft_download_response = client.get(f"/ruolo/tributi/reminders/{draft_id}/download", headers=headers)
    assert draft_download_response.status_code == 404


def test_tributi_filters_and_overpaid_status() -> None:
    avviso_id = seed_avviso(amount=100.0)
    db = TestingSessionLocal()
    avviso = db.get(RuoloAvviso, UUID(avviso_id))
    assert avviso is not None
    db.add(RuoloPartita(avviso_id=avviso.id, codice_partita="P-TRIB", comune_nome="ORISTANO"))
    db.commit()
    db.close()
    headers = auth_headers()

    for query in (
        "anno=2024",
        "subject_id=not-a-uuid",
        "q=ROSSI",
        "q=ORISTANO",
        "codice_fiscale=RSSMRA",
        "comune=ORISTANO",
        "codice_utenza=UT-TRIBUTI",
        "unlinked=true",
    ):
        response = client.get(f"/ruolo/tributi/avvisi?{query}", headers=headers)
        assert response.status_code == 200

    invalid_subject_response = client.get("/ruolo/tributi/avvisi?subject_id=not-a-uuid", headers=headers)
    assert invalid_subject_response.json()["total"] == 0

    payment_response = client.post(
        f"/ruolo/tributi/avvisi/{avviso_id}/payments",
        headers=headers,
        json={"amount": 120.0, "payment_reference": "PAY-OVER"},
    )
    assert payment_response.status_code == 200

    overpaid_response = client.get("/ruolo/tributi/avvisi?payment_status=overpaid", headers=headers)
    assert overpaid_response.status_code == 200
    assert overpaid_response.json()["total"] == 1
    assert overpaid_response.json()["items"][0]["saldo_amount"] == -20.0


def test_tributi_status_can_be_created_before_any_payment_and_filtered_by_workflow() -> None:
    avviso_id = seed_avviso(amount=100.0)
    headers = auth_headers()

    status_response = client.patch(
        f"/ruolo/tributi/avvisi/{avviso_id}/status",
        headers=headers,
        json={"workflow_status": "moroso", "capacitas_url": None, "capacitas_avviso_code": "AVV-001"},
    )
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["payment_status"] == "unpaid"
    assert payload["saldo_amount"] == 100.0

    workflow_response = client.get("/ruolo/tributi/avvisi?workflow_status=moroso", headers=headers)
    assert workflow_response.status_code == 200
    assert workflow_response.json()["total"] == 1


def test_tributi_returns_404_for_unknown_avviso_operations() -> None:
    missing_id = uuid4()
    headers = auth_headers()

    detail_response = client.get(f"/ruolo/tributi/avvisi/{missing_id}", headers=headers)
    assert detail_response.status_code == 404

    payment_response = client.post(
        f"/ruolo/tributi/avvisi/{missing_id}/payments",
        headers=headers,
        json={"amount": 10.0},
    )
    assert payment_response.status_code == 404

    status_response = client.patch(
        f"/ruolo/tributi/avvisi/{missing_id}/status",
        headers=headers,
        json={"workflow_status": "moroso"},
    )
    assert status_response.status_code == 404

    note_response = client.post(
        f"/ruolo/tributi/avvisi/{missing_id}/notes",
        headers=headers,
        json={"body": "nota"},
    )
    assert note_response.status_code == 404
