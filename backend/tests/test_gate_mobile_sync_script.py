from __future__ import annotations

import httpx

from app.scripts import gate_mobile_sync
from app.services.gate_mobile_sync import GateMobileSyncExecutionResult, GateMobileSyncReport


class _DummySession:
    def close(self) -> None:
        return None


def test_main_logs_success_without_exposing_token(monkeypatch, caplog) -> None:
    caplog.set_level("INFO")

    async def fake_execute_gate_mobile_sync(_db, **_kwargs):
        return GateMobileSyncExecutionResult(
            status="succeeded",
            run_id="run-1",
            report=GateMobileSyncReport(
                requested_tasks=[{"type": "operators"}],
                catalogs_pushed=5,
                operators_pushed=276,
                worksets_pushed=12,
            ),
        )

    monkeypatch.setattr(gate_mobile_sync.settings, "gate_mobile_sync_enabled", True)
    monkeypatch.setattr(gate_mobile_sync, "SessionLocal", lambda: _DummySession())
    monkeypatch.setattr(gate_mobile_sync, "execute_gate_mobile_sync", fake_execute_gate_mobile_sync)

    exit_code = gate_mobile_sync.main()

    assert exit_code == 0
    assert "gate-mobile sync completed" in caplog.text
    assert "catalogs_pushed=5" in caplog.text
    assert "operators_pushed=276" in caplog.text
    assert "worksets_pushed=12" in caplog.text
    assert "token" not in caplog.text.lower()


def test_main_logs_skip_when_sync_disabled(monkeypatch, caplog) -> None:
    caplog.set_level("INFO")
    called = False

    async def fake_execute_gate_mobile_sync(_db, **_kwargs):
        nonlocal called
        called = True
        return GateMobileSyncExecutionResult(
            status="skipped",
            run_id="run-2",
            report=None,
            error_kind="disabled",
            error_message="GATE_MOBILE_SYNC_ENABLED=false",
        )

    monkeypatch.setattr(gate_mobile_sync, "SessionLocal", lambda: _DummySession())
    monkeypatch.setattr(gate_mobile_sync, "execute_gate_mobile_sync", fake_execute_gate_mobile_sync)

    exit_code = gate_mobile_sync.main()

    assert exit_code == 0
    assert called is True
    assert "GATE_MOBILE_SYNC_ENABLED=false" in caplog.text


def test_main_logs_http_error_without_exposing_token(monkeypatch, caplog) -> None:
    caplog.set_level("INFO")
    request = httpx.Request("POST", "https://gateway.example.test/api/mobile/connector/sync/plan")
    response = httpx.Response(401, request=request)

    async def fake_execute_gate_mobile_sync(_db, **_kwargs):
        raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    monkeypatch.setattr(gate_mobile_sync, "SessionLocal", lambda: _DummySession())
    monkeypatch.setattr(gate_mobile_sync, "execute_gate_mobile_sync", fake_execute_gate_mobile_sync)

    exit_code = gate_mobile_sync.main()

    assert exit_code == 1
    assert "status=401" in caplog.text
    assert "/api/mobile/connector/sync/plan" in caplog.text
    assert "Bearer" not in caplog.text


def test_script_contention_and_failure_exit_codes(monkeypatch):
    monkeypatch.setenv("GATE_MOBILE_SYNC_TRIGGER_SOURCE", "outbound_runner")
    monkeypatch.setattr(gate_mobile_sync.settings, "app_env", "production")
    outcomes = [
        gate_mobile_sync.GateMobileSyncBusy(),
        RuntimeError("invalid config"),
        httpx.ConnectError("unavailable"),
        ValueError("unexpected"),
    ]

    async def fail_cycle(_db, *, trigger_source, **_kwargs):
        assert trigger_source == "outbound_runner"
        raise outcomes.pop(0)

    monkeypatch.setattr(gate_mobile_sync, "SessionLocal", _DummySession)
    monkeypatch.setattr(gate_mobile_sync, "execute_gate_mobile_sync", fail_cycle)
    assert [gate_mobile_sync.main() for _ in range(4)] == [0, 1, 1, 1]


def test_script_entrypoint_and_production_trigger(monkeypatch):
    import runpy

    import pytest

    monkeypatch.delenv("GATE_MOBILE_SYNC_TRIGGER_SOURCE", raising=False)
    monkeypatch.setattr(gate_mobile_sync.settings, "app_env", "production")
    assert gate_mobile_sync._detect_trigger_source(gate_mobile_sync.settings) == "systemd_timer_or_manual"
    configured = []
    monkeypatch.setattr(gate_mobile_sync.logging.getLogger(), "handlers", [])
    monkeypatch.setattr(gate_mobile_sync.logging, "basicConfig", lambda **kw: configured.append(kw))
    gate_mobile_sync._configure_logging()
    assert configured
    monkeypatch.setattr("app.core.database.SessionLocal", _DummySession)

    async def busy(_db, **_kwargs):
        raise gate_mobile_sync.GateMobileSyncBusy

    monkeypatch.setattr("app.services.gate_mobile_sync.execute_gate_mobile_sync", busy)
    with pytest.raises(SystemExit, match="0"):
        runpy.run_module("app.scripts.gate_mobile_sync", run_name="__main__")
