"""Exercise APScheduler's real executor with a deliberately blocked database job."""

import asyncio
import importlib.util
import os
import sys
import threading
from datetime import UTC, datetime

import pytest
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_MAX_INSTANCES
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.modules.elaborazioni import domande_irrigue_autosync_scheduler as scheduler_module


@pytest.fixture
def candidate():
    path = os.environ.get("GAIA_SCHEDULER_CANDIDATE_PATH")
    if not path:
        return scheduler_module
    spec = importlib.util.spec_from_file_location("scheduler_executor_release_candidate", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.anyio
@pytest.mark.parametrize("failure", [False, True])
async def test_blocked_job_keeps_loop_responsive_and_database_in_one_thread(
    monkeypatch, candidate, failure
):
    loop = asyncio.get_running_loop()
    main_thread = threading.get_ident()
    entered, skipped, finished, heartbeat = (asyncio.Event() for _ in range(4))
    release = threading.Event()
    lifecycle = []
    calls = []
    job_id = "capacitas_domande_irrigue_autosync"

    def record(stage):
        lifecycle.append((stage, threading.get_ident()))

    class Db:
        def close(self):
            record("close")

    class AsyncDb:
        async def close(self):
            await asyncio.sleep(0)
            record("close")

    def get_db():
        record("create")
        try:
            yield AsyncDb() if failure else Db()
        finally:
            record("finalize")

    def slow_job(db):
        record("run")
        calls.append(db)
        loop.call_soon_threadsafe(entered.set)
        assert release.wait(3), "Test did not release the worker"
        if failure:
            raise RuntimeError("Expected database job failure")
        return 0

    def event_received(event):
        if event.job_id == job_id:
            (skipped if event.code == EVENT_JOB_MAX_INSTANCES else finished).set()

    async def tick():
        heartbeat.set()

    monkeypatch.setattr(candidate.settings, "capacitas_domande_irrigue_autosync_enabled", True)
    monkeypatch.setattr(candidate, "run_domande_irrigue_autosync", slow_job)
    scheduler = AsyncIOScheduler(timezone="UTC", event_loop=loop)
    scheduler.add_listener(event_received, EVENT_JOB_EXECUTED | EVENT_JOB_MAX_INSTANCES)
    await candidate.register_domande_irrigue_autosync_scheduler(scheduler, get_db)
    job = scheduler.get_job(job_id)
    assert job.max_instances == 1 and job.coalesce is True
    scheduler.reschedule_job(job_id, trigger=IntervalTrigger(seconds=0.02))
    scheduler.start()
    try:
        await asyncio.wait_for(entered.wait(), 2)
        scheduler.add_job(tick, "date", run_date=datetime.now(UTC))
        await asyncio.wait_for(heartbeat.wait(), 1)
        await asyncio.wait_for(skipped.wait(), 1)
        scheduler.pause_job(job_id)
        assert len(calls) == 1
        assert not finished.is_set()
        release.set()
        await asyncio.wait_for(finished.wait(), 2)
    finally:
        release.set()
        scheduler.shutdown(wait=True)
        await asyncio.sleep(0)
    assert [stage for stage, _ in lifecycle] == ["create", "run", "close", "finalize"]
    assert len({thread for _, thread in lifecycle}) == 1
    assert lifecycle[0][1] != main_thread
