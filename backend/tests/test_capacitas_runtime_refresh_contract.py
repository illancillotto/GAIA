import asyncio
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest

from app.modules.elaborazioni import domande_irrigue_parallel as parallel
from app.modules.elaborazioni.domande_irrigue_refresh import RecentDomandeIrrigueScraper
from app.services import elaborazioni_capacitas_runtime as runtime


@pytest.mark.parametrize(
    ("getter", "runner", "payload"),
    [
        ("get_incass_sync_job", "run_incass_job_by_id", {"subject_ids": [str(uuid4())]}),
        (
            "get_terreni_sync_job",
            "run_terreni_job_by_id",
            {"items": [{"foglio": "1", "particella": "2"}]},
        ),
        ("get_particelle_sync_job", "run_particelle_job_by_id", {}),
        (
            "get_anagrafica_history_job",
            "run_anagrafica_history_job_by_id",
            {"items": [{"idxana": "IDX"}]},
        ),
        (
            "get_domande_irrigue_sync_job",
            "run_domande_irrigue_job_by_id",
            {"searches": [{"q": "ABC"}]},
        ),
    ],
)
@pytest.mark.parametrize("disappeared", [False, True])
def test_error_before_credential_preserves_terminal_or_deleted_job(
    monkeypatch, getter, runner, payload, disappeared
):
    db = MagicMock()
    job = SimpleNamespace(payload_json=payload, credential_id=7, status="succeeded")
    get = MagicMock(side_effect=[job, None if disappeared else job])
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(runtime, getter, get)
    monkeypatch.setattr(
        runtime, "pick_credential", MagicMock(side_effect=ValueError("invalid credential"))
    )
    error = MagicMock()
    monkeypatch.setattr(runtime, "mark_credential_error", error)
    asyncio.run(getattr(runtime, runner)(1))
    db.rollback.assert_called_once()
    db.close.assert_called_once()
    db.commit.assert_not_called()
    error.assert_not_called()
    assert job.status == "succeeded"


def test_incass_non_dict_resume_state():
    job = SimpleNamespace(result_json=None)
    runtime._defer_incass_job_for_credentials(job, RuntimeError("fuori fascia oraria"))
    assert job.result_json is None
    assert job.status == "queued_resume"


def test_incass_exhausts_retries_with_rollback_and_session_cleanup(monkeypatch):
    job = SimpleNamespace(
        id=1,
        credential_id=7,
        payload_json={"subject_ids": [str(uuid4())]},
        status="pending",
    )
    databases = [MagicMock() for _ in range(3)]
    managers = [
        SimpleNamespace(
            login=AsyncMock(),
            activate_app=AsyncMock(),
            start_keepalive=AsyncMock(),
            close=AsyncMock(),
        )
        for _ in range(3)
    ]
    lifecycle = []
    for attempt, (database, manager) in enumerate(zip(databases, managers, strict=True), 1):
        database.rollback.side_effect = lambda attempt=attempt: lifecycle.append(
            ("rollback", attempt)
        )
        database.commit.side_effect = lambda attempt=attempt: lifecycle.append(("commit", attempt))
        database.close.side_effect = lambda attempt=attempt: lifecycle.append(("db_close", attempt))
        manager.close.side_effect = lambda attempt=attempt: lifecycle.append(
            ("session_close", attempt)
        )

    async def sleep(delay):
        lifecycle.append(("sleep", delay))

    session_factory = MagicMock(side_effect=databases)
    manager_factory = MagicMock(side_effect=managers)
    run_job = AsyncMock(side_effect=httpx.ReadTimeout("request timed out"))
    credential_error = MagicMock()
    credential_used = MagicMock()
    monkeypatch.setattr(runtime, "SessionLocal", session_factory)
    monkeypatch.setattr(runtime, "get_incass_sync_job", lambda *args: job)
    monkeypatch.setattr(
        runtime, "pick_credential", lambda *args: (SimpleNamespace(id=7, username="user"), "pw")
    )
    monkeypatch.setattr(runtime, "CapacitasSessionManager", manager_factory)
    monkeypatch.setattr(runtime, "InCassClient", lambda *args: object())
    monkeypatch.setattr(runtime, "run_incass_sync_job", run_job)
    monkeypatch.setattr(runtime, "mark_credential_error", credential_error)
    monkeypatch.setattr(runtime, "mark_credential_used", credential_used)
    monkeypatch.setattr(runtime.asyncio, "sleep", sleep)

    asyncio.run(runtime.run_incass_job_by_id(job.id))

    assert session_factory.call_count == manager_factory.call_count == run_job.await_count == 3
    assert credential_error.call_count == 3
    credential_used.assert_not_called()
    assert lifecycle == [
        ("rollback", 1),
        ("sleep", 2),
        ("session_close", 1),
        ("db_close", 1),
        ("rollback", 2),
        ("sleep", 5),
        ("session_close", 2),
        ("db_close", 2),
        ("rollback", 3),
        ("commit", 3),
        ("session_close", 3),
        ("db_close", 3),
    ]
    assert job.status == "failed"
    assert job.error_detail == "request timed out"
    assert job.completed_at.tzinfo is not None
    for manager in managers:
        manager.login.assert_awaited_once()
        manager.activate_app.assert_awaited_once_with("incass")
        manager.start_keepalive.assert_awaited_once_with("incass")
        manager.close.assert_awaited_once()


@pytest.mark.parametrize("parallel_mode", [False, True])
def test_both_workers_use_raw_persisted_refresh_bounds(monkeypatch, parallel_mode):
    db = MagicMock()
    job = SimpleNamespace(
        id=1,
        credential_id=7,
        payload_json={"searches": [{"q": "ABC"}], "refresh_years": [2025, 2026]},
    )
    manager = SimpleNamespace(
        login=AsyncMock(),
        activate_app=AsyncMock(),
        start_keepalive=AsyncMock(),
        close=AsyncMock(),
    )
    captured = []

    async def run(_db, client, scraper, _job):
        if parallel_mode:
            captured.extend(scraper._scrapers)
        else:
            captured.append(scraper)

    credential = SimpleNamespace(id=7, username="user")
    if parallel_mode:
        monkeypatch.setattr(parallel, "SessionLocal", lambda: nullcontext(db))
        db.get.return_value = job
        monkeypatch.setattr(parallel, "pick_credential", lambda *args: (credential, "pw"))
        monkeypatch.setattr(
            parallel,
            "open_sources",
            AsyncMock(return_value=([object()], [SimpleNamespace(_manager=manager)])),
        )
        monkeypatch.setattr(parallel.service, "_job_searches", lambda *args: [])
        monkeypatch.setattr(parallel.service, "run_domande_irrigue_sync_job", run)
        monkeypatch.setattr(parallel, "mark_credential_used", MagicMock())
        asyncio.run(parallel.run_parallel_domande_job(1, 1))
    else:
        monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
        monkeypatch.setattr(runtime, "get_domande_irrigue_sync_job", lambda *args: job)
        monkeypatch.setattr(runtime, "pick_credential", lambda *args: (credential, "pw"))
        monkeypatch.setattr(runtime, "CapacitasSessionManager", lambda *args: manager)
        monkeypatch.setattr(runtime, "InVoltureClient", lambda *args: object())
        monkeypatch.setattr(runtime, "run_domande_irrigue_sync_job", run)
        monkeypatch.setattr(runtime, "mark_credential_used", MagicMock())
        asyncio.run(runtime.run_domande_irrigue_job_by_id(1))
    assert len(captured) == 1
    assert isinstance(captured[0], RecentDomandeIrrigueScraper)
    assert captured[0]._years == {2025, 2026}
    assert captured[0]._manager is manager
