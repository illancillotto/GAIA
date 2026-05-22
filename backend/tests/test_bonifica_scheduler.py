from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytest

from app.modules.elaborazioni.bonifica_oristanese_scheduler import register_bonifica_scheduler


@pytest.mark.anyio
async def test_register_bonifica_scheduler_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    monkeypatch.setattr("app.core.config.settings.wc_sync_daily_enabled", False)

    await register_bonifica_scheduler(scheduler, lambda: None)

    assert scheduler.get_job("whitecompany_daily_sync") is None


@pytest.mark.anyio
async def test_register_bonifica_scheduler_adds_job(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    monkeypatch.setattr("app.core.config.settings.wc_sync_daily_enabled", True)
    monkeypatch.setattr("app.core.config.settings.wc_sync_daily_cron", "30 1 * * *")
    monkeypatch.setattr("app.core.config.settings.wc_sync_daily_timezone", "Europe/Rome")

    await register_bonifica_scheduler(scheduler, lambda: None)

    job = scheduler.get_job("whitecompany_daily_sync")
    assert job is not None
    assert job.id == "whitecompany_daily_sync"
