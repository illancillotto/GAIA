from collections.abc import Generator
from pathlib import Path
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.catasto import CatastoDocument
from app.modules.utenze.router import get_anagrafica_import_service
from app.modules.utenze.models import (
    AnagraficaDocument,
    AnagraficaImportJob,
    AnagraficaImportJobItem,
    AnagraficaImportJobItemStatus,
    AnagraficaImportJobStatus,
    AnagraficaSubject,
)
from app.modules.utenze.services.import_service import (
    AnagraficaImportPreviewService,
    prepare_registry_import_jobs_for_recovery,
    process_registry_bulk_import_job,
)


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


class FakeNasConnector:
    def run_command(self, command: str) -> str:
        outputs = {
            "find '/archive' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": "/archive/O",
            "find '/archive/O' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": (
                "/archive/O/Obinu_Santina_BNOSTN34L64I743F"
            ),
            (
                "find '/archive/O/Obinu_Santina_BNOSTN34L64I743F' -type f 2>/dev/null | sort"
            ): "/archive/O/Obinu_Santina_BNOSTN34L64I743F/INGIUNZIONE-2024.pdf",
        }
        return outputs.get(command, "")

    def download_file(self, path: str) -> bytes:
        if path.endswith("INGIUNZIONE-2024.pdf"):
            return b"%PDF-1.4 fake pdf bytes"
        raise RuntimeError(f"Unexpected download path: {path}")


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_anagrafica_import_service] = lambda: AnagraficaImportPreviewService(
        FakeNasConnector(),
        archive_root="/archive",
    )
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def create_user(username: str, *, module_utenze: bool) -> None:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username=username,
        email=f"{username}@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_accessi=True,
        module_utenze=module_utenze,
    )
    db.add(user)
    db.commit()
    db.close()


def login(username: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": "secret123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_import_preview_returns_structured_payload() -> None:
    create_user("alice", module_utenze=True)
    token = login("alice")

    response = client.post(
        "/utenze/import/preview",
        json={"letter": "o"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["letter"] == "O"
    assert body["total_folders"] == 1
    assert body["parsed_subjects"] == 1
    assert body["total_documents"] == 1
    assert body["subjects"][0]["subject_type"] == "person"
    assert body["subjects"][0]["documents"][0]["doc_type"] == "ingiunzione"


def test_import_preview_without_letter_scans_full_archive() -> None:
    create_user("alice_all", module_utenze=True)
    token = login("alice_all")

    response = client.post(
        "/utenze/import/preview",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["letter"] == "ALL"
    assert body["total_folders"] == 1
    assert body["parsed_subjects"] == 1


def test_import_preview_requires_module_flag() -> None:
    create_user("bob", module_utenze=False)
    token = login("bob")

    response = client.post(
        "/utenze/import/preview",
        json={"letter": "O"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_import_preview_validates_letter() -> None:
    create_user("carla", module_utenze=True)
    token = login("carla")

    response = client.post(
        "/utenze/import/preview",
        json={"letter": "12"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_import_run_persists_job_and_returns_summary() -> None:
    create_user("dario", module_utenze=True)
    token = login("dario")

    response = client.post(
        "/utenze/import/run",
        json={"letter": "O"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "completed"
    assert body["total_folders"] == 1
    assert body["imported_ok"] == 1

    jobs_response = client.get("/utenze/import/jobs", headers={"Authorization": f"Bearer {token}"})
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert len(jobs) == 1
    assert jobs[0]["job_id"] == body["job_id"]
    assert jobs[0]["items"][0]["payload_json"]["source_name_raw"] == "Obinu_Santina_BNOSTN34L64I743F"

    detail_response = client.get(
        f"/utenze/import/jobs/{body['job_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "completed"


def test_import_run_without_letter_imports_full_archive() -> None:
    create_user("dario_all", module_utenze=True)
    token = login("dario_all")

    response = client.post(
        "/utenze/import/run",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["letter"] == "ALL"
    assert body["total_folders"] == 1


def test_import_job_detail_includes_items_and_resume_endpoint() -> None:
    create_user("franco", module_utenze=True)
    token = login("franco")
    headers = {"Authorization": f"Bearer {token}"}

    run_response = client.post("/utenze/import/run", json={}, headers=headers)
    assert run_response.status_code == 202
    job_id = run_response.json()["job_id"]

    detail_response = client.get(f"/utenze/import/jobs/{job_id}", headers=headers)
    assert detail_response.status_code == 200
    completed_job = detail_response.json()
    assert completed_job["items"]
    assert completed_job["items"][0]["folder_name"] == "Obinu_Santina_BNOSTN34L64I743F"
    assert completed_job["items"][0]["payload_json"]["documents"][0]["filename"] == "INGIUNZIONE-2024.pdf"

    resume_response = client.post(f"/utenze/import/jobs/{job_id}/resume", headers=headers)
    assert resume_response.status_code == 409


    create_user("csv_user", module_utenze=True)
    token = login("csv_user")
    headers = {"Authorization": f"Bearer {token}"}

    csv_payload = (
        "Codice Fiscale;Cognome;Nome;Sesso;Data_Nascita;Com_Nascita;Com_Residenza;CAP;PR;Indirizzo_Residenza;Variaz_Anagr;STATO;Decesso\n"
        "RSSMRA80A01H501Z;Rossi;Mario;M;01/01/1980;Oristano;Oristano;09170;OR;Via Roma 1;;ATTIVO;\n"
    )

    import_response = client.post(
        "/utenze/subjects/import-csv",
        headers=headers,
        files={"file": ("anagrafica.csv", csv_payload.encode("utf-8"), "text/csv")},
    )
    assert import_response.status_code == 200
    payload = import_response.json()
    assert payload["total_rows"] == 1
    assert payload["created_subjects"] == 1
    assert payload["updated_subjects"] == 0

    list_response = client.get("/utenze/subjects?search=RSSMRA80A01H501Z", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    subject_id = list_response.json()["items"][0]["id"]

    detail_response = client.get(f"/utenze/subjects/{subject_id}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["person"]["cognome"] == "Rossi"
    assert detail["person"]["data_nascita"] == "1980-01-01"
    assert detail["person"]["comune_residenza"] == "Oristano (OR)"

    csv_update_payload = (
        "Codice Fiscale;Cognome;Nome;Sesso;Data_Nascita;Com_Nascita;Com_Residenza;CAP;PR;Indirizzo_Residenza;Variaz_Anagr;STATO;Decesso\n"
        "RSSMRA80A01H501Z;Rossi;Mario;M;01/01/1980;Oristano;Cabras;09072;OR;Via Diaz 3;Cambio residenza;ATTIVO;\n"
    )
    update_response = client.post(
        "/utenze/subjects/import-csv",
        headers=headers,
        files={"file": ("anagrafica.csv", csv_update_payload.encode("utf-8"), "text/csv")},
    )
    assert update_response.status_code == 200
    assert update_response.json()["created_subjects"] == 0
    assert update_response.json()["updated_subjects"] == 1

    updated_detail_response = client.get(f"/utenze/subjects/{subject_id}", headers=headers)
    assert updated_detail_response.status_code == 200
    updated_detail = updated_detail_response.json()
    assert updated_detail["person"]["comune_residenza"] == "Cabras (OR)"
    assert "[CSV IMPORT]" in (updated_detail["person"]["note"] or "")


def test_csv_import_handles_duplicate_codice_fiscale_rows_without_500() -> None:
    create_user("csv_duplicates", module_utenze=True)
    token = login("csv_duplicates")
    headers = {"Authorization": f"Bearer {token}"}

    csv_payload = (
        "Codice Fiscale;Cognome;Nome;Sesso;Data_Nascita;Com_Nascita;Com_Residenza;CAP;PR;Indirizzo_Residenza;Variaz_Anagr;STATO;Decesso\n"
        "SRRPQL38P11I743U;Serra;Pasquale;M;11/09/1938;Simaxis;Ollastra;09088;OR;Via Marconi 33;;ATTIVO;\n"
        "SRRPQL38P11I743U;Serra;Pasquale;M;11/09/1938;Simaxis;Simaxis;09088;OR;Via Marconi 33;Aggiornamento;ATTIVO;\n"
    )

    response = client.post(
        "/utenze/subjects/import-csv",
        headers=headers,
        files={"file": ("anagrafica.csv", csv_payload.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 2
    assert payload["created_subjects"] == 1
    assert payload["updated_subjects"] == 1
    assert payload["skipped_rows"] == 0

    detail_search = client.get("/utenze/subjects?search=SRRPQL38P11I743U", headers=headers)
    assert detail_search.status_code == 200
    assert detail_search.json()["total"] == 1


def test_csv_import_rejects_missing_required_headers() -> None:
    create_user("csv_invalid", module_utenze=True)
    token = login("csv_invalid")

    csv_payload = "Cognome;Nome\nRossi;Mario\n"
    response = client.post(
        "/utenze/subjects/import-csv",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("anagrafica.csv", csv_payload.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 422


def test_subjects_crud_search_and_stats() -> None:
    create_user("eva", module_utenze=True)
    token = login("eva")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/utenze/subjects",
        headers=headers,
        json={
            "subject_type": "person",
            "source_name_raw": "Rossi_Mario_RSSMRA80A01H501Z",
            "nas_folder_letter": "R",
            "requires_review": False,
            "person": {
                "cognome": "Rossi",
                "nome": "Mario",
                "codice_fiscale": "RSSMRA80A01H501Z",
                "email": "mario.rossi@example.local",
            },
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    subject_id = created["id"]
    assert created["person"]["cognome"] == "Rossi"

    list_response = client.get("/utenze/subjects?search=rossi", headers=headers)
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] >= 1
    assert list_payload["items"][0]["display_name"] == "Rossi Mario"

    detail_response = client.get(f"/utenze/subjects/{subject_id}", headers=headers)
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["person"]["codice_fiscale"] == "RSSMRA80A01H501Z"
    assert len(detail_payload["audit_log"]) == 1
    assert detail_payload["person_snapshots"] == []

    update_response = client.put(
        f"/utenze/subjects/{subject_id}",
        headers=headers,
        json={
            "requires_review": True,
            "person": {
                "cognome": "Rossi",
                "nome": "Mario",
                "codice_fiscale": "RSSMRA80A01H501Z",
                "telefono": "0783123456",
            },
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["requires_review"] is True
    assert updated["person"]["telefono"] == "0783123456"
    assert len(updated["person_snapshots"]) == 1
    assert updated["person_snapshots"][0]["is_capacitas_history"] is False
    assert updated["person_snapshots"][0]["email"] == "mario.rossi@example.local"
    assert updated["person_snapshots"][0]["telefono"] is None

    search_response = client.get("/utenze/search?q=mario", headers=headers)
    assert search_response.status_code == 200
    assert search_response.json()["total"] >= 1

    stats_response = client.get("/utenze/stats", headers=headers)
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["total_subjects"] >= 1
    assert stats["total_persons"] >= 1
    assert "deceased_updates_last_24h" in stats
    assert "deceased_updates_current_month" in stats
    assert "deceased_updates_current_year" in stats
    assert stats["by_letter"]["R"] >= 1

    deactivate_response = client.delete(f"/utenze/subjects/{subject_id}", headers=headers)
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["status"] == "inactive"

    token_search_response = client.get("/utenze/search?q=rossi RSSMRA80A01H501Z", headers=headers)
    assert token_search_response.status_code == 200
    assert token_search_response.json()["total"] >= 1


def test_create_subject_rejects_duplicate_codice_fiscale() -> None:
    create_user("eva_duplicate_cf", module_utenze=True)
    token = login("eva_duplicate_cf")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "subject_type": "person",
        "source_name_raw": "Rossi_Mario_RSSMRA80A01H501Z",
        "nas_folder_letter": "R",
        "requires_review": False,
        "person": {
            "cognome": "Rossi",
            "nome": "Mario",
            "codice_fiscale": "RSSMRA80A01H501Z",
        },
    }

    first_response = client.post("/utenze/subjects", headers=headers, json=payload)
    assert first_response.status_code == 201

    duplicate_response = client.post("/utenze/subjects", headers=headers, json=payload)
    assert duplicate_response.status_code == 409
    assert "codice fiscale" in duplicate_response.json()["detail"].lower()


def test_document_summary_returns_breakdown_and_recent_unclassified() -> None:
    create_user("doc_summary", module_utenze=True)
    token = login("doc_summary")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/utenze/subjects",
        headers=headers,
        json={
            "subject_type": "person",
            "source_name_raw": "Rossi_Mario_RSSMRA80A01H501Z",
            "nas_folder_letter": "R",
            "person": {
                "cognome": "Rossi",
                "nome": "Mario",
                "codice_fiscale": "RSSMRA80A01H501Z",
            },
        },
    )
    assert create_response.status_code == 201
    subject_id = create_response.json()["id"]

    db = TestingSessionLocal()
    try:
        db.add(
            AnagraficaDocument(
                subject_id=uuid.UUID(subject_id),
                doc_type="altro",
                filename="documento-non-classificato.pdf",
                classification_source="auto",
                storage_type="local_upload",
                local_path="/tmp/documento-non-classificato.pdf",
            )
        )
        db.add(
            AnagraficaDocument(
                subject_id=uuid.UUID(subject_id),
                doc_type="visura",
                filename="visura.pdf",
                classification_source="manual",
                storage_type="local_upload",
                local_path="/tmp/visura.pdf",
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/utenze/documents/summary", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_documents"] == 2
    assert payload["documents_unclassified"] == 1
    assert payload["classified_documents"] == 1
    assert any(bucket["doc_type"] == "altro" and bucket["count"] == 1 for bucket in payload["by_doc_type"])
    assert any(bucket["doc_type"] == "visura" and bucket["count"] == 1 for bucket in payload["by_doc_type"])
    assert payload["recent_unclassified"][0]["filename"] == "documento-non-classificato.pdf"
    assert payload["recent_unclassified"][0]["subject_display_name"] == "Rossi Mario"


def test_subject_detail_skips_thumbs_db_documents() -> None:
    create_user("thumbs_filter", module_utenze=True)
    token = login("thumbs_filter")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/utenze/subjects",
        headers=headers,
        json={
            "subject_type": "person",
            "source_name_raw": "Rossi_Mario_RSSMRA80A01H501Z",
            "nas_folder_letter": "R",
            "person": {
                "cognome": "Rossi",
                "nome": "Mario",
                "codice_fiscale": "RSSMRA80A01H501Z",
            },
        },
    )
    assert create_response.status_code == 201
    subject_id = create_response.json()["id"]

    db = TestingSessionLocal()
    try:
        db.add(
            AnagraficaDocument(
                subject_id=uuid.UUID(subject_id),
                doc_type="altro",
                filename="Thumbs.db",
                classification_source="auto",
                storage_type="nas_link",
                nas_path="/archive/R/Rossi_Mario_RSSMRA80A01H501Z/Thumbs.db",
            )
        )
        db.add(
            AnagraficaDocument(
                subject_id=uuid.UUID(subject_id),
                doc_type="visura",
                filename="visura.xlsx",
                classification_source="manual",
                storage_type="local_upload",
                local_path="/tmp/visura.xlsx",
            )
        )
        db.commit()
    finally:
        db.close()

    detail_response = client.get(f"/utenze/subjects/{subject_id}", headers=headers)
    assert detail_response.status_code == 200
    filenames = [item["filename"] for item in detail_response.json()["documents"]]
    assert "Thumbs.db" not in filenames
    assert "visura.xlsx" in filenames


def test_documents_summary_skips_thumbs_db_documents() -> None:
    create_user("thumbs_summary", module_utenze=True)
    token = login("thumbs_summary")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/utenze/subjects",
        headers=headers,
        json={
            "subject_type": "person",
            "source_name_raw": "Verdi_Luca_VRDLCU80A01H501Z",
            "nas_folder_letter": "V",
            "person": {
                "cognome": "Verdi",
                "nome": "Luca",
                "codice_fiscale": "VRDLCU80A01H501Z",
            },
        },
    )
    assert create_response.status_code == 201
    subject_id = create_response.json()["id"]

    db = TestingSessionLocal()
    try:
        db.add(
            AnagraficaDocument(
                subject_id=uuid.UUID(subject_id),
                doc_type="altro",
                filename="Thumbs.db",
                classification_source="auto",
                storage_type="nas_link",
                nas_path="/archive/V/Verdi_Luca_VRDLCU80A01H501Z/Thumbs.db",
            )
        )
        db.add(
            AnagraficaDocument(
                subject_id=uuid.UUID(subject_id),
                doc_type="visura",
                filename="visura-valida.pdf",
                classification_source="manual",
                storage_type="local_upload",
                local_path="/tmp/visura-valida.pdf",
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/utenze/documents/summary", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_documents"] == 1
    assert payload["documents_unclassified"] == 0
    assert payload["classified_documents"] == 1
    assert payload["recent_unclassified"] == []
    assert all(bucket["doc_type"] != "altro" for bucket in payload["by_doc_type"])
    assert any(bucket["doc_type"] == "visura" and bucket["count"] == 1 for bucket in payload["by_doc_type"])


def test_document_update_and_delete() -> None:
    create_user("franco", module_utenze=True)
    token = login("franco")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/utenze/subjects",
        headers=headers,
        json={
            "subject_type": "person",
            "source_name_raw": "Rossi_Mario_RSSMRA80A01H501Z",
            "nas_folder_letter": "R",
            "requires_review": False,
            "person": {
                "cognome": "Rossi",
                "nome": "Mario",
                "codice_fiscale": "RSSMRA80A01H501Z",
            },
        },
    )
    assert create_response.status_code == 201
    subject_id = create_response.json()["id"]

    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "franco").one()
        db.add(
            CatastoDocument(
                user_id=user.id,
                request_id=None,
                comune="Oristano",
                foglio="1",
                particella="2",
                subalterno=None,
                catasto="fabbricati",
                tipo_visura="storica",
                filename="visura.pdf",
                filepath="/catasto/visura.pdf",
                codice_fiscale="RSSMRA80A01H501Z",
            )
        )
        db.add(
            AnagraficaDocument(
                subject_id=uuid.UUID(subject_id),
                doc_type="ingiunzione",
                filename="INGIUNZIONE-2024.pdf",
                nas_path="/archive/R/Rossi_Mario_RSSMRA80A01H501Z/INGIUNZIONE-2024.pdf",
                classification_source="auto",
                storage_type="nas_link",
                mime_type="application/pdf",
            )
        )
        db.commit()
    finally:
        db.close()

    documents_response = client.get(f"/utenze/subjects/{subject_id}/documents", headers=headers)
    assert documents_response.status_code == 200
    documents = documents_response.json()
    assert len(documents) == 1
    document_id = documents[0]["id"]

    detail_response = client.get(f"/utenze/subjects/{subject_id}", headers=headers)
    assert detail_response.status_code == 200
    assert len(detail_response.json()["documents"]) == 1

    patch_response = client.patch(
        f"/utenze/documents/{document_id}",
        headers=headers,
        json={"doc_type": "visura", "notes": "riclassificato"},
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["doc_type"] == "visura"
    assert "riclassificato" in ",".join(patched["warnings"]) or patched["warnings"] == []

    delete_response = client.delete(f"/utenze/documents/{document_id}", headers=headers)
    assert delete_response.status_code == 204

    documents_after_delete = client.get(f"/utenze/subjects/{subject_id}/documents", headers=headers)
    assert documents_after_delete.status_code == 200
    assert documents_after_delete.json() == []


def test_export_and_catasto_correlation() -> None:
    create_user("gina", module_utenze=True)
    token = login("gina")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/utenze/subjects",
        headers=headers,
        json={
          "subject_type": "person",
          "source_name_raw": "Pinna_Giulia_PNNGLI80A01H501Z",
          "nas_folder_letter": "P",
          "person": {
            "cognome": "Pinna",
            "nome": "Giulia",
            "codice_fiscale": "PNNGLI80A01H501Z",
          },
        },
    )
    assert create_response.status_code == 201
    subject_id = create_response.json()["id"]

    db = TestingSessionLocal()
    db.add(
        CatastoDocument(
            user_id=1,
            request_id=None,
            comune="Oristano",
            foglio="12",
            particella="345",
            subalterno="2",
            catasto="Terreni",
            tipo_visura="Sintetica",
            filename="visura-pinna.pdf",
            filepath="/tmp/visura-pinna.pdf",
            file_size=1024,
            codice_fiscale="PNNGLI80A01H501Z",
        )
    )
    db.commit()
    db.close()

    detail_response = client.get(f"/utenze/subjects/{subject_id}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["catasto_documents"]) == 1
    assert detail["catasto_documents"][0]["comune"] == "Oristano"
    assert detail["catasto_documents"][0]["filename"] == "visura-pinna.pdf"

    csv_response = client.get("/utenze/export?format=csv&search=Pinna", headers=headers)
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "display_name" in csv_response.text
    assert "Pinna Giulia" in csv_response.text

    xlsx_response = client.get("/utenze/export?format=xlsx&search=Pinna", headers=headers)
    assert xlsx_response.status_code == 200
    assert xlsx_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_import_single_subject_from_existing_registry_persists_local_file(tmp_path) -> None:
    create_user("henry", module_utenze=True)
    token = login("henry")
    headers = {"Authorization": f"Bearer {token}"}
    original_storage_path = settings.utenze_document_storage_path
    settings.utenze_document_storage_path = str(tmp_path / "utenze-docs")

    try:
        create_response = client.post(
            "/utenze/subjects",
            headers=headers,
            json={
                "subject_type": "person",
                "source_name_raw": "Obinu_Santina_BNOSTN34L64I743F",
                "person": {
                    "cognome": "Obinu",
                    "nome": "Santina",
                    "codice_fiscale": "BNOSTN34L64I743F",
                },
            },
        )
        assert create_response.status_code == 201
        subject_id = create_response.json()["id"]

        import_response = client.post(f"/utenze/subjects/{subject_id}/import-from-nas", headers=headers)
        assert import_response.status_code == 200
        payload = import_response.json()
        assert payload["created_documents"] == 1
        assert payload["matched_folder_name"] == "Obinu_Santina_BNOSTN34L64I743F"

        detail_response = client.get(f"/utenze/subjects/{subject_id}", headers=headers)
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["nas_folder_path"] == "/archive/O/Obinu_Santina_BNOSTN34L64I743F"
        assert len(detail["documents"]) == 1

        db = TestingSessionLocal()
        try:
            document = db.query(AnagraficaDocument).filter(AnagraficaDocument.subject_id == uuid.UUID(subject_id)).one()
            assert document.storage_type == "local_upload"
            assert document.local_path is not None
            assert Path(document.local_path).exists()
            assert Path(document.local_path).read_bytes().startswith(b"%PDF-1.4")
        finally:
            db.close()
    finally:
        settings.utenze_document_storage_path = original_storage_path


def test_subject_nas_candidates_returns_scored_matches() -> None:
    create_user("manual_match", module_utenze=True)
    token = login("manual_match")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/utenze/subjects",
        headers=headers,
        json={
            "subject_type": "person",
            "source_name_raw": "Obinu_Santina_BNOSTN34L64I743F",
            "person": {
                "cognome": "Obinu",
                "nome": "Santina",
                "codice_fiscale": "BNOSTN34L64I743F",
            },
        },
    )
    assert create_response.status_code == 201
    subject_id = create_response.json()["id"]

    candidates_response = client.get(f"/utenze/subjects/{subject_id}/nas-candidates", headers=headers)
    assert candidates_response.status_code == 200
    candidates = candidates_response.json()
    assert len(candidates) >= 1
    assert candidates[0]["folder_name"] == "Obinu_Santina_BNOSTN34L64I743F"
    assert candidates[0]["score"] > 0
    assert candidates[0]["nas_folder_path"] == "/archive/O/Obinu_Santina_BNOSTN34L64I743F"


def test_subject_nas_import_status_uses_identifier_and_reports_missing_subject_in_nas() -> None:
    create_user("nas_status", module_utenze=True)
    token = login("nas_status")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/utenze/subjects",
        headers=headers,
        json={
            "subject_type": "person",
            "source_name_raw": "ATZORI_TOMASA_TZRTMS31L61F840T",
            "person": {
                "cognome": "ATZORI",
                "nome": "TOMASA",
                "codice_fiscale": "TZRTMS31L61F840T",
            },
        },
    )
    assert create_response.status_code == 201
    subject_id = create_response.json()["id"]

    status_response = client.get(f"/utenze/subjects/{subject_id}/nas-import-status", headers=headers)
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["can_import_from_nas"] is False
    assert payload["missing_in_nas"] is True
    assert payload["pending_files_in_nas"] == 0


def test_subject_nas_import_status_ignores_stale_saved_nas_path_with_different_identifier() -> None:
    create_user("nas_stale_path", module_utenze=True)
    token = login("nas_stale_path")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/utenze/subjects",
        headers=headers,
        json={
            "subject_type": "person",
            "source_name_raw": "ATZORI_TOMASA_TZRTMS31L61F840T",
            "nas_folder_path": "/volume1/Settore Catasto/ARCHIVIO/A/Atzori Andrea_Tzrndr62s16g113n",
            "nas_folder_letter": "A",
            "person": {
                "cognome": "ATZORI",
                "nome": "TOMASA",
                "codice_fiscale": "TZRTMS31L61F840T",
            },
        },
    )
    assert create_response.status_code == 201
    subject_id = create_response.json()["id"]

    status_response = client.get(f"/utenze/subjects/{subject_id}/nas-import-status", headers=headers)
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["can_import_from_nas"] is False
    assert payload["missing_in_nas"] is True
    assert payload["matched_folder_path"] is None


def test_subject_nas_import_status_does_not_fallback_to_name_when_primary_identifier_differs() -> None:
    class WrongSurnameOnlyNasConnector:
        def run_command(self, command: str) -> str:
            outputs = {
                "find '/archive/A' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": (
                    "/archive/A/Atzori Andrea_Tzrndr62s16g113n"
                ),
                "find '/archive/A/Atzori Andrea_Tzrndr62s16g113n' -type f 2>/dev/null | sort": (
                    "/archive/A/Atzori Andrea_Tzrndr62s16g113n/INGIUNZIONE-2024.pdf"
                ),
            }
            return outputs.get(command, "")

        def download_file(self, path: str) -> bytes:
            if path.endswith("INGIUNZIONE-2024.pdf"):
                return b"%PDF-1.4 fake pdf bytes"
            raise RuntimeError(f"Unexpected download path: {path}")

    app.dependency_overrides[get_anagrafica_import_service] = lambda: AnagraficaImportPreviewService(
        WrongSurnameOnlyNasConnector(),
        archive_root="/archive",
    )

    create_user("nas_no_name_fallback", module_utenze=True)
    token = login("nas_no_name_fallback")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/utenze/subjects",
        headers=headers,
        json={
            "subject_type": "person",
            "source_name_raw": "ATZORI_TOMASA_TZRTMS31L61F840T",
            "person": {
                "cognome": "ATZORI",
                "nome": "TOMASA",
                "codice_fiscale": "TZRTMS31L61F840T",
            },
        },
    )
    assert create_response.status_code == 201
    subject_id = create_response.json()["id"]

    status_response = client.get(f"/utenze/subjects/{subject_id}/nas-import-status", headers=headers)
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["can_import_from_nas"] is False
    assert payload["missing_in_nas"] is True
    assert payload["matched_folder_path"] is None
    assert payload["total_files_in_nas"] == 0
    assert payload["pending_files_in_nas"] == 0


def test_manual_document_upload_creates_local_document(tmp_path) -> None:
    create_user("manual_upload", module_utenze=True)
    token = login("manual_upload")
    headers = {"Authorization": f"Bearer {token}"}
    original_storage_path = settings.utenze_document_storage_path
    settings.utenze_document_storage_path = str(tmp_path / "utenze-docs")

    try:
      create_response = client.post(
          "/utenze/subjects",
          headers=headers,
          json={
              "subject_type": "person",
              "source_name_raw": "ATZORI_TOMASA_TZRTMS31L61F840T",
              "person": {
                  "cognome": "ATZORI",
                  "nome": "TOMASA",
                  "codice_fiscale": "TZRTMS31L61F840T",
              },
          },
      )
      assert create_response.status_code == 201
      subject_id = create_response.json()["id"]

      upload_response = client.post(
          f"/utenze/subjects/{subject_id}/documents/upload",
          headers=headers,
          files={"file": ("manuale.pdf", b"%PDF-1.4 manual", "application/pdf")},
          data={"doc_type": "visura", "notes": "upload manuale"},
      )
      assert upload_response.status_code == 200
      payload = upload_response.json()
      assert payload["filename"] == "manuale.pdf"
      assert payload["doc_type"] == "visura"

      download_response = client.get(f"/utenze/documents/{payload['id']}/download", headers=headers)
      assert download_response.status_code == 200
      assert download_response.content == b"%PDF-1.4 manual"
      assert download_response.headers["content-type"] == "application/pdf"

      detail_response = client.get(f"/utenze/subjects/{subject_id}", headers=headers)
      assert detail_response.status_code == 200
      assert len(detail_response.json()["documents"]) == 1
    finally:
      settings.utenze_document_storage_path = original_storage_path


def test_manual_document_upload_syncs_to_nas_when_subject_has_nas_path(tmp_path, monkeypatch) -> None:
    create_user("manual_upload_nas", module_utenze=True)
    token = login("manual_upload_nas")
    headers = {"Authorization": f"Bearer {token}"}
    original_storage_path = settings.utenze_document_storage_path
    settings.utenze_document_storage_path = str(tmp_path / "utenze-docs")
    uploaded: dict[str, bytes] = {}

    class FakeNasClient:
        def __init__(self) -> None:
            self.existing_paths = {
                "/volume1/Settore Catasto/ARCHIVIO/A/Atzori_Antonio_TZRNTN56E11B314E/manuale-sync.pdf"
            }

        def ensure_directory(self, path: str) -> None:
            uploaded[f"dir:{path}"] = b""

        def path_exists(self, path: str) -> bool:
            return path in self.existing_paths or path in uploaded

        def upload_file(self, path: str, content: bytes) -> None:
            uploaded[path] = content

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.modules.utenze.services.import_service.get_nas_client", lambda: FakeNasClient())

    try:
        create_response = client.post(
            "/utenze/subjects",
            headers=headers,
            json={
                "subject_type": "person",
                "source_name_raw": "ATZORI_ANTONIO_TZRNTN56E11B314E",
                "nas_folder_path": "/volume1/Settore Catasto/ARCHIVIO/A/Atzori_Antonio_TZRNTN56E11B314E",
                "nas_folder_letter": "A",
                "person": {
                    "cognome": "ATZORI",
                    "nome": "ANTONIO",
                    "codice_fiscale": "TZRNTN56E11B314E",
                },
            },
        )
        assert create_response.status_code == 201
        subject_id = create_response.json()["id"]

        upload_response = client.post(
            f"/utenze/subjects/{subject_id}/documents/upload",
            headers=headers,
            files={"file": ("manuale-sync.pdf", b"%PDF-1.4 manual sync", "application/pdf")},
            data={"doc_type": "visura", "notes": "upload con sync nas"},
        )
        assert upload_response.status_code == 200
        payload = upload_response.json()
        assert payload["filename"] == "manuale-sync.pdf"
        assert payload["nas_path"].endswith("/manuale-sync (1).pdf")

        matching_paths = [path for path in uploaded if path.endswith(".pdf")]
        assert len(matching_paths) == 1
        assert matching_paths[0].endswith("/manuale-sync (1).pdf")
        assert uploaded[matching_paths[0]] == b"%PDF-1.4 manual sync"
    finally:
        settings.utenze_document_storage_path = original_storage_path


def test_bulk_import_from_existing_registry_and_reset(tmp_path) -> None:
    create_user("irene", module_utenze=True)
    token = login("irene")
    headers = {"Authorization": f"Bearer {token}"}
    original_storage_path = settings.utenze_document_storage_path
    settings.utenze_document_storage_path = str(tmp_path / "utenze-docs")

    try:
        create_response = client.post(
            "/utenze/subjects",
            headers=headers,
            json={
                "subject_type": "person",
                "source_name_raw": "Obinu_Santina_BNOSTN34L64I743F",
                "person": {
                    "cognome": "Obinu",
                    "nome": "Santina",
                    "codice_fiscale": "BNOSTN34L64I743F",
                },
            },
        )
        assert create_response.status_code == 201

        bulk_response = client.post("/utenze/import/run-from-subjects", headers=headers)
        assert bulk_response.status_code == 202
        bulk_payload = bulk_response.json()
        assert bulk_payload["letter"] == "REGISTRY"
        assert bulk_payload["status"] == "pending"
        job_id = bulk_payload["job_id"]

        job_detail = client.get(f"/utenze/import/jobs/{job_id}", headers=headers)
        assert job_detail.status_code == 200
        queued_job_payload = job_detail.json()
        assert queued_job_payload["status"] == "pending"
        assert queued_job_payload["items"] == []

        db = TestingSessionLocal()
        try:
            process_registry_bulk_import_job(
                db,
                uuid.UUID(job_id),
                service=AnagraficaImportPreviewService(FakeNasConnector(), archive_root="/archive"),
            )
        finally:
            db.close()

        job_detail = client.get(f"/utenze/import/jobs/{job_id}", headers=headers)
        assert job_detail.status_code == 200
        job_payload = job_detail.json()
        assert job_payload["status"] == "completed"
        assert job_payload["imported_ok"] == 1
        assert job_payload["items"][0]["documents_created"] == 1

        jobs_response = client.get("/utenze/import/jobs", headers=headers)
        assert jobs_response.status_code == 200
        jobs = jobs_response.json()
        assert jobs[0]["letter"] == "REGISTRY"
        assert jobs[0]["items"][0]["nas_folder_path"] == "/archive/O/Obinu_Santina_BNOSTN34L64I743F"

        reset_response = client.post("/utenze/reset", headers=headers, json={"confirm": "RESET UTENZE"})
        assert reset_response.status_code == 200
        reset_payload = reset_response.json()
        assert reset_payload["cleared_subject_links"] == 1
        assert reset_payload["deleted_documents"] == 1
        assert reset_payload["deleted_import_jobs"] >= 1
        assert reset_payload["deleted_storage_files"] == 1

        subjects_after_reset = client.get("/utenze/subjects", headers=headers)
        assert subjects_after_reset.status_code == 200
        assert subjects_after_reset.json()["total"] == 1
        subject_id = subjects_after_reset.json()["items"][0]["id"]
        detail_after_reset = client.get(f"/utenze/subjects/{subject_id}", headers=headers)
        assert detail_after_reset.status_code == 200
        detail_payload = detail_after_reset.json()
        assert detail_payload["documents"] == []
        assert detail_payload["nas_folder_path"] is None
        assert detail_payload["nas_folder_letter"] is None
        assert detail_payload["imported_at"] is None
    finally:
        settings.utenze_document_storage_path = original_storage_path


def test_prepare_registry_import_jobs_for_recovery_requeues_processing_items() -> None:
    create_user("registry_recovery", module_utenze=True)
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "registry_recovery").one()
        subject = AnagraficaSubject(
            subject_type="person",
            source_name_raw="Obinu_Santina_BNOSTN34L64I743F",
        )
        db.add(subject)
        db.flush()
        subject_id = subject.id

        job_id = uuid.uuid4()
        db.execute(
            AnagraficaImportJob.__table__.insert().values(
                id=job_id,
                requested_by_user_id=user.id,
                letter="REGISTRY",
                status=AnagraficaImportJobStatus.RUNNING.value,
                total_folders=1,
                imported_ok=0,
                imported_errors=0,
                warning_count=0,
                log_json={"mode": "registry_import"},
            )
        )
        db.add(
            AnagraficaImportJobItem(
                job_id=job_id,
                subject_id=subject_id,
                folder_name="Obinu_Santina_BNOSTN34L64I743F",
                nas_folder_path="subject:test",
                status=AnagraficaImportJobItemStatus.PROCESSING.value,
            )
        )
        db.commit()

        recovered_ids = prepare_registry_import_jobs_for_recovery(db)
        assert recovered_ids == [job_id]

        db.expire_all()
        recovered_job = db.get(AnagraficaImportJob, job_id)
        assert recovered_job is not None
        assert recovered_job.status == AnagraficaImportJobStatus.PENDING.value
        assert recovered_job.started_at is None
        assert recovered_job.log_json["mode"] == "registry_import_resume"
        recovered_item = db.query(AnagraficaImportJobItem).filter(AnagraficaImportJobItem.job_id == job_id).one()
        assert recovered_item.status == AnagraficaImportJobItemStatus.PENDING.value
        assert recovered_item.last_error is None
        assert recovered_item.completed_at is None
    finally:
        db.close()


def test_recovered_registry_job_runs_in_resume_mode_without_duplicate_items(tmp_path) -> None:
    create_user("registry_resume", module_utenze=True)
    token = login("registry_resume")
    headers = {"Authorization": f"Bearer {token}"}
    original_storage_path = settings.utenze_document_storage_path
    settings.utenze_document_storage_path = str(tmp_path / "utenze-docs")

    try:
        create_response = client.post(
            "/utenze/subjects",
            headers=headers,
            json={
                "subject_type": "person",
                "source_name_raw": "Obinu_Santina_BNOSTN34L64I743F",
                "person": {
                    "cognome": "Obinu",
                    "nome": "Santina",
                    "codice_fiscale": "BNOSTN34L64I743F",
                },
            },
        )
        assert create_response.status_code == 201
        subject_id = uuid.UUID(create_response.json()["id"])

        bulk_response = client.post("/utenze/import/run-from-subjects", headers=headers)
        assert bulk_response.status_code == 202
        job_id = uuid.UUID(bulk_response.json()["job_id"])

        db = TestingSessionLocal()
        try:
            job = db.get(AnagraficaImportJob, job_id)
            assert job is not None
            job.status = AnagraficaImportJobStatus.RUNNING.value
            job.started_at = None
            db.add(job)
            db.add(
                AnagraficaImportJobItem(
                    job_id=job_id,
                    subject_id=subject_id,
                    letter="O",
                    folder_name="Obinu Santina",
                    nas_folder_path=f"subject:{subject_id}",
                    status=AnagraficaImportJobItemStatus.PROCESSING.value,
                )
            )
            db.commit()

            recovered_ids = prepare_registry_import_jobs_for_recovery(db)
            assert recovered_ids == [job_id]

            process_registry_bulk_import_job(
                db,
                job_id,
                service=AnagraficaImportPreviewService(FakeNasConnector(), archive_root="/archive"),
            )

            db.expire_all()
            items = db.query(AnagraficaImportJobItem).filter(AnagraficaImportJobItem.job_id == job_id).all()
            assert len(items) == 1
            assert items[0].status == AnagraficaImportJobItemStatus.COMPLETED.value
        finally:
            db.close()
    finally:
        settings.utenze_document_storage_path = original_storage_path
