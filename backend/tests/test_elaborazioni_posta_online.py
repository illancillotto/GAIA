from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timedelta
import sys
from types import ModuleType

from cryptography.fernet import Fernet
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

if "shapely.geometry" not in sys.modules:
    shapely_module = ModuleType("shapely")
    shapely_geometry_module = ModuleType("shapely.geometry")
    shapely_geometry_module.shape = lambda value: value
    shapely_module.geometry = shapely_geometry_module
    sys.modules["shapely"] = shapely_module
    sys.modules["shapely.geometry"] = shapely_geometry_module

if "geoalchemy2.shape" not in sys.modules:
    geoalchemy2_module = ModuleType("geoalchemy2")
    geoalchemy2_shape_module = ModuleType("geoalchemy2.shape")
    geoalchemy2_shape_module.to_shape = lambda value: value
    geoalchemy2_module.shape = geoalchemy2_shape_module
    sys.modules["geoalchemy2"] = geoalchemy2_module
    sys.modules["geoalchemy2.shape"] = geoalchemy2_shape_module

if "shapefile" not in sys.modules:
    shapefile_module = ModuleType("shapefile")
    shapefile_module.Reader = object
    sys.modules["shapefile"] = shapefile_module

if "pypdf" not in sys.modules:
    pypdf_module = ModuleType("pypdf")
    pypdf_module.PdfReader = object
    sys.modules["pypdf"] = pypdf_module

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.posta_online import PostaOnlineRegisteredMailSyncJob
from app.modules.elaborazioni.posta_online.schemas import PostaOnlineRegisteredMailSyncJobCreateRequest
from app.services.catasto_credentials import get_credential_fernet
from app.services.elaborazioni_posta_online import (
    expire_stale_registered_mail_sync_jobs,
    get_credential,
    has_available_credential,
    mark_credential_error,
    mark_credential_used,
    pick_credential,
    prepare_registered_mail_sync_jobs_for_recovery,
)


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
client = TestClient(app)


def test_registered_mail_sync_payload_defaults_to_full_sync() -> None:
    payload = PostaOnlineRegisteredMailSyncJobCreateRequest()

    assert payload.max_pages is None
    assert payload.max_details is None


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    generated_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr("app.services.catasto_credentials.settings.credential_master_key", generated_key)
    monkeypatch.setattr("app.core.config.settings.credential_master_key", generated_key)
    get_credential_fernet.cache_clear()

    db = TestingSessionLocal()
    db.add(
        ApplicationUser(
            username="posta-online-admin",
            email="posta-online@example.local",
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


def auth_headers() -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "posta-online-admin", "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_posta_online_credentials_and_jobs_api_flow() -> None:
    headers = auth_headers()
    create_response = client.post(
        "/elaborazioni/posta-online/credentials",
        headers=headers,
        json={
            "label": "Poste Business",
            "username": "utente-poste",
            "password": "secret",
            "min_delay_ms": 4000,
            "max_delay_ms": 8000,
        },
    )
    assert create_response.status_code == 201
    credential = create_response.json()
    assert credential["username"] == "utente-poste"
    assert credential["min_delay_ms"] == 4000
    assert "password" not in credential

    list_response = client.get("/elaborazioni/posta-online/credentials", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == credential["id"]

    get_response = client.get(f"/elaborazioni/posta-online/credentials/{credential['id']}", headers=headers)
    assert get_response.status_code == 200

    patch_response = client.patch(
        f"/elaborazioni/posta-online/credentials/{credential['id']}",
        headers=headers,
        json={"label": "Poste Online aggiornato", "max_delay_ms": 9000},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["label"] == "Poste Online aggiornato"
    assert patch_response.json()["max_delay_ms"] == 9000

    invalid_patch = client.patch(
        f"/elaborazioni/posta-online/credentials/{credential['id']}",
        headers=headers,
        json={"min_delay_ms": 10000, "max_delay_ms": 2000},
    )
    assert invalid_patch.status_code == 422
    service_invalid_patch = client.patch(
        f"/elaborazioni/posta-online/credentials/{credential['id']}",
        headers=headers,
        json={"min_delay_ms": 10000},
    )
    assert service_invalid_patch.status_code == 422
    missing_patch = client.patch(
        "/elaborazioni/posta-online/credentials/999999",
        headers=headers,
        json={"label": "missing"},
    )
    assert missing_patch.status_code == 404

    full_patch_response = client.patch(
        f"/elaborazioni/posta-online/credentials/{credential['id']}",
        headers=headers,
        json={
            "label": "Poste Online completo",
            "username": "utente-poste-2",
            "password": "secret-2",
            "active": False,
            "allowed_hours_start": 1,
            "allowed_hours_end": 22,
            "min_delay_ms": 2000,
            "max_delay_ms": 6000,
        },
    )
    assert full_patch_response.status_code == 200
    patched = full_patch_response.json()
    assert patched["username"] == "utente-poste-2"
    assert patched["active"] is False
    assert patched["allowed_hours_start"] == 1
    assert patched["allowed_hours_end"] == 22
    assert patched["min_delay_ms"] == 2000
    assert patched["max_delay_ms"] == 6000
    assert client.patch(
        f"/elaborazioni/posta-online/credentials/{credential['id']}",
        headers=headers,
        json={"active": True},
    ).status_code == 200

    test_job_response = client.post(
        f"/elaborazioni/posta-online/credentials/{credential['id']}/test",
        headers=headers,
        json={"min_delay_ms": 2000, "max_delay_ms": 3000},
    )
    assert test_job_response.status_code == 202
    test_job = test_job_response.json()
    assert test_job["status"] == "pending"
    assert test_job["mode"] == "credential_test"
    assert test_job["payload_json"]["credential_id"] == credential["id"]
    assert test_job["payload_json"]["min_delay_ms"] == 2000

    invalid_test_job = client.post(
        f"/elaborazioni/posta-online/credentials/{credential['id']}/test",
        headers=headers,
        json={"min_delay_ms": 4000, "max_delay_ms": 2000},
    )
    assert invalid_test_job.status_code == 422
    assert client.post("/elaborazioni/posta-online/credentials/999999/test", headers=headers).status_code == 404

    missing_credential_job = client.post(
        "/elaborazioni/posta-online/raccomandate/jobs",
        headers=headers,
        json={"credential_id": 999999},
    )
    assert missing_credential_job.status_code == 503
    invalid_job_delay = client.post(
        "/elaborazioni/posta-online/raccomandate/jobs",
        headers=headers,
        json={"min_delay_ms": 4000, "max_delay_ms": 2000},
    )
    assert invalid_job_delay.status_code == 422

    job_response = client.post(
        "/elaborazioni/posta-online/raccomandate/jobs",
        headers=headers,
        json={
            "credential_id": credential["id"],
            "annualita": [2022, 2023],
            "max_pages": 2,
            "max_details": 3,
            "min_delay_ms": 5000,
            "max_delay_ms": 7000,
        },
    )
    assert job_response.status_code == 202
    job = job_response.json()
    assert job["status"] == "pending"
    assert job["payload_json"]["annualita"] == [2022, 2023]
    assert job["payload_json"]["max_details"] == 3

    assert client.get("/elaborazioni/posta-online/raccomandate/jobs", headers=headers).json()[0]["id"] == job["id"]
    assert client.get(f"/elaborazioni/posta-online/raccomandate/jobs/{job['id']}", headers=headers).status_code == 200
    assert client.delete(f"/elaborazioni/posta-online/raccomandate/jobs/{job['id']}", headers=headers).status_code == 409
    assert client.post(f"/elaborazioni/posta-online/raccomandate/jobs/{job['id']}/run", headers=headers).status_code == 200

    db = TestingSessionLocal()
    db_job = db.get(PostaOnlineRegisteredMailSyncJob, job["id"])
    assert db_job is not None
    db_job.status = "succeeded"
    db.commit()
    db.close()

    assert client.delete(f"/elaborazioni/posta-online/raccomandate/jobs/{job['id']}", headers=headers).status_code == 204
    assert client.get(f"/elaborazioni/posta-online/raccomandate/jobs/{job['id']}", headers=headers).status_code == 404
    assert client.delete("/elaborazioni/posta-online/raccomandate/jobs/999999", headers=headers).status_code == 404
    assert client.post("/elaborazioni/posta-online/raccomandate/jobs/999999/run", headers=headers).status_code == 404
    assert client.get("/elaborazioni/posta-online/credentials/999999", headers=headers).status_code == 404
    assert client.delete("/elaborazioni/posta-online/credentials/999999", headers=headers).status_code == 404
    assert client.delete(f"/elaborazioni/posta-online/credentials/{credential['id']}", headers=headers).status_code == 204


def test_posta_online_service_credential_selection_and_recovery() -> None:
    headers = auth_headers()
    credential_id = client.post(
        "/elaborazioni/posta-online/credentials",
        headers=headers,
        json={
            "label": "Poste",
            "username": "poste-user",
            "password": "secret",
            "allowed_hours_start": 0,
            "allowed_hours_end": 23,
        },
    ).json()["id"]

    db = TestingSessionLocal()
    credential = get_credential(db, credential_id)
    assert credential is not None
    selected, password = pick_credential(db)
    assert selected.id == credential_id
    assert password == "secret"
    assert has_available_credential(db)
    mark_credential_used(db, credential_id)
    db.refresh(credential)
    assert credential.last_used_at is not None
    mark_credential_used(db, 999_999)
    mark_credential_error(db, None, "missing")
    mark_credential_error(db, 999_999, "missing")

    for index in range(5):
        mark_credential_error(db, credential_id, f"errore {index}")
    db.refresh(credential)
    assert credential.active is False
    assert has_available_credential(db, credential_id) is False

    credential.active = True
    credential.allowed_hours_start = (datetime.now().hour + 1) % 24
    credential.allowed_hours_end = credential.allowed_hours_start
    db.commit()
    assert has_available_credential(db, credential_id) is False
    credential.allowed_hours_start = 23
    credential.allowed_hours_end = 1
    db.commit()
    assert has_available_credential(db, credential_id) is False

    job = PostaOnlineRegisteredMailSyncJob(
        credential_id=credential_id,
        status="processing",
        started_at=datetime.now() - timedelta(minutes=5),
        payload_json={"credential_id": credential_id, "annualita": [2022, 2023]},
    )
    db.add(job)
    db.commit()
    recovered = prepare_registered_mail_sync_jobs_for_recovery(db)
    assert recovered == [job.id]
    assert job.status == "queued_resume"

    stale_job = PostaOnlineRegisteredMailSyncJob(
        credential_id=credential_id,
        status="processing",
        completed_at=datetime.now(),
        payload_json={"credential_id": credential_id, "annualita": [2022, 2023]},
    )
    db.add(stale_job)
    db.commit()
    expire_stale_registered_mail_sync_jobs(db)
    assert stale_job.status == "failed"
    assert stale_job.error_detail == "Job in stato incoerente"
    db.close()


def test_posta_online_validation_rejects_bad_payloads() -> None:
    headers = auth_headers()
    db = TestingSessionLocal()
    try:
        assert has_available_credential(db) is False
        with pytest.raises(RuntimeError, match="Nessuna credenziale Poste Online disponibile"):
            pick_credential(db)
    finally:
        db.close()

    invalid_credential = client.post(
        "/elaborazioni/posta-online/credentials",
        headers=headers,
        json={
            "label": "Poste",
            "username": "poste-user",
            "password": "secret",
            "min_delay_ms": 9000,
            "max_delay_ms": 3000,
        },
    )
    assert invalid_credential.status_code == 422

    invalid_job = client.post(
        "/elaborazioni/posta-online/raccomandate/jobs",
        headers=headers,
        json={"annualita": [2021]},
    )
    assert invalid_job.status_code == 422
