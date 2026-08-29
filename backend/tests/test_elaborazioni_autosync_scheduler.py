from __future__ import annotations

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.modules.elaborazioni.autosync_scheduler import (
    _consume_db_factory,
    _run_job_wrapper,
    register_ruolo_autosync_scheduler,
)


@pytest.mark.anyio
async def test_register_perpetual_sync_scheduler() -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")

    await register_ruolo_autosync_scheduler(scheduler, lambda: None)

    job = scheduler.get_job("elaborazioni_ruolo_autosync")
    assert job is not None
    assert job.max_instances == 1


@pytest.mark.anyio
async def test_perpetual_sync_scheduler_consumes_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        closed = False

        def close(self) -> None:
            self.closed = True

    db = FakeDb()

    def factory():
        yield db

    monkeypatch.setattr(
        "app.modules.elaborazioni.autosync_scheduler.run_perpetual_sync_maintenance_for_all_users",
        lambda value: 2 if value is db else 0,
    )
    await _run_job_wrapper(factory)
    assert db.closed is True


@pytest.mark.anyio
async def test_perpetual_sync_scheduler_awaits_plain_db_close(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        closed = False

        async def close(self) -> None:
            self.closed = True

    db = FakeDb()
    monkeypatch.setattr(
        "app.modules.elaborazioni.autosync_scheduler.run_perpetual_sync_maintenance_for_all_users",
        lambda _value: 0,
    )
    resource, generator = await _consume_db_factory(lambda: db)
    assert resource is db
    assert generator is None
    await _run_job_wrapper(lambda: db)
    assert db.closed is True


@pytest.mark.anyio
async def test_perpetual_sync_scheduler_accepts_resource_without_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = object()
    monkeypatch.setattr(
        "app.modules.elaborazioni.autosync_scheduler.run_perpetual_sync_maintenance_for_all_users",
        lambda value: 0 if value is resource else 1,
    )
    await _run_job_wrapper(lambda: resource)
