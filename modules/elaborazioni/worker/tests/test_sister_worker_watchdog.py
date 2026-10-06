import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

import sister_worker_watchdog as module


@pytest.mark.parametrize(
    "timeout,interval", [(0, 1), (1, 0), (1, 1), (float("inf"), 1), (2, float("nan"))]
)
def test_invalid_timing_fails_closed(tmp_path, timeout, interval):
    with pytest.raises(ValueError):
        module.WorkerWatchdog(tmp_path / "heartbeat", timeout=timeout, interval=interval)


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"pid": -1},
        {"pid": os.getpid(), "updated_at_epoch": True},
        {"pid": os.getpid(), "updated_at_epoch": "bad"},
        {"pid": os.getpid(), "updated_at_epoch": float("nan")},
    ],
)
def test_invalid_or_foreign_heartbeat_does_not_hide_stall(tmp_path, payload):
    path = tmp_path / "heartbeat"
    path.write_text(json.dumps(payload))
    assert module.WorkerWatchdog(path).read_marker() is None


def test_missing_or_malformed_heartbeat_does_not_hide_stall(tmp_path):
    path = tmp_path / "heartbeat"
    watchdog = module.WorkerWatchdog(path)
    assert watchdog.read_marker() is None
    path.write_text("broken json")
    assert watchdog.read_marker() is None


def test_current_process_heartbeat_accepts_finite_timestamp(tmp_path):
    path = tmp_path / "heartbeat"
    path.write_text(json.dumps({"pid": os.getpid(), "updated_at_epoch": 123.0}))
    assert module.WorkerWatchdog(path).read_marker() == 123.0


def test_progress_and_unchanged_marker_use_monotonic_time(tmp_path, monkeypatch):
    watchdog = module.WorkerWatchdog(tmp_path / "heartbeat", timeout=10, interval=1)
    watchdog.stopped = Mock()
    watchdog.stopped.wait.side_effect = [False, False, False, True]
    monkeypatch.setattr(module.time, "monotonic", Mock(side_effect=[1, 2, 3]))
    monkeypatch.setattr(watchdog, "read_marker", Mock(side_effect=[123.0, 123.0, None]))
    watchdog.monitor()
    assert watchdog.last_progress == 1
    assert watchdog.marker == 123.0
    assert watchdog.stopped.wait.call_count == 4


def test_stalled_heartbeat_exits_nonzero(tmp_path, monkeypatch, capsys):
    watchdog = module.WorkerWatchdog(tmp_path / "heartbeat", timeout=10, interval=1)
    watchdog.last_progress = 0
    watchdog.stopped = Mock()
    watchdog.stopped.wait.side_effect = [False, True]
    monkeypatch.setattr(module.time, "monotonic", lambda: 10)
    exit_process = Mock()
    monkeypatch.setattr(module.os, "_exit", exit_process)
    watchdog.monitor()
    exit_process.assert_called_once_with(1)
    assert "heartbeat fermo" in capsys.readouterr().err


@pytest.mark.parametrize("fail", [False, True])
def test_supervisor_stops_thread_on_clean_return_or_error(tmp_path, monkeypatch, fail):
    thread = Mock()
    stopped = Mock()
    monkeypatch.setattr(module.threading, "Thread", Mock(return_value=thread))
    monkeypatch.setattr(module.threading, "Event", Mock(return_value=stopped))

    async def operation():
        if fail:
            raise RuntimeError("database unavailable")

    if fail:
        with pytest.raises(RuntimeError, match="database unavailable"):
            module.run_supervised(operation, tmp_path / "heartbeat")
    else:
        module.run_supervised(operation, tmp_path / "heartbeat")
    thread.start.assert_called_once()
    stopped.set.assert_called_once()
    thread.join.assert_called_once()


@pytest.mark.parametrize("mode", ["blocked_loop", "blocked_shutdown", "healthy"])
def test_real_process_supervision(tmp_path, mode):
    source = """
import asyncio, json, os, sys, time
from pathlib import Path
from sister_worker_watchdog import run_supervised
path = Path(sys.argv[1])
mode = sys.argv[2]
async def operation():
    if mode == 'blocked_loop':
        time.sleep(30)
    elif mode == 'blocked_shutdown':
        async def cleanup():
            try:
                await asyncio.sleep(30)
            finally:
                await asyncio.sleep(30)
        asyncio.create_task(cleanup())
        await asyncio.sleep(0.01)
        raise RuntimeError('database unavailable')
    else:
        for step in range(12):
            path.write_text(json.dumps({'pid': os.getpid(), 'updated_at_epoch': time.time()}))
            await asyncio.sleep(0.1)
run_supervised(operation, path, timeout=0.5, interval=0.05)
"""
    environment = {**os.environ, "PYTHONPATH": str(Path(module.__file__).parent)}
    result = subprocess.run(
        [sys.executable, "-c", source, str(tmp_path / "heartbeat"), mode],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == (0 if mode == "healthy" else 1)
    assert ("heartbeat fermo" in result.stderr) == (mode != "healthy")
