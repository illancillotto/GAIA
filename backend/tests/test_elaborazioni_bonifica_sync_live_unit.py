from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.services.elaborazioni_bonifica_sync import run_operazioni_live_bonifica_sync_job


class FakeDb:
    def __init__(self, user: object | None) -> None:
        self.user = user

    def scalar(self, _statement):
        return self.user


def test_run_operazioni_live_bonifica_sync_job_queues_expected_entities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.core.config.settings.wc_sync_operazioni_live_lookback_days", 1)
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync._expire_stale_running_jobs", lambda db: None)
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync._has_active_jobs", lambda db, entities: False)

    seen = {}

    def fake_resolve_entities(request):
        seen["entities"] = request.entities
        return list(request.entities)

    async def fake_run_bonifica_sync(db, current_user, request):
        seen["username"] = current_user.username
        seen["request"] = request
        return {"ok": True}

    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync._resolve_entities", fake_resolve_entities)
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync.run_bonifica_sync", fake_run_bonifica_sync)

    result = asyncio.run(run_operazioni_live_bonifica_sync_job(FakeDb(SimpleNamespace(username="ops-admin"))))

    assert result == {"ok": True}
    assert seen["username"] == "ops-admin"
    assert seen["entities"] == ["reports", "refuels", "taken_charge", "warehouse_requests"]
    assert seen["request"].date_from is not None
    assert seen["request"].date_to is not None


def test_run_operazioni_live_bonifica_sync_job_skips_when_subset_has_active_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync._expire_stale_running_jobs", lambda db: None)
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync._resolve_entities", lambda request: list(request.entities))
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync._has_active_jobs", lambda db, entities: True)

    called = False

    async def fake_run_bonifica_sync(db, current_user, request):
        nonlocal called
        called = True
        return {"ok": True}

    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync.run_bonifica_sync", fake_run_bonifica_sync)

    result = asyncio.run(run_operazioni_live_bonifica_sync_job(FakeDb(SimpleNamespace(username="ops-admin"))))

    assert result is None
    assert called is False
