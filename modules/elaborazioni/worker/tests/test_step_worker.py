from __future__ import annotations

import asyncio
import os
import runpy
import signal

os.environ.setdefault("CREDENTIAL_MASTER_KEY", "WnCjZ2L63B1kIh_2mDkk8j5M6Bf0dzxN3Qv8QbQwB0A=")
os.environ.setdefault("DATABASE_URL", "sqlite:///./.pytest-worker.db")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import step_worker
from app.core.database import Base
from app.modules.elaborazioni.step.models import StepSyncJob


@pytest.fixture
def factory() -> sessionmaker:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[Base.metadata.tables["step_credentials"], Base.metadata.tables["step_sync_jobs"]],
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_worker_recovers_claims_and_runs_jobs(
    factory, monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    with factory() as db:
        db.add_all(
            [
                StepSyncJob(status="processing", mode="relink"),
                StepSyncJob(status="pending", mode="relink"),
            ]
        )
        db.commit()
    ran: list[int] = []

    async def fake_run(*, job_id, session_factory, headless):
        ran.append(job_id)
        worker.request_stop()

    sleeps: list[float] = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(step_worker, "run_step_job_by_id", fake_run)
    monkeypatch.setattr(step_worker.asyncio, "sleep", fake_sleep)
    worker = step_worker.StepWorker(factory, headless=True, poll_interval_sec=7)
    caplog.set_level("INFO")

    asyncio.run(worker.run())
    assert ran == [1] and "Recuperati 1 job STEP" in caplog.text

    worker.stop_requested = False
    asyncio.run(worker.run_once())
    assert ran == [1, 2]
    assert asyncio.run(worker.run_once()) is False

    worker.stop_requested = False
    calls = {"count": 0}

    async def idle_once():
        calls["count"] += 1
        worker.stop_requested = calls["count"] > 1
        return False

    monkeypatch.setattr(worker, "run_once", idle_once)
    monkeypatch.setattr(worker, "recover", lambda: None)
    asyncio.run(worker.run())
    assert sleeps == [7, 7]
    step_worker.StepWorker.recover(worker)
    step_worker.StepWorker.recover(worker)


def test_build_worker_and_main(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("ELABORAZIONI_HEADLESS", "false")
    monkeypatch.setenv("ELABORAZIONI_POLL_INTERVAL_SEC", "2.5")
    worker = step_worker.build_worker()
    assert worker.headless is False and worker.poll_interval_sec == 2.5

    captured: dict = {}

    class Worker:
        def request_stop(self):
            captured["stopped"] = True

        async def run(self):
            captured["ran"] = True

    async def run_with_heartbeat(operation, heartbeat):
        captured["heartbeat"] = heartbeat
        await operation

    monkeypatch.setattr(step_worker, "build_worker", Worker)
    monkeypatch.setattr(step_worker, "run_with_heartbeat", run_with_heartbeat)

    async def scenario():
        await step_worker.main()
        asyncio.get_running_loop().remove_signal_handler(signal.SIGTERM)

    asyncio.run(scenario())
    assert captured["ran"] and captured["heartbeat"].details == {"families": ["step"]}


def test_module_main_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[object] = []
    monkeypatch.setattr(asyncio, "run", lambda coro: (called.append(coro), coro.close()))
    monkeypatch.setattr("sister_worker_watchdog.WorkerWatchdog.monitor", lambda self: None)
    runpy.run_module("step_worker", run_name="__main__")
    assert len(called) == 1


def test_idle_worker_claims_the_nightly_autosync_job(
    factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    def queue_due_autosync(db):
        job = StepSyncJob(status="pending", mode="sync")
        db.add(job)
        db.commit()
        return job.id

    monkeypatch.setattr(step_worker, "queue_due_autosync", queue_due_autosync)
    worker = step_worker.StepWorker(factory, headless=True, poll_interval_sec=1)
    job_id = worker.claim()
    with factory() as db:
        assert db.get(StepSyncJob, job_id).status == "processing"
