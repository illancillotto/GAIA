from __future__ import annotations

from types import SimpleNamespace

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.modules.utenze.anpr.scheduler import register_anpr_scheduler


@pytest.mark.anyio
async def test_register_anpr_scheduler_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")

    class FakeDb:
        def close(self) -> None:
            return None

    def fake_get_db():
        db = FakeDb()
        yield db

    async def fake_get_config(db):
        return SimpleNamespace(job_enabled=False, job_cron="0 2 * * *")

    monkeypatch.setattr("app.modules.utenze.anpr.scheduler.get_config", fake_get_config)

    await register_anpr_scheduler(scheduler, fake_get_db)

    assert scheduler.get_job("anpr_daily_check") is None


@pytest.mark.anyio
async def test_register_anpr_scheduler_adds_job(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")

    class FakeDb:
        def close(self) -> None:
            return None

    def fake_get_db():
        db = FakeDb()
        yield db

    async def fake_get_config(db):
        return SimpleNamespace(job_enabled=True, job_cron="15 3 * * *")

    monkeypatch.setattr("app.modules.utenze.anpr.scheduler.get_config", fake_get_config)

    await register_anpr_scheduler(scheduler, fake_get_db)

    job = scheduler.get_job("anpr_daily_check")
    assert job is not None
    assert job.id == "anpr_daily_check"
