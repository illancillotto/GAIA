from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytest

from app.modules.elaborazioni.bonifica_oristanese_scheduler import (
    _run_operazioni_live_job_wrapper,
    register_bonifica_scheduler,
)


@pytest.mark.anyio
async def test_register_bonifica_scheduler_registers_job_even_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    monkeypatch.setattr("app.core.config.settings.wc_sync_daily_enabled", False)
    monkeypatch.setattr("app.core.config.settings.wc_sync_operazioni_live_enabled", False)

    await register_bonifica_scheduler(scheduler, lambda: None)

    job = scheduler.get_job("whitecompany_daily_sync")
    assert job is not None
    assert job.id == "whitecompany_daily_sync"
    live_job = scheduler.get_job("whitecompany_operazioni_live_sync")
    assert live_job is not None
    assert live_job.id == "whitecompany_operazioni_live_sync"


@pytest.mark.anyio
async def test_register_bonifica_scheduler_adds_job(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    monkeypatch.setattr("app.core.config.settings.wc_sync_daily_enabled", True)
    monkeypatch.setattr("app.core.config.settings.wc_sync_daily_cron", "30 1 * * *")
    monkeypatch.setattr("app.core.config.settings.wc_sync_daily_timezone", "Europe/Rome")
    monkeypatch.setattr("app.core.config.settings.wc_sync_operazioni_live_enabled", True)
    monkeypatch.setattr("app.core.config.settings.wc_sync_operazioni_live_interval_seconds", 600)

    await register_bonifica_scheduler(scheduler, lambda: None)

    job = scheduler.get_job("whitecompany_daily_sync")
    assert job is not None
    assert job.id == "whitecompany_daily_sync"
    live_job = scheduler.get_job("whitecompany_operazioni_live_sync")
    assert live_job is not None
    assert live_job.id == "whitecompany_operazioni_live_sync"
    assert live_job.max_instances == 1


@pytest.mark.anyio
async def test_run_operazioni_live_job_wrapper_skips_when_toggle_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        closed = False

        def close(self) -> None:
            self.closed = True

    fake_db = FakeDb()

    def fake_get_db():
        yield fake_db

    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese_scheduler.is_whitecompany_operazioni_live_sync_enabled",
        lambda db: False,
    )

    called = False

    async def fake_run(_db) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese_scheduler.run_operazioni_live_bonifica_sync_job",
        fake_run,
    )

    await _run_operazioni_live_job_wrapper(fake_get_db)

    assert fake_db.closed is True
    assert called is False
