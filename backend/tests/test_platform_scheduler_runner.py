from __future__ import annotations

import pytest
from app import platform_scheduler_runner


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
async def test_register_platform_schedulers_registers_each_family_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduler = FakeScheduler(timezone="UTC")
    calls: list[tuple[str, object, object]] = []
    registrar_names = (
        "register_catasto_ade_autosync_scheduler",
        "register_bonifica_scheduler",
        "register_elaborazioni_db_backup_scheduler",
        "register_incass_autosync_scheduler",
        "register_domande_irrigue_autosync_scheduler",
        "register_ruolo_autosync_scheduler",
        "register_gis_export_scheduler",
        "register_presenze_scheduler",
        "register_network_telemetry_scheduler",
        "register_anpr_scheduler",
        "register_visure_router_scheduler",
        "register_wiki_telemetry_scheduler",
    )

    for name in registrar_names:
        async def register(
            current_scheduler: object,
            db_factory: object,
            *,
            registrar_name: str = name,
        ) -> None:
            calls.append((registrar_name, current_scheduler, db_factory))

        monkeypatch.setattr(platform_scheduler_runner, name, register)

    await platform_scheduler_runner.register_platform_schedulers(scheduler)

    assert [name for name, _, _ in calls] == list(registrar_names)
    assert all(current_scheduler is scheduler for _, current_scheduler, _ in calls)
    assert all(db_factory is platform_scheduler_runner.get_db for _, _, db_factory in calls)


@pytest.mark.anyio
async def test_runner_handles_signals_and_graceful_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduler = FakeScheduler(timezone="UTC")
    loop = FakeLoop()
    registrations: list[object] = []
    heartbeat_calls: list[tuple[object, object]] = []

    async def register(current_scheduler: object) -> None:
        registrations.append(current_scheduler)

    monkeypatch.setattr(
        platform_scheduler_runner,
        "AsyncIOScheduler",
        lambda timezone: scheduler,
    )
    monkeypatch.setattr(
        platform_scheduler_runner,
        "register_platform_schedulers",
        register,
    )
    monkeypatch.setattr(platform_scheduler_runner.asyncio, "Event", FakeEvent)
    monkeypatch.setattr(platform_scheduler_runner.asyncio, "get_running_loop", lambda: loop)

    async def run_with_heartbeat(operation: object, heartbeat: object) -> None:
        heartbeat_calls.append((operation, heartbeat))
        await operation

    monkeypatch.setattr(
        platform_scheduler_runner,
        "run_with_heartbeat",
        run_with_heartbeat,
    )

    await platform_scheduler_runner.run_scheduler()

    assert registrations == [scheduler]
    assert scheduler.timezone == "UTC"
    assert scheduler.started is True
    assert scheduler.shutdown_wait is True
    assert heartbeat_calls[0][1] is platform_scheduler_runner.SCHEDULER_HEARTBEAT
    assert [signal_number for signal_number, _ in loop.handlers] == [
        platform_scheduler_runner.signal.SIGINT,
        platform_scheduler_runner.signal.SIGTERM,
    ]


def test_main_runs_async_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def run(coroutine: object) -> None:
        calls.append(coroutine)
        coroutine.close()

    monkeypatch.setattr(platform_scheduler_runner.asyncio, "run", run)

    platform_scheduler_runner.main()

    assert len(calls) == 1
