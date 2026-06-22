from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytest

from app.modules.elaborazioni.db_backup_scheduler import (
    _consume_db_factory,
    _run_job_wrapper,
    register_elaborazioni_db_backup_scheduler,
)


@pytest.mark.anyio
async def test_register_db_backup_scheduler_registers_job(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_cron", "5 2 * * *")
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_timezone", "Europe/Rome")
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_retention_count", 5)
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_enabled", True)

    await register_elaborazioni_db_backup_scheduler(scheduler, lambda: None)

    job = scheduler.get_job("elaborazioni_db_backup")
    assert job is not None
    assert job.id == "elaborazioni_db_backup"
    assert job.max_instances == 1


@pytest.mark.anyio
async def test_run_db_backup_scheduler_job_skips_when_toggle_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        closed = False

        def close(self) -> None:
            self.closed = True

    fake_db = FakeDb()

    def fake_get_db():
        yield fake_db

    monkeypatch.setattr("app.modules.elaborazioni.db_backup_scheduler.is_elaborazioni_db_backup_enabled", lambda db: False)

    backup_called = False

    def fake_run_backup() -> str:
        nonlocal backup_called
        backup_called = True
        return "/volume1/Backups/GAIA/db/latest.json"

    monkeypatch.setattr("app.modules.elaborazioni.db_backup_scheduler.run_elaborazioni_db_backup_job", fake_run_backup)

    await _run_job_wrapper(fake_get_db)

    assert fake_db.closed is True
    assert backup_called is False


@pytest.mark.anyio
async def test_consume_db_factory_supports_plain_object() -> None:
    resource, generator = await _consume_db_factory(lambda: "db-object")
    assert resource == "db-object"
    assert generator is None


@pytest.mark.anyio
async def test_run_db_backup_scheduler_job_runs_and_awaits_async_close(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        def __init__(self) -> None:
            self.closed = False

        async def close(self) -> None:
            self.closed = True

    fake_db = FakeDb()

    def fake_get_db():
        return fake_db

    monkeypatch.setattr("app.modules.elaborazioni.db_backup_scheduler.is_elaborazioni_db_backup_enabled", lambda db: True)

    backup_calls: list[str] = []
    monkeypatch.setattr(
        "app.modules.elaborazioni.db_backup_scheduler.run_elaborazioni_db_backup_job",
        lambda: backup_calls.append("run") or "/volume1/Backups/GAIA/db/latest.json",
    )

    await _run_job_wrapper(fake_get_db)

    assert backup_calls == ["run"]
    assert fake_db.closed is True
