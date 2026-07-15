from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytest

from app.modules.elaborazioni.bonifica_oristanese_scheduler import (
    _operazioni_live_hour_range,
    _run_job_wrapper,
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
    monkeypatch.setattr("app.core.config.settings.wc_sync_operazioni_live_interval_seconds", 3600)
    monkeypatch.setattr("app.core.config.settings.wc_sync_operazioni_live_start_hour", 6)
    monkeypatch.setattr("app.core.config.settings.wc_sync_operazioni_live_end_hour", 21)
    monkeypatch.setattr("app.core.config.settings.wc_sync_operazioni_live_timezone", "Europe/Rome")

    await register_bonifica_scheduler(scheduler, lambda: None)

    job = scheduler.get_job("whitecompany_daily_sync")
    assert job is not None
    assert job.id == "whitecompany_daily_sync"
    live_job = scheduler.get_job("whitecompany_operazioni_live_sync")
    assert live_job is not None
    assert live_job.id == "whitecompany_operazioni_live_sync"
    assert live_job.max_instances == 1
    assert isinstance(live_job.trigger, CronTrigger)
    assert str(live_job.trigger.fields[5]) == "6-21"
    assert str(live_job.trigger.fields[6]) == "0"


def test_operazioni_live_hour_range_falls_back_on_invalid_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.wc_sync_operazioni_live_start_hour", 22)
    monkeypatch.setattr("app.core.config.settings.wc_sync_operazioni_live_end_hour", 6)

    assert _operazioni_live_hour_range() == "0-23"


@pytest.mark.anyio
async def test_run_daily_job_wrapper_runs_and_awaits_async_close(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        closed = False

        async def close(self) -> None:
            self.closed = True

    fake_db = FakeDb()
    called = False

    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese_scheduler.is_whitecompany_daily_sync_enabled",
        lambda db: True,
    )

    async def fake_run(db) -> None:
        nonlocal called
        assert db is fake_db
        called = True

    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese_scheduler.run_daily_bonifica_sync_job",
        fake_run,
    )

    await _run_job_wrapper(lambda: fake_db)

    assert called is True
    assert fake_db.closed is True


@pytest.mark.anyio
async def test_run_daily_job_wrapper_skips_when_toggle_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        closed = False

        def close(self) -> None:
            self.closed = True

    fake_db = FakeDb()
    called = False

    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese_scheduler.is_whitecompany_daily_sync_enabled",
        lambda db: False,
    )

    async def fake_run(_db) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese_scheduler.run_daily_bonifica_sync_job",
        fake_run,
    )

    await _run_job_wrapper(lambda: fake_db)

    assert fake_db.closed is True
    assert called is False


@pytest.mark.anyio
async def test_run_daily_job_wrapper_closes_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        closed = False

        def close(self) -> None:
            self.closed = True

    fake_db = FakeDb()
    finalized = False

    def fake_get_db():
        nonlocal finalized
        try:
            yield fake_db
        finally:
            finalized = True

    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese_scheduler.is_whitecompany_daily_sync_enabled",
        lambda db: True,
    )

    async def fake_run(_db) -> None:
        return None

    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese_scheduler.run_daily_bonifica_sync_job",
        fake_run,
    )

    await _run_job_wrapper(fake_get_db)

    assert fake_db.closed is True
    assert finalized is True


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


@pytest.mark.anyio
async def test_run_operazioni_live_job_wrapper_runs_and_awaits_async_close(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        closed = False

        async def close(self) -> None:
            self.closed = True

    fake_db = FakeDb()
    called = False

    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese_scheduler.is_whitecompany_operazioni_live_sync_enabled",
        lambda db: True,
    )

    async def fake_run(db) -> None:
        nonlocal called
        assert db is fake_db
        called = True

    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese_scheduler.run_operazioni_live_bonifica_sync_job",
        fake_run,
    )

    await _run_operazioni_live_job_wrapper(lambda: fake_db)

    assert called is True
    assert fake_db.closed is True
