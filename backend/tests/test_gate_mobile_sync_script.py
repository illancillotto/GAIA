from __future__ import annotations

import httpx

from app.scripts import gate_mobile_sync
from app.services.gate_mobile_sync import GateMobileSyncReport


class _DummySession:
    def close(self) -> None:
        return None


def test_main_logs_success_without_exposing_token(monkeypatch, caplog) -> None:
    caplog.set_level("INFO")

    async def fake_run_gate_mobile_sync_once(_db):
        return GateMobileSyncReport(requested_tasks=[{"type": "operators"}], operators_pushed=276)

    monkeypatch.setattr(gate_mobile_sync.settings, "gate_mobile_sync_enabled", True)
    monkeypatch.setattr(gate_mobile_sync, "SessionLocal", lambda: _DummySession())
    monkeypatch.setattr(gate_mobile_sync, "run_gate_mobile_sync_once", fake_run_gate_mobile_sync_once)

    exit_code = gate_mobile_sync.main()

    assert exit_code == 0
    assert "gate-mobile sync completed" in caplog.text
    assert "operators_pushed=276" in caplog.text
    assert "token" not in caplog.text.lower()


def test_main_logs_skip_when_sync_disabled(monkeypatch, caplog) -> None:
    caplog.set_level("INFO")
    called = False

    async def fake_run_gate_mobile_sync_once(_db):
        nonlocal called
        called = True
        return GateMobileSyncReport(requested_tasks=[], operators_pushed=0)

    monkeypatch.setattr(gate_mobile_sync.settings, "gate_mobile_sync_enabled", False)
    monkeypatch.setattr(gate_mobile_sync, "SessionLocal", lambda: _DummySession())
    monkeypatch.setattr(gate_mobile_sync, "run_gate_mobile_sync_once", fake_run_gate_mobile_sync_once)

    exit_code = gate_mobile_sync.main()

    assert exit_code == 0
    assert called is False
    assert "GATE_MOBILE_SYNC_ENABLED=false" in caplog.text


def test_main_logs_http_error_without_exposing_token(monkeypatch, caplog) -> None:
    caplog.set_level("INFO")
    request = httpx.Request("POST", "https://gateway.example.test/api/mobile/connector/sync/plan")
    response = httpx.Response(401, request=request)

    async def fake_run_gate_mobile_sync_once(_db):
        raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    monkeypatch.setattr(gate_mobile_sync.settings, "gate_mobile_sync_enabled", True)
    monkeypatch.setattr(gate_mobile_sync, "SessionLocal", lambda: _DummySession())
    monkeypatch.setattr(gate_mobile_sync, "run_gate_mobile_sync_once", fake_run_gate_mobile_sync_once)

    exit_code = gate_mobile_sync.main()

    assert exit_code == 1
    assert "status=401" in caplog.text
    assert "/api/mobile/connector/sync/plan" in caplog.text
    assert "Bearer" not in caplog.text
