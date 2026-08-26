from __future__ import annotations

import pytest

from app.modules.gis import export_scheduler_runner


class FakeScheduler:
    def __init__(self, *, timezone: str) -> None:
        self.timezone = timezone
        self.started = False
        self.shutdown_wait: bool | None = None

    def start(self) -> None:
        self.started = True

    def shutdown(self, *, wait: bool) -> None:
        self.shutdown_wait = wait


class FakeEvent:
    async def wait(self) -> None:
        return None

    def set(self) -> None:
        return None


class FakeLoop:
    def __init__(self) -> None:
        self.handlers: list[tuple[object, object]] = []

    def add_signal_handler(self, signal_number: object, handler: object) -> None:
        self.handlers.append((signal_number, handler))


@pytest.mark.anyio
async def test_runner_requires_enabled_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        export_scheduler_runner.settings, "gis_export_scheduler_enabled", False
    )

    with pytest.raises(RuntimeError, match="runner is disabled"):
        await export_scheduler_runner.run_scheduler()


@pytest.mark.anyio
async def test_runner_registers_single_job_and_shuts_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        export_scheduler_runner.settings, "gis_export_scheduler_enabled", True
    )
    monkeypatch.setattr(
        export_scheduler_runner.settings,
        "gis_export_scheduler_timezone",
        "Europe/Rome",
    )
    scheduler = FakeScheduler(timezone="Europe/Rome")
    loop = FakeLoop()
    registrations: list[tuple[object, object]] = []

    async def register(current_scheduler: object, db_factory: object) -> None:
        registrations.append((current_scheduler, db_factory))

    monkeypatch.setattr(
        export_scheduler_runner,
        "AsyncIOScheduler",
        lambda timezone: scheduler,
    )
    monkeypatch.setattr(export_scheduler_runner, "register_gis_export_scheduler", register)
    monkeypatch.setattr(export_scheduler_runner.asyncio, "Event", FakeEvent)
    monkeypatch.setattr(export_scheduler_runner.asyncio, "get_running_loop", lambda: loop)

    await export_scheduler_runner.run_scheduler()

    assert registrations == [(scheduler, export_scheduler_runner.get_db)]
    assert scheduler.started is True
    assert scheduler.shutdown_wait is True
    assert len(loop.handlers) == 2


def test_main_runs_async_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def run(coroutine: object) -> None:
        calls.append(coroutine)
        coroutine.close()

    monkeypatch.setattr(export_scheduler_runner.asyncio, "run", run)

    export_scheduler_runner.main()

    assert len(calls) == 1
