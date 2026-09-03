import zipfile
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

import pandas as pd
import pytest
from cryptography.fernet import Fernet
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
from app.models.catasto import (
    CatastoBatch,
    CatastoBatchStatus,
    CatastoComune,
    CatastoConnectionTest,
    CatastoConnectionTestStatus,
    CatastoCredential,
    CatastoCredentialLease,
    CatastoDocument,
    CatastoPerpetualSyncItem,
    CatastoRuoloAutoSyncConfig,
    CatastoRuoloAutoSyncItem,
    CatastoRuoloAutoSyncItemStatus,
    CatastoVisuraRequest,
    CatastoVisuraRequestStatus,
)
from app.models.catasto_phase1 import CatParticella
from app.models.elaborazioni import ElaborazioneAutoJobConfig
from app.modules.ruolo.models import (
    RuoloAvviso,
    RuoloImportJob,
    RuoloParticella,
    RuoloPartita,
)
from app.modules.utenze.anpr.models import AnprJobRun, AnprSyncConfig
from app.modules.utenze.models import AnagraficaPerson, AnagraficaSubject
from app.schemas.catasto import CatastoRuoloAutoSyncConfigUpdateRequest
from app.services.catasto_credentials import get_credential_fernet
from app.services.elaborazioni_autosync_dashboard import _as_utc, build_autosync_dashboard
from app.services.elaborazioni_batches import (
    RELEASE_REQUESTED_MESSAGE,
    RELEASE_REQUESTED_OPERATION,
    BatchConflictError,
)
from app.services.elaborazioni_perpetual_sources import (
    PerpetualSourceTarget,
    _subject_target,
    load_enabled_targets,
    load_ruolo_parcel_targets,
    load_ruolo_subject_targets,
)
from app.services.elaborazioni_perpetual_sync import (
    _autosync_schedule,
    available_perpetual_credentials,
    ensure_perpetual_sync_batch,
    maintain_perpetual_sync,
    perpetual_sync_counts,
    reconcile_perpetual_sync_items,
    refresh_perpetual_sync_sources,
    retry_perpetual_sync_failures,
)
from app.services.elaborazioni_ruolo_autosync import (
    classify_ruolo_autosync_failure,
    ensure_ruolo_autosync_batch,
    reconcile_ruolo_autosync_items,
    recover_stale_pending_ruolo_autosync_batches,
)

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
            role=ApplicationUserRole.SUPER_ADMIN.value,
            is_active=True,
        )
    )
    db.add(
        ApplicationUser(
            username="elaborazioni-super-admin",
            email="elaborazioni-super-admin@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.SUPER_ADMIN.value,
            is_active=True,
        )
    )
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def auth_headers(username: str = "elaborazioni-admin") -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": "secret123"})
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
    assert payload["total_runs"] == 0
    assert payload["total_subjects_selected"] == 0
    assert payload["total_subjects_processed"] == 0
    assert payload["total_deceased_found"] == 0
    assert payload["total_errors"] == 0
    assert payload["total_calls_used"] == 0
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
    assert payload["total_runs"] == 2
    assert payload["total_subjects_selected"] == 10
    assert payload["total_subjects_processed"] == 10
    assert payload["total_deceased_found"] == 2
    assert payload["total_errors"] == 1
    assert payload["total_calls_used"] == 10
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
            "schedule_enabled": True,
            "availability_schedule": {
                "timezone": "Europe/Rome",
                "weekly": {"0": [{"start": "18:00", "end": "08:00"}]},
            },
        },
    )

    assert response.status_code == 200
    assert "sister_password" not in response.json()
    assert response.json()["schedule_enabled"] is True
    assert response.json()["availability_schedule"]["weekly"]["0"][0] == {"start": "18:00", "end": "08:00"}

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
    assert [item["request_type"] for item in payload["requests"]] == ["STORICA", "ATTUALITA"]

    batch_id = payload["id"]
    start_response = client.post(f"/elaborazioni/batches/{batch_id}/start", headers=auth_headers())
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "processing"


def test_batch_credential_allowlist_is_persisted_and_revalidated_on_start() -> None:
    first_response = client.post(
        "/elaborazioni/credentials",
        headers=auth_headers(),
        json={
            "label": "Alessandro",
            "sister_username": "ALLOWLIST-ONE",
            "sister_password": "sister-secret",
        },
    )
    second_response = client.post(
        "/elaborazioni/credentials",
        headers=auth_headers(),
        json={
            "label": "Marika",
            "sister_username": "ALLOWLIST-TWO",
            "sister_password": "sister-secret",
        },
    )
    credential_ids = [first_response.json()["id"], second_response.json()["id"]]
    csv_content = (
        "citta,catasto,foglio,particella,tipo_visura\n"
        "MARRUBIU,Terreni,33,815,Analitica\n"
    )

    response = client.post(
        "/elaborazioni/batches",
        headers=auth_headers(),
        files={"file": ("storiche.csv", csv_content, "text/csv")},
        data={"name": "Storiche allowlist", "credential_ids": credential_ids},
    )

    assert response.status_code == 201
    payload = response.json()
    assert set(payload["credential_ids"]) == set(credential_ids)
    assert payload["requests"][0]["request_type"] == "STORICA"
    assert payload["requests"][0]["tipo_visura"] == "Analitica"

    deactivate = client.patch(
        f"/elaborazioni/credentials/{credential_ids[1]}",
        headers=auth_headers(),
        json={"active": False},
    )
    assert deactivate.status_code == 200
    blocked = client.post(f"/elaborazioni/batches/{payload['id']}/start", headers=auth_headers())
    assert blocked.status_code == 409
    assert "missing or inactive" in blocked.json()["detail"]

    reactivate = client.patch(
        f"/elaborazioni/credentials/{credential_ids[1]}",
        headers=auth_headers(),
        json={"active": True},
    )
    assert reactivate.status_code == 200
    started = client.post(f"/elaborazioni/batches/{payload['id']}/start", headers=auth_headers())
    assert started.status_code == 200
    assert started.json()["status"] == "processing"


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


def test_cancel_batch_clears_request_execution_fencing_and_retry_schedule() -> None:
    batch_id = create_processing_batch()

    db = TestingSessionLocal()
    try:
        requests = (
            db.query(CatastoVisuraRequest)
            .filter(CatastoVisuraRequest.batch_id == UUID(batch_id))
            .all()
        )
        for request in requests:
            request.execution_token = uuid4()
            request.retry_not_before = datetime.now(UTC) + timedelta(minutes=5)
        db.commit()
    finally:
        db.close()

    response = client.post(f"/elaborazioni/batches/{batch_id}/cancel", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    db = TestingSessionLocal()
    try:
        requests = (
            db.query(CatastoVisuraRequest)
            .filter(CatastoVisuraRequest.batch_id == UUID(batch_id))
            .all()
        )
        assert all(request.status == CatastoVisuraRequestStatus.SKIPPED.value for request in requests)
        assert all(request.execution_token is None for request in requests)
        assert all(request.retry_not_before is None for request in requests)
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
    assert payload["statistics"]["processed_items"] == 1
    assert payload["statistics"]["remaining_items"] == 1
    assert payload["statistics"]["progress_percent"] == 50.0

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
        avviso = RuoloAvviso(
            import_job_id=import_job.id,
            codice_cnc="CNC-001",
            anno_tributario=2026,
            codice_fiscale_raw="RSSMRA80A01G113A",
            nominativo_raw="Mario Rossi",
        )
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


def test_ruolo_autosync_status_exposes_operational_dashboard() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()
    assert client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={"enabled": True, "credential_id": credential_id},
    ).status_code == 200

    now = datetime.now(UTC).replace(minute=30, second=0, microsecond=0)
    batch_id = uuid4()
    completed_request_id = uuid4()
    db = TestingSessionLocal()
    try:
        db.add(
            CatastoBatch(
                id=batch_id,
                user_id=user_id,
                name="AutoSync operativo",
                batch_kind="perpetual_sync",
                status=CatastoBatchStatus.COMPLETED.value,
                total_items=2,
                completed_items=1,
                failed_items=1,
                skipped_items=0,
                not_found_items=0,
                current_operation="Micro-batch completato",
                created_at=now - timedelta(minutes=20),
                started_at=now - timedelta(minutes=15),
                completed_at=now,
            )
        )
        db.add_all(
            [
                CatastoVisuraRequest(
                    id=completed_request_id,
                    batch_id=batch_id,
                    user_id=user_id,
                    row_index=1,
                    tipo_visura="Sintetica",
                    status=CatastoVisuraRequestStatus.COMPLETED.value,
                    current_operation="Visura scaricata",
                    attempts=1,
                    created_at=now - timedelta(minutes=15),
                    processed_at=now,
                ),
                CatastoVisuraRequest(
                    batch_id=batch_id,
                    user_id=user_id,
                    row_index=2,
                    tipo_visura="Sintetica",
                    status=CatastoVisuraRequestStatus.FAILED.value,
                    current_operation="Blocco SISTER",
                    error_message="CAPTCHA richiesto",
                    last_error_code="CAPTCHA_REQUIRED",
                    attempts=2,
                    created_at=now - timedelta(minutes=15),
                    processed_at=now,
                ),
            ]
        )
        db.add(
            CatastoDocument(
                user_id=user_id,
                request_id=completed_request_id,
                search_mode="immobile",
                tipo_visura="Sintetica",
                filename="visura.pdf",
                filepath="/tmp/visura.pdf",
                created_at=now,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/elaborazioni/ruolo-autosync/status", headers=auth_headers())
    assert response.status_code == 200
    dashboard = response.json()["dashboard"]
    assert dashboard["summary"] == {
        "period_hours": 24,
        "batches_total": 1,
        "batches_active": 0,
        "batches_completed": 1,
        "batches_failed": 0,
        "requests_total": 2,
        "requests_completed": 1,
        "requests_failed": 1,
        "requests_blocked": 1,
        "documents_downloaded": 1,
        "completed_per_hour": 1.0,
        "average_batch_duration_seconds": 900,
        "last_activity_at": now.isoformat().replace("+00:00", "Z"),
    }
    assert dashboard["hourly"][-1]["completed"] == 1
    assert dashboard["hourly"][-1]["failed"] == 1
    assert dashboard["hourly"][-1]["documents_downloaded"] == 1
    assert dashboard["recent_batches"][0]["id"] == str(batch_id)
    assert dashboard["events"][0]["level"] == "error"
    assert dashboard["events"][0]["detail"] == "CAPTCHA richiesto"


def test_autosync_dashboard_exposes_empty_state_and_normalizes_utc() -> None:
    db = TestingSessionLocal()
    try:
        dashboard = build_autosync_dashboard(db, user_id=-1)
    finally:
        db.close()

    assert dashboard.summary.batches_total == 0
    assert dashboard.summary.completed_per_hour == 0
    assert dashboard.hourly == []
    assert dashboard.recent_batches == []
    assert dashboard.events == []
    aware = datetime(2026, 8, 30, 12, tzinfo=UTC)
    assert _as_utc(aware) == aware


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


def test_ruolo_autosync_reuses_existing_pending_batch_instead_of_creating_a_new_one() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()

    client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={"enabled": True, "credential_id": credential_id},
    )
    client.post("/elaborazioni/ruolo-autosync/refresh-source", headers=auth_headers())

    db = TestingSessionLocal()
    try:
        first_batch = ensure_ruolo_autosync_batch(db, user_id)
        assert first_batch is not None
        first_batch.status = "pending"
        first_batch.started_at = None
        first_batch.completed_at = None
        db.add(first_batch)
        requests = db.query(CatastoVisuraRequest).filter(CatastoVisuraRequest.batch_id == first_batch.id).all()
        for request in requests:
            request.status = CatastoVisuraRequestStatus.PENDING.value
            request.current_operation = "Awaiting start"
            request.processed_at = None
            db.add(request)
        db.commit()

        reused_batch = ensure_ruolo_autosync_batch(db, user_id)
        assert reused_batch is not None
        assert reused_batch.id == first_batch.id

        batch_ids = [row[0] for row in db.query(CatastoBatch.id).filter(CatastoBatch.user_id == user_id).all()]
        assert batch_ids == [first_batch.id]
    finally:
        db.close()


def test_ruolo_autosync_conflict_cleanup_does_not_leave_orphan_pending_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()

    client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={"enabled": True, "credential_id": credential_id},
    )
    client.post("/elaborazioni/ruolo-autosync/refresh-source", headers=auth_headers())

    import app.services.elaborazioni_ruolo_autosync as autosync_module

    real_start_batch = autosync_module.start_batch
    call_count = 0

    def fake_start_batch(db, current_user_id, batch_id):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise autosync_module.BatchConflictError("Only one processing batch per user is allowed")
        return real_start_batch(db, current_user_id, batch_id)

    monkeypatch.setattr(autosync_module, "start_batch", fake_start_batch)

    db = TestingSessionLocal()
    try:
        batch = ensure_ruolo_autosync_batch(db, user_id)
        assert batch is None

        batches = db.query(CatastoBatch).filter(CatastoBatch.user_id == user_id).all()
        assert batches == []

        item = db.query(CatastoRuoloAutoSyncItem).filter(CatastoRuoloAutoSyncItem.user_id == user_id).one()
        assert item.status == CatastoRuoloAutoSyncItemStatus.PENDING.value
        assert item.linked_batch_id is None
        assert item.linked_request_id is None
        assert item.retry_after is not None
    finally:
        db.close()


def test_ruolo_autosync_recovers_stale_pending_batch_and_requeues_items() -> None:
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
        batch = db.query(CatastoBatch).filter(CatastoBatch.user_id == user_id).one()
        request = db.query(CatastoVisuraRequest).filter(CatastoVisuraRequest.batch_id == batch.id).one()
        item = db.query(CatastoRuoloAutoSyncItem).filter(CatastoRuoloAutoSyncItem.user_id == user_id).one()

        batch.status = "pending"
        batch.started_at = None
        batch.completed_at = None
        batch.created_at = datetime.now(UTC) - timedelta(minutes=10)
        request.status = CatastoVisuraRequestStatus.PENDING.value
        request.processed_at = None
        item.status = CatastoRuoloAutoSyncItemStatus.QUEUED.value
        db.add_all([batch, request, item])
        db.commit()

        recovered = recover_stale_pending_ruolo_autosync_batches(db, user_id)
        assert recovered == 1

        db.refresh(batch)
        db.refresh(request)
        db.refresh(item)
        assert batch.status == "failed"
        assert batch.current_operation == "Batch autosync pendente bonificato automaticamente dopo mancato avvio"
        assert request.status == CatastoVisuraRequestStatus.FAILED.value
        assert item.status == CatastoRuoloAutoSyncItemStatus.PENDING.value
        assert item.linked_batch_id is None
        assert item.linked_request_id is None
        assert item.retry_after is None
    finally:
        db.close()


def test_ruolo_autosync_status_route_is_read_only_for_stale_pending_batch() -> None:
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
        batch = db.query(CatastoBatch).filter(CatastoBatch.user_id == user_id).one()
        request = db.query(CatastoVisuraRequest).filter(CatastoVisuraRequest.batch_id == batch.id).one()
        item = db.query(CatastoRuoloAutoSyncItem).filter(CatastoRuoloAutoSyncItem.user_id == user_id).one()

        batch.status = "pending"
        batch.started_at = None
        batch.completed_at = None
        batch.created_at = datetime.now(UTC) - timedelta(minutes=10)
        request.status = CatastoVisuraRequestStatus.PENDING.value
        request.processed_at = None
        item.status = CatastoRuoloAutoSyncItemStatus.QUEUED.value
        db.add_all([batch, request, item])
        db.commit()
    finally:
        db.close()

    status_response = client.get("/elaborazioni/ruolo-autosync/status", headers=auth_headers())
    assert status_response.status_code == 200

    db = TestingSessionLocal()
    try:
        item = db.query(CatastoRuoloAutoSyncItem).filter(CatastoRuoloAutoSyncItem.user_id == user_id).one()
        batch = db.query(CatastoBatch).filter(CatastoBatch.user_id == user_id).one()
        assert item.status == CatastoRuoloAutoSyncItemStatus.QUEUED.value
        assert item.linked_batch_id == batch.id
        assert batch.status == "pending"
    finally:
        db.close()


def test_ruolo_autosync_source_refresh_deduplicates_and_uses_incremental_watermark() -> None:
    user_id, _ = _seed_ruolo_autosync_fixture()

    import app.services.elaborazioni_ruolo_autosync as autosync_module

    db = TestingSessionLocal()
    try:
        original = db.query(RuoloParticella).one()
        newer = RuoloParticella(
            partita_id=original.partita_id,
            anno_tributario=2027,
            foglio="99",
            particella=original.particella,
            subalterno="A",
            cat_particella_id=original.cat_particella_id,
            created_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        db.add(newer)
        db.commit()

        first = autosync_module.refresh_ruolo_autosync_source(db, user_id)
        assert first == {"created": 1, "updated": 0, "total_candidates": 1}
        item = db.query(CatastoRuoloAutoSyncItem).one()
        assert item.ruolo_particella_id == newer.id
        assert item.foglio == "99"
        assert item.subalterno == "A"

        second = autosync_module.refresh_ruolo_autosync_source(db, user_id)
        assert second == {"created": 0, "updated": 1, "total_candidates": 1}

        config = db.query(CatastoRuoloAutoSyncConfig).filter_by(user_id=user_id).one()
        watermark = config.last_source_refresh_at
        assert watermark is not None
        incremental_created_at = datetime.now(UTC)
        config.last_source_refresh_at = incremental_created_at - timedelta(seconds=1)
        original.created_at = incremental_created_at - timedelta(seconds=10)
        newer.created_at = incremental_created_at - timedelta(seconds=10)
        incremental_row = RuoloParticella(
            partita_id=original.partita_id,
            anno_tributario=2028,
            foglio="100",
            particella="604",
            cat_particella_id=uuid4(),
            created_at=incremental_created_at,
        )
        db.add(incremental_row)
        db.commit()

        incremental = autosync_module._refresh_ruolo_autosync_source_incremental(db, user_id)
        assert incremental == {"created": 1, "updated": 0, "total_candidates": 1}

        empty = autosync_module._refresh_ruolo_autosync_source_incremental(db, user_id)
        assert empty == {"created": 0, "updated": 0, "total_candidates": 0}
    finally:
        db.close()


def test_ruolo_autosync_source_refresh_blocks_and_unblocks_unknown_comune() -> None:
    user_id, _ = _seed_ruolo_autosync_fixture()

    import app.services.elaborazioni_ruolo_autosync as autosync_module

    db = TestingSessionLocal()
    try:
        partita = db.query(RuoloPartita).one()
        partita.comune_nome = "Atlantide"
        db.commit()

        autosync_module.refresh_ruolo_autosync_source(db, user_id)
        item = db.query(CatastoRuoloAutoSyncItem).one()
        assert item.status == CatastoRuoloAutoSyncItemStatus.BLOCKED_SOURCE.value
        assert "non censito" in (item.last_error_message or "")

        db.add(CatastoComune(nome="Atlantide", codice_sister="A000#ATLANTIDE#0#0", ufficio="ORISTANO"))
        db.commit()
        autosync_module.refresh_ruolo_autosync_source(db, user_id)
        db.refresh(item)

        assert item.status == CatastoRuoloAutoSyncItemStatus.PENDING.value
        assert item.last_error_message is None
    finally:
        db.close()


def test_ruolo_autosync_postgres_advisory_lock_helpers() -> None:
    import app.services.elaborazioni_ruolo_autosync as autosync_module

    class FakeTransaction:
        def __init__(self) -> None:
            self.rolled_back = False

        def rollback(self) -> None:
            self.rolled_back = True

    class FakeConnection:
        def __init__(self) -> None:
            self.statement = ""
            self.transaction = FakeTransaction()
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.closed = True

        def begin(self):
            return self.transaction

        def scalar(self, statement):
            self.statement = str(statement)
            return True

    class FakePostgresSession:
        def __init__(self) -> None:
            self.connection = FakeConnection()

        def get_bind(self):
            return SimpleNamespace(
                dialect=SimpleNamespace(name="postgresql"),
                connect=lambda: self.connection,
            )

    db = FakePostgresSession()

    with autosync_module._ruolo_autosync_xact_lock(db, 42) as acquired:
        assert acquired is True
        assert "pg_try_advisory_xact_lock" in db.connection.statement
        assert db.connection.transaction.rolled_back is False

    assert db.connection.transaction.rolled_back is True
    assert db.connection.closed is True


def test_ruolo_autosync_maintenance_skips_busy_lock_and_releases_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from contextlib import contextmanager

    import app.services.elaborazioni_ruolo_autosync as autosync_module

    calls: list[str] = []
    monkeypatch.setattr(
        autosync_module,
        "get_ruolo_autosync_config",
        lambda _db, _user_id: SimpleNamespace(credential_ids=None),
    )

    @contextmanager
    def busy_lock(_db, _user_id):
        yield False

    monkeypatch.setattr(autosync_module, "_ruolo_autosync_xact_lock", busy_lock)
    monkeypatch.setattr(
        autosync_module,
        "_refresh_ruolo_autosync_source_incremental",
        lambda *_args, **_kwargs: calls.append("refresh"),
    )

    assert autosync_module.maintain_ruolo_autosync(object(), 7) is None
    assert calls == []

    @contextmanager
    def acquired_lock(_db, _user_id):
        calls.append("acquire")
        try:
            yield True
        finally:
            calls.append("release")

    monkeypatch.setattr(autosync_module, "_ruolo_autosync_xact_lock", acquired_lock)
    monkeypatch.setattr(
        autosync_module,
        "_refresh_ruolo_autosync_source_incremental",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("refresh failed")),
    )

    with pytest.raises(RuntimeError, match="refresh failed"):
        autosync_module.maintain_ruolo_autosync(object(), 7)
    assert calls == ["acquire", "release"]


def test_ruolo_autosync_serialized_operation_returns_conflict_when_lock_is_busy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from contextlib import contextmanager

    import app.services.elaborazioni_ruolo_autosync as autosync_module

    @contextmanager
    def busy_lock(_db, _user_id):
        yield False

    monkeypatch.setattr(autosync_module, "_ruolo_autosync_xact_lock", busy_lock)
    operation = autosync_module._ruolo_autosync_serialized(lambda _db, _user_id: {"unexpected": True})

    with pytest.raises(autosync_module.RuoloAutosyncBusyError) as exc:
        operation(object(), 7)

    assert exc.value.status_code == 409
    assert exc.value.detail == "Un aggiornamento delle sorgenti è già in corso. Riprova tra poco."


def test_ruolo_autosync_config_validation_and_missing_config_fallback() -> None:
    import app.services.elaborazioni_ruolo_autosync as autosync_module

    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter_by(username="elaborazioni-super-admin").one()
        config = autosync_module.get_ruolo_autosync_config_for_update(db, user.id)
        assert config.user_id == user.id

        disabled = autosync_module.update_ruolo_autosync_config(
            db,
            user.id,
            CatastoRuoloAutoSyncConfigUpdateRequest(enabled=False, credential_id=None),
        )
        assert disabled.enabled is False
        assert disabled.credential_id is None
        unchanged = autosync_module.update_ruolo_autosync_config(
            db,
            user.id,
            CatastoRuoloAutoSyncConfigUpdateRequest(),
        )
        assert unchanged.enabled is False

        with pytest.raises(ValueError, match="non trovata"):
            autosync_module.update_ruolo_autosync_config(
                db,
                user.id,
                CatastoRuoloAutoSyncConfigUpdateRequest(credential_id=uuid4()),
            )

        inactive = CatastoCredential(
            user_id=user.id,
            label="Inactive",
            sister_username="inactive",
            sister_password_encrypted=b"encrypted",
            ufficio_provinciale="ORISTANO Territorio",
            active=False,
        )
        db.add(inactive)
        db.commit()
        with pytest.raises(ValueError, match="non e attiva"):
            autosync_module.update_ruolo_autosync_config(
                db,
                user.id,
                CatastoRuoloAutoSyncConfigUpdateRequest(credential_id=inactive.id),
            )

        waiting_for_credentials = autosync_module.update_ruolo_autosync_config(
            db,
            user.id,
            CatastoRuoloAutoSyncConfigUpdateRequest(enabled=True),
        )
        assert waiting_for_credentials.enabled is True
        waiting_for_credentials.enabled = False
        db.commit()

        config.enabled = True
        config.credential_id = uuid4()
        db.add(config)
        db.commit()
        with pytest.raises(ValueError, match="non e disponibile"):
            autosync_module.update_ruolo_autosync_config(
                db,
                user.id,
                CatastoRuoloAutoSyncConfigUpdateRequest(enabled=True),
            )
    finally:
        db.close()


def test_ruolo_autosync_reconcile_covers_missing_processing_completed_and_retryable_requests() -> None:
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
        item = db.query(CatastoRuoloAutoSyncItem).one()
        request = db.get(CatastoVisuraRequest, item.linked_request_id)
        assert request is not None

        request.status = CatastoVisuraRequestStatus.PROCESSING.value
        request.attempts = 3
        db.commit()
        reconcile_ruolo_autosync_items(db, user_id)
        assert item.status == CatastoRuoloAutoSyncItemStatus.PROCESSING.value
        assert item.attempt_count == 3

        request.status = CatastoVisuraRequestStatus.COMPLETED.value
        request.processed_at = None
        request.error_message = "completed note"
        db.commit()
        reconcile_ruolo_autosync_items(db, user_id)
        assert item.status == CatastoRuoloAutoSyncItemStatus.COMPLETED.value
        assert item.last_completed_at is not None

        request.status = CatastoVisuraRequestStatus.FAILED.value
        request.error_message = "temporary transport failure"
        db.commit()
        reconcile_ruolo_autosync_items(db, user_id)
        assert item.status == CatastoRuoloAutoSyncItemStatus.PENDING.value
        assert item.retry_after is not None

        item.linked_request_id = uuid4()
        item.status = CatastoRuoloAutoSyncItemStatus.QUEUED.value
        db.commit()
        reconcile_ruolo_autosync_items(db, user_id)
        assert item.status == CatastoRuoloAutoSyncItemStatus.PENDING.value
        assert item.retry_after is None

        item.linked_request_id = uuid4()
        item.status = CatastoRuoloAutoSyncItemStatus.COMPLETED.value
        db.commit()
        reconcile_ruolo_autosync_items(db, user_id)
        assert item.status == CatastoRuoloAutoSyncItemStatus.COMPLETED.value

        item.linked_request_id = request.id
        item.status = CatastoRuoloAutoSyncItemStatus.PROCESSING.value
        request.status = "cancelled"
        db.commit()
        reconcile_ruolo_autosync_items(db, user_id)
        assert item.status == CatastoRuoloAutoSyncItemStatus.PROCESSING.value
    finally:
        db.close()


def test_ruolo_autosync_batch_guard_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()

    import app.services.elaborazioni_ruolo_autosync as autosync_module

    db = TestingSessionLocal()
    try:
        assert ensure_ruolo_autosync_batch(db, user_id) is None

        config = db.query(CatastoRuoloAutoSyncConfig).filter_by(user_id=user_id).one()
        config.enabled = True
        config.credential_id = uuid4()
        db.commit()
        assert ensure_ruolo_autosync_batch(db, user_id) is None
        assert "non disponibile" in (config.last_error_message or "")

        config.credential_id = UUID(credential_id)
        db.commit()
        assert ensure_ruolo_autosync_batch(db, user_id) is None

        autosync_module.refresh_ruolo_autosync_source(db, user_id)
        processing = CatastoBatch(
            user_id=user_id,
            name="Manual processing",
            status=CatastoVisuraRequestStatus.PROCESSING.value,
            total_items=1,
        )
        db.add(processing)
        db.commit()
        assert ensure_ruolo_autosync_batch(db, user_id) is None
        db.delete(processing)
        db.commit()

        first_batch = ensure_ruolo_autosync_batch(db, user_id)
        assert first_batch is not None
        first_batch.status = CatastoBatchStatus.PENDING.value
        first_batch.started_at = None
        first_batch.completed_at = None
        db.commit()
        monkeypatch.setattr(
            autosync_module,
            "start_batch",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(autosync_module.BatchConflictError("busy")),
        )
        assert ensure_ruolo_autosync_batch(db, user_id) is None
    finally:
        db.close()


def test_ruolo_autosync_scheduler_continues_after_user_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.elaborazioni_ruolo_autosync as autosync_module

    db = TestingSessionLocal()
    try:
        db.add(
            ApplicationUser(
                username="elaborazioni-third-admin",
                email="elaborazioni-third-admin@example.local",
                password_hash=hash_password("secret123"),
                role=ApplicationUserRole.SUPER_ADMIN.value,
                is_active=True,
            )
        )
        db.commit()
        users = db.query(ApplicationUser).order_by(ApplicationUser.id).all()
        configs = [CatastoRuoloAutoSyncConfig(user_id=user.id, enabled=True) for user in users]
        db.add_all(configs)
        db.commit()

        def maintain(_db, user_id):
            if user_id == users[0].id:
                return object()
            if user_id == users[1].id:
                return None
            raise RuntimeError("isolated failure")

        monkeypatch.setattr(autosync_module, "maintain_ruolo_autosync", maintain)

        assert autosync_module.run_ruolo_autosync_maintenance_for_all_users(db) == 1
        db.refresh(configs[2])
        assert configs[2].last_error_message == "isolated failure"
    finally:
        db.close()


def test_ruolo_autosync_stale_recovery_handles_empty_and_terminal_batches() -> None:
    user_id, _ = _seed_ruolo_autosync_fixture()
    db = TestingSessionLocal()
    try:
        created_at = datetime.now(UTC) - timedelta(minutes=10)
        empty_batch = CatastoBatch(
            user_id=user_id,
            name="Empty stale autosync",
            batch_kind="ruolo_autosync",
            status="pending",
            total_items=0,
            created_at=created_at,
        )
        terminal_batch = CatastoBatch(
            user_id=user_id,
            name="Terminal stale autosync",
            batch_kind="ruolo_autosync",
            status="pending",
            total_items=1,
            created_at=created_at,
        )
        db.add_all([empty_batch, terminal_batch])
        db.flush()
        completed_request = CatastoVisuraRequest(
            batch_id=terminal_batch.id,
            user_id=user_id,
            row_index=1,
            comune="Oristano",
            comune_codice="G113#ORISTANO#5#5",
            catasto="Terreni",
            foglio="1",
            particella="1",
            tipo_visura="Sintetica",
            status=CatastoVisuraRequestStatus.COMPLETED.value,
        )
        db.add(completed_request)
        db.commit()

        assert recover_stale_pending_ruolo_autosync_batches(db, user_id) == 2
        db.refresh(completed_request)
        assert completed_request.status == CatastoVisuraRequestStatus.COMPLETED.value
    finally:
        db.close()


def test_continuous_sync_refreshes_primary_and_secondary_targets() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()
    db = TestingSessionLocal()
    try:
        subject = AnagraficaSubject(
            source_name_raw="Azienda Consortile",
            subject_type="company",
            status="active",
        )
        db.add(subject)
        db.flush()
        db.add(
            AnagraficaSubject(
                source_name_raw="Soggetto senza identificativo",
                subject_type="person",
                status="active",
            )
        )
        import_job = db.query(RuoloImportJob).one()
        db.add(
            RuoloAvviso(
                import_job_id=import_job.id, codice_cnc="CNC-NO-CF",
                anno_tributario=2026, nominativo_raw="Senza codice fiscale",
            )
        )
        db.add(
            AnagraficaPerson(
                subject_id=subject.id,
                cognome="Verdi",
                nome="Anna",
                codice_fiscale="VRDNNA80A41G113Z",
            )
        )
        db.add(
            CatParticella(
                cod_comune_capacitas=1,
                codice_catastale="G113",
                nome_comune="Oristano",
                foglio="20",
                particella="100",
                is_current=True,
                suppressed=False,
            )
        )
        db.commit()
    finally:
        db.close()

    update = client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={
            "enabled": True,
            "credential_ids": [credential_id],
            "primary_enabled": True,
            "secondary_enabled": True,
            "batch_size": 12,
            "role_parcel_refresh_hours": 24,
        },
    )
    assert update.status_code == 200
    assert update.json()["credential_ids"] == [credential_id]
    assert update.json()["secondary_enabled"] is True

    response = client.post(
        "/elaborazioni/ruolo-autosync/refresh-source", headers=auth_headers()
    )
    assert response.status_code == 200

    db = TestingSessionLocal()
    try:
        items = db.query(CatastoPerpetualSyncItem).filter_by(user_id=user_id).all()
        assert {item.scope for item in items} == {
            "ruolo_particella",
            "ruolo_soggetto",
            "consorzio_particella",
            "anagrafe_soggetto",
        }
        assert [item.priority for item in sorted(items, key=lambda item: item.priority)] == [
            10,
            20,
            30,
            40,
        ]
    finally:
        db.close()


def test_continuous_sync_uses_only_open_unleased_credentials() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()
    db = TestingSessionLocal()
    try:
        config = CatastoRuoloAutoSyncConfig(
            user_id=user_id,
            enabled=True,
            credential_ids=[credential_id],
        )
        db.add(config)
        db.flush()
        credential = db.get(CatastoCredential, UUID(credential_id))
        assert credential is not None
        batch = CatastoBatch(
            user_id=user_id,
            name="Manuale",
            total_items=1,
            status="processing",
        )
        db.add(batch)
        db.flush()
        db.add(
            CatastoCredentialLease(
                sister_username=credential.sister_username,
                credential_id=credential.id,
                batch_id=batch.id,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
        )
        db.commit()
        assert available_perpetual_credentials(db, config) == []

        db.query(CatastoCredentialLease).delete()
        credential.schedule_enabled = True
        credential.availability_schedule = {"weekly": {}}
        db.commit()
        assert available_perpetual_credentials(db, config) == []

        credential.schedule_enabled = False
        db.commit()
        assert [item.id for item in available_perpetual_credentials(db, config)] == [
            credential.id
        ]

        config.credential_profiles = {
            credential_id: {
                "enabled": True,
                "schedule_enabled": False,
                "availability_schedule": None,
            }
        }
        credential.schedule_enabled = True
        credential.availability_schedule = {"weekly": {}}
        db.commit()
        assert [item.id for item in available_perpetual_credentials(db, config)] == [
            credential.id
        ]

        config.credential_profiles = {
            credential_id: {
                "enabled": True,
                "schedule_enabled": True,
                "availability_schedule": {"weekly": {}},
            }
        }
        db.commit()
        assert available_perpetual_credentials(db, config) == []

        config.credential_profiles = {
            credential_id: {
                "enabled": False,
                "schedule_enabled": False,
                "availability_schedule": None,
            }
        }
        db.commit()
        assert _autosync_schedule(config, credential) == (True, None)
        assert available_perpetual_credentials(db, config) == []
    finally:
        db.close()


def test_autosync_profiles_update_active_pool_and_off_releases_only_autosync() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()
    profile = {
        "enabled": True,
        "schedule_enabled": False,
        "availability_schedule": None,
    }
    response = client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={
            "enabled": True,
            "credential_ids": [],
            "credential_profiles": {credential_id: profile},
        },
    )
    assert response.status_code == 200
    assert response.json()["credential_profiles"][credential_id] == profile
    assert response.json()["credential_ids"] == [credential_id]

    invalid_schedule = client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={
            "credential_profiles": {
                credential_id: {"enabled": True, "schedule_enabled": True}
            }
        },
    )
    assert invalid_schedule.status_code == 422

    missing_credential = client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={
            "credential_profiles": {
                str(uuid4()): {
                    "enabled": True,
                    "schedule_enabled": False,
                    "availability_schedule": None,
                }
            }
        },
    )
    assert missing_credential.status_code == 409

    stale_disabled_credential = client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={
            "credential_profiles": {
                str(uuid4()): {
                    "enabled": False,
                    "schedule_enabled": False,
                    "availability_schedule": None,
                }
            }
        },
    )
    assert stale_disabled_credential.status_code == 200
    assert stale_disabled_credential.json()["credential_profiles"] == {}
    assert stale_disabled_credential.json()["credential_ids"] == []

    assert client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={"enabled": False},
    ).status_code == 200
    assert client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={"enabled": True, "credential_profiles": {credential_id: profile}},
    ).status_code == 200

    db = TestingSessionLocal()
    try:
        manual = CatastoBatch(
            user_id=user_id,
            name="Manuale",
            batch_kind="manual_batch",
            status="processing",
            total_items=0,
        )
        autosync = CatastoBatch(
            user_id=user_id,
            name="AutoSync",
            batch_kind="perpetual_sync",
            status="processing",
            total_items=2,
            credential_ids=[credential_id],
        )
        db.add_all([manual, autosync])
        db.flush()
        autosync_request = CatastoVisuraRequest(
            batch_id=autosync.id,
            user_id=user_id,
            row_index=1,
            comune="Oristano",
            foglio="1",
            particella="1",
            tipo_visura="Sintetica",
            status=CatastoVisuraRequestStatus.PROCESSING.value,
        )
        completed_request = CatastoVisuraRequest(
            batch_id=autosync.id,
            user_id=user_id,
            row_index=2,
            comune="Oristano",
            foglio="1",
            particella="2",
            tipo_visura="Sintetica",
            status=CatastoVisuraRequestStatus.COMPLETED.value,
        )
        db.add_all([autosync_request, completed_request])
        db.commit()
        manual_id, autosync_id, autosync_request_id = manual.id, autosync.id, autosync_request.id
    finally:
        db.close()

    disabled_profile = {**profile, "enabled": False}
    response = client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={"credential_profiles": {credential_id: disabled_profile}},
    )
    assert response.status_code == 200

    db = TestingSessionLocal()
    try:
        assert db.get(CatastoBatch, autosync_id).credential_ids == []
        assert db.get(CatastoBatch, manual_id).status == "processing"
    finally:
        db.close()

    response = client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={"enabled": False},
    )
    assert response.status_code == 200

    db = TestingSessionLocal()
    try:
        assert db.get(CatastoBatch, autosync_id).status == "processing"
        assert db.get(CatastoBatch, autosync_id).current_operation == RELEASE_REQUESTED_OPERATION
        assert db.get(CatastoBatch, manual_id).status == "processing"
        released = db.get(CatastoVisuraRequest, autosync_request_id)
        assert released.status == CatastoVisuraRequestStatus.PROCESSING.value
        assert released.current_operation is None
        assert released.error_message is None
        released.status = CatastoVisuraRequestStatus.COMPLETED.value
        active_batch = db.get(CatastoBatch, autosync_id)
        active_batch.status = CatastoBatchStatus.COMPLETED.value
        db.commit()
    finally:
        db.close()

    assert client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={"enabled": True},
    ).status_code == 200
    db = TestingSessionLocal()
    try:
        pending_batch = CatastoBatch(
            user_id=user_id,
            name="AutoSync in attesa",
            batch_kind="perpetual_sync",
            status="processing",
            total_items=1,
            credential_ids=[credential_id],
        )
        db.add(pending_batch)
        db.flush()
        pending_request = CatastoVisuraRequest(
            batch_id=pending_batch.id,
            user_id=user_id,
            row_index=1,
            comune="Oristano",
            foglio="1",
            particella="3",
            tipo_visura="Sintetica",
            status=CatastoVisuraRequestStatus.PENDING.value,
        )
        db.add(pending_request)
        db.commit()
        pending_batch_id, pending_request_id = pending_batch.id, pending_request.id
    finally:
        db.close()

    assert client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={"enabled": False},
    ).status_code == 200
    db = TestingSessionLocal()
    try:
        assert db.get(CatastoBatch, pending_batch_id).status == CatastoBatchStatus.CANCELLED.value
        pending_request = db.get(CatastoVisuraRequest, pending_request_id)
        assert pending_request.status == CatastoVisuraRequestStatus.SKIPPED.value
        assert pending_request.current_operation == RELEASE_REQUESTED_OPERATION
    finally:
        db.close()


def test_continuous_sync_processes_permanent_role_campaigns_sequentially() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()
    config_response = client.put(
        "/elaborazioni/ruolo-autosync/config",
        headers=auth_headers(),
        json={
            "enabled": True,
            "credential_ids": [credential_id],
            "primary_enabled": True,
            "secondary_enabled": False,
            "role_parcel_refresh_hours": 24,
            "role_subject_refresh_hours": 48,
        },
    )
    assert config_response.status_code == 200
    assert client.post(
        "/elaborazioni/ruolo-autosync/refresh-source", headers=auth_headers()
    ).status_code == 200
    run = client.post("/elaborazioni/ruolo-autosync/run-now", headers=auth_headers())
    assert run.status_code == 200
    assert "avviato sul batch" in run.json()["message"]

    db = TestingSessionLocal()
    try:
        batch = db.query(CatastoBatch).filter_by(batch_kind="perpetual_sync").one()
        requests = (
            db.query(CatastoVisuraRequest)
            .filter_by(batch_id=batch.id)
            .order_by(CatastoVisuraRequest.row_index)
            .all()
        )
        assert batch.credential_id is None
        assert batch.credential_ids == [credential_id]
        assert [request.search_mode for request in requests] == ["immobile"]

        completed_at = datetime.now(UTC)
        requests[0].status = CatastoVisuraRequestStatus.COMPLETED.value
        requests[0].processed_at = completed_at
        batch.status = CatastoBatchStatus.COMPLETED.value
        batch.completed_at = completed_at
        config = db.query(CatastoRuoloAutoSyncConfig).filter_by(user_id=user_id).one()
        db.commit()
        reconcile_perpetual_sync_items(db, config)
        items = (
            db.query(CatastoPerpetualSyncItem)
            .filter_by(user_id=user_id)
            .order_by(CatastoPerpetualSyncItem.priority)
            .all()
        )
        assert [item.status for item in items] == ["completed", "pending"]
        assert items[0].next_due_at.replace(tzinfo=UTC) == completed_at

        subject_batch = ensure_perpetual_sync_batch(db, config)
        assert subject_batch is not None
        subject_requests = (
            db.query(CatastoVisuraRequest)
            .filter_by(batch_id=subject_batch.id)
            .order_by(CatastoVisuraRequest.row_index)
            .all()
        )
        assert [request.search_mode for request in subject_requests] == ["soggetto"]
        subject_requests[0].status = CatastoVisuraRequestStatus.COMPLETED.value
        subject_requests[0].processed_at = completed_at
        subject_batch.status = CatastoBatchStatus.COMPLETED.value
        subject_batch.completed_at = completed_at
        db.commit()
        reconcile_perpetual_sync_items(db, config)
        assert [item.status for item in items] == ["completed", "completed"]
    finally:
        db.close()


def test_perpetual_source_refresh_reopens_updates_and_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id, _credential_id = _seed_ruolo_autosync_fixture()
    db = TestingSessionLocal()
    try:
        config = db.query(CatastoRuoloAutoSyncConfig).filter_by(user_id=user_id).one_or_none()
        if config is None:
            config = CatastoRuoloAutoSyncConfig(user_id=user_id)
            db.add(config)
            db.commit()
        first_at = datetime.now(UTC) - timedelta(days=1)

        def target(source_at: datetime) -> PerpetualSourceTarget:
            return PerpetualSourceTarget(
                scope="ruolo_particella", target_key="oristano|12|603|", priority=10,
                search_mode="immobile", source_updated_at=source_at, comune="Oristano",
                comune_codice="G113#ORISTANO#5#5", catasto="Terreni", foglio="12",
                particella="603", request_type="STORICA",
            )

        monkeypatch.setattr(
            "app.services.elaborazioni_perpetual_sync.iter_enabled_targets",
            lambda *_args, **_kwargs: [target(first_at)],
        )
        assert refresh_perpetual_sync_sources(db, config) == {
            "created": 1, "updated": 0, "disabled": 0,
        }
        item = db.query(CatastoPerpetualSyncItem).filter_by(user_id=user_id).one()
        item.status = "completed"
        item.next_due_at = datetime.now(UTC) + timedelta(days=7)
        db.commit()

        monkeypatch.setattr(
            "app.services.elaborazioni_perpetual_sync.iter_enabled_targets",
            lambda *_args, **_kwargs: [target(first_at + timedelta(hours=1))],
        )
        assert refresh_perpetual_sync_sources(db, config)["updated"] == 1
        db.refresh(item)
        assert item.status == "pending"
        assert refresh_perpetual_sync_sources(db, config)["updated"] == 1

        monkeypatch.setattr(
            "app.services.elaborazioni_perpetual_sync.iter_enabled_targets",
            lambda *_args, **_kwargs: [],
        )
        assert refresh_perpetual_sync_sources(db, config)["disabled"] == 1
        db.refresh(item)
        assert item.status == "disabled"

        monkeypatch.setattr(
            "app.services.elaborazioni_perpetual_sync.iter_enabled_targets",
            lambda *_args, **_kwargs: [target(first_at + timedelta(hours=1))],
        )
        assert refresh_perpetual_sync_sources(db, config)["updated"] == 1
        db.refresh(item)
        assert item.status == "pending"
        assert item.retry_after is None

        monkeypatch.setattr(
            "app.services.elaborazioni_perpetual_sync.iter_enabled_targets",
            lambda *_args, **_kwargs: [],
        )
        item.status = "queued"
        db.commit()
        assert refresh_perpetual_sync_sources(db, config)["disabled"] == 0
        assert perpetual_sync_counts(db, user_id) == {"ruolo_particella": {"queued": 1}}
    finally:
        db.close()


def test_perpetual_reconcile_handles_request_states_and_missing_request() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()
    client.put(
        "/elaborazioni/ruolo-autosync/config", headers=auth_headers(),
        json={"enabled": True, "credential_ids": [credential_id], "primary_enabled": True},
    )
    client.post("/elaborazioni/ruolo-autosync/refresh-source", headers=auth_headers())
    client.post("/elaborazioni/ruolo-autosync/run-now", headers=auth_headers())
    db = TestingSessionLocal()
    try:
        config = db.query(CatastoRuoloAutoSyncConfig).filter_by(user_id=user_id).one()
        item = db.query(CatastoPerpetualSyncItem).filter_by(user_id=user_id).first()
        assert item is not None
        request = db.get(CatastoVisuraRequest, item.linked_request_id)
        assert request is not None

        for request_status, expected in (
            (CatastoVisuraRequestStatus.PENDING.value, "queued"),
            (CatastoVisuraRequestStatus.PROCESSING.value, "processing"),
            (CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value, "processing"),
        ):
            request.status = request_status
            request.attempts = 2
            db.commit()
            reconcile_perpetual_sync_items(db, config)
            db.refresh(item)
            assert item.status == expected
            assert item.attempt_count == 2

        request.status = CatastoVisuraRequestStatus.FAILED.value
        request.error_message = "errore temporaneo"
        request.last_error_code = None
        db.commit()
        reconcile_perpetual_sync_items(db, config)
        db.refresh(item)
        assert item.status == "pending"
        assert item.retry_after is not None
        first_retry_after = item.retry_after
        reconcile_perpetual_sync_items(db, config)
        db.refresh(item)
        assert item.retry_after == first_retry_after

        request.status = CatastoVisuraRequestStatus.SKIPPED.value
        request.last_error_code = "session_timeout"
        db.commit()
        reconcile_perpetual_sync_items(db, config)
        db.refresh(item)
        assert item.status == "skipped"
        assert item.retry_after is None

        request.current_operation = RELEASE_REQUESTED_OPERATION
        request.error_message = RELEASE_REQUESTED_MESSAGE
        item.status = "queued"
        db.commit()
        reconcile_perpetual_sync_items(db, config)
        db.refresh(item)
        assert item.status == "pending"
        assert item.linked_batch_id is None
        assert item.linked_request_id is None

        request.status = "custom_terminal_state"
        item.status = "processing"
        item.linked_batch_id = request.batch_id
        item.linked_request_id = request.id
        db.commit()
        reconcile_perpetual_sync_items(db, config)
        db.refresh(item)
        assert item.status == "processing"

        item.linked_request_id = uuid4()
        db.commit()
        reconcile_perpetual_sync_items(db, config)
        db.refresh(item)
        assert item.status == "pending"
        item.status = "completed"
        db.commit()
        reconcile_perpetual_sync_items(db, config)
        db.refresh(item)
        assert item.status == "completed"
    finally:
        db.close()


def test_perpetual_campaigns_process_role_parcels_before_role_subjects() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()
    db = TestingSessionLocal()
    try:
        config = CatastoRuoloAutoSyncConfig(
            user_id=user_id, enabled=True, credential_ids=[credential_id],
            primary_enabled=True, secondary_enabled=False, batch_size=20,
        )
        db.add(config)
        now = datetime.now(UTC)
        db.add_all([
            CatastoPerpetualSyncItem(
                user_id=user_id, scope="ruolo_particella", target_key="oristano|12|603|",
                priority=10, search_mode="immobile", comune="Oristano",
                comune_codice="G113#ORISTANO#5#5", catasto="Terreni", foglio="12",
                particella="603", request_type="STORICA", next_due_at=now,
            ),
            CatastoPerpetualSyncItem(
                user_id=user_id, scope="ruolo_soggetto", target_key="RSSMRA80A01H501U",
                priority=20, search_mode="soggetto", subject_kind="PF",
                subject_identifier="RSSMRA80A01H501U", request_type="ATTUALITA",
                next_due_at=now,
            ),
        ])
        db.commit()

        first = ensure_perpetual_sync_batch(db, config)
        assert first is not None
        first_requests = db.query(CatastoVisuraRequest).filter_by(batch_id=first.id).all()
        assert [request.search_mode for request in first_requests] == ["immobile"]

        first_requests[0].status = CatastoVisuraRequestStatus.COMPLETED.value
        first_requests[0].processed_at = now
        first.status = CatastoBatchStatus.COMPLETED.value
        first.completed_at = now
        db.commit()
        reconcile_perpetual_sync_items(db, config)

        second = ensure_perpetual_sync_batch(db, config)
        assert second is not None
        second_requests = db.query(CatastoVisuraRequest).filter_by(batch_id=second.id).all()
        assert [request.search_mode for request in second_requests] == ["soggetto"]
    finally:
        db.close()


def test_perpetual_planner_ignores_other_users_active_campaign_batch() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()
    db = TestingSessionLocal()
    try:
        other = db.query(ApplicationUser).filter_by(username="elaborazioni-super-admin").one()
        now = datetime.now(UTC)
        config = CatastoRuoloAutoSyncConfig(
            user_id=user_id,
            enabled=True,
            credential_ids=[credential_id],
            primary_enabled=True,
            secondary_enabled=False,
            batch_size=20,
        )
        db.add_all(
            [
                config,
                CatastoBatch(
                    user_id=other.id,
                    name="Other user AutoSync",
                    batch_kind="perpetual_sync",
                    status="pending",
                    total_items=1,
                ),
                CatastoPerpetualSyncItem(
                    user_id=user_id,
                    scope="ruolo_particella",
                    target_key="owner-parcel",
                    priority=10,
                    search_mode="immobile",
                    comune="Oristano",
                    comune_codice="G113#ORISTANO#5#5",
                    catasto="Terreni",
                    foglio="12",
                    particella="603",
                    request_type="STORICA",
                    next_due_at=now,
                ),
            ]
        )
        db.commit()

        batch = ensure_perpetual_sync_batch(db, config)

        assert batch is not None
        assert batch.user_id == user_id
    finally:
        db.close()


def test_perpetual_planner_waits_when_campaign_items_are_not_due() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()
    db = TestingSessionLocal()
    try:
        config = CatastoRuoloAutoSyncConfig(
            user_id=user_id, enabled=True, credential_ids=[credential_id],
            primary_enabled=True, secondary_enabled=False,
        )
        db.add(config)
        db.add(CatastoPerpetualSyncItem(
            user_id=user_id, scope="ruolo_particella", target_key="oristano|12|603|",
            priority=10, search_mode="immobile", comune="Oristano",
            comune_codice="G113#ORISTANO#5#5", catasto="Terreni", foglio="12",
            particella="603", request_type="STORICA",
            next_due_at=datetime.now(UTC) + timedelta(hours=1),
        ))
        db.commit()

        assert ensure_perpetual_sync_batch(db, config) is None
    finally:
        db.close()


def test_perpetual_secondary_scopes_remain_processable_after_role_campaigns() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()
    db = TestingSessionLocal()
    try:
        config = CatastoRuoloAutoSyncConfig(
            user_id=user_id, enabled=True, credential_ids=[credential_id],
            primary_enabled=False, secondary_enabled=True, batch_size=20,
        )
        db.add(config)
        db.add(CatastoPerpetualSyncItem(
            user_id=user_id, scope="consorzio_particella", target_key="oristano|12|603|",
            priority=30, search_mode="immobile", comune="Oristano",
            comune_codice="G113#ORISTANO#5#5", catasto="Terreni", foglio="12",
            particella="603", request_type="STORICA", next_due_at=datetime.now(UTC),
        ))
        db.commit()

        batch = ensure_perpetual_sync_batch(db, config)

        assert batch is not None
        requests = db.query(CatastoVisuraRequest).filter_by(batch_id=batch.id).all()
        assert [request.search_mode for request in requests] == ["immobile"]
    finally:
        db.close()


def test_perpetual_failures_stop_after_three_attempts_and_manual_retry_requeues() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()
    db = TestingSessionLocal()
    try:
        config = CatastoRuoloAutoSyncConfig(
            user_id=user_id, enabled=True, credential_ids=[credential_id],
            primary_enabled=True, secondary_enabled=False,
        )
        db.add(config)
        item = CatastoPerpetualSyncItem(
            user_id=user_id, scope="ruolo_particella", target_key="oristano|12|603|",
            priority=10, search_mode="immobile", comune="Oristano",
            comune_codice="G113#ORISTANO#5#5", catasto="Terreni", foglio="12",
            particella="603", request_type="STORICA", next_due_at=datetime.now(UTC),
        )
        db.add(item)
        db.commit()
        batch = ensure_perpetual_sync_batch(db, config)
        assert batch is not None
        request = db.query(CatastoVisuraRequest).filter_by(batch_id=batch.id).one()
        request.status = CatastoVisuraRequestStatus.FAILED.value
        request.attempts = 3
        request.error_message = "errore tecnico"
        request.last_error_code = "sister_timeout"
        db.commit()

        reconcile_perpetual_sync_items(db, config)
        db.refresh(item)
        assert item.status == "failed"
        assert item.attempt_count == 3
        assert item.retry_after is None

        response = client.post(
            "/elaborazioni/ruolo-autosync/campaigns/ruolo_particella/retry-failed",
            headers=auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["message"].startswith("1 elementi falliti rimessi in coda")
        db.refresh(item)
        assert item.status == "pending"
        assert item.attempt_count == 0
        assert item.linked_batch_id is None
        assert item.linked_request_id is None
        assert item.last_error_message is None
    finally:
        db.close()


def test_perpetual_skipped_items_are_terminal_without_automatic_retry() -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()
    db = TestingSessionLocal()
    try:
        config = CatastoRuoloAutoSyncConfig(
            user_id=user_id, enabled=True, credential_ids=[credential_id],
            primary_enabled=True, secondary_enabled=False,
        )
        db.add(config)
        item = CatastoPerpetualSyncItem(
            user_id=user_id, scope="ruolo_particella", target_key="oristano|12|603|",
            priority=10, search_mode="immobile", comune="Oristano",
            comune_codice="G113#ORISTANO#5#5", catasto="Terreni", foglio="12",
            particella="603", request_type="STORICA", next_due_at=datetime.now(UTC),
        )
        db.add(item)
        db.commit()
        batch = ensure_perpetual_sync_batch(db, config)
        assert batch is not None
        request = db.query(CatastoVisuraRequest).filter_by(batch_id=batch.id).one()
        request.status = CatastoVisuraRequestStatus.SKIPPED.value
        request.attempts = 1
        request.error_message = "saltata dall'operatore"
        db.commit()

        reconcile_perpetual_sync_items(db, config)
        db.refresh(item)

        assert item.status == "skipped"
        assert item.retry_after is None
    finally:
        db.close()


def test_perpetual_campaign_items_endpoint_is_owner_scoped_and_paginated() -> None:
    db = TestingSessionLocal()
    try:
        owner = db.query(ApplicationUser).filter_by(username="elaborazioni-admin").one()
        other = db.query(ApplicationUser).filter_by(username="elaborazioni-super-admin").one()
        now = datetime.now(UTC)
        db.add_all(
            [
                CatastoPerpetualSyncItem(
                    user_id=owner.id,
                    scope="ruolo_particella",
                    target_key="owner-parcel",
                    priority=10,
                    search_mode="immobile",
                    comune="Oristano",
                    comune_codice="G113#ORISTANO#5#5",
                    catasto="Terreni",
                    foglio="12",
                    particella="603",
                    request_type="STORICA",
                    next_due_at=now,
                ),
                CatastoPerpetualSyncItem(
                    user_id=other.id,
                    scope="ruolo_particella",
                    target_key="other-parcel",
                    priority=10,
                    search_mode="immobile",
                    comune="Cabras",
                    comune_codice="B314#CABRAS#5#5",
                    catasto="Terreni",
                    foglio="4",
                    particella="99",
                    request_type="STORICA",
                    next_due_at=now,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/elaborazioni/ruolo-autosync/campaigns/ruolo_particella/items?limit=1&offset=0",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["limit"] == 1
    assert payload["offset"] == 0
    assert payload["has_more"] is False
    assert [item["target_key"] for item in payload["items"]] == ["owner-parcel"]


def test_retry_perpetual_campaign_failures_service_rejects_unknown_scope() -> None:
    db = TestingSessionLocal()
    try:
        with pytest.raises(ValueError, match="Campagna AutoSync non valida"):
            retry_perpetual_sync_failures(db, 1, "unknown")
    finally:
        db.close()


def test_retry_perpetual_campaign_failures_returns_zero_without_failed_items() -> None:
    db = TestingSessionLocal()
    try:
        assert retry_perpetual_sync_failures(db, 1, "ruolo_particella") == 0
    finally:
        db.close()


def test_retry_perpetual_campaign_failures_endpoint_rejects_unknown_scope() -> None:
    response = client.post(
        "/elaborazioni/ruolo-autosync/campaigns/unknown/retry-failed",
        headers=auth_headers(),
    )
    assert response.status_code == 422


def test_completed_perpetual_items_are_requeued_only_when_source_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, _credential_id = _seed_ruolo_autosync_fixture()
    db = TestingSessionLocal()
    try:
        config = CatastoRuoloAutoSyncConfig(user_id=user_id, enabled=True, primary_enabled=True)
        db.add(config)
        source_at = datetime.now(UTC) - timedelta(days=1)

        def target(updated_at: datetime) -> PerpetualSourceTarget:
            return PerpetualSourceTarget(
                scope="ruolo_particella", target_key="oristano|12|603|", priority=10,
                search_mode="immobile", source_updated_at=updated_at, comune="Oristano",
                comune_codice="G113#ORISTANO#5#5", catasto="Terreni", foglio="12",
                particella="603", request_type="STORICA",
            )

        monkeypatch.setattr(
            "app.services.elaborazioni_perpetual_sync.iter_enabled_targets",
            lambda *_args, **_kwargs: [target(source_at)],
        )
        refresh_perpetual_sync_sources(db, config)
        item = db.query(CatastoPerpetualSyncItem).filter_by(user_id=user_id).one()
        item.status = "completed"
        item.next_due_at = datetime.now(UTC) - timedelta(days=30)
        db.commit()

        refresh_perpetual_sync_sources(db, config)
        db.refresh(item)
        assert item.status == "completed"

        monkeypatch.setattr(
            "app.services.elaborazioni_perpetual_sync.iter_enabled_targets",
            lambda *_args, **_kwargs: [target(source_at + timedelta(minutes=1))],
        )
        refresh_perpetual_sync_sources(db, config)
        db.refresh(item)
        assert item.status == "pending"
    finally:
        db.close()


def test_perpetual_planner_guards_and_batch_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id, credential_id = _seed_ruolo_autosync_fixture()
    db = TestingSessionLocal()
    try:
        config = CatastoRuoloAutoSyncConfig(
            user_id=user_id, enabled=False, credential_ids=[credential_id], primary_enabled=True,
        )
        db.add(config)
        db.commit()
        assert ensure_perpetual_sync_batch(db, config) is None

        config.enabled = True
        config.credential_ids = ["invalid-uuid"]
        db.commit()
        assert ensure_perpetual_sync_batch(db, config) is None

        config.credential_ids = [credential_id]
        db.commit()
        assert ensure_perpetual_sync_batch(db, config) is None

        item = CatastoPerpetualSyncItem(
            user_id=user_id, scope="ruolo_particella", target_key="broken", priority=10,
            search_mode="immobile", status="pending", next_due_at=datetime.now(UTC),
            comune="Oristano", comune_codice=None, foglio="12", particella="603",
        )
        db.add(item)
        db.commit()
        assert ensure_perpetual_sync_batch(db, config) is None

        item.comune_codice = "G113#ORISTANO#5#5"
        monkeypatch.setattr(
            "app.services.elaborazioni_perpetual_sync.start_batch",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(BatchConflictError("batch concorrente")),
        )
        db.commit()
        assert ensure_perpetual_sync_batch(db, config) is None
        db.refresh(item)
        assert item.status == "pending"
        assert item.linked_request_id is None
        assert config.last_error_message == "batch concorrente"

        active = db.query(CatastoBatch).filter_by(batch_kind="perpetual_sync").one()
        active.status = CatastoBatchStatus.PROCESSING.value
        db.commit()
        assert ensure_perpetual_sync_batch(db, config) is None
    finally:
        db.close()


def test_perpetual_maintenance_skips_disabled_config_before_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(enabled=False, last_source_refresh_at=None)
    calls: list[str] = []
    monkeypatch.setattr(
        "app.services.elaborazioni_perpetual_sync.refresh_perpetual_sync_sources",
        lambda *_args: calls.append("refresh"),
    )
    monkeypatch.setattr(
        "app.services.elaborazioni_perpetual_sync.ensure_perpetual_sync_batch",
        lambda *_args: calls.append("ensure"),
    )

    assert maintain_perpetual_sync(SimpleNamespace(), config) is None  # type: ignore[arg-type]
    assert calls == []


def test_perpetual_maintenance_refresh_interval_and_subject_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(enabled=True, last_source_refresh_at=None)
    calls: list[str] = []
    monkeypatch.setattr(
        "app.services.elaborazioni_perpetual_sync.refresh_perpetual_sync_sources",
        lambda *_args: calls.append("refresh"),
    )
    monkeypatch.setattr(
        "app.services.elaborazioni_perpetual_sync.ensure_perpetual_sync_batch",
        lambda *_args: calls.append("ensure"),
    )
    maintain_perpetual_sync(SimpleNamespace(), config)  # type: ignore[arg-type]
    assert calls == ["refresh", "ensure"]
    calls.clear()
    config.last_source_refresh_at = datetime.now(UTC)
    maintain_perpetual_sync(SimpleNamespace(), config)  # type: ignore[arg-type]
    assert calls == ["ensure"]
    assert _subject_target(
        scope="anagrafe_soggetto", priority=40, subject_id=None,
        identifier="  ", name=None, updated_at=None,
    ) is None
    assert load_enabled_targets(SimpleNamespace(), primary=False, secondary=False) == []  # type: ignore[arg-type]


def test_perpetual_source_iterator_is_lazy() -> None:
    import app.services.elaborazioni_perpetual_sources as sources

    iterator = sources.iter_enabled_targets(
        SimpleNamespace(),  # type: ignore[arg-type]
        primary=False,
        secondary=False,
    )

    assert not isinstance(iterator, list)
    assert list(iterator) == []


def test_perpetual_source_chunk_and_loader_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.elaborazioni_perpetual_sources as sources
    import app.services.elaborazioni_perpetual_sync as sync

    target = PerpetualSourceTarget(
        scope="consorzio_particella",
        target_key="boundary",
        priority=30,
        search_mode="immobile",
        source_updated_at=None,
    )
    chunks = list(sync._target_chunks(target for _ in range(1_001)))
    assert [len(chunk) for chunk in chunks] == [1_000, 1]

    monkeypatch.setattr(
        sources,
        "iter_consortium_parcel_targets",
        lambda _db: iter([target]),
    )
    monkeypatch.setattr(
        sources,
        "iter_registry_subject_targets",
        lambda _db: iter([target]),
    )
    assert sources.load_consortium_parcel_targets(SimpleNamespace()) == [target]
    assert sources.load_registry_subject_targets(SimpleNamespace()) == [target]


def test_perpetual_disable_missing_items_flushes_full_chunk() -> None:
    import app.services.elaborazioni_perpetual_sync as sync

    user_id, _credential_id = _seed_ruolo_autosync_fixture()
    db = TestingSessionLocal()
    try:
        db.add_all(
            [
                CatastoPerpetualSyncItem(
                    user_id=user_id,
                    scope="ruolo_particella",
                    target_key=f"missing-{index}",
                    priority=10,
                    search_mode="immobile",
                    next_due_at=datetime.now(UTC),
                )
                for index in range(1_000)
            ]
        )
        db.commit()

        assert sync._disable_missing_items(db, user_id, set()) == 1_000
        db.commit()
        assert db.query(CatastoPerpetualSyncItem).filter_by(status="disabled").count() == 1_000
    finally:
        db.close()


def test_perpetual_role_sources_only_use_latest_completed_import() -> None:
    db = TestingSessionLocal()
    try:
        jobs = [
            RuoloImportJob(anno_tributario=2024, status="completed"),
            RuoloImportJob(anno_tributario=2025, status="completed"),
            RuoloImportJob(anno_tributario=2026, status="processing"),
        ]
        db.add_all(jobs)
        db.flush()
        for index, job in enumerate(jobs, start=1):
            avviso = RuoloAvviso(
                import_job_id=job.id,
                codice_cnc=f"LATEST-{index}",
                anno_tributario=job.anno_tributario,
                codice_fiscale_raw=f"RSSMRA80A01H50{index}X",
                nominativo_raw=f"Soggetto {index}",
            )
            db.add(avviso)
            db.flush()
            partita = RuoloPartita(
                avviso_id=avviso.id,
                codice_partita=f"P-{index}",
                comune_nome="Oristano",
            )
            db.add(partita)
            db.flush()
            db.add(
                RuoloParticella(
                    partita_id=partita.id,
                    anno_tributario=job.anno_tributario,
                    foglio=str(index),
                    particella=str(index * 10),
                )
            )
        db.commit()

        parcels = load_ruolo_parcel_targets(db)
        subjects = load_ruolo_subject_targets(db)

        assert [(item.foglio, item.particella) for item in parcels] == [("2", "20")]
        assert [item.subject_identifier for item in subjects] == ["RSSMRA80A01H502X"]
    finally:
        db.close()


def test_perpetual_refresh_consumes_streaming_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, _credential_id = _seed_ruolo_autosync_fixture()
    db = TestingSessionLocal()
    try:
        config = CatastoRuoloAutoSyncConfig(user_id=user_id)
        db.add(config)
        db.commit()
        source_at = datetime.now(UTC)
        streamed_target = PerpetualSourceTarget(
            scope="ruolo_particella",
            target_key="oristano|12|603|",
            priority=10,
            search_mode="immobile",
            source_updated_at=source_at,
            comune="Oristano",
            foglio="12",
            particella="603",
        )
        monkeypatch.setattr(
            "app.services.elaborazioni_perpetual_sync.iter_enabled_targets",
            lambda *_args, **_kwargs: iter([streamed_target]),
            raising=False,
        )

        assert refresh_perpetual_sync_sources(db, config)["created"] == 1
    finally:
        db.close()


def test_perpetual_sources_deduplicate_parcels_and_credentials_stay_owner_scoped() -> None:
    _user_id, _credential_id = _seed_ruolo_autosync_fixture()
    db = TestingSessionLocal()
    try:
        partita = db.query(RuoloPartita).one()
        db.add(
            RuoloParticella(
                partita_id=partita.id, anno_tributario=2025, foglio="12",
                particella="603", subalterno=None, cat_particella_id=uuid4(),
            )
        )
        ordinary = ApplicationUser(
            username="autosync-owner", email="autosync-owner@example.local",
            password_hash=hash_password("secret123"), role=ApplicationUserRole.OPERATOR.value,
            is_active=True,
        )
        db.add(ordinary)
        db.flush()
        own_credential = CatastoCredential(
            user_id=ordinary.id, label="Owner SISTER", sister_username="owner-sister",
            sister_password_encrypted=get_credential_fernet().encrypt(b"secret-pass"),
            ufficio_provinciale="ORISTANO Territorio", active=True,
        )
        db.add(own_credential)
        db.flush()
        config = CatastoRuoloAutoSyncConfig(user_id=ordinary.id, credential_ids=None)
        db.add(config)
        db.commit()

        assert len(load_ruolo_parcel_targets(db)) == 1
        assert [credential.id for credential in available_perpetual_credentials(db, config)] == [
            own_credential.id
        ]
    finally:
        db.close()


def test_perpetual_config_validates_priority_and_non_super_admin_credential() -> None:
    import app.services.elaborazioni_ruolo_autosync as autosync_module

    db = TestingSessionLocal()
    try:
        user = ApplicationUser(
            username="continuous-operator", email="continuous-operator@example.local",
            password_hash=hash_password("secret123"), role=ApplicationUserRole.OPERATOR.value,
            is_active=True,
        )
        db.add(user)
        db.flush()
        credential = CatastoCredential(
            user_id=user.id, label="Operator SISTER", sister_username="operator-sister",
            sister_password_encrypted=get_credential_fernet().encrypt(b"secret-pass"),
            ufficio_provinciale="ORISTANO Territorio", active=True,
        )
        db.add(credential)
        db.commit()
        updated = autosync_module.update_ruolo_autosync_config(
            db, user.id,
            CatastoRuoloAutoSyncConfigUpdateRequest(
                enabled=True, credential_ids=[credential.id], primary_enabled=True,
            ),
        )
        assert updated.credential_ids == [str(credential.id)]
        with pytest.raises(ValueError, match="almeno una priorita"):
            autosync_module.update_ruolo_autosync_config(
                db, user.id,
                CatastoRuoloAutoSyncConfigUpdateRequest(
                    primary_enabled=False, secondary_enabled=False,
                ),
            )
    finally:
        db.close()


def test_perpetual_scheduler_continues_after_owner_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.elaborazioni_ruolo_autosync as autosync_module

    db = TestingSessionLocal()
    try:
        db.add(
            ApplicationUser(
                username="continuous-third", email="continuous-third@example.local",
                password_hash=hash_password("secret123"), role=ApplicationUserRole.SUPER_ADMIN.value,
                is_active=True,
            )
        )
        db.commit()
        users = db.query(ApplicationUser).order_by(ApplicationUser.id).all()
        configs = [CatastoRuoloAutoSyncConfig(user_id=user.id, enabled=True) for user in users]
        db.add_all(configs)
        db.commit()

        def run(_db, user_id):
            if user_id == users[0].id:
                return object()
            if user_id == users[1].id:
                return None
            raise RuntimeError("planner failure")

        monkeypatch.setattr(autosync_module, "maintain_ruolo_autosync", run)
        assert autosync_module.run_perpetual_sync_maintenance_for_all_users(db) == 1
        db.refresh(configs[2])
        assert configs[2].last_error_message == "planner failure"
    finally:
        db.close()

def test_auto_job_controls_dashboard_lists_controls_and_updates_visure_toggle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.visure_nas_router_cron", "15 */2 * * *")
    monkeypatch.setattr("app.core.config.settings.visure_nas_inbox_path", "/volume1/pubblica condivisa/GAIA/Visure")
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_cron", "5 2 * * *")
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_timezone", "Europe/Rome")
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_retention_count", 5)

    response = client.get("/elaborazioni/auto-job-controls", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    keys = {item["key"] for item in payload}
    assert {
        "visure_nas_router",
        "anpr_daily_sync",
        "ruolo_visure_autosync",
        "whitecompany_daily_sync",
        "whitecompany_operazioni_live_sync",
        "elaborazioni_db_backup",
    } <= keys

    update_response = client.put(
        "/elaborazioni/auto-job-controls/visure_nas_router",
        json={"enabled": True},
        headers=auth_headers("elaborazioni-super-admin"),
    )

    assert update_response.status_code == 200
    assert update_response.json()["enabled"] is True

    db = TestingSessionLocal()
    try:
        row = db.query(ElaborazioneAutoJobConfig).filter(ElaborazioneAutoJobConfig.job_key == "visure_nas_router").one()
        assert row.enabled is True
    finally:
        db.close()


def test_auto_job_controls_dashboard_updates_anpr_toggle() -> None:
    db = TestingSessionLocal()
    try:
        db.add(AnprSyncConfig(id=1, job_enabled=True, job_cron="0 8-17 * * *", max_calls_per_day=90))
        db.commit()
    finally:
        db.close()

    response = client.put(
        "/elaborazioni/auto-job-controls/anpr_daily_sync",
        json={"enabled": False},
        headers=auth_headers("elaborazioni-super-admin"),
    )

    assert response.status_code == 200
    assert response.json()["enabled"] is False

    db = TestingSessionLocal()
    try:
        config = db.get(AnprSyncConfig, 1)
        assert config is not None
        assert config.job_enabled is False
    finally:
        db.close()
