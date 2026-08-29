from __future__ import annotations

import runpy
import signal

import pytest
from app.scripts import gate_mobile_sync_runner


def test_interval_uses_default_minimum_and_configured_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GATE_MOBILE_SYNC_INTERVAL_SECONDS", raising=False)
    assert (
        gate_mobile_sync_runner._interval_seconds()
        == gate_mobile_sync_runner.DEFAULT_INTERVAL_SECONDS
    )
    monkeypatch.setenv("GATE_MOBILE_SYNC_INTERVAL_SECONDS", "invalid")
    assert (
        gate_mobile_sync_runner._interval_seconds()
        == gate_mobile_sync_runner.DEFAULT_INTERVAL_SECONDS
    )
    monkeypatch.setenv("GATE_MOBILE_SYNC_INTERVAL_SECONDS", "1")
    assert (
        gate_mobile_sync_runner._interval_seconds()
        == gate_mobile_sync_runner.MIN_INTERVAL_SECONDS
    )
    monkeypatch.setenv("GATE_MOBILE_SYNC_INTERVAL_SECONDS", "45")
    assert gate_mobile_sync_runner._interval_seconds() == 45.0


def test_main_retries_failed_cycle_and_stops_on_event(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    exit_codes = iter([1, 0])
    signal_handlers: dict[int, object] = {}
    waits: list[float] = []
    heartbeat_calls: list[tuple[str, object]] = []
    monkeypatch.setenv("GATE_MOBILE_SYNC_INTERVAL_SECONDS", "45")
    monkeypatch.setattr(
        gate_mobile_sync_runner.gate_mobile_sync,
        "_configure_logging",
        lambda: None,
    )
    monkeypatch.setattr(
        gate_mobile_sync_runner.gate_mobile_sync,
        "main",
        lambda: next(exit_codes),
    )
    monkeypatch.setattr(
        gate_mobile_sync_runner.signal,
        "signal",
        lambda signum, handler: signal_handlers.setdefault(signum, handler),
    )

    def fake_wait(interval: float) -> bool:
        waits.append(interval)
        return len(waits) == 2

    monkeypatch.setattr(gate_mobile_sync_runner._shutdown_event, "wait", fake_wait)
    class FakeHeartbeat:
        def touch(self, *, status="running", details=None) -> None:
            heartbeat_calls.append((status, details))

    monkeypatch.setattr(gate_mobile_sync_runner, "GATE_MOBILE_HEARTBEAT", FakeHeartbeat())
    caplog.set_level("INFO")

    assert gate_mobile_sync_runner.main() == 0
    assert waits == [45.0, 45.0]
    assert set(signal_handlers) == {signal.SIGTERM, signal.SIGINT}
    assert heartbeat_calls == [
        ("cycle_running", None),
        ("waiting", {"last_exit_code": 1}),
        ("cycle_running", None),
        ("waiting", {"last_exit_code": 0}),
    ]
    assert "cycle failed" in caplog.text


def test_handle_shutdown_sets_event(caplog: pytest.LogCaptureFixture) -> None:
    gate_mobile_sync_runner._shutdown_event.clear()
    caplog.set_level("INFO")

    gate_mobile_sync_runner._handle_shutdown(signal.SIGTERM, None)

    assert gate_mobile_sync_runner._shutdown_event.is_set() is True
    assert "stopping after signal" in caplog.text
    gate_mobile_sync_runner._shutdown_event.clear()


def test_module_main_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    class AlreadyStoppedEvent:
        def clear(self) -> None:
            return None

        def is_set(self) -> bool:
            return True

    monkeypatch.setattr(
        gate_mobile_sync_runner.threading,
        "Event",
        lambda: AlreadyStoppedEvent(),
    )
    monkeypatch.setattr(gate_mobile_sync_runner.signal, "signal", lambda *_args: None)
    with pytest.raises(SystemExit, match="0"):
        runpy.run_module(
            "app.scripts.gate_mobile_sync_runner",
            run_name="__main__",
        )
