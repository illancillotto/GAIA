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
            report=GateMobileSyncReport(requested_tasks=[{"type": "operators"}], operators_pushed=276),
        )

    monkeypatch.setattr(gate_mobile_sync.settings, "gate_mobile_sync_enabled", True)
    monkeypatch.setattr(gate_mobile_sync, "SessionLocal", lambda: _DummySession())
    monkeypatch.setattr(gate_mobile_sync, "execute_gate_mobile_sync", fake_execute_gate_mobile_sync)

    exit_code = gate_mobile_sync.main()

    assert exit_code == 0
    assert "gate-mobile sync completed" in caplog.text
    assert "operators_pushed=276" in caplog.text
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
