from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytest

from app.modules.gis import export_scheduler


@pytest.mark.anyio
async def test_register_gis_export_scheduler_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    monkeypatch.setattr("app.core.config.settings.gis_export_scheduler_enabled", False)

    await export_scheduler.register_gis_export_scheduler(scheduler, lambda: None)

    assert scheduler.get_job("gis_shapefile_export_schedule") is None


@pytest.mark.anyio
async def test_register_gis_export_scheduler_registers_job(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    monkeypatch.setattr("app.core.config.settings.gis_export_scheduler_enabled", True)
    monkeypatch.setattr("app.core.config.settings.gis_export_scheduler_cron", "30 2 * * *")
    monkeypatch.setattr("app.core.config.settings.gis_export_scheduler_timezone", "Europe/Rome")
    monkeypatch.setattr("app.core.config.settings.gis_export_retention_count", 5)
    monkeypatch.setattr("app.core.config.settings.gis_export_max_layers_per_run", 50)

    await export_scheduler.register_gis_export_scheduler(scheduler, lambda: None)

    job = scheduler.get_job("gis_shapefile_export_schedule")
    assert job is not None
    assert job.id == "gis_shapefile_export_schedule"
    assert job.max_instances == 1
    assert job.coalesce is True


@pytest.mark.anyio
async def test_consume_db_factory_supports_plain_object() -> None:
    resource, generator = await export_scheduler._consume_db_factory(lambda: "db-object")

    assert resource == "db-object"
    assert generator is None


@pytest.mark.anyio
async def test_run_job_wrapper_runs_summary_and_closes_generator_db(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        closed = False

        def close(self) -> None:
            self.closed = True

    fake_db = FakeDb()

    def fake_get_db():
        yield fake_db

    calls: list[tuple[int, int]] = []

    class Summary:
        attempted_layers = 2
        completed_exports = 1
        failed_exports = 1
        pruned_exports = 3

    def fake_run(db, *, retention_count: int, max_layers: int):
        calls.append((retention_count, max_layers))
        assert db is fake_db
        return Summary()

    monkeypatch.setattr("app.core.config.settings.gis_export_retention_count", 7)
    monkeypatch.setattr("app.core.config.settings.gis_export_max_layers_per_run", 4)
    monkeypatch.setattr(export_scheduler, "run_scheduled_shapefile_exports", fake_run)

    await export_scheduler._run_job_wrapper(fake_get_db)

    assert calls == [(7, 4)]
    assert fake_db.closed is True


@pytest.mark.anyio
async def test_run_job_wrapper_logs_failures_and_awaits_async_close(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        def __init__(self) -> None:
            self.closed = False

        async def close(self) -> None:
            self.closed = True

    fake_db = FakeDb()

    monkeypatch.setattr(
        export_scheduler,
        "run_scheduled_shapefile_exports",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    await export_scheduler._run_job_wrapper(lambda: fake_db)

    assert fake_db.closed is True
