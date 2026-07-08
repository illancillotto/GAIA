from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import date, datetime, timezone
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
from app.modules.utenze.anpr.models import AnprCheckLog
from app.modules.utenze.anpr.routes import AnprJobSummary, _job_runtime_state, _serialize_job_summary
from app.modules.utenze.anpr.routes import router as anpr_router
from app.modules.utenze.models import AnagraficaPerson, AnagraficaSubject


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
UTC = timezone.utc


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


def _create_subject_with_person() -> uuid.UUID:
    db = TestingSessionLocal()
    subject = AnagraficaSubject(
        subject_type="person",
        status="active",
        source_name_raw="Rossi_Mario_RSSMRA80A01H501U",
        nas_folder_path=f"/tmp/{uuid.uuid4()}",
        requires_review=False,
    )
    db.add(subject)
    db.flush()
    db.add(
        AnagraficaPerson(
            subject_id=subject.id,
            cognome="Rossi",
            nome="Mario",
            codice_fiscale="RSSMRA80A01H501U",
            anpr_id="ANPR-123",
            stato_anpr="alive",
        )
    )
    db.commit()
    subject_id = subject.id
    db.close()
    return subject_id


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


def test_post_verify_subject_alive_returns_result(monkeypatch: pytest.MonkeyPatch) -> None:
    reviewer = _create_user(ApplicationUserRole.REVIEWER.value)
    subject_id = uuid.uuid4()

    async def fake_verify_single_subject_alive(subject_id: str, db, triggered_by: str, auth, client):
        assert triggered_by == f"user:{reviewer.id}"
        return {
            "subject_id": subject_id,
            "success": True,
            "esito": "alive",
            "data_decesso": None,
            "anpr_id": "123456789",
            "calls_made": 1,
            "message": "ok",
        }

    monkeypatch.setattr("app.modules.utenze.anpr.routes.verify_single_subject_alive", fake_verify_single_subject_alive)

    response = client.post(f"/utenze/anpr/sync/{subject_id}/verify-alive", headers=_auth_headers(reviewer.username))

    assert response.status_code == 200
    assert response.json()["calls_made"] == 1
    assert response.json()["esito"] == "alive"


def test_post_verify_subject_death_date_returns_result(monkeypatch: pytest.MonkeyPatch) -> None:
    reviewer = _create_user(ApplicationUserRole.REVIEWER.value)
    subject_id = uuid.uuid4()

    async def fake_verify_single_subject_death_date(subject_id: str, db, triggered_by: str, auth, client):
        assert triggered_by == f"user:{reviewer.id}"
        return {
            "subject_id": subject_id,
            "success": True,
            "esito": "deceased",
            "data_decesso": "2025-08-20",
            "anpr_id": "123456789",
            "calls_made": 4,
            "message": "Data decesso determinata.",
        }

    monkeypatch.setattr("app.modules.utenze.anpr.routes.verify_single_subject_death_date", fake_verify_single_subject_death_date)

    response = client.post(f"/utenze/anpr/sync/{subject_id}/verify-death-date", headers=_auth_headers(reviewer.username))

    assert response.status_code == 200
    assert response.json()["calls_made"] == 4
    assert response.json()["esito"] == "deceased"


def test_post_verify_routes_cover_503_and_404_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    reviewer = _create_user(ApplicationUserRole.REVIEWER.value)
    subject_id = uuid.uuid4()

    async def fake_verify_subject_alive_404(subject_id: str, db, triggered_by: str, auth, client):
        return {
            "subject_id": subject_id,
            "success": False,
            "esito": "error",
            "data_decesso": None,
            "anpr_id": None,
            "calls_made": 0,
            "message": "missing subject",
        }

    async def fake_verify_subject_death_date_503(subject_id: str, db, triggered_by: str, auth, client):
        raise PdndConfigurationError("pdnd fail death date")

    async def fake_sync_subject_404(subject_id: str, db, triggered_by: str, auth, client):
        return {
            "subject_id": subject_id,
            "success": False,
            "esito": "error",
            "data_decesso": None,
            "anpr_id": None,
            "calls_made": 0,
            "message": "missing sync subject",
        }

    monkeypatch.setattr("app.modules.utenze.anpr.routes.verify_single_subject_alive", fake_verify_subject_alive_404)
    monkeypatch.setattr("app.modules.utenze.anpr.routes.verify_single_subject_death_date", fake_verify_subject_death_date_503)
    monkeypatch.setattr("app.modules.utenze.anpr.routes.sync_single_subject", fake_sync_subject_404)

    sync_response = client.post(f"/utenze/anpr/sync/{subject_id}", headers=_auth_headers(reviewer.username))
    alive_response = client.post(f"/utenze/anpr/sync/{subject_id}/verify-alive", headers=_auth_headers(reviewer.username))
    death_response = client.post(f"/utenze/anpr/sync/{subject_id}/verify-death-date", headers=_auth_headers(reviewer.username))

    assert sync_response.status_code == 404
    assert sync_response.json()["detail"] == "missing sync subject"
    assert alive_response.status_code == 404
    assert alive_response.json()["detail"] == "missing subject"
    assert death_response.status_code == 503
    assert death_response.json()["detail"] == "pdnd fail death date"


def test_verify_routes_cover_alive_503_and_death_date_404(monkeypatch: pytest.MonkeyPatch) -> None:
    reviewer = _create_user(ApplicationUserRole.REVIEWER.value)
    subject_id = uuid.uuid4()

    async def fake_verify_subject_alive_503(subject_id: str, db, triggered_by: str, auth, client):
        raise PdndConfigurationError("pdnd fail alive")

    async def fake_verify_subject_death_date_404(subject_id: str, db, triggered_by: str, auth, client):
        return {
            "subject_id": subject_id,
            "success": False,
            "esito": "error",
            "data_decesso": None,
            "anpr_id": None,
            "calls_made": 0,
            "message": "missing death-date subject",
        }

    monkeypatch.setattr("app.modules.utenze.anpr.routes.verify_single_subject_alive", fake_verify_subject_alive_503)
    monkeypatch.setattr("app.modules.utenze.anpr.routes.verify_single_subject_death_date", fake_verify_subject_death_date_404)

    alive_response = client.post(f"/utenze/anpr/sync/{subject_id}/verify-alive", headers=_auth_headers(reviewer.username))
    death_response = client.post(f"/utenze/anpr/sync/{subject_id}/verify-death-date", headers=_auth_headers(reviewer.username))

    assert alive_response.status_code == 503
    assert death_response.status_code == 404


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


def test_route_helpers_cover_runtime_loop_and_summary() -> None:
    import app.modules.utenze.anpr.routes as routes_module

    assert routes_module._get_runtime_loop() is None

    empty = _serialize_job_summary(None, message="idle")
    summary = _serialize_job_summary(
        AnprJobSummary(
            started_at=datetime.now(UTC),
            subjects_processed=2,
            deceased_found=1,
            errors=0,
            calls_used=3,
            message="done",
        ),
        message="done",
    )

    assert empty.message == "idle"
    assert summary.subjects_processed == 2


def test_get_runtime_loop_returns_loop_inside_asyncio_run() -> None:
    import app.modules.utenze.anpr.routes as routes_module
    import asyncio

    async def probe():
        return routes_module._get_runtime_loop()

    assert asyncio.run(probe()) is not None


def test_run_daily_job_helpers_cover_session_and_state(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.modules.utenze.anpr.routes as routes_module

    async def fake_run_daily_job(db_factory):
        session = await db_factory()
        assert isinstance(session, Session)
        session.close()
        return AnprJobSummary(
            started_at=datetime.now(UTC),
            subjects_processed=1,
            deceased_found=0,
            errors=0,
            calls_used=2,
            message="ok",
        )

    monkeypatch.setattr(routes_module, "run_daily_job", fake_run_daily_job)

    import asyncio

    summary = asyncio.run(routes_module._run_daily_job_with_sync_session())

    assert summary.calls_used == 2

    async def fake_run_with_sync_session():
        return AnprJobSummary(
            started_at=datetime.now(UTC),
            subjects_processed=1,
            deceased_found=0,
            errors=0,
            calls_used=2,
            message="ok",
        )

    monkeypatch.setattr(routes_module, "_run_daily_job_with_sync_session", fake_run_with_sync_session)
    routes_module._run_daily_job_task()
    assert routes_module._job_runtime_state["running"] is False
    assert routes_module._job_runtime_state["last_summary"].subjects_processed == 1


def test_get_subject_status_logs_config_jobs_and_capacitas_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    admin = _create_user(ApplicationUserRole.ADMIN.value)
    reviewer = _create_user(ApplicationUserRole.REVIEWER.value)
    subject_id = _create_subject_with_person()

    db = TestingSessionLocal()
    db.add(
        AnprCheckLog(
            subject_id=subject_id,
            call_type="C004",
            id_operazione_client="op1",
            id_operazione_anpr="anpr1",
            esito="alive",
            error_detail=None,
            data_decesso_anpr=None,
            triggered_by="user:1",
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.close()

    class Dumpable(dict):
        def model_dump(self):
            return dict(self)

    monkeypatch.setattr(
        "app.modules.utenze.anpr.routes.AnprCheckLogItem.model_validate",
        lambda item: Dumpable(
            id=str(item.id),
            subject_id=str(item.subject_id),
            call_type=item.call_type,
            id_operazione_client=item.id_operazione_client,
            id_operazione_anpr=item.id_operazione_anpr,
            esito=item.esito,
            error_detail=item.error_detail,
            data_decesso_anpr=item.data_decesso_anpr,
            triggered_by=item.triggered_by,
            created_at=item.created_at.isoformat(),
        ),
    )

    status_response = client.get(f"/utenze/anpr/sync/{subject_id}/status", headers=_auth_headers(reviewer.username))
    missing_response = client.get(f"/utenze/anpr/sync/{uuid.uuid4()}/status", headers=_auth_headers(reviewer.username))
    logs_response = client.get("/utenze/anpr/log", headers=_auth_headers(admin.username), params={"esito": "alive", "subject_id": str(subject_id)})
    subject_logs_response = client.get(f"/utenze/anpr/log/{subject_id}", headers=_auth_headers(reviewer.username))

    async def fake_update_config(db, payload, user_id):
        return SimpleNamespace(
            max_calls_per_day=50,
            job_enabled=False,
            job_cron="15 3 * * *",
            lookback_years=2,
            retry_not_found_days=180,
            updated_at=None,
        )

    async def fake_refresh(db, credential_id=None, min_age_years=100, limit=100, force=False):
        return {"processed": 1, "marked_deceased": 1, "unchanged": 0, "failed": 0, "items": []}

    monkeypatch.setattr("app.modules.utenze.anpr.routes.update_config", fake_update_config)
    monkeypatch.setattr("app.modules.utenze.anpr.routes.refresh_capacitas_deceased_flags", fake_refresh)

    put_response = client.put("/utenze/anpr/config", headers=_auth_headers(admin.username), json={"job_enabled": False, "job_cron": "15 3 * * *"})
    job_running_prev = dict(_job_runtime_state)
    _job_runtime_state["running"] = True
    trigger_running_response = client.post("/utenze/anpr/job/trigger", headers=_auth_headers(admin.username))
    _job_runtime_state["running"] = False
    _job_runtime_state["last_summary"] = None
    _job_runtime_state["last_error"] = "boom"
    status_error_response = client.get("/utenze/anpr/job/status", headers=_auth_headers(admin.username))
    _job_runtime_state["running"] = True
    status_running_response = client.get("/utenze/anpr/job/status", headers=_auth_headers(admin.username))
    _job_runtime_state["running"] = False
    _job_runtime_state["last_error"] = None
    status_idle_response = client.get("/utenze/anpr/job/status", headers=_auth_headers(admin.username))
    capacitas_response = client.post("/utenze/anpr/capacitas/refresh-deceased", headers=_auth_headers(admin.username))
    _job_runtime_state.update(job_running_prev)

    assert status_response.status_code == 200
    assert status_response.json()["subject_id"] == str(subject_id)
    assert missing_response.status_code == 404
    assert logs_response.status_code == 200 and logs_response.json()["total"] == 1
    assert subject_logs_response.status_code == 200 and len(subject_logs_response.json()) == 1
    assert put_response.status_code == 200 and put_response.json()["job_enabled"] is False
    assert trigger_running_response.status_code == 202 and trigger_running_response.json()["message"] == "job already running"
    assert status_error_response.json()["message"] == "boom"
    assert status_running_response.json()["message"] == "job running"
    assert status_idle_response.json()["message"] == "job idle"
    assert capacitas_response.status_code == 200 and capacitas_response.json()["processed"] == 1

    logs_subject_only_response = client.get("/utenze/anpr/log", headers=_auth_headers(admin.username), params={"subject_id": str(subject_id)})
    logs_all_response = client.get("/utenze/anpr/log", headers=_auth_headers(admin.username))
    assert logs_subject_only_response.status_code == 200
    assert logs_all_response.status_code == 200


def test_put_config_and_capacitas_routes_cover_error_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    admin = _create_user(ApplicationUserRole.ADMIN.value)

    async def fake_update_config(db, payload, user_id):
        raise ValueError("bad config")

    async def fake_refresh_value_error(db, credential_id=None, min_age_years=100, limit=100, force=False):
        raise ValueError("no credentials")

    async def fake_refresh_runtime_error(db, credential_id=None, min_age_years=100, limit=100, force=False):
        raise RuntimeError("gateway down")

    monkeypatch.setattr("app.modules.utenze.anpr.routes.update_config", fake_update_config)
    monkeypatch.setattr("app.modules.utenze.anpr.routes.refresh_capacitas_deceased_flags", fake_refresh_value_error)
    bad_config = client.put("/utenze/anpr/config", headers=_auth_headers(admin.username), json={"job_cron": "0 2 * * *"})
    bad_refresh = client.post("/utenze/anpr/capacitas/refresh-deceased", headers=_auth_headers(admin.username))

    monkeypatch.setattr("app.modules.utenze.anpr.routes.refresh_capacitas_deceased_flags", fake_refresh_runtime_error)
    runtime_refresh = client.post("/utenze/anpr/capacitas/refresh-deceased", headers=_auth_headers(admin.username))

    assert bad_config.status_code == 422
    assert bad_refresh.status_code == 503
    assert runtime_refresh.status_code == 502
