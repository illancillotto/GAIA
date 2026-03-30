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
from app.modules.anagrafica.router import get_anagrafica_import_service
from app.modules.anagrafica.models import AnagraficaDocument
from app.modules.anagrafica.services.import_service import AnagraficaImportPreviewService


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


def create_user(username: str, *, module_anagrafica: bool) -> None:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username=username,
        email=f"{username}@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_accessi=True,
        module_anagrafica=module_anagrafica,
    )
    db.add(user)
    db.commit()
    db.close()


def login(username: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": "secret123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_import_preview_returns_structured_payload() -> None:
    create_user("alice", module_anagrafica=True)
    token = login("alice")

    response = client.post(
        "/anagrafica/import/preview",
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
    create_user("alice_all", module_anagrafica=True)
    token = login("alice_all")

    response = client.post(
        "/anagrafica/import/preview",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["letter"] == "ALL"
    assert body["total_folders"] == 1
    assert body["parsed_subjects"] == 1


def test_import_preview_requires_module_flag() -> None:
    create_user("bob", module_anagrafica=False)
    token = login("bob")

    response = client.post(
        "/anagrafica/import/preview",
        json={"letter": "O"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_import_preview_validates_letter() -> None:
    create_user("carla", module_anagrafica=True)
    token = login("carla")

    response = client.post(
        "/anagrafica/import/preview",
        json={"letter": "12"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_import_run_persists_job_and_returns_summary() -> None:
    create_user("dario", module_anagrafica=True)
    token = login("dario")

    response = client.post(
        "/anagrafica/import/run",
        json={"letter": "O"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "completed"
    assert body["total_folders"] == 1
    assert body["imported_ok"] == 1

    jobs_response = client.get("/anagrafica/import/jobs", headers={"Authorization": f"Bearer {token}"})
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert len(jobs) == 1
    assert jobs[0]["job_id"] == body["job_id"]
    assert jobs[0]["items"][0]["payload_json"]["source_name_raw"] == "Obinu_Santina_BNOSTN34L64I743F"

    detail_response = client.get(
        f"/anagrafica/import/jobs/{body['job_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "completed"


def test_import_run_without_letter_imports_full_archive() -> None:
    create_user("dario_all", module_anagrafica=True)
    token = login("dario_all")

    response = client.post(
        "/anagrafica/import/run",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["letter"] == "ALL"
    assert body["total_folders"] == 1


def test_import_job_detail_includes_items_and_resume_endpoint() -> None:
    create_user("franco", module_anagrafica=True)
    token = login("franco")
    headers = {"Authorization": f"Bearer {token}"}

    run_response = client.post("/anagrafica/import/run", json={}, headers=headers)
    assert run_response.status_code == 202
    job_id = run_response.json()["job_id"]

    detail_response = client.get(f"/anagrafica/import/jobs/{job_id}", headers=headers)
    assert detail_response.status_code == 200
    completed_job = detail_response.json()
    assert completed_job["items"]
    assert completed_job["items"][0]["folder_name"] == "Obinu_Santina_BNOSTN34L64I743F"
    assert completed_job["items"][0]["payload_json"]["documents"][0]["filename"] == "INGIUNZIONE-2024.pdf"

    resume_response = client.post(f"/anagrafica/import/jobs/{job_id}/resume", headers=headers)
    assert resume_response.status_code == 409


def test_csv_import_creates_and_updates_person_subjects() -> None:
    create_user("csv_user", module_anagrafica=True)
    token = login("csv_user")
    headers = {"Authorization": f"Bearer {token}"}

    csv_payload = (
        "Codice Fiscale;Cognome;Nome;Sesso;Data_Nascita;Com_Nascita;Com_Residenza;CAP;PR;Indirizzo_Residenza;Variaz_Anagr;STATO;Decesso\n"
        "RSSMRA80A01H501Z;Rossi;Mario;M;01/01/1980;Oristano;Oristano;09170;OR;Via Roma 1;;ATTIVO;\n"
    )

    import_response = client.post(
        "/anagrafica/subjects/import-csv",
        headers=headers,
        files={"file": ("anagrafica.csv", csv_payload.encode("utf-8"), "text/csv")},
    )
    assert import_response.status_code == 200
    payload = import_response.json()
    assert payload["total_rows"] == 1
    assert payload["created_subjects"] == 1
    assert payload["updated_subjects"] == 0

    list_response = client.get("/anagrafica/subjects?search=RSSMRA80A01H501Z", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    subject_id = list_response.json()["items"][0]["id"]

    detail_response = client.get(f"/anagrafica/subjects/{subject_id}", headers=headers)
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
        "/anagrafica/subjects/import-csv",
        headers=headers,
        files={"file": ("anagrafica.csv", csv_update_payload.encode("utf-8"), "text/csv")},
    )
    assert update_response.status_code == 200
    assert update_response.json()["created_subjects"] == 0
    assert update_response.json()["updated_subjects"] == 1

    updated_detail_response = client.get(f"/anagrafica/subjects/{subject_id}", headers=headers)
    assert updated_detail_response.status_code == 200
    updated_detail = updated_detail_response.json()
    assert updated_detail["person"]["comune_residenza"] == "Cabras (OR)"
    assert "[CSV IMPORT]" in (updated_detail["person"]["note"] or "")


def test_csv_import_handles_duplicate_codice_fiscale_rows_without_500() -> None:
    create_user("csv_duplicates", module_anagrafica=True)
    token = login("csv_duplicates")
    headers = {"Authorization": f"Bearer {token}"}

    csv_payload = (
        "Codice Fiscale;Cognome;Nome;Sesso;Data_Nascita;Com_Nascita;Com_Residenza;CAP;PR;Indirizzo_Residenza;Variaz_Anagr;STATO;Decesso\n"
        "SRRPQL38P11I743U;Serra;Pasquale;M;11/09/1938;Simaxis;Ollastra;09088;OR;Via Marconi 33;;ATTIVO;\n"
        "SRRPQL38P11I743U;Serra;Pasquale;M;11/09/1938;Simaxis;Simaxis;09088;OR;Via Marconi 33;Aggiornamento;ATTIVO;\n"
    )

    response = client.post(
        "/anagrafica/subjects/import-csv",
        headers=headers,
        files={"file": ("anagrafica.csv", csv_payload.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 2
    assert payload["created_subjects"] == 1
    assert payload["updated_subjects"] == 1
    assert payload["skipped_rows"] == 0

    detail_search = client.get("/anagrafica/subjects?search=SRRPQL38P11I743U", headers=headers)
    assert detail_search.status_code == 200
    assert detail_search.json()["total"] == 1


def test_csv_import_rejects_missing_required_headers() -> None:
    create_user("csv_invalid", module_anagrafica=True)
    token = login("csv_invalid")

    csv_payload = "Cognome;Nome\nRossi;Mario\n"
    response = client.post(
        "/anagrafica/subjects/import-csv",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("anagrafica.csv", csv_payload.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 422


def test_subjects_crud_search_and_stats() -> None:
    create_user("eva", module_anagrafica=True)
    token = login("eva")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/anagrafica/subjects",
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

    list_response = client.get("/anagrafica/subjects?search=rossi", headers=headers)
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] >= 1
    assert list_payload["items"][0]["display_name"] == "Rossi Mario"

    detail_response = client.get(f"/anagrafica/subjects/{subject_id}", headers=headers)
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["person"]["codice_fiscale"] == "RSSMRA80A01H501Z"
    assert len(detail_payload["audit_log"]) == 1

    update_response = client.put(
        f"/anagrafica/subjects/{subject_id}",
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

    search_response = client.get("/anagrafica/search?q=mario", headers=headers)
    assert search_response.status_code == 200
    assert search_response.json()["total"] >= 1

    stats_response = client.get("/anagrafica/stats", headers=headers)
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["total_subjects"] >= 1
    assert stats["total_persons"] >= 1
    assert stats["by_letter"]["R"] >= 1

    deactivate_response = client.delete(f"/anagrafica/subjects/{subject_id}", headers=headers)
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["status"] == "inactive"

    token_search_response = client.get("/anagrafica/search?q=rossi RSSMRA80A01H501Z", headers=headers)
    assert token_search_response.status_code == 200
    assert token_search_response.json()["total"] >= 1


def test_document_update_and_delete() -> None:
    create_user("franco", module_anagrafica=True)
    token = login("franco")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/anagrafica/subjects",
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

    documents_response = client.get(f"/anagrafica/subjects/{subject_id}/documents", headers=headers)
    assert documents_response.status_code == 200
    documents = documents_response.json()
    assert len(documents) == 1
    document_id = documents[0]["id"]

    detail_response = client.get(f"/anagrafica/subjects/{subject_id}", headers=headers)
    assert detail_response.status_code == 200
    assert len(detail_response.json()["documents"]) == 1

    patch_response = client.patch(
        f"/anagrafica/documents/{document_id}",
        headers=headers,
        json={"doc_type": "visura", "notes": "riclassificato"},
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["doc_type"] == "visura"
    assert "riclassificato" in ",".join(patched["warnings"]) or patched["warnings"] == []

    delete_response = client.delete(f"/anagrafica/documents/{document_id}", headers=headers)
    assert delete_response.status_code == 204

    documents_after_delete = client.get(f"/anagrafica/subjects/{subject_id}/documents", headers=headers)
    assert documents_after_delete.status_code == 200
    assert documents_after_delete.json() == []


def test_export_and_catasto_correlation() -> None:
    create_user("gina", module_anagrafica=True)
    token = login("gina")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/anagrafica/subjects",
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

    detail_response = client.get(f"/anagrafica/subjects/{subject_id}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["catasto_documents"]) == 1
    assert detail["catasto_documents"][0]["comune"] == "Oristano"
    assert detail["catasto_documents"][0]["filename"] == "visura-pinna.pdf"

    csv_response = client.get("/anagrafica/export?format=csv&search=Pinna", headers=headers)
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "display_name" in csv_response.text
    assert "Pinna Giulia" in csv_response.text

    xlsx_response = client.get("/anagrafica/export?format=xlsx&search=Pinna", headers=headers)
    assert xlsx_response.status_code == 200
    assert xlsx_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_import_single_subject_from_existing_registry_persists_local_file(tmp_path) -> None:
    create_user("henry", module_anagrafica=True)
    token = login("henry")
    headers = {"Authorization": f"Bearer {token}"}
    original_storage_path = settings.anagrafica_document_storage_path
    settings.anagrafica_document_storage_path = str(tmp_path / "anagrafica-docs")

    try:
        create_response = client.post(
            "/anagrafica/subjects",
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

        import_response = client.post(f"/anagrafica/subjects/{subject_id}/import-from-nas", headers=headers)
        assert import_response.status_code == 200
        payload = import_response.json()
        assert payload["created_documents"] == 1
        assert payload["matched_folder_name"] == "Obinu_Santina_BNOSTN34L64I743F"

        detail_response = client.get(f"/anagrafica/subjects/{subject_id}", headers=headers)
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
        settings.anagrafica_document_storage_path = original_storage_path


def test_subject_nas_candidates_returns_scored_matches() -> None:
    create_user("manual_match", module_anagrafica=True)
    token = login("manual_match")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/anagrafica/subjects",
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

    candidates_response = client.get(f"/anagrafica/subjects/{subject_id}/nas-candidates", headers=headers)
    assert candidates_response.status_code == 200
    candidates = candidates_response.json()
    assert len(candidates) >= 1
    assert candidates[0]["folder_name"] == "Obinu_Santina_BNOSTN34L64I743F"
    assert candidates[0]["score"] > 0
    assert candidates[0]["nas_folder_path"] == "/archive/O/Obinu_Santina_BNOSTN34L64I743F"


def test_bulk_import_from_existing_registry_and_reset(tmp_path) -> None:
    create_user("irene", module_anagrafica=True)
    token = login("irene")
    headers = {"Authorization": f"Bearer {token}"}
    original_storage_path = settings.anagrafica_document_storage_path
    settings.anagrafica_document_storage_path = str(tmp_path / "anagrafica-docs")

    try:
        create_response = client.post(
            "/anagrafica/subjects",
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

        bulk_response = client.post("/anagrafica/import/run-from-subjects", headers=headers)
        assert bulk_response.status_code == 202
        bulk_payload = bulk_response.json()
        assert bulk_payload["letter"] == "REGISTRY"
        assert bulk_payload["imported_ok"] == 1
        assert bulk_payload["created_documents"] == 1

        jobs_response = client.get("/anagrafica/import/jobs", headers=headers)
        assert jobs_response.status_code == 200
        jobs = jobs_response.json()
        assert jobs[0]["letter"] == "REGISTRY"
        assert jobs[0]["items"][0]["nas_folder_path"] == "/archive/O/Obinu_Santina_BNOSTN34L64I743F"

        reset_response = client.post("/anagrafica/reset", headers=headers, json={"confirm": "RESET ANAGRAFICA"})
        assert reset_response.status_code == 200
        reset_payload = reset_response.json()
        assert reset_payload["cleared_subject_links"] == 1
        assert reset_payload["deleted_documents"] == 1
        assert reset_payload["deleted_import_jobs"] >= 1
        assert reset_payload["deleted_storage_files"] == 1

        subjects_after_reset = client.get("/anagrafica/subjects", headers=headers)
        assert subjects_after_reset.status_code == 200
        assert subjects_after_reset.json()["total"] == 1
        subject_id = subjects_after_reset.json()["items"][0]["id"]
        detail_after_reset = client.get(f"/anagrafica/subjects/{subject_id}", headers=headers)
        assert detail_after_reset.status_code == 200
        detail_payload = detail_after_reset.json()
        assert detail_payload["documents"] == []
        assert detail_payload["nas_folder_path"] is None
        assert detail_payload["nas_folder_letter"] is None
        assert detail_payload["imported_at"] is None
    finally:
        settings.anagrafica_document_storage_path = original_storage_path
