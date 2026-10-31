from __future__ import annotations

import asyncio
import runpy
from pathlib import Path

import pytest

import ruoli_export_runner as runner


def test_parse_args_accepts_groups_and_once():
    args = runner.parse_args(["incass", "--once"])
    assert (args.group, args.once) == ("incass", True)
    assert runner.parse_args(["inbollettini"]).once is False
    with pytest.raises(SystemExit):
        runner.parse_args(["sister"])


@pytest.mark.parametrize(
    ("enabled", "due", "expected"),
    [(False, True, []), (True, False, []), (True, True, ["incass"])],
)
def test_run_if_due_respects_flag_and_schedule(monkeypatch, enabled, due, expected):
    ran: list[str] = []

    async def export(group):
        ran.append(group)

    monkeypatch.setattr(runner.settings, "capacitas_ruoli_export_enabled", enabled)
    monkeypatch.setattr(runner, "export_is_due", lambda group, now: due)
    monkeypatch.setattr(runner, "run_group_export", export)

    asyncio.run(runner.run_if_due("incass"))

    assert ran == expected


def test_run_if_due_survives_export_failure(monkeypatch, caplog):
    async def export(group):
        raise RuntimeError("drive giu")

    monkeypatch.setattr(runner.settings, "capacitas_ruoli_export_enabled", True)
    monkeypatch.setattr(runner, "export_is_due", lambda group, now: True)
    monkeypatch.setattr(runner, "run_group_export", export)

    asyncio.run(runner.run_if_due("incass"))

    assert "Export ruoli incass interrotto" in caplog.text


def test_run_loops_until_stop_signal(monkeypatch):
    checks: list[str] = []
    events: list[asyncio.Event] = []
    monkeypatch.setattr(runner, "install_signal_handlers", events.append)
    monkeypatch.setattr(runner, "POLL_INTERVAL_SEC", 0)

    async def check(group):
        checks.append(group)
        if len(checks) == 2:
            events[0].set()

    monkeypatch.setattr(runner, "run_if_due", check)

    asyncio.run(runner.run("inbollettini"))

    assert checks == ["inbollettini", "inbollettini"]


def test_install_signal_handlers_registers_sigterm():
    async def scenario():
        stop = asyncio.Event()
        runner.install_signal_handlers(stop)
        loop = asyncio.get_running_loop()
        assert loop.remove_signal_handler(runner.signal.SIGTERM) is True
        loop.remove_signal_handler(runner.signal.SIGINT)

    asyncio.run(scenario())


def test_main_runs_once_or_with_group_heartbeat(monkeypatch):
    exported: list[str] = []
    services: list[str] = []

    async def export(group):
        exported.append(group)

    async def loop(group):
        return None

    async def with_heartbeat(operation, heartbeat):
        services.append(heartbeat.service)
        await operation

    monkeypatch.setattr(runner, "run_group_export", export)
    monkeypatch.setattr(runner, "run", loop)
    monkeypatch.setattr(runner, "run_with_heartbeat", with_heartbeat)

    asyncio.run(runner.main(["incass", "--once"]))
    asyncio.run(runner.main(["inbollettini"]))

    assert exported == ["incass"]
    assert services == ["elaborazioni-worker-ruoli-inbollettini"]


def test_script_entrypoint_starts_main(monkeypatch):
    started = []

    def fake_run(operation):
        started.append(operation)
        operation.close()

    monkeypatch.setattr(asyncio, "run", fake_run)
    runpy.run_path(str(Path(runner.__file__)), run_name="__main__")

    assert len(started) == 1
