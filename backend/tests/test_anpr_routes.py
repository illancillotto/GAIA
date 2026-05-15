from __future__ import annotations

import uuid
from collections.abc import Generator
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.accessi.routes.auth import router as auth_router
from app.modules.utenze.anpr.auth import PdndConfigurationError
from app.modules.utenze.anpr.routes import router as anpr_router


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
app = FastAPI()
app.include_router(auth_router)
app.include_router(anpr_router)
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
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _create_user(role: str, *, module_utenze: bool = True) -> ApplicationUser:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username=f"{role}_user",
        email=f"{role}@example.local",
        password_hash=hash_password("secret123"),
        role=role,
        is_active=True,
        module_accessi=True,
        module_utenze=module_utenze,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _auth_headers(username: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": "secret123"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_post_sync_subject_allows_reviewer_and_returns_result(monkeypatch: pytest.MonkeyPatch) -> None:
    reviewer = _create_user(ApplicationUserRole.REVIEWER.value)
    subject_id = uuid.uuid4()

    async def fake_sync_single_subject(subject_id: str, db, triggered_by: str, auth, client):
        assert triggered_by == f"user:{reviewer.id}"
        return {
            "subject_id": subject_id,
            "success": True,
            "esito": "alive",
            "data_decesso": None,
            "anpr_id": "123456789",
            "calls_made": 2,
            "message": "ok",
        }

    monkeypatch.setattr("app.modules.utenze.anpr.routes.sync_single_subject", fake_sync_single_subject)

    response = client.post(f"/utenze/anpr/sync/{subject_id}", headers=_auth_headers(reviewer.username))

    assert response.status_code == 200
    body = response.json()
    assert body["subject_id"] == str(subject_id)
    assert body["esito"] == "alive"
    assert body["calls_made"] == 2


def test_post_preview_lookup_returns_body_for_reviewer(monkeypatch: pytest.MonkeyPatch) -> None:
    reviewer = _create_user(ApplicationUserRole.REVIEWER.value)

    async def fake_lookup(codice_fiscale: str, *, client=None, auth_manager=None):
        assert codice_fiscale == "RSSMRA80A01H501U"
        from app.modules.utenze.anpr.schemas import AnprPreviewLookupResponse

        return AnprPreviewLookupResponse(
            success=True,
            anpr_id="ID-999",
            stato_anpr="alive",
            calls_made=2,
            message="ok preview",
        )

    monkeypatch.setattr("app.modules.utenze.anpr.routes.lookup_anpr_by_codice_fiscale", fake_lookup)

    response = client.post(
        "/utenze/anpr/preview-lookup",
        headers=_auth_headers(reviewer.username),
        json={"codice_fiscale": "RSSMRA80A01H501U"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["anpr_id"] == "ID-999"
    assert body["calls_made"] == 2
    assert body["message"] == "ok preview"


def test_post_preview_lookup_denies_viewer() -> None:
    viewer = _create_user(ApplicationUserRole.VIEWER.value)

    response = client.post(
        "/utenze/anpr/preview-lookup",
        headers=_auth_headers(viewer.username),
        json={"codice_fiscale": "RSSMRA80A01H501U"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient role"


def test_post_preview_lookup_returns_503_for_pdnd_misconfiguration(monkeypatch: pytest.MonkeyPatch) -> None:
    reviewer = _create_user(ApplicationUserRole.REVIEWER.value)

    async def fake_lookup(codice_fiscale: str, *, client=None, auth_manager=None):
        raise PdndConfigurationError("PDND private key missing")

    monkeypatch.setattr("app.modules.utenze.anpr.routes.lookup_anpr_by_codice_fiscale", fake_lookup)

    response = client.post(
        "/utenze/anpr/preview-lookup",
        headers=_auth_headers(reviewer.username),
        json={"codice_fiscale": "RSSMRA80A01H501U"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "PDND private key missing"


def test_post_sync_subject_denies_viewer() -> None:
    viewer = _create_user(ApplicationUserRole.VIEWER.value)
    subject_id = uuid.uuid4()

    response = client.post(f"/utenze/anpr/sync/{subject_id}", headers=_auth_headers(viewer.username))

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient role"


def test_post_sync_subject_returns_503_for_pdnd_misconfiguration(monkeypatch: pytest.MonkeyPatch) -> None:
    reviewer = _create_user(ApplicationUserRole.REVIEWER.value)
    subject_id = uuid.uuid4()

    async def fake_sync_single_subject(subject_id: str, db, triggered_by: str, auth, client):
        raise PdndConfigurationError("PDND private key not configured: set PDND_PRIVATE_KEY_PATH or PDND_PRIVATE_KEY_PEM")

    monkeypatch.setattr("app.modules.utenze.anpr.routes.sync_single_subject", fake_sync_single_subject)

    response = client.post(f"/utenze/anpr/sync/{subject_id}", headers=_auth_headers(reviewer.username))

    assert response.status_code == 503
    assert response.json()["detail"] == "PDND private key not configured: set PDND_PRIVATE_KEY_PATH or PDND_PRIVATE_KEY_PEM"


def test_post_sync_subject_returns_200_with_operational_anpr_error_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    reviewer = _create_user(ApplicationUserRole.REVIEWER.value)
    subject_id = uuid.uuid4()

    async def fake_sync_single_subject(subject_id: str, db, triggered_by: str, auth, client):
        assert triggered_by == f"user:{reviewer.id}"
        return {
            "subject_id": subject_id,
            "success": False,
            "esito": "error",
            "data_decesso": None,
            "anpr_id": "ANPR-123",
            "calls_made": 2,
            "message": "EN148 | E | Devi specificare la sezione verifica dati decesso per questo caso d'uso",
        }

    monkeypatch.setattr("app.modules.utenze.anpr.routes.sync_single_subject", fake_sync_single_subject)

    response = client.post(f"/utenze/anpr/sync/{subject_id}", headers=_auth_headers(reviewer.username))

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["esito"] == "error"
    assert body["anpr_id"] == "ANPR-123"
    assert body["calls_made"] == 2
    assert "EN148" in body["message"]


def test_get_config_returns_admin_config(monkeypatch: pytest.MonkeyPatch) -> None:
    admin = _create_user(ApplicationUserRole.ADMIN.value)

    async def fake_get_config(db):
        return SimpleNamespace(
            max_calls_per_day=100,
            job_enabled=True,
            job_cron="0 2 * * *",
            lookback_years=1,
            retry_not_found_days=90,
            updated_at=None,
        )

    monkeypatch.setattr("app.modules.utenze.anpr.routes.get_config", fake_get_config)

    response = client.get("/utenze/anpr/config", headers=_auth_headers(admin.username))

    assert response.status_code == 200
    assert response.json()["job_cron"] == "0 2 * * *"


def test_post_job_trigger_returns_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    admin = _create_user(ApplicationUserRole.ADMIN.value)
    monkeypatch.setattr("app.modules.utenze.anpr.routes._run_daily_job_task", lambda: None)
    monkeypatch.setitem(
        __import__("app.modules.utenze.anpr.routes", fromlist=["_job_runtime_state"])._job_runtime_state,
        "running",
        False,
    )

    response = client.post("/utenze/anpr/job/trigger", headers=_auth_headers(admin.username))

    assert response.status_code == 202
    assert response.json()["message"] == "job scheduled"
