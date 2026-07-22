from collections.abc import Generator
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from uuid import UUID, uuid4
from zipfile import ZipFile

from openpyxl import Workbook
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
from app.modules.ruolo import tributi_repositories as tributi_repo
from app.modules.ruolo.services import tributi_reminder_service as reminder_service
from app.modules.ruolo.models import (
    RuoloAvviso,
    RuoloImportJob,
    RuoloParticella,
    RuoloPartita,
    RuoloTributiReminder,
    RuoloTributiYearManager,
)
from app.modules.ruolo.schemas import RuoloImportJobResponse
from app.modules.ruolo.services.tributi_reminder_service import (
    convert_docx_to_pdf,
    generate_batch_reminder_docx,
    generate_batch_reminder_pdf,
)
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPaymentNotice, AnagraficaPerson, AnagraficaSubject


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
            Section(
                key="ruolo.tributi.import_payments",
                label="Ruolo Tributi import pagamenti",
                module="ruolo",
                min_role="admin",
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


def seed_avviso(
    *,
    amount: float | None = 100.0,
    tax_code: str = "RSSMRA80A01H501Z",
    nominativo: str = "ROSSI MARIO",
    anno: int = 2024,
    subject_id: UUID | None = None,
) -> str:
    db = TestingSessionLocal()
    job = RuoloImportJob(anno_tributario=anno, filename=f"ruolo_tributi_{anno}", status="completed")
    db.add(job)
    db.flush()
    avviso = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc=f"CNC-{uuid4()}",
        anno_tributario=anno,
        subject_id=subject_id,
        codice_fiscale_raw=tax_code,
        nominativo_raw=nominativo,
        domicilio_raw="VIA TEST 1",
        residenza_raw="ORISTANO",
        codice_utenza="UT-TRIBUTI",
        importo_totale_euro=amount,
        importo_totale_0648=amount,
    )
    db.add(avviso)
    db.commit()
    avviso_id = str(avviso.id)
    db.close()
    return avviso_id


def seed_subject_with_nas(tmp_path: Path, *, tax_code: str = "RSSMRA80A01H501Z") -> UUID:
    db = TestingSessionLocal()
    subject = AnagraficaSubject(
        source_name_raw="ROSSI MARIO",
        nas_folder_path=str(tmp_path / "archivio" / tax_code),
        nas_folder_letter="R",
    )
    db.add(subject)
    db.flush()
    db.add(
        AnagraficaPerson(
            subject_id=subject.id,
            cognome="ROSSI",
            nome="MARIO",
            codice_fiscale=tax_code,
        )
    )
    db.commit()
    subject_id = subject.id
    db.close()
    return subject_id


def test_tributi_archive_folder_helpers_cover_sanitising_and_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    assert tributi_repo._safe_archive_folder_component('  Società "Test"/Nord  ') == "Societa Test Nord"
    assert tributi_repo._build_archive_folder_name(display_name=None, codice_fiscale="rss mra 80") == "RSSMRA80_RSSMRA80"
    assert tributi_repo._build_archive_folder_name(display_name=None, codice_fiscale="") == "UTENZA"
    long_name = "A" * 140
    truncated = tributi_repo._build_archive_folder_name(display_name=long_name, codice_fiscale="ABC123")
    assert truncated.endswith("_ABC123")
    assert len(truncated) == 96
    assert tributi_repo._derive_archive_letter("123", " società") == "S"
    assert tributi_repo._derive_archive_letter("123", "___") is None
    assert tributi_repo._valid_archive_letter(" r ") == "R"
    assert tributi_repo._valid_archive_letter("rr") is None

    db = TestingSessionLocal()
    company_subject = AnagraficaSubject(source_name_raw="RAW COMPANY", nas_folder_path=None, nas_folder_letter=None)
    person_subject = AnagraficaSubject(source_name_raw="RAW PERSON", nas_folder_path=None, nas_folder_letter=None)
    fallback_subject = AnagraficaSubject(source_name_raw="RAW FALLBACK", nas_folder_path=None, nas_folder_letter=None)
    db.add_all([company_subject, person_subject, fallback_subject])
    db.flush()
    db.add(AnagraficaCompany(subject_id=company_subject.id, ragione_sociale="AZIENDA TEST", partita_iva="12345678901"))
    db.add(AnagraficaPerson(subject_id=person_subject.id, cognome="", nome="", codice_fiscale="RSSMRA80A01H501Z"))
    db.commit()

    assert tributi_repo._subject_archive_display_name(db, company_subject) == "AZIENDA TEST"
    assert tributi_repo._subject_archive_display_name(db, person_subject) == "RAW PERSON"
    assert tributi_repo._subject_archive_display_name(db, fallback_subject) == "RAW FALLBACK"
    monkeypatch.setattr(tributi_repo, "canonical_subject_nas_folder_path", lambda **_kwargs: None)
    assert tributi_repo._ensure_subject_archive_path(db, fallback_subject, "RSSMRA80A01H501Z") is None
    monkeypatch.setattr(tributi_repo, "canonical_subject_nas_folder_path", lambda **_kwargs: "/nas/R/RAW")
    assert tributi_repo._ensure_subject_archive_path(db, fallback_subject, "RSSMRA80A01H501Z") == "/nas/R/RAW"
    assert fallback_subject.nas_folder_path == "/nas/R/RAW"
    assert tributi_repo._ensure_subject_archive_path(db, fallback_subject, "RSSMRA80A01H501Z") == "/nas/R/RAW"
    db.close()


def test_tributi_incass_mailing_delivery_edge_branches() -> None:
    assert tributi_repo._extract_incass_mailing_delivery(source_notice_id="A1", raw_detail_json=None) is None
    assert tributi_repo._extract_incass_mailing_delivery(source_notice_id="A1", raw_detail_json={}) is None
    assert tributi_repo._extract_incass_mailing_delivery(source_notice_id="A1", raw_detail_json={"mailing_list": {}}) is None

    fallback = tributi_repo._extract_incass_mailing_delivery(
        source_notice_id="A1",
        raw_detail_json={
            "mailing_list": {
                "shipments": [
                    "bad-row",
                    {"external_id": "sped-1", "recipient": "utente@example.it", "status_label": "Accettazione"},
                ],
                "receipt_parents_by_shipment_id": "bad",
                "receipt_documents_by_parent_id": "bad",
            }
        },
    )
    assert fallback is not None
    assert fallback["pec_recipient"] == "utente@example.it"
    assert fallback["receipt_documents_count"] == 0
    assert tributi_repo._find_receipt_parent(["bad"], "CONSEGNA") is None


def test_tributi_archive_folder_helpers_and_subject_resolution_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    assert tributi_repo._derive_archive_letter("  123 ") is None
    assert tributi_repo._derive_archive_letter("  123 beta") == "B"
    assert tributi_repo._valid_archive_letter(" rr ") is None
    assert tributi_repo._valid_archive_letter("r") == "R"
    assert tributi_repo._build_archive_folder_name(display_name="<<<>>>", codice_fiscale="") == "UTENZA"

    db = TestingSessionLocal()
    person_subject = AnagraficaSubject(source_name_raw="Fallback Source", nas_folder_path=None, nas_folder_letter=None)
    unknown_subject = AnagraficaSubject(source_name_raw="Only Source", nas_folder_path=None, nas_folder_letter=None)
    db.add_all([person_subject, unknown_subject])
    db.flush()
    db.add(AnagraficaPerson(subject_id=person_subject.id, cognome="PINNA", nome="", codice_fiscale="PNNFLL80A01H501Z"))
    db.flush()

    assert tributi_repo._subject_archive_display_name(db, person_subject) == "PINNA"
    assert tributi_repo._subject_archive_display_name(db, unknown_subject) == "Only Source"

    monkeypatch.setattr("app.modules.ruolo.tributi_repositories.canonical_subject_nas_folder_path", lambda **_kwargs: None)
    assert tributi_repo._ensure_subject_archive_path(db, unknown_subject, "123") is None
    db.close()


def test_ruolo_import_job_response_duration_branches() -> None:
    started_at = datetime(2026, 7, 22, 10, 0, tzinfo=timezone.utc)
    finished_at = datetime(2026, 7, 22, 10, 0, 2, 250000, tzinfo=timezone.utc)

    completed = RuoloImportJobResponse(
        id=uuid4(),
        anno_tributario=2026,
        filename="ruolo.txt",
        status="completed",
        started_at=started_at,
        finished_at=finished_at,
        total_partite=1,
        records_imported=1,
        records_skipped=0,
        records_errors=0,
        error_detail=None,
        triggered_by=None,
        params_json=None,
        created_at=started_at,
    )
    pending = completed.model_copy(update={"finished_at": None})

    assert completed.duration_seconds == 2.2
    assert pending.duration_seconds is None


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


def test_tributi_import_pagamenti_csv_matches_by_cnc_and_reports_unmatched() -> None:
    matched_avviso_id = seed_avviso(amount=100.0, anno=2024)
    seed_avviso(amount=80.0, tax_code="BNCLGU80A01H501Y", nominativo="BIANCHI LUIGI", anno=2024)
    db = TestingSessionLocal()
    matched_avviso = db.get(RuoloAvviso, UUID(matched_avviso_id))
    assert matched_avviso is not None
    codice_cnc = matched_avviso.codice_cnc
    db.close()

    csv_content = (
        "Avviso;Anno;Importo pagato;Data pagamento;Riferimento;Metodo\n"
        f"{codice_cnc};2024;40,50;17/07/2026;PAY-CAP-001;PagoPA\n"
        "CNC-MISSING;2024;12,00;18/07/2026;PAY-CAP-002;PagoPA\n"
        f"{codice_cnc};2024;;19/07/2026;PAY-CAP-003;PagoPA\n"
    ).encode("utf-8")

    response = client.post(
        "/ruolo/tributi/import-pagamenti",
        headers=auth_headers(),
        files={"file": ("pagamenti.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["records_total"] == 3
    assert payload["records_imported"] == 1
    assert payload["records_matched"] == 1
    assert payload["records_unmatched"] == 1
    assert payload["records_errors"] == 1
    assert payload["mapping_json"]["resolved_mapping"]["codice_cnc"] == "Avviso"
    assert payload["mapping_json"]["resolved_mapping"]["amount"] == "Importo pagato"

    detail_response = client.get(f"/ruolo/tributi/avvisi/{matched_avviso_id}", headers=auth_headers())
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["payment_status"] == "partial"
    assert detail_payload["paid_amount"] == 40.5
    assert detail_payload["payments"][0]["import_job_id"] == payload["id"]
    assert detail_payload["payments"][0]["source"] == "capacitas_excel"
    assert detail_payload["payments"][0]["payment_reference"] == "PAY-CAP-001"

    jobs_response = client.get("/ruolo/tributi/import-pagamenti/jobs", headers=auth_headers())
    assert jobs_response.status_code == 200
    assert jobs_response.json()["total"] == 1
    assert jobs_response.json()["items"][0]["id"] == payload["id"]

    job_response = client.get(f"/ruolo/tributi/import-pagamenti/jobs/{payload['id']}", headers=auth_headers())
    assert job_response.status_code == 200
    assert job_response.json()["filename"] == "pagamenti.csv"

    unmatched_response = client.get(f"/ruolo/tributi/import-pagamenti/jobs/{payload['id']}/unmatched", headers=auth_headers())
    assert unmatched_response.status_code == 200
    unmatched_payload = unmatched_response.json()
    assert unmatched_payload["total"] == 2
    assert [item["row_number"] for item in unmatched_payload["items"]] == [3, 4]
    assert "Avviso non trovato" in unmatched_payload["items"][0]["reason"]
    assert unmatched_payload["items"][1]["reason"] == "Importo pagamento mancante"


def test_tributi_import_pagamenti_xlsx_uses_mapping_and_skips_duplicates() -> None:
    avviso_id = seed_avviso(amount=100.0, anno=2025)
    db = TestingSessionLocal()
    avviso = db.get(RuoloAvviso, UUID(avviso_id))
    assert avviso is not None
    codice_utenza = avviso.codice_utenza
    db.close()

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Codice utenza export", "Anno ruolo", "Totale versato", "Data incasso", "Quietanza"])
    sheet.append([codice_utenza, 2025, 100.0, datetime(2026, 7, 20, 8, 30), "QUIET-001"])
    buffer = BytesIO()
    workbook.save(buffer)
    mapping = {
        "codice_utenza": "Codice utenza export",
        "anno_tributario": "Anno ruolo",
        "amount": "Totale versato",
        "paid_at": "Data incasso",
        "payment_reference": "Quietanza",
    }
    headers = auth_headers()

    first_response = client.post(
        "/ruolo/tributi/import-pagamenti",
        headers=headers,
        data={"mapping_json": json.dumps(mapping)},
        files={
            "file": (
                "pagamenti.xlsx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert first_response.status_code == 200
    first_payload = first_response.json()
    assert first_payload["records_imported"] == 1
    assert first_payload["records_unmatched"] == 0

    second_response = client.post(
        "/ruolo/tributi/import-pagamenti",
        headers=headers,
        data={"mapping_json": json.dumps(mapping)},
        files={
            "file": (
                "pagamenti.xlsx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert second_response.status_code == 200
    second_payload = second_response.json()
    assert second_payload["records_imported"] == 0
    assert second_payload["records_unmatched"] == 1
    assert second_payload["mapping_json"]["unmatched"][0]["reason"] == "Pagamento gia importato"

    paid_response = client.get("/ruolo/tributi/avvisi?payment_status=paid", headers=headers)
    assert paid_response.status_code == 200
    assert paid_response.json()["total"] == 1


def test_tributi_import_pagamenti_rejects_bad_mapping_and_empty_files() -> None:
    headers = auth_headers()
    invalid_mapping_response = client.post(
        "/ruolo/tributi/import-pagamenti",
        headers=headers,
        data={"mapping_json": "{bad"},
        files={"file": ("pagamenti.csv", b"Avviso;Importo\n", "text/csv")},
    )
    assert invalid_mapping_response.status_code == 422

    empty_response = client.post(
        "/ruolo/tributi/import-pagamenti",
        headers=headers,
        files={"file": ("pagamenti.csv", b"", "text/csv")},
    )
    assert empty_response.status_code == 422
    assert empty_response.json()["detail"] == "File import pagamenti vuoto"

    missing_job_response = client.get(f"/ruolo/tributi/import-pagamenti/jobs/{uuid4()}", headers=headers)
    assert missing_job_response.status_code == 404
    missing_unmatched_response = client.get(f"/ruolo/tributi/import-pagamenti/jobs/{uuid4()}/unmatched", headers=headers)
    assert missing_unmatched_response.status_code == 404


def test_tributi_detail_uses_incass_capacitas_link_when_manual_status_is_missing() -> None:
    avviso_id = seed_avviso(amount=100.0, anno=2025)
    db = TestingSessionLocal()
    db.add(
        AnagraficaPaymentNotice(
            source_system="incass",
            source_notice_id="020250001234560",
            codice_fiscale="RSSMRA80A01H501Z",
            anno="2025",
            detail_url="https://incass3.servizicapacitas.com/pages/dettaglioAvviso.aspx?avviso=020250001234560",
            raw_detail_json={
                "mailing_list": {
                    "shipments": [
                        {
                            "external_id": "sped-1",
                            "recipient": "rossi.mario@pec.example.it",
                            "status_label": "Accettazione, Consegna",
                            "event_at": "2021-12-17T20:01:59.643000Z",
                        }
                    ],
                    "receipt_parents_by_shipment_id": {
                        "sped-1": [
                            {"parent_id": "parent-acc", "group": "ACCETTAZIONE", "date": "17/12/2021 20:01:57"},
                            {"parent_id": "parent-del", "group": "CONSEGNA", "date": "17/12/2021 20:01:58"},
                        ]
                    },
                    "receipt_documents_by_parent_id": {
                        "parent-acc": [{"object_id": "obj-acc"}],
                        "parent-del": [{"object_id": "obj-del"}],
                    },
                }
            },
        )
    )
    db.commit()
    db.close()

    response = client.get(f"/ruolo/tributi/avvisi/{avviso_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["capacitas_url"] == "https://incass3.servizicapacitas.com/pages/dettaglioAvviso.aspx?avviso=020250001234560"
    assert payload["capacitas_avviso_code"] == "020250001234560"
    assert payload["mailing_delivery"]["pec_recipient"] == "rossi.mario@pec.example.it"
    assert payload["mailing_delivery"]["delivered_at"] == "17/12/2021 20:01:58"
    assert payload["mailing_delivery"]["accepted_at"] == "17/12/2021 20:01:57"
    assert payload["mailing_delivery"]["receipt_documents_count"] == 2


def test_tributi_summary_counts_open_notices_and_detected_pec_shipments() -> None:
    first_avviso_id = seed_avviso(amount=100.0, anno=2025)
    second_avviso_id = seed_avviso(amount=80.0, tax_code="BNCLGU80A01H501Y", nominativo="BIANCHI LUIGI", anno=2025)
    db = TestingSessionLocal()
    db.add(
        AnagraficaPaymentNotice(
            source_system="incass",
            source_notice_id="020250009999999",
            codice_fiscale="RSSMRA80A01H501Z",
            anno="2025",
            detail_url="https://incass3.servizicapacitas.com/pages/dettaglioAvviso.aspx?avviso=020250009999999",
            raw_detail_json={
                "mailing_list": {
                    "shipments": [
                        {
                            "external_id": "sped-1",
                            "recipient": "rossi.mario@pec.example.it",
                            "status_label": "Accettazione, Consegna",
                            "event_at": "2021-12-17T20:01:59.643000Z",
                        }
                    ],
                    "receipt_parents_by_shipment_id": {
                        "sped-1": [
                            {"parent_id": "parent-acc", "group": "ACCETTAZIONE", "date": "17/12/2021 20:01:57"},
                            {"parent_id": "parent-del", "group": "CONSEGNA", "date": "17/12/2021 20:01:58"},
                        ]
                    },
                    "receipt_documents_by_parent_id": {
                        "parent-acc": [{"object_id": "obj-acc"}],
                        "parent-del": [{"object_id": "obj-del"}],
                    },
                }
            },
        )
    )
    db.commit()
    db.close()

    headers = auth_headers()
    response = client.get("/ruolo/tributi/summary?anno=2025&open_only=true", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_count"] == 2
    assert payload["total_amount"] == 180.0
    assert payload["pec_count"] == 1
    assert payload["pec_amount"] == 100.0
    assert payload["sent_count"] == 1
    assert payload["to_send_count"] == 1
    assert payload["raccomandata_count"] == 0
    assert payload["raccomandata_amount"] == 0.0
    assert payload["raccomandata_source_available"] is False

    first_detail = client.get(f"/ruolo/tributi/avvisi/{first_avviso_id}", headers=headers)
    second_detail = client.get(f"/ruolo/tributi/avvisi/{second_avviso_id}", headers=headers)
    assert first_detail.status_code == 200
    assert second_detail.status_code == 200
    assert first_detail.json()["mailing_delivery"]["pec_recipient"] == "rossi.mario@pec.example.it"
    assert second_detail.json()["mailing_delivery"] is None


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


def test_tributi_list_orders_by_due_amount_descending_with_missing_due_last() -> None:
    seed_avviso(amount=100.0)
    seed_avviso(amount=None)
    seed_avviso(amount=250.0)

    response = client.get("/ruolo/tributi/avvisi?open_only=false", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert [item["importo_totale_euro"] for item in payload["items"]] == [250.0, 100.0, None]


def test_tributi_year_managers_are_configurable_and_filter_avvisi() -> None:
    seed_avviso(amount=100.0, anno=2016)
    step_avviso_id = seed_avviso(amount=120.0, anno=2020)
    seed_avviso(amount=140.0, anno=2024)
    headers = auth_headers()

    pre_seed_response = client.get("/ruolo/tributi/avvisi?manager_key=gaia&open_only=false", headers=headers)
    assert pre_seed_response.status_code == 200
    assert pre_seed_response.json()["items"][0]["annuality_manager_label"] == "Consorzio/GAIA"

    managers_response = client.get("/ruolo/tributi/year-managers", headers=headers)
    assert managers_response.status_code == 200
    managers_payload = managers_response.json()
    assert [item["manager_key"] for item in managers_payload["items"]] == ["agenzia_entrate", "step", "gaia"]

    step_response = client.get("/ruolo/tributi/avvisi?manager_key=step&open_only=false", headers=headers)
    assert step_response.status_code == 200
    step_payload = step_response.json()
    assert step_payload["total"] == 1
    assert step_payload["items"][0]["id"] == step_avviso_id
    assert step_payload["items"][0]["annuality_manager_label"] == "STEP - Agenzia recupero crediti"
    assert step_payload["items"][0]["calculation_policy"] == "external_recovery"

    create_overlap_response = client.post(
        "/ruolo/tributi/year-managers",
        headers=headers,
        json={
            "manager_key": "overlap",
            "manager_label": "Overlap",
            "year_from": 2021,
            "year_to": 2023,
            "calculation_policy": "external",
        },
    )
    assert create_overlap_response.status_code == 422
    assert "Range annualita sovrapposto" in create_overlap_response.json()["detail"]

    gaia_id = next(item["id"] for item in managers_payload["items"] if item["manager_key"] == "gaia")
    invalid_update_response = client.put(
        f"/ruolo/tributi/year-managers/{gaia_id}",
        headers=headers,
        json={"manager_key": "gaia", "manager_label": "Consorzio/GAIA", "year_from": 2030, "year_to": 2029},
    )
    assert invalid_update_response.status_code == 422

    update_response = client.put(
        f"/ruolo/tributi/year-managers/{gaia_id}",
        headers=headers,
        json={
            "manager_key": "gaia",
            "manager_label": "Consorzio/GAIA",
            "year_from": 2023,
            "year_to": None,
            "calculation_policy": "internal_gaia",
            "notes": "Dal 2023 per test.",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["year_from"] == 2023

    create_response = client.post(
        "/ruolo/tributi/year-managers",
        headers=headers,
        json={
            "manager_key": "nostra",
            "manager_label": "Gestione diretta test",
            "year_from": 2022,
            "year_to": 2022,
            "calculation_policy": "internal_gaia",
            "is_active": True,
        },
    )
    assert create_response.status_code == 200
    created_id = create_response.json()["id"]

    inactive_response = client.post(
        "/ruolo/tributi/year-managers",
        headers=headers,
        json={
            "manager_key": "archivio_inattivo",
            "manager_label": "Archivio inattivo",
            "year_from": 2000,
            "year_to": 2030,
            "calculation_policy": "external",
            "is_active": False,
        },
    )
    assert inactive_response.status_code == 200
    assert client.post(
        "/ruolo/tributi/year-managers",
        headers=headers,
        json={"manager_key": "!!!", "manager_label": "Bad", "year_from": 2031, "year_to": 2032},
    ).status_code == 422

    candidates_response = client.get("/ruolo/tributi/solleciti/candidates?manager_key=step", headers=headers)
    assert candidates_response.status_code == 200
    assert candidates_response.json()["total"] == 0

    gaia_candidates_response = client.get("/ruolo/tributi/solleciti/candidates?manager_key=gaia", headers=headers)
    assert gaia_candidates_response.status_code == 200
    assert gaia_candidates_response.json()["items"][0]["annuality_managers"] == ["Consorzio/GAIA"]

    delete_response = client.delete(f"/ruolo/tributi/year-managers/{created_id}", headers=headers)
    assert delete_response.status_code == 204
    assert client.delete(f"/ruolo/tributi/year-managers/{uuid4()}", headers=headers).status_code == 404
    assert (
        client.put(
            f"/ruolo/tributi/year-managers/{uuid4()}",
            headers=headers,
            json={"manager_key": "missing", "manager_label": "Missing", "year_from": 2030, "year_to": 2031},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/ruolo/tributi/year-managers",
            headers=headers,
            json={"manager_key": "bad", "manager_label": "Bad", "year_from": 2031, "year_to": 2030},
        ).status_code
        == 422
    )


def test_tributi_year_manager_helper_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    assert tributi_repo._manager_range_label(
        RuoloTributiYearManager(manager_key="all", manager_label="All", year_from=None, year_to=None)
    ) == "tutte le annualita"
    assert tributi_repo._manager_range_label(
        RuoloTributiYearManager(manager_key="to", manager_label="To", year_from=None, year_to=2017)
    ) == "fino al 2017"
    assert tributi_repo._manager_range_label(
        RuoloTributiYearManager(manager_key="from", manager_label="From", year_from=2022, year_to=None)
    ) == "dal 2022"
    assert tributi_repo._manager_range_label(
        RuoloTributiYearManager(manager_key="single", manager_label="Single", year_from=2022, year_to=2022)
    ) == "2022"

    monkeypatch.setattr(tributi_repo, "DEFAULT_YEAR_MANAGERS", ())
    assert tributi_repo._default_year_manager_for_year(2024) == {
        "manager_key": None,
        "manager_label": None,
        "calculation_policy": None,
    }

    db = TestingSessionLocal()
    db.add(
        RuoloTributiYearManager(
            manager_key="inactive",
            manager_label="Inactive",
            year_from=2024,
            year_to=2024,
            calculation_policy="external",
            is_active=False,
        )
    )
    db.commit()
    assert tributi_repo.get_year_manager_for_year(db, 2024) == {
        "manager_key": None,
        "manager_label": None,
        "calculation_policy": None,
    }
    db.close()


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


def test_tributi_reminder_batch_groups_candidates_generates_pdf_and_tracks_items(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    subject_id = seed_subject_with_nas(tmp_path)
    first_avviso_id = seed_avviso(amount=100.0, anno=2022, subject_id=subject_id)
    second_avviso_id = seed_avviso(amount=150.0, anno=2023, subject_id=subject_id)
    orphan_avviso_id = seed_avviso(amount=80.0, tax_code="BNCLGU80A01H501Y", nominativo="BIANCHI LUIGI", anno=2023)

    db = TestingSessionLocal()
    first_avviso = db.get(RuoloAvviso, UUID(first_avviso_id))
    second_avviso = db.get(RuoloAvviso, UUID(second_avviso_id))
    orphan_avviso = db.get(RuoloAvviso, UUID(orphan_avviso_id))
    assert first_avviso is not None
    assert second_avviso is not None
    assert orphan_avviso is not None
    first_partita = RuoloPartita(avviso_id=first_avviso.id, codice_partita="000000268/00000", comune_nome="URAS", importo_0648=100)
    second_partita = RuoloPartita(avviso_id=second_avviso.id, codice_partita="000000269/00000", comune_nome="MOGORO", importo_0648=150)
    orphan_partita = RuoloPartita(avviso_id=orphan_avviso.id, codice_partita="000000270/00000", comune_nome="ALES", importo_0648=80)
    db.add_all([first_partita, second_partita, orphan_partita])
    db.flush()
    db.add(
        RuoloParticella(
            partita_id=first_partita.id,
            anno_tributario=2022,
            domanda_irrigua="1",
            distretto="2",
            foglio="10",
            particella="20",
            subalterno="",
            sup_catastale_ha=1.5,
            sup_irrigata_ha=1.2,
            coltura="SEMINATIVO",
            importo_manut=100,
        )
    )
    db.add(
        RuoloParticella(
            partita_id=second_partita.id,
            anno_tributario=2023,
            foglio="11",
            particella="21",
        )
    )
    db.commit()
    db.close()

    def fake_generate_batch_reminder_pdf(payload: dict, *, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.4 fake gaia reminder")
        assert payload["codice_fiscale"] == "RSSMRA80A01H501Z"
        assert payload["years"] == [2022, 2023]
        assert payload["avvisi"][0]["partite"]

    monkeypatch.setattr(
        "app.modules.ruolo.tributi_repositories.generate_batch_reminder_pdf",
        fake_generate_batch_reminder_pdf,
    )
    headers = auth_headers()

    candidates_response = client.get("/ruolo/tributi/solleciti/candidates?anno_from=2022&anno_to=2023", headers=headers)
    assert candidates_response.status_code == 200
    candidates_payload = candidates_response.json()
    assert candidates_payload["total"] == 2
    linked_candidate = next(item for item in candidates_payload["items"] if item["codice_fiscale"] == "RSSMRA80A01H501Z")
    assert linked_candidate["years"] == [2022, 2023]
    assert linked_candidate["avvisi_count"] == 2
    assert linked_candidate["due_amount"] == 250.0
    assert linked_candidate["has_nas_folder"] is True
    orphan_candidate = next(item for item in candidates_payload["items"] if item["codice_fiscale"] == "BNCLGU80A01H501Y")
    assert orphan_candidate["has_nas_folder"] is False

    create_response = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=headers,
        json={
            "title": "Batch test",
            "codice_fiscale": ["RSSMRA80A01H501Z"],
            "filters": {"anno_from": 2022, "anno_to": 2023},
            "template_path": "/tmp/template.docx",
            "notes": "test",
        },
    )
    assert create_response.status_code == 200
    batch_payload = create_response.json()
    assert batch_payload["status"] == "generated"
    assert batch_payload["items_total"] == 1
    assert batch_payload["items_generated"] == 1
    assert batch_payload["items"][0]["status"] == "generated"
    assert batch_payload["items"][0]["download_url"].endswith("/download")
    generated_path = Path(batch_payload["items"][0]["generated_document_path"])
    assert generated_path.name == "RSSMRA80A01H501Z_avviso_sollecito_2022-2023.pdf"
    assert generated_path.exists()

    list_response = client.get("/ruolo/tributi/solleciti/batches", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    detail_response = client.get(f"/ruolo/tributi/solleciti/batches/{batch_payload['id']}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["items"][0]["codice_fiscale"] == "RSSMRA80A01H501Z"

    download_response = client.get(batch_payload["items"][0]["download_url"], headers=headers)
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("application/pdf")

    generated_path.unlink()
    missing_file_response = client.get(batch_payload["items"][0]["download_url"], headers=headers)
    assert missing_file_response.status_code == 404
    assert missing_file_response.json()["detail"] == "Documento sollecito non trovato"


def test_tributi_reminder_batch_uploads_and_downloads_remote_nas_documents(monkeypatch: pytest.MonkeyPatch) -> None:
    tax_code = "RSSMRA80A01H501Z"
    remote_root = f"/volume1/Settore Catasto/ARCHIVIO/R/Rossi_Mario_{tax_code}"
    db = TestingSessionLocal()
    subject = AnagraficaSubject(source_name_raw="ROSSI MARIO", nas_folder_path=remote_root, nas_folder_letter="R")
    db.add(subject)
    db.flush()
    db.add(AnagraficaPerson(subject_id=subject.id, cognome="ROSSI", nome="MARIO", codice_fiscale=tax_code))
    subject_id = subject.id
    db.commit()
    db.close()
    seed_avviso(amount=100.0, anno=2025, subject_id=subject_id)

    class FakeNasClient:
        def __init__(self) -> None:
            self.directories: list[str] = []
            self.uploaded: dict[str, bytes] = {}
            self.closed = False

        def ensure_directory(self, path: str) -> None:
            self.directories.append(path)

        def upload_local_file(self, local_path: str, remote_path: str) -> None:
            self.uploaded[remote_path] = Path(local_path).read_bytes()

        def download_file(self, path: str) -> bytes:
            return self.uploaded[path]

        def close(self) -> None:
            self.closed = True

    fake_nas = FakeNasClient()

    def fake_generate_pdf(_payload: dict, *, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.4 remote")

    monkeypatch.setattr("app.modules.ruolo.tributi_repositories.get_nas_client", lambda: fake_nas)
    monkeypatch.setattr("app.modules.ruolo.tributi_repositories.generate_batch_reminder_pdf", fake_generate_pdf)
    headers = auth_headers()

    response = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=headers,
        json={"codice_fiscale": [tax_code], "filters": {"anno_from": 2025, "anno_to": 2025}},
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    remote_path = item["generated_document_path"]
    assert item["status"] == "generated"
    assert remote_path == f"{remote_root}/solleciti/{tax_code}_avviso_sollecito_2025.pdf"
    assert fake_nas.directories == [f"{remote_root}/solleciti"]
    assert fake_nas.uploaded[remote_path] == b"%PDF-1.4 remote"

    download_response = client.get(item["download_url"], headers=headers)
    assert download_response.status_code == 200
    assert download_response.content == b"%PDF-1.4 remote"
    assert download_response.headers["content-type"].startswith("application/pdf")
    assert fake_nas.closed is True


def test_tributi_reminder_batch_uploads_remote_docx_when_libreoffice_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    tax_code = "VRDLGI80A01H501X"
    remote_root = f"/volume1/Settore Catasto/ARCHIVIO/V/Verdi_Luigi_{tax_code}"
    db = TestingSessionLocal()
    subject = AnagraficaSubject(source_name_raw="VERDI LUIGI", nas_folder_path=remote_root, nas_folder_letter="V")
    db.add(subject)
    db.flush()
    db.add(AnagraficaPerson(subject_id=subject.id, cognome="VERDI", nome="LUIGI", codice_fiscale=tax_code))
    subject_id = subject.id
    db.commit()
    db.close()
    seed_avviso(amount=90.0, tax_code=tax_code, nominativo="VERDI LUIGI", anno=2025, subject_id=subject_id)

    class FakeNasClient:
        uploaded: dict[str, bytes] = {}

        def ensure_directory(self, _path: str) -> None:
            return None

        def upload_local_file(self, local_path: str, remote_path: str) -> None:
            self.uploaded[remote_path] = Path(local_path).read_bytes()

        def close(self) -> None:
            raise RuntimeError("close ignored")

    def missing_libreoffice(_payload: dict, *, output_path: Path) -> None:
        raise RuntimeError("LibreOffice non trovato: impossibile convertire il sollecito in PDF")

    monkeypatch.setattr("app.modules.ruolo.tributi_repositories.get_nas_client", lambda: FakeNasClient())
    monkeypatch.setattr("app.modules.ruolo.tributi_repositories.generate_batch_reminder_pdf", missing_libreoffice)
    headers = auth_headers()

    response = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=headers,
        json={"codice_fiscale": [tax_code], "filters": {"anno_from": 2025, "anno_to": 2025}},
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    remote_docx_path = f"{remote_root}/solleciti/{tax_code}_avviso_sollecito_2025.docx"
    assert item["status"] == "generated_docx"
    assert item["generated_document_path"] == remote_docx_path
    assert FakeNasClient.uploaded[remote_docx_path].startswith(b"PK")


def test_tributi_reminder_batch_tracks_remote_docx_upload_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    tax_code = "BNCLGU80A01H501Y"
    remote_root = f"/volume1/Settore Catasto/ARCHIVIO/B/Bianchi_Luigi_{tax_code}"
    db = TestingSessionLocal()
    subject = AnagraficaSubject(source_name_raw="BIANCHI LUIGI", nas_folder_path=remote_root, nas_folder_letter="B")
    db.add(subject)
    db.flush()
    db.add(AnagraficaPerson(subject_id=subject.id, cognome="BIANCHI", nome="LUIGI", codice_fiscale=tax_code))
    subject_id = subject.id
    db.commit()
    db.close()
    seed_avviso(amount=90.0, tax_code=tax_code, nominativo="BIANCHI LUIGI", anno=2025, subject_id=subject_id)

    class FailingNasClient:
        def ensure_directory(self, _path: str) -> None:
            return None

        def upload_local_file(self, _local_path: str, _remote_path: str) -> None:
            raise RuntimeError("NAS upload non disponibile")

    def missing_libreoffice(_payload: dict, *, output_path: Path) -> None:
        raise RuntimeError("LibreOffice non trovato: impossibile convertire il sollecito in PDF")

    monkeypatch.setattr("app.modules.ruolo.tributi_repositories.get_nas_client", lambda: FailingNasClient())
    monkeypatch.setattr("app.modules.ruolo.tributi_repositories.generate_batch_reminder_pdf", missing_libreoffice)
    headers = auth_headers()

    response = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=headers,
        json={"codice_fiscale": [tax_code], "filters": {"anno_from": 2025, "anno_to": 2025}},
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["status"] == "failed"
    assert item["error_detail"] == "NAS upload non disponibile"
    assert item["download_url"] is None


def test_tributi_reminder_batch_handles_partial_and_generation_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    subject_id = seed_subject_with_nas(tmp_path)
    seed_avviso(amount=100.0, anno=2024, subject_id=subject_id)
    seed_avviso(amount=90.0, tax_code="BNCLGU80A01H501Y", nominativo="BIANCHI LUIGI", anno=2024)

    def fake_generate_batch_reminder_pdf(payload: dict, *, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.4 fake")
        assert Path(payload["template_path"]).name == "Avviso_Sollecito_Template.docx"
        assert Path(payload["template_path"]).exists()

    monkeypatch.setattr(
        "app.modules.ruolo.tributi_repositories.generate_batch_reminder_pdf",
        fake_generate_batch_reminder_pdf,
    )
    headers = auth_headers()
    partial_response = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=headers,
        json={
            "codice_fiscale": ["RSSMRA80A01H501Z", "BNCLGU80A01H501Y"],
            "filters": {"anno_from": 2024, "anno_to": 2024},
        },
    )
    assert partial_response.status_code == 200
    assert partial_response.json()["status"] == "partial_failed"

    def failing_generate_batch_reminder_pdf(payload: dict, *, output_path: Path) -> None:
        raise RuntimeError("NAS non scrivibile")

    monkeypatch.setattr(
        "app.modules.ruolo.tributi_repositories.generate_batch_reminder_pdf",
        failing_generate_batch_reminder_pdf,
    )
    failed_response = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=headers,
        json={"codice_fiscale": ["RSSMRA80A01H501Z"], "filters": {"anno_from": "bad", "anno_to": ""}},
    )
    assert failed_response.status_code == 200
    failed_payload = failed_response.json()
    assert failed_payload["status"] == "failed"
    assert failed_payload["items"][0]["error_detail"] == "NAS non scrivibile"


def test_tributi_reminder_batch_falls_back_to_docx_when_libreoffice_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject_id = seed_subject_with_nas(tmp_path)
    seed_avviso(amount=100.0, anno=2024, subject_id=subject_id)

    def missing_libreoffice(_payload: dict, *, output_path: Path) -> None:
        raise RuntimeError("LibreOffice non trovato: impossibile convertire il sollecito in PDF")

    monkeypatch.setattr(
        "app.modules.ruolo.tributi_repositories.generate_batch_reminder_pdf",
        missing_libreoffice,
    )
    headers = auth_headers()
    response = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=headers,
        json={"codice_fiscale": ["RSSMRA80A01H501Z"], "filters": {"anno_from": 2024, "anno_to": 2024}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "generated"
    assert payload["items_generated"] == 1
    item = payload["items"][0]
    assert item["status"] == "generated_docx"
    assert item["generated_document_path"].endswith(".docx")
    assert item["error_detail"] == "LibreOffice non disponibile: generato DOCX scaricabile senza preview PDF"
    download_response = client.get(item["download_url"], headers=headers)
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_tributi_reminder_candidates_resolve_subject_from_person_and_company(tmp_path: Path) -> None:
    person_subject_id = seed_subject_with_nas(tmp_path, tax_code="VRDLGI80A01H501X")
    db = TestingSessionLocal()
    company_subject = AnagraficaSubject(
        source_name_raw="ACME SRL",
        nas_folder_path=str(tmp_path / "archivio" / "12345678901"),
        nas_folder_letter="A",
    )
    db.add(company_subject)
    db.flush()
    db.add(
        AnagraficaCompany(
            subject_id=company_subject.id,
            ragione_sociale="ACME SRL",
            partita_iva="12345678901",
            codice_fiscale="12345678901",
        )
    )
    db.commit()
    company_subject_id = company_subject.id
    db.close()

    seed_avviso(amount=50.0, tax_code="VRDLGI80A01H501X", nominativo="VERDI LUIGI", anno=2024)
    seed_avviso(amount=75.0, tax_code="12345678901", nominativo="ACME SRL", anno=2024)

    response = client.get("/ruolo/tributi/solleciti/candidates?q=VERDI", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["subject_id"] == str(person_subject_id)
    assert payload["items"][0]["has_nas_folder"] is True

    company_response = client.get("/ruolo/tributi/solleciti/candidates?comune=NO_MATCH&codice_fiscale=12345678901", headers=auth_headers())
    assert company_response.status_code == 200
    assert company_response.json()["total"] == 0

    company_response = client.get("/ruolo/tributi/solleciti/candidates?codice_fiscale=12345678901", headers=auth_headers())
    assert company_response.status_code == 200
    assert company_response.json()["items"][0]["subject_id"] == str(company_subject_id)


def test_tributi_reminder_candidates_skip_non_normalisable_tax_code_and_promote_group_subject(tmp_path: Path) -> None:
    subject_id = seed_subject_with_nas(tmp_path, tax_code="MSTGNN80A01H501W")
    seed_avviso(amount=30.0, tax_code="!!!", nominativo="CODICE ERRATO", anno=2024)
    seed_avviso(amount=20.0, tax_code="MSTGNN80A01H501W", nominativo="MISTO GIOVANNI", anno=2021, subject_id=subject_id)
    seed_avviso(amount=40.0, tax_code="MSTGNN80A01H501W", nominativo="MISTO GIOVANNI", anno=2022)
    seed_avviso(amount=60.0, tax_code="MSTGNN80A01H501W", nominativo="MISTO GIOVANNI", anno=2023, subject_id=subject_id)

    response = client.get("/ruolo/tributi/solleciti/candidates", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["codice_fiscale"] == "MSTGNN80A01H501W"
    assert payload["items"][0]["subject_id"] == str(subject_id)
    assert payload["items"][0]["years"] == [2022, 2023]

    pre_2022_response = client.get(
        "/ruolo/tributi/solleciti/candidates?codice_fiscale=MSTGNN80A01H501W&anno_from=2020&anno_to=2021",
        headers=auth_headers(),
    )
    assert pre_2022_response.status_code == 200
    assert pre_2022_response.json()["total"] == 0


def test_tributi_batch_document_generation_helpers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "display_name": "ROSSI MARIO",
        "codice_fiscale": "RSSMRA80A01H501Z",
        "years": [2022, 2024],
        "due_amount": "250.00 EUR",
        "paid_amount": "40.00 EUR",
        "saldo_amount": "210.00 EUR",
        "template_path": "/tmp/template.docx",
        "generated_at": "2026-07-22T00:00:00Z",
        "avvisi": [
            {
                "codice_cnc": "CNC-001",
                "anno_tributario": 2022,
                "domicilio_raw": "VIA TEST 1",
                "residenza_raw": "09170 ORISTANO (OR)",
                "importo_totale_0648": 80,
                "importo_totale_0985": 20,
                "importo_totale_0668": 0,
                "importo_totale_euro": "100.00 EUR",
                "paid_amount": "40.00 EUR",
                "saldo_amount": "60.00 EUR",
                "partite": [
                    {
                        "codice_partita": "000000268/00000",
                        "comune_nome": "URAS",
                        "importo_0648": "100.00 EUR",
                        "importo_0985": None,
                        "importo_0668": None,
                        "particelle": [{"foglio": "10", "particella": "20", "coltura": "SEMINATIVO"}],
                    }
                ],
            },
            {
                "codice_cnc": "CNC-002",
                "anno_tributario": 2024,
                "domicilio_raw": "VIA TEST 1",
                "residenza_raw": "09170 ORISTANO (OR)",
                "importo_totale_0648": 30,
                "importo_totale_0985": 10,
                "importo_totale_0668": 10,
                "importo_totale_euro": "150.00 EUR",
                "paid_amount": None,
                "saldo_amount": "150.00 EUR",
                "partite": [],
            },
        ],
    }
    docx_path = tmp_path / "batch.docx"
    generate_batch_reminder_docx(payload, output_path=docx_path)
    archive = ZipFile(docx_path)
    document_xml = archive.read("word/document.xml").decode("utf-8")
    assert "Partitario" in document_xml
    assert "Partita 000000268/00000" in document_xml

    template_path = tmp_path / "template.docx"
    template_document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        "<w:p><w:r><w:t>«Denominazione»</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>«CodFiscale»</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>«INDIRIZZO»</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>«CAP» «CITTA» «PROVINCIA»</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>«Avviso_n» - «Oggetto_Ruoli»</w:t></w:r></w:p>"
        "<w:tbl>"
        "<w:tr><w:tc><w:p><w:r><w:t>RIEPILOGO (rif avvisi di pagamento «Rif_Ruoli»)</w:t></w:r></w:p></w:tc></w:tr>"
        "<w:tr><w:tc><w:p><w:r><w:t>«Anno_Ruolo»</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>«M_648»</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>«M_985»</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>«M_668»</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>«Riscosso»</w:t></w:r></w:p></w:tc></w:tr>"
        "</w:tbl>"
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr>'
        "</w:body></w:document>"
    )
    with ZipFile(template_path, "w") as template_archive:
        template_archive.writestr("word/document.xml", template_document_xml)

    templated_docx_path = tmp_path / "templated.docx"
    generate_batch_reminder_docx({**payload, "template_path": str(template_path)}, output_path=templated_docx_path)
    templated_xml = ZipFile(templated_docx_path).read("word/document.xml").decode("utf-8")
    assert "ROSSI MARIO" in templated_xml
    assert "RSSMRA80A01H501Z" in templated_xml
    assert "VIA TEST 1" in templated_xml
    assert "09170 ORISTANO OR" in templated_xml
    assert "CNC-001, CNC-002 - Tributi Consortili anni 2022 e 2024" in templated_xml
    assert "RIEPILOGO (rif avvisi di pagamento 2022: CNC-001; 2024: CNC-002)" in templated_xml
    assert "Ruolo 2022" in templated_xml
    assert "Ruolo 2024" in templated_xml
    assert "80,00" in templated_xml
    assert "30,00" in templated_xml
    assert templated_xml.count("Ruolo ") == 2
    assert "Partitario" in templated_xml

    no_section_template_path = tmp_path / "template_no_section.docx"
    no_section_document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>«Complessivo»</w:t></w:r></w:p></w:body></w:document>"
    )
    with ZipFile(no_section_template_path, "w") as template_archive:
        template_archive.writestr("word/document.xml", no_section_document_xml)

    defensive_docx_path = tmp_path / "templated_defensive.docx"
    generate_batch_reminder_docx(
        {
            **payload,
            "saldo_amount": "not-money",
            "template_path": str(no_section_template_path),
            "avvisi": [{**payload["avvisi"][0], "anno_tributario": "bad"}],
        },
        output_path=defensive_docx_path,
    )
    defensive_xml = ZipFile(defensive_docx_path).read("word/document.xml").decode("utf-8")
    assert "0,00" in defensive_xml
    assert "Partitario" in defensive_xml

    output_pdf = tmp_path / "output.pdf"

    def fake_convert_docx_to_pdf(docx_path: Path, *, output_dir: Path, libreoffice_binary: str | None = None) -> Path:
        converted = output_dir / f"{docx_path.stem}.pdf"
        converted.write_bytes(b"%PDF-1.4 converted")
        return converted

    monkeypatch.setattr(
        "app.modules.ruolo.services.tributi_reminder_service.convert_docx_to_pdf",
        fake_convert_docx_to_pdf,
    )
    generate_batch_reminder_pdf(payload, output_path=output_pdf)
    assert output_pdf.read_bytes() == b"%PDF-1.4 converted"


def test_tributi_batch_pdf_conversion_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docx_path = tmp_path / "source.docx"
    docx_path.write_bytes(b"docx")
    monkeypatch.setattr("app.modules.ruolo.services.tributi_reminder_service.shutil.which", lambda _name: None)
    with pytest.raises(RuntimeError, match="LibreOffice non trovato"):
        convert_docx_to_pdf(docx_path, output_dir=tmp_path)

    class Completed:
        returncode = 1
        stderr = "errore conversione"
        stdout = ""

    monkeypatch.setattr("app.modules.ruolo.services.tributi_reminder_service.shutil.which", lambda _name: "/usr/bin/libreoffice")
    monkeypatch.setattr("app.modules.ruolo.services.tributi_reminder_service.subprocess.run", lambda *_args, **_kwargs: Completed())
    with pytest.raises(RuntimeError, match="errore conversione"):
        convert_docx_to_pdf(docx_path, output_dir=tmp_path)

    class CompletedOk:
        returncode = 0
        stderr = ""
        stdout = ""

    monkeypatch.setattr("app.modules.ruolo.services.tributi_reminder_service.subprocess.run", lambda *_args, **_kwargs: CompletedOk())
    with pytest.raises(RuntimeError, match="senza file"):
        convert_docx_to_pdf(docx_path, output_dir=tmp_path)

    def successful_run(args: list[str], **_kwargs: object) -> CompletedOk:
        output_dir = Path(args[5])
        source = Path(args[6])
        (output_dir / f"{source.stem}.pdf").write_bytes(b"%PDF-1.4")
        return CompletedOk()

    monkeypatch.setattr("app.modules.ruolo.services.tributi_reminder_service.subprocess.run", successful_run)
    assert convert_docx_to_pdf(docx_path, output_dir=tmp_path).exists()


def test_tributi_reminder_service_helper_fallbacks() -> None:
    malformed_with_section = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>base</w:t></w:r></w:p><w:sectPr"
    )
    malformed_without_section = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>base</w:t></w:r></w:p></w:body>"
    )
    partitario_xml = "<w:p><w:r><w:t>Partitario</w:t></w:r></w:p>"
    assert "Partitario" in reminder_service._append_partitario_xml(malformed_with_section, partitario_xml)
    assert "Partitario" in reminder_service._append_partitario_xml(malformed_without_section, partitario_xml)

    xml_without_body = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"></w:document>'
    )
    assert reminder_service._append_partitario_xml(xml_without_body, partitario_xml) == xml_without_body

    assert reminder_service._expand_yearly_summary_rows("<bad-xml", [{"Anno_Ruolo": "Ruolo 2022"}]) == "<bad-xml"
    assert reminder_service._sorted_payload_years({}, {2025: {"codice_cnc": "CNC-1"}}) == [2025]
    assert reminder_service._role_subject_label([]) == "Tributi Consortili"
    assert reminder_service._yearly_reference_summary({2025: {"codice_cnc": "-"}}) == "-"
    assert reminder_service._join_human_list([]) == ""
    assert reminder_service._join_human_list(["2025"]) == "2025"
    assert reminder_service._join_human_list(["2022", "2023", "2024"]) == "2022, 2023 e 2024"


def test_tributi_reminder_batch_tracks_missing_nas_and_missing_resources() -> None:
    seed_avviso(amount=80.0, tax_code="BNCLGU80A01H501Y", nominativo="BIANCHI LUIGI", anno=2023)
    headers = auth_headers()

    create_response = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=headers,
        json={"codice_fiscale": ["BNCLGU80A01H501Y"], "filters": {"anno_from": 2023, "anno_to": 2023}},
    )
    assert create_response.status_code == 200
    payload = create_response.json()
    assert payload["status"] == "failed"
    assert payload["items_failed"] == 1
    assert payload["items"][0]["error_detail"] == "Cartella archivio NAS mancante per l'utenza"
    assert payload["items"][0]["download_url"] is None
    failed_item_id = payload["items"][0]["id"]
    assert client.get(f"/ruolo/tributi/solleciti/items/{failed_item_id}/download", headers=headers).status_code == 404

    empty_response = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=headers,
        json={"codice_fiscale": ["UNKNOWN"], "filters": {"anno_from": 2023}},
    )
    assert empty_response.status_code == 422

    missing_id = uuid4()
    assert client.get(f"/ruolo/tributi/solleciti/batches/{missing_id}", headers=headers).status_code == 404
    assert client.get(f"/ruolo/tributi/solleciti/items/{missing_id}/download", headers=headers).status_code == 404


def test_tributi_reminder_batch_derives_missing_subject_nas_folder_with_truncated_company_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_root = tmp_path / "archivio"
    monkeypatch.setattr(
        "app.modules.utenze.services.nas_path_service.get_settings",
        lambda: SimpleNamespace(utenze_nas_archive_root=str(archive_root), anagrafica_nas_archive_root=str(archive_root)),
    )

    tax_code = "00050540384"
    long_company_name = (
        "Societa Per La Bonifica Dei Terreni Ferraresi E Per Imprese Agricole S.P.A. "
        "Societa Agricola Con Denominazione Operativa Molto Lunga"
    )
    db = TestingSessionLocal()
    subject = AnagraficaSubject(
        source_name_raw=long_company_name,
        nas_folder_path=None,
        nas_folder_letter="S",
    )
    db.add(subject)
    db.flush()
    db.add(
        AnagraficaCompany(
            subject_id=subject.id,
            ragione_sociale=long_company_name,
            partita_iva=tax_code,
            codice_fiscale=None,
        )
    )
    subject_id = subject.id
    db.commit()
    db.close()
    seed_avviso(amount=120.0, tax_code=tax_code, nominativo=long_company_name, anno=2025, subject_id=subject_id)

    def fake_generate_batch_reminder_pdf(payload: dict, *, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.4 fake")

    monkeypatch.setattr(
        "app.modules.ruolo.tributi_repositories.generate_batch_reminder_pdf",
        fake_generate_batch_reminder_pdf,
    )
    headers = auth_headers()
    response = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=headers,
        json={"codice_fiscale": [tax_code], "filters": {"anno_from": 2025, "anno_to": 2025}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "generated"
    generated_path = Path(payload["items"][0]["generated_document_path"])
    assert generated_path.exists()
    assert generated_path.parent.name == "solleciti"
    assert generated_path.parent.parent.parent == archive_root / "S"
    assert generated_path.parent.parent.name.endswith(f"_{tax_code}")
    assert len(generated_path.parent.parent.name) <= 96
    assert "Denominazione Operativa Molto Lunga" not in generated_path.parent.parent.name

    db = TestingSessionLocal()
    refreshed_subject = db.get(AnagraficaSubject, subject_id)
    assert refreshed_subject is not None
    assert refreshed_subject.nas_folder_path == str(generated_path.parent.parent)
    assert refreshed_subject.nas_folder_letter == "S"
    db.close()


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


def test_tributi_reminder_download_reads_remote_nas_document_and_handles_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    avviso_id = seed_avviso(amount=100.0)
    remote_path = "/volume1/Settore Catasto/ARCHIVIO/R/Rossi_Mario_RSSMRA80A01H501Z/solleciti/legacy.docx"
    missing_remote_path = "/volume1/Settore Catasto/ARCHIVIO/R/Rossi_Mario_RSSMRA80A01H501Z/solleciti/missing.docx"
    db = TestingSessionLocal()
    reminder = RuoloTributiReminder(
        avviso_id=UUID(avviso_id),
        status="generated",
        generated_document_path=remote_path,
        generated_at=datetime.now(timezone.utc),
    )
    missing_reminder = RuoloTributiReminder(
        avviso_id=UUID(avviso_id),
        status="generated",
        generated_document_path=missing_remote_path,
        generated_at=datetime.now(timezone.utc),
    )
    db.add_all([reminder, missing_reminder])
    db.commit()
    reminder_id = reminder.id
    missing_reminder_id = missing_reminder.id
    db.close()

    class FakeNasClient:
        def download_file(self, path: str) -> bytes:
            if path == remote_path:
                return b"remote docx"
            raise RuntimeError("Documento remoto non trovato")

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.modules.ruolo.tributi_repositories.get_nas_client", lambda: FakeNasClient())
    headers = auth_headers()

    response = client.get(f"/ruolo/tributi/reminders/{reminder_id}/download", headers=headers)
    assert response.status_code == 200
    assert response.content == b"remote docx"
    assert response.headers["content-disposition"] == "attachment; filename*=UTF-8''legacy.docx"

    missing_response = client.get(f"/ruolo/tributi/reminders/{missing_reminder_id}/download", headers=headers)
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "Documento sollecito non trovato"


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
