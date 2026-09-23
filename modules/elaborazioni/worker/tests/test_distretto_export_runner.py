from __future__ import annotations

import asyncio
import runpy
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import test_worker_orchestration_coverage as support

import distretto_export_runner as runner


@pytest.mark.parametrize("recovered", [0, 2])
def test_recovery_commits_before_claiming(monkeypatch: pytest.MonkeyPatch, recovered: int) -> None:
    db = support.FakeDb()
    monkeypatch.setattr(runner, "SessionLocal", support.SessionQueue(db))
    monkeypatch.setattr(runner, "prepare_distretto_export_jobs_for_recovery", lambda _db: recovered)

    runner.recover_exports()

    assert db.commits == 1


def test_claim_next_export_marks_oldest_pending_job(monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = uuid4()
    job = SimpleNamespace(id=job_id, status="pending", started_at=None, error_message="old")
    db = support.FakeDb(scalar_values=[job])
    monkeypatch.setattr(runner, "SessionLocal", support.SessionQueue(db))

    assert runner.claim_next_export() == job_id
    assert job.status == "processing"
    assert job.started_at is not None
    assert job.error_message is None
    assert db.commits == 1

    empty_db = support.FakeDb(scalar_values=[None])
    monkeypatch.setattr(runner, "SessionLocal", support.SessionQueue(empty_db))
    assert runner.claim_next_export() is None
    assert empty_db.commits == 0


def test_signal_handlers_request_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    handlers = []
    loop = SimpleNamespace(
        add_signal_handler=lambda signame, callback: handlers.append((signame, callback))
    )
    monkeypatch.setattr(runner.asyncio, "get_running_loop", lambda: loop)
    stop_requested = asyncio.Event()

    runner.install_signal_handlers(stop_requested)

    assert len(handlers) == 2
    handlers[0][1]()
    assert stop_requested.is_set()


def test_run_processes_next_export_after_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    first_id, second_id = uuid4(), uuid4()
    jobs = iter((first_id, second_id, None))
    processed = []
    stop_events = []
    monkeypatch.setattr(runner, "recover_exports", lambda: None)
    monkeypatch.setattr(runner, "claim_next_export", lambda: next(jobs))
    monkeypatch.setattr(runner, "install_signal_handlers", stop_events.append)

    async def process(_function, job_id):
        if job_id == first_id:
            raise RuntimeError("export failed")
        processed.append(job_id)

    async def stop_after_idle(_seconds):
        stop_events[0].set()

    monkeypatch.setattr(runner.asyncio, "to_thread", process)
    monkeypatch.setattr(runner.asyncio, "sleep", stop_after_idle)

    asyncio.run(runner.run())

    assert processed == [second_id]


def test_main_uses_export_heartbeat(monkeypatch: pytest.MonkeyPatch) -> None:
    services = []

    async def no_work():
        return None

    async def with_heartbeat(operation, heartbeat):
        services.append(heartbeat.service)
        await operation

    monkeypatch.setattr(runner, "run", no_work)
    monkeypatch.setattr(runner, "run_with_heartbeat", with_heartbeat)

    asyncio.run(runner.main())

    assert services == ["elaborazioni-worker-exports"]


def test_script_entrypoint_starts_main(monkeypatch: pytest.MonkeyPatch) -> None:
    started = []

    def fake_run(operation):
        started.append(operation)
        operation.close()

    monkeypatch.setattr(asyncio, "run", fake_run)
    runpy.run_path(str(Path(runner.__file__)), run_name="__main__")

    assert len(started) == 1
