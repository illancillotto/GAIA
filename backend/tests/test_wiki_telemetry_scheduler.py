from __future__ import annotations

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.modules.wiki.telemetry_scheduler import register_wiki_telemetry_scheduler


@pytest.mark.anyio
async def test_register_wiki_telemetry_scheduler_skips_when_disabled(monkeypatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    monkeypatch.setattr("app.core.config.settings.wiki_telemetry_schedule_enabled", False)

    await register_wiki_telemetry_scheduler(scheduler, lambda: None)

    assert scheduler.get_job("wiki_telemetry_refresh") is None


@pytest.mark.anyio
async def test_register_wiki_telemetry_scheduler_adds_job(monkeypatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    monkeypatch.setattr("app.core.config.settings.wiki_telemetry_schedule_enabled", True)
    monkeypatch.setattr("app.core.config.settings.wiki_telemetry_schedule_cron", "45 4 * * *")
    monkeypatch.setattr("app.core.config.settings.wiki_telemetry_schedule_timezone", "Europe/Rome")

    await register_wiki_telemetry_scheduler(scheduler, lambda: None)

    job = scheduler.get_job("wiki_telemetry_refresh")
    assert job is not None
    assert job.trigger is not None
