from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.services import elaborazioni_capacitas_runtime as runtime


class _FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


class _FakeManager:
    instances: list["_FakeManager"] = []

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.login_calls = 0
        self.activate_calls: list[str] = []
        self.keepalive_calls: list[str] = []
        self.closed = False
        _FakeManager.instances.append(self)

    async def login(self) -> None:
        self.login_calls += 1

    async def activate_app(self, app_name: str) -> None:
        self.activate_calls.append(app_name)

    async def start_keepalive(self, app_name: str) -> None:
        self.keepalive_calls.append(app_name)

    async def close(self) -> None:
        self.closed = True


def _make_incass_job(*, status: str = "pending", credential_id: int | None = 7, payload_json: dict | None = None):
    return SimpleNamespace(
        id=11,
        status=status,
        credential_id=credential_id,
        payload_json=payload_json or {"subject_ids": [str(uuid4())]},
        result_json={"processed_subjects": 1},
        error_detail=None,
        started_at=datetime.now(timezone.utc),
        completed_at=None,
    )


def _make_terreni_job(*, status: str = "pending", credential_id: int | None = 7, payload_json: dict | None = None):
    return SimpleNamespace(
        id=12,
        status=status,
        credential_id=credential_id,
        payload_json=payload_json or {"items": [{"foglio": "1", "particella": "2"}], "parallel_workers": 2},
        error_detail=None,
        completed_at=None,
    )


def _make_particelle_job(*, status: str = "pending", credential_id: int | None = 7, payload_json: dict | None = None):
    return SimpleNamespace(
        id=13,
        status=status,
        credential_id=credential_id,
        payload_json=payload_json or {"parallel_workers": 2},
        error_detail=None,
        completed_at=None,
    )


def _make_anagrafica_history_job(
    *,
    status: str = "pending",
    credential_id: int | None = 7,
    payload_json: dict | None = None,
):
    return SimpleNamespace(
        id=14,
        status=status,
        credential_id=credential_id,
        payload_json=payload_json or {"items": [{"idxana": "IDX-001"}]},
        error_detail=None,
        completed_at=None,
    )


@pytest.fixture(autouse=True)
def reset_fake_manager() -> None:
    _FakeManager.instances.clear()


def test_run_incass_job_by_id_returns_when_job_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_incass_sync_job", lambda current_db, job_id: None)

    asyncio.run(runtime.run_incass_job_by_id(11))

    assert db.closed is True
    assert db.commits == 0
    assert db.rollbacks == 0


def test_run_incass_job_by_id_defers_when_credential_is_temporarily_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    job = _make_incass_job()
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_incass_sync_job", lambda current_db, job_id: job)
    monkeypatch.setattr(
        runtime,
        "pick_credential",
        lambda current_db, credential_id: (_ for _ in ()).throw(
            RuntimeError("Nessuna credenziale Capacitas disponibile: nessuna credenziale attiva"),
        ),
    )

    asyncio.run(runtime.run_incass_job_by_id(job.id))

    assert job.status == "queued_resume"
    assert job.started_at is None
    assert job.completed_at is None
    assert job.error_detail.startswith("Credenziale Capacitas temporaneamente non disponibile")
    assert job.result_json["resume_reason"] == "credentials_unavailable"
    assert job.result_json["resume_count"] == 1
    assert db.commits == 1


def test_run_incass_job_by_id_marks_failed_when_credential_error_is_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    job = _make_incass_job()
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_incass_sync_job", lambda current_db, job_id: job)
    monkeypatch.setattr(
        runtime,
        "pick_credential",
        lambda current_db, credential_id: (_ for _ in ()).throw(RuntimeError("Credenziale 99 non trovata")),
    )

    asyncio.run(runtime.run_incass_job_by_id(job.id))

    assert job.status == "failed"
    assert job.error_detail == "Credenziale 99 non trovata"
    assert isinstance(job.completed_at, datetime)
    assert db.commits == 1


def test_run_incass_job_by_id_retries_retryable_errors_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    db_instances = [_FakeDb(), _FakeDb()]
    job = _make_incass_job(payload_json={"subject_ids": [str(uuid4())], "credential_id": 9})
    manager_close_calls: list[bool] = []
    run_attempts: list[int] = []
    sleep_calls: list[int] = []

    def session_local() -> _FakeDb:
        return db_instances.pop(0)

    monkeypatch.setattr(runtime, "SessionLocal", session_local)
    monkeypatch.setattr(runtime, "get_incass_sync_job", lambda current_db, job_id: job)
    monkeypatch.setattr(runtime, "pick_credential", lambda current_db, credential_id: (SimpleNamespace(id=9, username="user"), "pw"))
    monkeypatch.setattr(runtime, "CapacitasSessionManager", _FakeManager)
    monkeypatch.setattr(runtime, "InCassClient", lambda manager: SimpleNamespace(manager=manager))
    monkeypatch.setattr(runtime, "mark_credential_used", lambda current_db, credential_id: run_attempts.append(100 + credential_id))
    monkeypatch.setattr(runtime, "mark_credential_error", lambda current_db, credential_id, error: run_attempts.append(-credential_id))

    async def fake_run_incass_sync_job(current_db, client, current_job) -> None:
        run_attempts.append(current_db.commits + current_db.rollbacks + 1)
        if len(run_attempts) == 1:
            raise httpx.TimeoutException("timeout")

    async def fake_sleep(delay: int) -> None:
        sleep_calls.append(delay)

    async def wrapped_close(self) -> None:
        manager_close_calls.append(True)
        self.closed = True

    monkeypatch.setattr(runtime, "run_incass_sync_job", fake_run_incass_sync_job)
    monkeypatch.setattr(runtime.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(_FakeManager, "close", wrapped_close)

    asyncio.run(runtime.run_incass_job_by_id(job.id))

    assert sleep_calls == [2]
    assert run_attempts == [1, -9, 1, 109]
    assert len(manager_close_calls) == 2


def test_run_incass_job_by_id_marks_failed_after_non_retryable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    job = _make_incass_job()
    error_marks: list[tuple[int, str]] = []
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_incass_sync_job", lambda current_db, job_id: job)
    monkeypatch.setattr(runtime, "pick_credential", lambda current_db, credential_id: (SimpleNamespace(id=7, username="user"), "pw"))
    monkeypatch.setattr(runtime, "CapacitasSessionManager", _FakeManager)
    monkeypatch.setattr(runtime, "InCassClient", lambda manager: SimpleNamespace(manager=manager))
    monkeypatch.setattr(runtime, "run_incass_sync_job", lambda current_db, client, current_job: (_ for _ in ()).throw(ValueError("boom")))
    monkeypatch.setattr(runtime, "mark_credential_error", lambda current_db, credential_id, error: error_marks.append((credential_id, error)))

    asyncio.run(runtime.run_incass_job_by_id(job.id))

    assert db.rollbacks == 1
    assert error_marks == [(7, "boom")]
    assert job.status == "failed"
    assert job.error_detail == "boom"
    assert isinstance(job.completed_at, datetime)


def test_is_retryable_incass_runtime_exception_covers_all_supported_types() -> None:
    request = httpx.Request("GET", "https://example.test")
    response = httpx.Response(status_code=503, request=request)

    assert runtime._is_retryable_incass_runtime_exception(runtime.CapacitasInCassSessionExpiredError("expired")) is True
    assert runtime._is_retryable_incass_runtime_exception(httpx.TimeoutException("timeout")) is True
    assert runtime._is_retryable_incass_runtime_exception(httpx.NetworkError("network")) is True
    assert runtime._is_retryable_incass_runtime_exception(httpx.HTTPStatusError("bad", request=request, response=response)) is True
    assert runtime._is_retryable_incass_runtime_exception(RuntimeError("Errore.aspx sessione temporanea")) is True
    assert runtime._is_retryable_incass_runtime_exception(ValueError("nope")) is False


def test_run_terreni_job_by_id_builds_parallel_clients_and_marks_credential_used(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    job = _make_terreni_job(
        payload_json={
            "items": [
                {"foglio": "1", "particella": "2"},
                {"foglio": "1", "particella": "3"},
            ],
            "parallel_workers": 2,
        }
    )
    used_credentials: list[int] = []
    captured_clients: list[list[object]] = []
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_terreni_sync_job", lambda current_db, job_id: job)
    monkeypatch.setattr(runtime, "pick_credential", lambda current_db, credential_id: (SimpleNamespace(id=7, username="user"), "pw"))
    monkeypatch.setattr(runtime, "CapacitasSessionManager", _FakeManager)
    monkeypatch.setattr(runtime, "InVoltureClient", lambda manager: SimpleNamespace(manager=manager))
    monkeypatch.setattr(runtime, "mark_credential_used", lambda current_db, credential_id: used_credentials.append(credential_id))

    async def fake_run_terreni_sync_job(current_db, client, current_job, *, session_factory, clients) -> None:
        captured_clients.append(clients)
        assert session_factory is runtime.SessionLocal
        assert client.manager is clients[0].manager

    monkeypatch.setattr(runtime, "run_terreni_sync_job", fake_run_terreni_sync_job)

    asyncio.run(runtime.run_terreni_job_by_id(job.id))

    assert used_credentials == [7]
    assert len(captured_clients) == 1
    assert len(captured_clients[0]) == 2
    assert len(_FakeManager.instances) == 2
    assert all(manager.closed for manager in _FakeManager.instances)


def test_run_terreni_job_by_id_marks_failed_on_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    job = _make_terreni_job()
    error_marks: list[tuple[int, str]] = []
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_terreni_sync_job", lambda current_db, job_id: job)
    monkeypatch.setattr(runtime, "pick_credential", lambda current_db, credential_id: (SimpleNamespace(id=7, username="user"), "pw"))
    monkeypatch.setattr(runtime, "CapacitasSessionManager", _FakeManager)
    monkeypatch.setattr(runtime, "InVoltureClient", lambda manager: SimpleNamespace(manager=manager))
    monkeypatch.setattr(runtime, "mark_credential_error", lambda current_db, credential_id, error: error_marks.append((credential_id, error)))

    async def fake_run_terreni_sync_job(current_db, client, current_job, *, session_factory, clients) -> None:
        raise RuntimeError("terreni boom")

    monkeypatch.setattr(runtime, "run_terreni_sync_job", fake_run_terreni_sync_job)

    asyncio.run(runtime.run_terreni_job_by_id(job.id))

    assert db.rollbacks == 1
    assert error_marks == [(7, "terreni boom")]
    assert job.status == "failed"
    assert job.error_detail == "terreni boom"


def test_run_terreni_job_by_id_returns_when_job_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_terreni_sync_job", lambda current_db, job_id: None)

    asyncio.run(runtime.run_terreni_job_by_id(12))

    assert db.closed is True
    assert db.commits == 0
    assert db.rollbacks == 0


def test_run_terreni_job_by_id_marks_failed_when_credential_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    job = _make_terreni_job()
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_terreni_sync_job", lambda current_db, job_id: job)
    monkeypatch.setattr(runtime, "pick_credential", lambda current_db, credential_id: (_ for _ in ()).throw(RuntimeError("no terreni cred")))

    asyncio.run(runtime.run_terreni_job_by_id(job.id))

    assert job.status == "failed"
    assert job.error_detail == "no terreni cred"
    assert isinstance(job.completed_at, datetime)
    assert db.commits == 1


def test_run_particelle_job_by_id_uses_parallel_workers_from_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    job = _make_particelle_job(payload_json={"parallel_workers": 2})
    used_credentials: list[int] = []
    captured_clients: list[list[object]] = []
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_particelle_sync_job", lambda current_db, job_id: job)
    monkeypatch.setattr(runtime, "pick_credential", lambda current_db, credential_id: (SimpleNamespace(id=7, username="user"), "pw"))
    monkeypatch.setattr(runtime, "CapacitasSessionManager", _FakeManager)
    monkeypatch.setattr(runtime, "InVoltureClient", lambda manager: SimpleNamespace(manager=manager))
    monkeypatch.setattr(runtime, "mark_credential_used", lambda current_db, credential_id: used_credentials.append(credential_id))

    async def fake_run_particelle_sync_job(current_db, client, current_job, *, session_factory, clients) -> None:
        captured_clients.append(clients)
        assert session_factory is runtime.SessionLocal
        assert client.manager is clients[0].manager

    monkeypatch.setattr(runtime, "run_particelle_sync_job", fake_run_particelle_sync_job)

    asyncio.run(runtime.run_particelle_job_by_id(job.id))

    assert used_credentials == [7]
    assert len(captured_clients[0]) == 2
    assert len(_FakeManager.instances) == 2


def test_run_particelle_job_by_id_returns_when_job_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_particelle_sync_job", lambda current_db, job_id: None)

    asyncio.run(runtime.run_particelle_job_by_id(13))

    assert db.closed is True
    assert db.commits == 0
    assert db.rollbacks == 0


def test_run_particelle_job_by_id_marks_failed_when_credential_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    job = _make_particelle_job()
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_particelle_sync_job", lambda current_db, job_id: job)
    monkeypatch.setattr(runtime, "pick_credential", lambda current_db, credential_id: (_ for _ in ()).throw(RuntimeError("no particelle cred")))

    asyncio.run(runtime.run_particelle_job_by_id(job.id))

    assert job.status == "failed"
    assert job.error_detail == "no particelle cred"
    assert isinstance(job.completed_at, datetime)
    assert db.commits == 1


def test_run_particelle_job_by_id_marks_failed_on_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    job = _make_particelle_job()
    error_marks: list[tuple[int, str]] = []
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_particelle_sync_job", lambda current_db, job_id: job)
    monkeypatch.setattr(runtime, "pick_credential", lambda current_db, credential_id: (SimpleNamespace(id=7, username="user"), "pw"))
    monkeypatch.setattr(runtime, "CapacitasSessionManager", _FakeManager)
    monkeypatch.setattr(runtime, "InVoltureClient", lambda manager: SimpleNamespace(manager=manager))
    monkeypatch.setattr(runtime, "mark_credential_error", lambda current_db, credential_id, error: error_marks.append((credential_id, error)))

    async def fake_run_particelle_sync_job(current_db, client, current_job, *, session_factory, clients) -> None:
        raise RuntimeError("particelle boom")

    monkeypatch.setattr(runtime, "run_particelle_sync_job", fake_run_particelle_sync_job)

    asyncio.run(runtime.run_particelle_job_by_id(job.id))

    assert db.rollbacks == 1
    assert error_marks == [(7, "particelle boom")]
    assert job.status == "failed"
    assert job.error_detail == "particelle boom"


def test_run_anagrafica_history_job_by_id_marks_job_failed_when_pick_credential_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = _FakeDb()
    job = _make_anagrafica_history_job()
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_anagrafica_history_job", lambda current_db, job_id: job)
    monkeypatch.setattr(runtime, "pick_credential", lambda current_db, credential_id: (_ for _ in ()).throw(RuntimeError("missing")))

    asyncio.run(runtime.run_anagrafica_history_job_by_id(job.id))

    assert job.status == "failed"
    assert job.error_detail == "missing"
    assert isinstance(job.completed_at, datetime)
    assert db.commits == 1


def test_run_anagrafica_history_job_by_id_returns_when_job_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_anagrafica_history_job", lambda current_db, job_id: None)

    asyncio.run(runtime.run_anagrafica_history_job_by_id(14))

    assert db.closed is True
    assert db.commits == 0
    assert db.rollbacks == 0


def test_run_anagrafica_history_job_by_id_marks_used_credential_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    job = _make_anagrafica_history_job(payload_json={"items": [{"idxana": "IDX-001"}], "credential_id": 3})
    used_credentials: list[int] = []
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_anagrafica_history_job", lambda current_db, job_id: job)
    monkeypatch.setattr(runtime, "pick_credential", lambda current_db, credential_id: (SimpleNamespace(id=3, username="user"), "pw"))
    monkeypatch.setattr(runtime, "CapacitasSessionManager", _FakeManager)
    monkeypatch.setattr(runtime, "InVoltureClient", lambda manager: SimpleNamespace(manager=manager))
    monkeypatch.setattr(runtime, "mark_credential_used", lambda current_db, credential_id: used_credentials.append(credential_id))

    async def fake_run_anagrafica_history_job(current_db, client, current_job) -> None:
        return None

    monkeypatch.setattr(runtime, "run_anagrafica_history_job", fake_run_anagrafica_history_job)

    asyncio.run(runtime.run_anagrafica_history_job_by_id(job.id))

    assert used_credentials == [3]
    assert len(_FakeManager.instances) == 1
    assert _FakeManager.instances[0].closed is True


def test_run_anagrafica_history_job_by_id_marks_failed_on_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    job = _make_anagrafica_history_job(payload_json={"items": [{"idxana": "IDX-001"}], "credential_id": 3})
    error_marks: list[tuple[int, str]] = []
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, "get_anagrafica_history_job", lambda current_db, job_id: job)
    monkeypatch.setattr(runtime, "pick_credential", lambda current_db, credential_id: (SimpleNamespace(id=3, username="user"), "pw"))
    monkeypatch.setattr(runtime, "CapacitasSessionManager", _FakeManager)
    monkeypatch.setattr(runtime, "InVoltureClient", lambda manager: SimpleNamespace(manager=manager))
    monkeypatch.setattr(runtime, "mark_credential_error", lambda current_db, credential_id, error: error_marks.append((credential_id, error)))

    async def fake_run_anagrafica_history_job(current_db, client, current_job) -> None:
        raise RuntimeError("history boom")

    monkeypatch.setattr(runtime, "run_anagrafica_history_job", fake_run_anagrafica_history_job)

    asyncio.run(runtime.run_anagrafica_history_job_by_id(job.id))

    assert db.rollbacks == 1
    assert error_marks == [(3, "history boom")]
    assert job.status == "failed"
    assert job.error_detail == "history boom"
