from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from io import BytesIO
import zipfile

from cryptography.fernet import Fernet
import pandas as pd
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
from app.modules.utenze.anpr.models import AnprJobRun, AnprSyncConfig
from app.models.catasto import (
    CatastoBatch,
    CatastoConnectionTest,
    CatastoConnectionTestStatus,
    CatastoCredential,
    CatastoDocument,
    CatastoVisuraRequest,
    CatastoVisuraRequestStatus,
)
from app.services.catasto_credentials import get_credential_fernet


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
    generated_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr(
        "app.services.catasto_credentials.settings.credential_master_key",
        generated_key,
    )
    monkeypatch.setattr(
        "app.core.config.settings.credential_master_key",
        generated_key,
    )
    get_credential_fernet.cache_clear()

    db = TestingSessionLocal()
    db.add(
        ApplicationUser(
            username="elaborazioni-admin",
            email="elaborazioni@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
        )
    )
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def auth_headers() -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "elaborazioni-admin", "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def auth_token() -> str:
    return auth_headers()["Authorization"].split(" ", maxsplit=1)[1]


def create_awaiting_captcha_request(tmp_path) -> tuple[str, str]:
    image_path = tmp_path / "captcha.png"
    image_path.write_bytes(b"fake-png")

    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "elaborazioni-admin").one()
        batch = CatastoBatch(
            user_id=user.id,
            name="Batch captcha",
            status="processing",
            total_items=1,
            current_operation="Waiting for captcha",
        )
        db.add(batch)
        db.flush()

        request = CatastoVisuraRequest(
            batch_id=batch.id,
            user_id=user.id,
            row_index=1,
            comune="Oristano",
            comune_codice="G113#ORISTANO#5#5",
            catasto="Terreni e Fabbricati",
            foglio="5",
            particella="120",
            subalterno="3",
            tipo_visura="Completa",
            status=CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value,
            current_operation="Waiting for manual CAPTCHA",
            captcha_image_path=str(image_path),
            captcha_requested_at=datetime.now(UTC),
            captcha_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        db.add(request)
        db.commit()
        return str(batch.id), str(request.id)
    finally:
        db.close()


def create_document(tmp_path) -> tuple[str, str]:
    document_path = tmp_path / "visura-oristano.pdf"
    document_path.write_bytes(b"%PDF-1.4 fake pdf")

    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "elaborazioni-admin").one()
        batch = CatastoBatch(
            user_id=user.id,
            name="Batch documenti",
            status="completed",
            total_items=1,
            completed_items=1,
            current_operation="Batch finished",
            started_at=datetime.now(UTC) - timedelta(minutes=3),
            completed_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        db.add(batch)
        db.flush()

        request = CatastoVisuraRequest(
            batch_id=batch.id,
            user_id=user.id,
            row_index=1,
            comune="Oristano",
            comune_codice="G113#ORISTANO#5#5",
            catasto="Terreni e Fabbricati",
            foglio="5",
            particella="120",
            subalterno="3",
            tipo_visura="Completa",
            status=CatastoVisuraRequestStatus.COMPLETED.value,
            current_operation="PDF downloaded",
            processed_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        db.add(request)
        db.flush()

        document = CatastoDocument(
            user_id=user.id,
            request_id=request.id,
            comune=request.comune,
            foglio=request.foglio,
            particella=request.particella,
            subalterno=request.subalterno,
            catasto=request.catasto,
            tipo_visura=request.tipo_visura,
            filename=document_path.name,
            filepath=str(document_path),
            file_size=document_path.stat().st_size,
            codice_fiscale="RSSMRA80A01G113X",
        )
        db.add(document)
        db.flush()
        request.document_id = document.id
        db.commit()
        return str(batch.id), str(document.id)
    finally:
        db.close()


def create_completed_connection_test() -> str:
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "elaborazioni-admin").one()
        connection_test = CatastoConnectionTest(
            user_id=user.id,
            sister_username="RSSMRA80A01G113X",
            sister_password_encrypted=get_credential_fernet().encrypt(b"sister-secret"),
            ufficio_provinciale="ORISTANO Territorio",
            persist_verification=False,
            status=CatastoConnectionTestStatus.COMPLETED.value,
            mode="worker",
            reachable=True,
            authenticated=True,
            message="Autenticazione SISTER confermata dal worker.",
            started_at=datetime.now(UTC) - timedelta(seconds=5),
            completed_at=datetime.now(UTC),
        )
        db.add(connection_test)
        db.commit()
        return str(connection_test.id)
    finally:
        db.close()


def test_elaborazioni_anpr_summary_returns_defaults_when_no_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.elaborazioni.runtime_routes.settings.anpr_daily_call_hard_limit", 90)
    monkeypatch.setattr("app.modules.elaborazioni.runtime_routes.settings.anpr_job_batch_size", 10)
    monkeypatch.setattr("app.modules.elaborazioni.runtime_routes.settings.anpr_job_ruolo_year", None)

    response = client.get("/elaborazioni/utenze-anpr/summary", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["calls_today"] == 0
    assert payload["configured_daily_limit"] == 90
    assert payload["hard_daily_limit"] == 90
    assert payload["effective_daily_limit"] == 90
    assert payload["batch_size"] == 10
    assert payload["ruolo_year"] is None
    assert payload["recent_runs"] == []


def test_elaborazioni_anpr_summary_returns_recent_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.elaborazioni.runtime_routes.settings.anpr_daily_call_hard_limit", 90)
    monkeypatch.setattr("app.modules.elaborazioni.runtime_routes.settings.anpr_job_batch_size", 10)
    monkeypatch.setattr("app.modules.elaborazioni.runtime_routes.settings.anpr_job_ruolo_year", None)
    monkeypatch.setattr("app.modules.elaborazioni.runtime_routes.settings.anpr_job_timezone", "Europe/Rome")

    db = TestingSessionLocal()
    try:
        db.add(
            AnprSyncConfig(
                id=1,
                max_calls_per_day=70,
                job_enabled=True,
                job_cron="0 8-17 * * *",
                lookback_years=1,
                retry_not_found_days=90,
            )
        )
        db.add_all(
            [
                AnprJobRun(
                    run_date=date(2026, 5, 15),
                    ruolo_year=2025,
                    triggered_by="job",
                    status="limit_reached",
                    batch_size=10,
                    hard_daily_limit=90,
                    configured_daily_limit=70,
                    daily_calls_before=70,
                    daily_calls_after=70,
                    subjects_selected=0,
                    subjects_processed=0,
                    deceased_found=0,
                    errors=0,
                    calls_used=0,
                    notes="daily limit reached",
                    payload_json=None,
                    started_at=datetime(2026, 5, 15, 10, 35, tzinfo=UTC),
                    completed_at=datetime(2026, 5, 15, 10, 35, tzinfo=UTC),
                ),
                AnprJobRun(
                    run_date=date(2026, 5, 15),
                    ruolo_year=2025,
                    triggered_by="job",
                    status="completed",
                    batch_size=10,
                    hard_daily_limit=90,
                    configured_daily_limit=70,
                    daily_calls_before=60,
                    daily_calls_after=70,
                    subjects_selected=10,
                    subjects_processed=10,
                    deceased_found=2,
                    errors=1,
                    calls_used=10,
                    notes="job completed",
                    payload_json=None,
                    started_at=datetime(2026, 5, 15, 8, 0, tzinfo=UTC),
                    completed_at=datetime(2026, 5, 15, 8, 20, tzinfo=UTC),
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)
            return current if tz is None else current.astimezone(tz)

    monkeypatch.setattr("app.modules.elaborazioni.runtime_routes.datetime", FrozenDateTime)

    response = client.get("/elaborazioni/utenze-anpr/summary", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["calls_today"] == 10
    assert payload["configured_daily_limit"] == 70
    assert payload["hard_daily_limit"] == 90
    assert payload["effective_daily_limit"] == 70
    assert payload["batch_size"] == 10
    assert payload["ruolo_year"] == 2025
    assert len(payload["recent_runs"]) == 2
    assert payload["recent_runs"][0]["status"] == "limit_reached"
    assert payload["recent_runs"][0]["daily_calls_before"] == 70
    assert payload["recent_runs"][1]["calls_used"] == 10
    assert payload["recent_runs"][1]["deceased_found"] == 2


def test_credentials_are_encrypted_and_hidden_from_api() -> None:
    response = client.post(
        "/elaborazioni/credentials",
        headers=auth_headers(),
        json={
            "label": "Profilo principale",
            "sister_username": "RSSMRA80A01G113X",
            "sister_password": "sister-secret",
            "convenzione": "Consorzio",
        },
    )

    assert response.status_code == 200
    assert "sister_password" not in response.json()

    db = TestingSessionLocal()
    try:
        credential = db.query(CatastoCredential).one()
        assert credential.sister_username == "RSSMRA80A01G113X"
        assert credential.sister_password_encrypted != b"sister-secret"
    finally:
        db.close()

    get_response = client.get("/elaborazioni/credentials", headers=auth_headers())
    assert get_response.status_code == 200
    assert get_response.json()["configured"] is True
    assert get_response.json()["credential"]["sister_username"] == "RSSMRA80A01G113X"
    assert get_response.json()["credentials"][0]["label"] == "Profilo principale"


def test_multiple_sister_credentials_support_default_and_delete() -> None:
    first_response = client.post(
        "/elaborazioni/credentials",
        headers=auth_headers(),
        json={
            "label": "Profilo A",
            "sister_username": "RSSMRA80A01G113X",
            "sister_password": "sister-secret",
            "is_default": True,
        },
    )
    second_response = client.post(
        "/elaborazioni/credentials",
        headers=auth_headers(),
        json={
            "label": "Profilo B",
            "sister_username": "VRDLGI80A01H501U",
            "sister_password": "sister-secret-2",
        },
    )
    assert first_response.status_code == 200
    assert second_response.status_code == 200

    list_response = client.get("/elaborazioni/credentials", headers=auth_headers())
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["configured"] is True
    assert len(payload["credentials"]) == 2
    assert payload["default_credential"]["label"] == "Profilo A"

    second_id = second_response.json()["id"]
    patch_response = client.patch(
        f"/elaborazioni/credentials/{second_id}",
        headers=auth_headers(),
        json={"is_default": True, "active": True},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["is_default"] is True

    delete_response = client.delete(f"/elaborazioni/credentials/{second_id}", headers=auth_headers())
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Credential deleted"

    get_response = client.get("/elaborazioni/credentials", headers=auth_headers())
    assert get_response.status_code == 200
    assert len(get_response.json()["credentials"]) == 1
    assert get_response.json()["default_credential"]["label"] == "Profilo A"


def test_credentials_test_queues_saved_credentials_and_exposes_worker_result() -> None:
    client.post(
        "/elaborazioni/credentials",
        headers=auth_headers(),
        json={"label": "Profilo A", "sister_username": "RSSMRA80A01G113X", "sister_password": "sister-secret"},
    )

    response = client.post("/elaborazioni/credentials/test", headers=auth_headers())
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["success"] is None
    assert payload["message"] == "Queued for elaborazioni worker"
    test_id = payload["id"]

    db = TestingSessionLocal()
    try:
        connection_test = db.query(CatastoConnectionTest).one()
        assert str(connection_test.id) == test_id
        assert connection_test.persist_verification is True
        connection_test.status = CatastoConnectionTestStatus.COMPLETED.value
        connection_test.mode = "worker"
        connection_test.reachable = True
        connection_test.authenticated = True
        connection_test.message = "Autenticazione SISTER confermata dal worker."
        connection_test.completed_at = datetime.now(UTC)
        credential = db.query(CatastoCredential).one()
        credential.verified_at = connection_test.completed_at
        db.commit()
    finally:
        db.close()

    status_response = client.get(f"/elaborazioni/credentials/test/{test_id}", headers=auth_headers())
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["status"] == "completed"
    assert status_payload["success"] is True
    assert status_payload["authenticated"] is True
    assert status_payload["mode"] == "worker"
    assert status_payload["verified_at"] is not None


def test_credentials_test_accepts_transient_payload_without_persisting() -> None:
    response = client.post(
        "/elaborazioni/credentials/test",
        headers=auth_headers(),
        json={"sister_username": "TEMPUSER", "sister_password": "temp-secret"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["success"] is None
    assert payload["verified_at"] is None

    db = TestingSessionLocal()
    try:
        connection_test = db.query(CatastoConnectionTest).one()
        assert connection_test.persist_verification is False
        assert connection_test.credential_id is None
        assert db.query(CatastoCredential).count() == 0
    finally:
        db.close()


def test_comuni_endpoint_seeds_and_returns_oristano_dictionary() -> None:
    response = client.get("/catasto/comuni", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert any(item["nome"] == "Oristano" for item in payload)
    assert any(item["nome"] == "Marrubiu" for item in payload)


def test_create_batch_from_csv_builds_requests() -> None:
    credentials_response = client.post(
        "/elaborazioni/credentials",
        headers=auth_headers(),
        json={"sister_username": "RSSMRA80A01G113X", "sister_password": "sister-secret"},
    )
    assert credentials_response.status_code == 200

    csv_content = (
        "citta,catasto,sezione,foglio,particella,subalterno,tipo_visura\n"
        "MARRUBIU,Terreni,,12,603,,Sintetica\n"
        "ORISTANO,Terreni e Fabbricati,,5,120,3,Completa\n"
    )

    response = client.post(
        "/elaborazioni/batches",
        headers=auth_headers(),
        files={"file": ("visure.csv", csv_content, "text/csv")},
        data={"name": "Lotto marzo"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Lotto marzo"
    assert payload["total_items"] == 2
    assert len(payload["requests"]) == 2
    assert payload["requests"][0]["comune"] == "Marrubiu"
    assert payload["requests"][0]["comune_codice"] == "E972#MARRUBIU#0#0"

    batch_id = payload["id"]
    start_response = client.post(f"/elaborazioni/batches/{batch_id}/start", headers=auth_headers())
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "processing"


def test_create_batch_rejects_invalid_rows_with_detail() -> None:
    csv_content = (
        "citta,catasto,sezione,foglio,particella,subalterno,tipo_visura\n"
        "COMUNE FALSO,Altro,,abc,603,,Totale\n"
    )

    response = client.post(
        "/elaborazioni/batches",
        headers=auth_headers(),
        files={"file": ("visure.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["message"] == "File validation failed"
    assert detail["errors"][0]["row_index"] == 1
    assert "Comune non valido o non censito in catasto_comuni." in detail["errors"][0]["errors"]


def test_create_batch_from_legacy_xlsx_maps_comune_code_and_skips_ue() -> None:
    credentials_response = client.post(
        "/elaborazioni/credentials",
        headers=auth_headers(),
        json={"sister_username": "RSSMRA80A01G113X", "sister_password": "sister-secret"},
    )
    assert credentials_response.status_code == 200

    dataframe = pd.DataFrame(
        [
            {
                "Scheda": "689_W",
                "Intestazione": "CORRIAS Marco",
                "FG": 34,
                "Mapp": "626",
                "Superf.": 944,
                "Maglia": "118",
                "Lotto": "3",
                "Comune": "E972",
            },
            {
                "Scheda": "689_W",
                "Intestazione": "CORRIAS Marco",
                "FG": 35,
                "Mapp": "700",
                "Superf.": 500,
                "Maglia": "118",
                "Lotto": "3",
                "Comune": "UE",
            },
        ]
    )
    buffer = BytesIO()
    dataframe.to_excel(buffer, index=False)

    response = client.post(
        "/elaborazioni/batches",
        headers=auth_headers(),
        files={"file": ("FileDiPartenza.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"name": "Import legacy xlsx"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["total_items"] == 2
    assert payload["skipped_items"] == 1
    assert payload["current_operation"] == "1 record saltati in import"

    first_request = payload["requests"][0]
    assert first_request["comune"] == "Marrubiu"
    assert first_request["comune_codice"] == "E972#MARRUBIU#0#0"
    assert first_request["catasto"] == "Terreni"
    assert first_request["tipo_visura"] == "Sintetica"

    skipped_request = payload["requests"][1]
    assert skipped_request["status"] == "skipped"
    assert skipped_request["current_operation"] == "Record UE saltato in import"
    assert skipped_request["error_message"] == "Record saltato: il valore Comune e' UE."


def test_create_single_visura_auto_starts_batch_and_exposes_request_status() -> None:
    credentials_response = client.post(
        "/elaborazioni/credentials",
        headers=auth_headers(),
        json={"sister_username": "RSSMRA80A01G113X", "sister_password": "sister-secret"},
    )
    assert credentials_response.status_code == 200

    response = client.post(
        "/elaborazioni/requests",
        headers=auth_headers(),
        json={
            "comune": "Oristano",
            "catasto": "Terreni e Fabbricati",
            "foglio": "5",
            "particella": "120",
            "subalterno": "3",
            "tipo_visura": "Completa",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "processing"
    request_id = payload["requests"][0]["id"]

    request_response = client.get(f"/elaborazioni/requests/{request_id}", headers=auth_headers())
    assert request_response.status_code == 200
    assert request_response.json()["status"] == "pending"

    db = TestingSessionLocal()
    try:
        assert db.query(CatastoVisuraRequest).count() == 1
    finally:
        db.close()


def test_captcha_endpoints_store_manual_solution_and_skip_flag(tmp_path) -> None:
    _, request_id = create_awaiting_captcha_request(tmp_path)

    image_response = client.get(f"/elaborazioni/captcha/{request_id}/image", headers=auth_headers())
    assert image_response.status_code == 200
    assert image_response.content == b"fake-png"

    solve_response = client.post(
        f"/elaborazioni/captcha/{request_id}/solve",
        headers=auth_headers(),
        json={"text": "AB12C"},
    )
    assert solve_response.status_code == 200
    assert solve_response.json()["current_operation"] == "Manual CAPTCHA submitted"

    db = TestingSessionLocal()
    try:
        request = db.query(CatastoVisuraRequest).one()
        assert request.captcha_manual_solution == "AB12C"
        assert request.captcha_skip_requested is False
    finally:
        db.close()

    skip_response = client.post(f"/elaborazioni/captcha/{request_id}/skip", headers=auth_headers())
    assert skip_response.status_code == 200
    assert skip_response.json()["current_operation"] == "Skip requested by user"

    db = TestingSessionLocal()
    try:
        request = db.query(CatastoVisuraRequest).one()
        assert request.captcha_skip_requested is True
        assert request.captcha_manual_solution is None
    finally:
        db.close()


def test_documents_archive_lists_filters_details_and_downloads(tmp_path) -> None:
    batch_id, document_id = create_document(tmp_path)

    list_response = client.get("/catasto/documents", headers=auth_headers())
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == document_id
    assert payload[0]["batch_id"] == batch_id

    filtered_response = client.get(
        "/catasto/documents/search",
        headers=auth_headers(),
        params={"q": "visura-oristano", "comune": "Orist", "foglio": "5", "particella": "120"},
    )
    assert filtered_response.status_code == 200
    assert len(filtered_response.json()) == 1

    detail_response = client.get(f"/catasto/documents/{document_id}", headers=auth_headers())
    assert detail_response.status_code == 200
    assert detail_response.json()["filename"] == "visura-oristano.pdf"

    download_response = client.get(f"/catasto/documents/{document_id}/download", headers=auth_headers())
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/pdf"
    assert download_response.content == b"%PDF-1.4 fake pdf"

    batch_download_response = client.get(f"/elaborazioni/batches/{batch_id}/download", headers=auth_headers())
    assert batch_download_response.status_code == 200
    assert batch_download_response.headers["content-type"] == "application/zip"

    archive = zipfile.ZipFile(BytesIO(batch_download_response.content))
    assert archive.namelist() == ["visura-oristano.pdf"]
    assert archive.read("visura-oristano.pdf") == b"%PDF-1.4 fake pdf"

    selection_download_response = client.post(
        "/catasto/documents/download",
        headers=auth_headers(),
        json={"document_ids": [document_id]},
    )
    assert selection_download_response.status_code == 200
    assert selection_download_response.headers["content-type"] == "application/zip"

    selected_archive = zipfile.ZipFile(BytesIO(selection_download_response.content))
    assert selected_archive.namelist() == ["visura-oristano.pdf"]


def test_batch_websocket_emits_progress_and_captcha_notification(tmp_path) -> None:
    batch_id, request_id = create_awaiting_captcha_request(tmp_path)

    with client.websocket_connect(f"/elaborazioni/ws/{batch_id}?token={auth_token()}") as websocket:
        progress_event = websocket.receive_json()
        captcha_event = websocket.receive_json()

    assert progress_event["type"] == "progress"
    assert progress_event["status"] == "processing"
    assert progress_event["current"] == "Waiting for captcha"
    assert captcha_event == {
        "type": "captcha_needed",
        "request_id": request_id,
        "image_url": f"/elaborazioni/captcha/{request_id}/image",
    }


def test_credentials_test_websocket_emits_terminal_state() -> None:
    test_id = create_completed_connection_test()

    with client.websocket_connect(f"/elaborazioni/ws/credentials-test/{test_id}?token={auth_token()}") as websocket:
        event = websocket.receive_json()

    assert event["type"] == "credentials_test"
    assert event["test"]["id"] == test_id
    assert event["test"]["status"] == "completed"
    assert event["test"]["authenticated"] is True
