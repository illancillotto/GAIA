from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from uuid import UUID, uuid4
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
from app.models.capacitas import CapacitasInCassSyncJob
from app.modules.ruolo.models import RuoloAvviso
from app.modules.utenze.models import AnagraficaSubject
from app.modules.utenze.anpr.models import AnprJobRun, AnprSyncConfig
from app.models.catasto import (
    CatastoBatch,
    CatastoConnectionTest,
    CatastoConnectionTestStatus,
    CatastoComune,
    CatastoCredential,
    CatastoRuoloAutoSyncItem,
    CatastoRuoloAutoSyncItemStatus,
    CatastoDocument,
    CatastoVisuraRequest,
    CatastoVisuraRequestStatus,
)
from app.services.elaborazioni_batches import (
    RELEASE_REQUESTED_MESSAGE,
    RELEASE_REQUESTED_OPERATION,
)
from app.services.catasto_credentials import get_credential_fernet
from app.services.elaborazioni_ruolo_autosync import classify_ruolo_autosync_failure, reconcile_ruolo_autosync_items
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita


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


def create_not_found_request_with_artifacts(tmp_path) -> tuple[str, str]:
    artifact_dir = tmp_path / "request-artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    preview_path = artifact_dir / "preview-not-found.png"
    full_path = artifact_dir / "final-not_found.png"
    preview_path.write_bytes(b"preview-png")
    full_path.write_bytes(b"full-png")

    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "elaborazioni-admin").one()
        batch = CatastoBatch(
            user_id=user.id,
            name="Batch not found",
            status="completed",
            total_items=1,
            not_found_items=1,
            current_operation="Utente senza titolarità catastale riga 1",
        )
        db.add(batch)
        db.flush()

        request = CatastoVisuraRequest(
            batch_id=batch.id,
            user_id=user.id,
            row_index=1,
            search_mode="soggetto",
            subject_kind="PF",
            subject_id="CNCFTN98A02B314E",
            request_type="ATTUALITA",
            tipo_visura="Sintetica",
            status=CatastoVisuraRequestStatus.NOT_FOUND.value,
            current_operation="Nessuna corrispondenza",
            error_message="Nessuna corrispondenza catastale per PF 'CNCFTN98A02B314E'",
            artifact_dir=str(artifact_dir),
            processed_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        db.add(request)
        db.commit()
        return str(batch.id), str(request.id)
    finally:
        db.close()


def create_processing_batch() -> str:
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "elaborazioni-admin").one()
        batch = CatastoBatch(
            user_id=user.id,
            name="Batch processing",
            status="processing",
            total_items=2,
            current_operation="Batch preso in carico dal worker",
            started_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        db.add(batch)
        db.flush()

        for row_index in (1, 2):
            request = CatastoVisuraRequest(
                batch_id=batch.id,
                user_id=user.id,
                row_index=row_index,
                comune="Oristano",
                comune_codice="G113#ORISTANO#5#5",
                catasto="Terreni e Fabbricati",
                foglio=str(row_index),
                particella=str(100 + row_index),
                tipo_visura="Completa",
                status=CatastoVisuraRequestStatus.PROCESSING.value if row_index == 1 else CatastoVisuraRequestStatus.PENDING.value,
                current_operation="Presa in carico dal worker",
            )
            db.add(request)

        db.commit()
        return str(batch.id)
    finally:
        db.close()


def create_cancelled_batch(*, release_requested: bool, include_completed: bool = False) -> str:
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "elaborazioni-admin").one()
        batch = CatastoBatch(
            user_id=user.id,
            name="Batch cancelled",
            status="cancelled",
            total_items=2 if include_completed else 1,
            current_operation="Release requested by user" if release_requested else "Cancelled by user",
            started_at=datetime.now(UTC) - timedelta(minutes=5),
            completed_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        db.add(batch)
        db.flush()

        row_index = 1
        if include_completed:
            db.add(
                CatastoVisuraRequest(
                    batch_id=batch.id,
                    user_id=user.id,
                    row_index=row_index,
                    comune="Oristano",
                    comune_codice="G113#ORISTANO#5#5",
                    catasto="Terreni e Fabbricati",
                    foglio="1",
                    particella="101",
                    tipo_visura="Completa",
                    status=CatastoVisuraRequestStatus.COMPLETED.value,
                    current_operation="PDF scaricato",
                    processed_at=datetime.now(UTC) - timedelta(minutes=2),
                )
            )
            row_index += 1

        db.add(
            CatastoVisuraRequest(
                batch_id=batch.id,
                user_id=user.id,
                row_index=row_index,
                comune="Oristano",
                comune_codice="G113#ORISTANO#5#5",
                catasto="Terreni e Fabbricati",
                foglio=str(row_index),
                particella=str(100 + row_index),
                tipo_visura="Completa",
                status=CatastoVisuraRequestStatus.SKIPPED.value,
                current_operation="Release requested by user" if release_requested else "Cancelled",
                error_message="Credenziale SISTER liberata su richiesta utente" if release_requested else "Batch cancelled by user",
                processed_at=datetime.now(UTC) - timedelta(minutes=1),
            )
        )

        db.commit()
        return str(batch.id)
    finally:
        db.close()


def create_batch_with_stale_counters() -> str:
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "elaborazioni-admin").one()
        batch = CatastoBatch(
            user_id=user.id,
            name="Batch stale counters",
            status="processing",
            total_items=2,
            completed_items=0,
            current_operation="Batch preso in carico dal worker",
        )
        db.add(batch)
        db.flush()

        completed_request = CatastoVisuraRequest(
            batch_id=batch.id,
            user_id=user.id,
            row_index=1,
            comune="Oristano",
            comune_codice="G113#ORISTANO#5#5",
            catasto="Terreni e Fabbricati",
            foglio="1",
            particella="101",
            tipo_visura="Completa",
            status=CatastoVisuraRequestStatus.COMPLETED.value,
            current_operation="PDF scaricato",
            processed_at=datetime.now(UTC),
        )
        pending_request = CatastoVisuraRequest(
            batch_id=batch.id,
            user_id=user.id,
            row_index=2,
            comune="Oristano",
            comune_codice="G113#ORISTANO#5#5",
            catasto="Terreni e Fabbricati",
            foglio="2",
            particella="102",
            tipo_visura="Completa",
            status=CatastoVisuraRequestStatus.PENDING.value,
            current_operation="Pending",
        )
        db.add_all([completed_request, pending_request])
        db.commit()
        return str(batch.id)
    finally:
        db.close()


def create_processing_batch_with_released_pending_request() -> str:
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "elaborazioni-admin").one()
        batch = CatastoBatch(
            user_id=user.id,
            name="Batch processing release normalization",
            status="processing",
            total_items=3,
            completed_items=0,
            failed_items=1,
            skipped_items=1,
            current_operation="Credenziale TEST in cooldown, attesa 300s",
            started_at=datetime.now(UTC) - timedelta(days=1),
        )
        db.add(batch)
        db.flush()

        db.add(
            CatastoVisuraRequest(
                batch_id=batch.id,
                user_id=user.id,
                row_index=1,
                comune="Oristano",
                comune_codice="G113#ORISTANO#5#5",
                catasto="Terreni e Fabbricati",
                foglio="1",
                particella="101",
                tipo_visura="Completa",
                status=CatastoVisuraRequestStatus.SKIPPED.value,
                current_operation=RELEASE_REQUESTED_OPERATION,
                error_message=RELEASE_REQUESTED_MESSAGE,
                processed_at=datetime.now(UTC) - timedelta(hours=4),
            )
        )
        db.add(
            CatastoVisuraRequest(
                batch_id=batch.id,
                user_id=user.id,
                row_index=2,
                comune="Oristano",
                comune_codice="G113#ORISTANO#5#5",
                catasto="Terreni e Fabbricati",
                foglio="2",
                particella="102",
                tipo_visura="Completa",
                status=CatastoVisuraRequestStatus.FAILED.value,
                current_operation="Richiesta fallita, batch in prosecuzione",
                error_message="Errore test",
                processed_at=datetime.now(UTC) - timedelta(hours=3),
            )
        )
        db.add(
            CatastoVisuraRequest(
                batch_id=batch.id,
                user_id=user.id,
                row_index=3,
                comune="Oristano",
                comune_codice="G113#ORISTANO#5#5",
                catasto="Terreni e Fabbricati",
                foglio="3",
                particella="103",
                tipo_visura="Completa",
                status=CatastoVisuraRequestStatus.PENDING.value,
                current_operation="Sessione/timeout su TEST, retry differito",
                error_message=RELEASE_REQUESTED_MESSAGE,
                processed_at=datetime.now(UTC) - timedelta(hours=2),
            )
        )
        db.commit()
        return str(batch.id)
    finally:
        db.close()


def create_failed_request_with_missing_artifacts(tmp_path) -> tuple[str, str]:
    artifact_dir = tmp_path / "missing-request-artifacts"

    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "elaborazioni-admin").one()
        batch = CatastoBatch(
            user_id=user.id,
            name="Batch failed artifact missing",
            status="failed",
            total_items=1,
            failed_items=1,
            current_operation="Fallita riga 1",
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
            tipo_visura="Completa",
            status=CatastoVisuraRequestStatus.FAILED.value,
            current_operation="Fallita",
            error_message="Timeout 60000ms exceeded.",
            artifact_dir=str(artifact_dir),
            processed_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        db.add(request)
        db.commit()
        return str(batch.id), str(request.id)
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


def test_capacitas_incass_jobs_crud_and_rerun() -> None:
    create_response = client.post(
        "/elaborazioni/capacitas/incass/avvisi/jobs",
        headers=auth_headers(),
        json={
            "limit": 25,
            "include_details": True,
            "include_partitario": True,
            "continue_on_error": True,
            "throttle_ms": 300,
        },
    )

    assert create_response.status_code == 202
    payload = create_response.json()
    assert payload["status"] == "pending"
    assert payload["mode"] == "subjects_sync"
    assert payload["payload_json"]["limit"] == 25
    job_id = payload["id"]

    list_response = client.get("/elaborazioni/capacitas/incass/avvisi/jobs", headers=auth_headers())
    assert list_response.status_code == 200
    jobs = list_response.json()
    assert len(jobs) == 1
    assert jobs[0]["id"] == job_id

    db = TestingSessionLocal()
    try:
      job = db.query(CapacitasInCassSyncJob).filter(CapacitasInCassSyncJob.id == job_id).one()
      job.status = "succeeded"
      job.result_json = {
          "items": [
              {
                  "subject_id": "550e8400-e29b-41d4-a716-446655440000",
                  "identifier": "01154130957",
                  "display_name": "Acme Srl",
                  "status": "synced",
                  "notices_found": 2,
                  "notices_synced": 2,
                  "error": None,
              }
          ],
          "processed_subjects": 1,
          "failed_subjects": 0,
          "notices_found": 2,
          "notices_synced": 2,
      }
      job.started_at = datetime.now(UTC) - timedelta(minutes=2)
      job.completed_at = datetime.now(UTC) - timedelta(minutes=1)
      db.commit()
    finally:
      db.close()

    detail_response = client.get(f"/elaborazioni/capacitas/incass/avvisi/jobs/{job_id}", headers=auth_headers())
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["result_json"]["processed_subjects"] == 1
    assert detail["result_json"]["items"][0]["display_name"] == "Acme Srl"

    rerun_response = client.post(f"/elaborazioni/capacitas/incass/avvisi/jobs/{job_id}/run", headers=auth_headers())
    assert rerun_response.status_code == 200
    rerun_payload = rerun_response.json()
    assert rerun_payload["status"] == "pending"
    assert rerun_payload["started_at"] is None
    assert rerun_payload["completed_at"] is None
    assert rerun_payload["error_detail"] is None

    db = TestingSessionLocal()
    try:
      job = db.query(CapacitasInCassSyncJob).filter(CapacitasInCassSyncJob.id == job_id).one()
      job.status = "failed"
      job.error_detail = "timeout"
      db.commit()
    finally:
      db.close()

    delete_response = client.delete(f"/elaborazioni/capacitas/incass/avvisi/jobs/{job_id}", headers=auth_headers())
    assert delete_response.status_code == 204

    not_found_response = client.get(f"/elaborazioni/capacitas/incass/avvisi/jobs/{job_id}", headers=auth_headers())
    assert not_found_response.status_code == 404


def test_capacitas_incass_ruolo_harvest_creates_chunked_jobs() -> None:
    db = TestingSessionLocal()
    try:
        subjects = [
            AnagraficaSubject(subject_type="company", source_name_raw=f"Soggetto {index}")
            for index in range(3)
        ]
        db.add_all(subjects)
        db.flush()

        for index, subject in enumerate(subjects):
            db.add(
                RuoloAvviso(
                    import_job_id=uuid4(),
                    codice_cnc=f"CNC{index}",
                    anno_tributario=2025,
                    subject_id=subject.id,
                )
            )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/elaborazioni/capacitas/incass/avvisi/jobs/ruolo-harvest",
        headers=auth_headers(),
        json={
            "anno": 2025,
            "chunk_size": 2,
            "include_details": True,
            "include_partitario": True,
            "continue_on_error": True,
            "throttle_ms": 250,
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["anno"] == 2025
    assert payload["chunk_size"] == 2
    assert payload["total_subjects"] == 3
    assert payload["total_jobs"] == 2
    assert len(payload["job_ids"]) == 2

    db = TestingSessionLocal()
    try:
        jobs = (
            db.query(CapacitasInCassSyncJob)
            .filter(CapacitasInCassSyncJob.id.in_(payload["job_ids"]))
            .order_by(CapacitasInCassSyncJob.id.asc())
            .all()
        )
        assert len(jobs) == 2
        assert jobs[0].status == "pending"
        assert len(jobs[0].payload_json["subject_ids"]) == 2
        assert len(jobs[1].payload_json["subject_ids"]) == 1
    finally:
        db.close()


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


def test_request_artifact_preview_prefers_dedicated_preview_file(tmp_path) -> None:
    _, request_id = create_not_found_request_with_artifacts(tmp_path)

    preview_response = client.get(f"/elaborazioni/requests/{request_id}/artifacts/preview", headers=auth_headers())
    assert preview_response.status_code == 200
    assert preview_response.content == b"preview-png"

    download_response = client.get(f"/elaborazioni/requests/{request_id}/artifacts/download", headers=auth_headers())
    assert download_response.status_code == 200
    archive = zipfile.ZipFile(BytesIO(download_response.content))
    assert sorted(archive.namelist()) == ["final-not_found.png", "preview-not-found.png"]


def test_request_artifact_download_returns_diagnostic_zip_when_directory_is_missing(tmp_path) -> None:
    _, request_id = create_failed_request_with_missing_artifacts(tmp_path)

    download_response = client.get(f"/elaborazioni/requests/{request_id}/artifacts/download", headers=auth_headers())

    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/zip"
    archive = zipfile.ZipFile(BytesIO(download_response.content))
    assert archive.namelist() == ["error.txt"]
    diagnostic = archive.read("error.txt").decode("utf-8")
    assert f"request_id={request_id}" in diagnostic
    assert "Artifact directory missing." in diagnostic
    assert "status=failed" in diagnostic


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


def test_release_credentials_stops_processing_batches() -> None:
    batch_id = create_processing_batch()

    response = client.post("/elaborazioni/credentials/release", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "Richiesta di rilascio inviata" in payload["message"]
    assert batch_id in payload["message"]

    db = TestingSessionLocal()
    try:
        batch = db.query(CatastoBatch).filter(CatastoBatch.id == UUID(batch_id)).one()
        requests = db.query(CatastoVisuraRequest).filter(CatastoVisuraRequest.batch_id == batch.id).order_by(CatastoVisuraRequest.row_index.asc()).all()

        assert batch.status == "cancelled"
        assert batch.current_operation == "Release requested by user"
        assert len(requests) == 2
        assert all(request.status == CatastoVisuraRequestStatus.SKIPPED.value for request in requests)
        assert all(request.current_operation == "Release requested by user" for request in requests)
    finally:
        db.close()


def test_start_batch_resumes_requests_released_by_user() -> None:
    credentials_response = client.post(
        "/elaborazioni/credentials",
        headers=auth_headers(),
        json={"sister_username": "RSSMRA80A01G113X", "sister_password": "sister-secret"},
    )
    assert credentials_response.status_code == 200

    batch_id = create_processing_batch()

    release_response = client.post("/elaborazioni/credentials/release", headers=auth_headers())
    assert release_response.status_code == 200

    start_response = client.post(f"/elaborazioni/batches/{batch_id}/start", headers=auth_headers())

    assert start_response.status_code == 200
    payload = start_response.json()
    assert payload["status"] == "processing"
    assert payload["current_operation"] == "Queued after release"

    db = TestingSessionLocal()
    try:
        batch = db.query(CatastoBatch).filter(CatastoBatch.id == UUID(batch_id)).one()
        requests = db.query(CatastoVisuraRequest).filter(CatastoVisuraRequest.batch_id == batch.id).order_by(CatastoVisuraRequest.row_index.asc()).all()

        assert batch.status == "processing"
        assert batch.skipped_items == 0
        assert len(requests) == 2
        assert all(request.status == CatastoVisuraRequestStatus.PENDING.value for request in requests)
        assert all(request.current_operation == "Queued after release" for request in requests)
        assert all(request.error_message is None for request in requests)
        assert all(request.processed_at is None for request in requests)
    finally:
        db.close()


def test_start_batch_rejects_cancelled_batch_without_release_marker() -> None:
    credentials_response = client.post(
        "/elaborazioni/credentials",
        headers=auth_headers(),
        json={"sister_username": "RSSMRA80A01G113X", "sister_password": "sister-secret"},
    )
    assert credentials_response.status_code == 200

    batch_id = create_cancelled_batch(release_requested=False)

    start_response = client.post(f"/elaborazioni/batches/{batch_id}/start", headers=auth_headers())

    assert start_response.status_code == 409
    assert "No released requests available to resume" in start_response.json()["detail"]


def test_start_batch_resumes_only_released_requests_and_keeps_completed_items() -> None:
    credentials_response = client.post(
        "/elaborazioni/credentials",
        headers=auth_headers(),
        json={"sister_username": "RSSMRA80A01G113X", "sister_password": "sister-secret"},
    )
    assert credentials_response.status_code == 200

    batch_id = create_cancelled_batch(release_requested=True, include_completed=True)

    start_response = client.post(f"/elaborazioni/batches/{batch_id}/start", headers=auth_headers())

    assert start_response.status_code == 200
    payload = start_response.json()
    assert payload["status"] == "processing"
    assert payload["completed_items"] == 1
    assert payload["skipped_items"] == 0

    db = TestingSessionLocal()
    try:
        batch = db.query(CatastoBatch).filter(CatastoBatch.id == UUID(batch_id)).one()
        requests = db.query(CatastoVisuraRequest).filter(CatastoVisuraRequest.batch_id == batch.id).order_by(CatastoVisuraRequest.row_index.asc()).all()

        assert batch.completed_items == 1
        assert batch.skipped_items == 0
        assert requests[0].status == CatastoVisuraRequestStatus.COMPLETED.value
        assert requests[1].status == CatastoVisuraRequestStatus.PENDING.value
        assert requests[1].current_operation == "Queued after release"
        assert requests[1].processed_at is None
    finally:
        db.close()


def test_get_batch_normalizes_processing_batch_left_pending_after_release() -> None:
    batch_id = create_processing_batch_with_released_pending_request()

    response = client.get(f"/elaborazioni/batches/{batch_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "cancelled"
    assert payload["current_operation"] == RELEASE_REQUESTED_OPERATION
    assert payload["skipped_items"] == 2
    assert payload["failed_items"] == 1

    db = TestingSessionLocal()
    try:
        batch = db.query(CatastoBatch).filter(CatastoBatch.id == UUID(batch_id)).one()
        requests = db.query(CatastoVisuraRequest).filter(CatastoVisuraRequest.batch_id == batch.id).order_by(CatastoVisuraRequest.row_index.asc()).all()
        assert batch.status == "cancelled"
        assert batch.current_operation == RELEASE_REQUESTED_OPERATION
        assert requests[2].status == CatastoVisuraRequestStatus.SKIPPED.value
        assert requests[2].current_operation == RELEASE_REQUESTED_OPERATION
        assert requests[2].error_message == RELEASE_REQUESTED_MESSAGE
    finally:
        db.close()


def test_get_batch_realigns_stale_completed_counter() -> None:
    batch_id = create_batch_with_stale_counters()

    response = client.get(f"/elaborazioni/batches/{batch_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["completed_items"] == 1
    assert len(payload["requests"]) == 2

    db = TestingSessionLocal()
    try:
        batch = db.query(CatastoBatch).filter(CatastoBatch.id == UUID(batch_id)).one()
        assert batch.completed_items == 1
    finally:
        db.close()


def test_runtime_metrics_reports_kpis_and_operating_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.elaborazioni_batches.settings.elaborazioni_operation_window_enabled", True)
    monkeypatch.setattr("app.services.elaborazioni_batches.settings.elaborazioni_operation_start_hour", 9)
    monkeypatch.setattr("app.services.elaborazioni_batches.settings.elaborazioni_operation_end_hour", 18)
    monkeypatch.setattr("app.services.elaborazioni_batches.settings.elaborazioni_operation_timezone", "Europe/Rome")

    now = datetime(2026, 5, 21, 5, 0, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = now
            if tz is not None:
                return current.astimezone(tz)
            return current.replace(tzinfo=None)

    monkeypatch.setattr("app.services.elaborazioni_batches.datetime", FrozenDateTime)

    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "elaborazioni-admin").one()
        batch = CatastoBatch(
            user_id=user.id,
            name="Batch KPI",
            status="completed",
            total_items=4,
            started_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=1),
        )
        db.add(batch)
        db.flush()

        request_specs = [
            (CatastoVisuraRequestStatus.COMPLETED.value, now - timedelta(hours=1, minutes=20), now - timedelta(hours=1)),
            (CatastoVisuraRequestStatus.FAILED.value, now - timedelta(hours=1, minutes=10), now - timedelta(minutes=50)),
            (CatastoVisuraRequestStatus.NOT_FOUND.value, now - timedelta(days=2, minutes=30), now - timedelta(days=2)),
            (CatastoVisuraRequestStatus.SKIPPED.value, now - timedelta(days=6, minutes=45), now - timedelta(days=6)),
        ]
        for index, (status, created_at, processed_at) in enumerate(request_specs, start=1):
            db.add(
                CatastoVisuraRequest(
                    batch_id=batch.id,
                    user_id=user.id,
                    row_index=index,
                    comune="Oristano",
                    comune_codice="G113#ORISTANO#5#5",
                    catasto="Terreni",
                    foglio=str(index),
                    particella=str(index),
                    tipo_visura="Sintetica",
                    status=status,
                    created_at=created_at,
                    processed_at=processed_at,
                )
            )
        db.commit()
    finally:
        db.close()

    response = client.get("/elaborazioni/metrics", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["operating_window"]["enabled"] is True
    assert payload["operating_window"]["is_within_window"] is False
    assert payload["operating_window"]["state_label"] == "In pausa"
    assert payload["totals"]["processed_requests"] == 4
    assert payload["totals"]["requests_completed"] == 1
    assert payload["totals"]["requests_failed"] == 1
    assert payload["totals"]["requests_not_found"] == 1
    assert payload["totals"]["requests_skipped"] == 1
    assert payload["totals"]["success_rate"] == 25.0
    assert payload["last_24_hours"]["processed_requests"] == 2
    assert payload["last_24_hours"]["throughput_per_hour"] == round(2 / 24, 2)
    assert payload["last_7_days"]["processed_requests"] == 4
    assert payload["totals"]["average_batch_duration_minutes"] == 60.0
    assert payload["totals"]["average_request_duration_seconds"] == 1725.0
    assert payload["recent_daily"][0]["date"] == "2026-05-21"
    assert payload["recent_daily"][0]["processed_requests"] == 2


def _seed_ruolo_autosync_fixture() -> tuple[int, str]:
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "elaborazioni-admin").one()
        credential = CatastoCredential(
            user_id=user.id,
            label="Autosync SISTER",
            sister_username="autosync-user",
            sister_password_encrypted=get_credential_fernet().encrypt(b"secret-pass"),
            ufficio_provinciale="ORISTANO Territorio",
            active=True,
            is_default=True,
        )
        db.add(credential)
        db.add(CatastoComune(nome="Oristano", codice_sister="G113#ORISTANO#5#5", ufficio="ORISTANO Territorio"))
        db.flush()

        import_job = RuoloImportJob(anno_tributario=2026, status="completed")
        db.add(import_job)
        db.flush()
        avviso = RuoloAvviso(import_job_id=import_job.id, codice_cnc="CNC-001", anno_tributario=2026)
        db.add(avviso)
        db.flush()
        partita = RuoloPartita(
            avviso_id=avviso.id,
            codice_partita="P-001",
            comune_nome="Oristano",
        )
        db.add(partita)
        db.flush()
        ruolo_particella = RuoloParticella(
            partita_id=partita.id,
            anno_tributario=2026,
            foglio="12",
            particella="603",
            subalterno=None,
            cat_particella_id=uuid4(),
        )
        db.add(ruolo_particella)
        db.commit()
        return user.id, str(credential.id)
    finally:
        db.close()


def test_ruolo_autosync_config_status_and_run_now() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()

    update_response = client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={"enabled": True, "credential_id": credential_id},
    )
    assert update_response.status_code == 200
    assert update_response.json()["enabled"] is True
    assert update_response.json()["credential_id"] == credential_id

    refresh_response = client.post("/elaborazioni/ruolo-autosync/refresh-source", headers=auth_headers())
    assert refresh_response.status_code == 200

    run_response = client.post("/elaborazioni/ruolo-autosync/run-now", headers=auth_headers())
    assert run_response.status_code == 200
    assert "Autosync avviato sul batch" in run_response.json()["message"]

    status_response = client.get("/elaborazioni/ruolo-autosync/status", headers=auth_headers())
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["config"]["enabled"] is True
    assert payload["counts"]["total"] == 1
    assert payload["counts"]["queued"] == 1
    assert payload["running_batch"] is not None
    assert payload["running_batch"]["batch_kind"] == "ruolo_autosync"
    assert payload["running_batch"]["credential_id"] == credential_id

    db = TestingSessionLocal()
    try:
        batch = db.query(CatastoBatch).filter(CatastoBatch.user_id == user_id).one()
        request = db.query(CatastoVisuraRequest).filter(CatastoVisuraRequest.batch_id == batch.id).one()
        item = db.query(CatastoRuoloAutoSyncItem).filter(CatastoRuoloAutoSyncItem.user_id == user_id).one()
        assert batch.batch_kind == "ruolo_autosync"
        assert str(batch.credential_id) == credential_id
        assert request.target_ruolo_particella_id == item.ruolo_particella_id
        assert item.status == "queued"
    finally:
        db.close()


def test_ruolo_autosync_failure_classifier_blocks_submit_anomaly() -> None:
    status = classify_ruolo_autosync_failure(
        "Submit visura non avanzato per richiesta abc: classification=current message=Particella presente in elenco immobili AdE."
    )
    assert status == CatastoRuoloAutoSyncItemStatus.BLOCKED_RUNTIME.value


def test_ruolo_autosync_failure_classifier_blocks_manual_captcha_missing() -> None:
    status = classify_ruolo_autosync_failure(
        "Automatic CAPTCHA exhausted; manual CAPTCHA response missing"
    )
    assert status == CatastoRuoloAutoSyncItemStatus.BLOCKED_RUNTIME.value


def test_ruolo_autosync_status_counts_runtime_anomalies_separately() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()

    client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={"enabled": True, "credential_id": credential_id},
    )
    client.post("/elaborazioni/ruolo-autosync/refresh-source", headers=auth_headers())
    client.post("/elaborazioni/ruolo-autosync/run-now", headers=auth_headers())

    db = TestingSessionLocal()
    try:
        item = db.query(CatastoRuoloAutoSyncItem).filter(CatastoRuoloAutoSyncItem.user_id == user_id).one()
        request = db.get(CatastoVisuraRequest, item.linked_request_id)
        assert request is not None
        request.status = CatastoVisuraRequestStatus.FAILED.value
        request.error_message = (
            "Submit visura non avanzato per richiesta abc: "
            "classification=current message=Particella presente in elenco immobili AdE."
        )
        db.add(request)
        db.commit()

        reconcile_ruolo_autosync_items(db, user_id)
        db.refresh(item)
        assert item.status == CatastoRuoloAutoSyncItemStatus.BLOCKED_RUNTIME.value
        assert item.retry_after is None
    finally:
        db.close()

    status_response = client.get("/elaborazioni/ruolo-autosync/status", headers=auth_headers())
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["counts"]["blocked_runtime"] == 1
    assert payload["counts"]["pending"] == 0
    assert payload["error_items"][0]["status"] == "blocked_runtime"


def test_ruolo_autosync_status_counts_manual_captcha_missing_as_runtime_anomaly() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()

    client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={"enabled": True, "credential_id": credential_id},
    )
    client.post("/elaborazioni/ruolo-autosync/refresh-source", headers=auth_headers())
    client.post("/elaborazioni/ruolo-autosync/run-now", headers=auth_headers())

    db = TestingSessionLocal()
    try:
        item = db.query(CatastoRuoloAutoSyncItem).filter(CatastoRuoloAutoSyncItem.user_id == user_id).one()
        request = db.get(CatastoVisuraRequest, item.linked_request_id)
        assert request is not None
        request.status = CatastoVisuraRequestStatus.FAILED.value
        request.error_message = "Automatic CAPTCHA exhausted; manual CAPTCHA response missing"
        db.add(request)
        db.commit()

        reconcile_ruolo_autosync_items(db, user_id)
        db.refresh(item)
        assert item.status == CatastoRuoloAutoSyncItemStatus.BLOCKED_RUNTIME.value
        assert item.retry_after is None
    finally:
        db.close()

    status_response = client.get("/elaborazioni/ruolo-autosync/status", headers=auth_headers())
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["counts"]["blocked_runtime"] == 1
    assert payload["counts"]["pending"] == 0
    assert payload["error_items"][0]["status"] == "blocked_runtime"
