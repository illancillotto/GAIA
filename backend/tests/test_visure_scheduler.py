from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytest

from app.modules.utenze.visure_scheduler import _run_visure_router_job, register_visure_router_scheduler


@pytest.mark.anyio
async def test_register_visure_scheduler_registers_job_even_when_env_default_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    monkeypatch.setattr("app.core.config.settings.visure_nas_router_enabled", False)
    monkeypatch.setattr("app.core.config.settings.visure_nas_router_cron", "15 */2 * * *")
    monkeypatch.setattr("app.core.config.settings.visure_nas_router_timezone", "Europe/Rome")

    await register_visure_router_scheduler(scheduler, lambda: None)

    job = scheduler.get_job("utenze_visure_nas_router")
    assert job is not None
    assert job.id == "utenze_visure_nas_router"


@pytest.mark.anyio
async def test_run_visure_scheduler_job_skips_when_toggle_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        closed = False

        def close(self) -> None:
            self.closed = True

    fake_db = FakeDb()

    def fake_get_db():
        yield fake_db

    monkeypatch.setattr("app.modules.utenze.visure_scheduler.is_visure_nas_router_enabled", lambda db: False)

    get_nas_client_called = False
    route_called = False

    def fake_get_nas_client():
        nonlocal get_nas_client_called
        get_nas_client_called = True
        return object()

    def fake_route_public_visure_files(*args, **kwargs):
        nonlocal route_called
        route_called = True
        return None

    monkeypatch.setattr("app.modules.utenze.visure_scheduler.get_nas_client", fake_get_nas_client)
    monkeypatch.setattr("app.modules.utenze.visure_scheduler.route_public_visure_files", fake_route_public_visure_files)

    await _run_visure_router_job(fake_get_db)

    assert fake_db.closed is True
    assert get_nas_client_called is False
    assert route_called is False
