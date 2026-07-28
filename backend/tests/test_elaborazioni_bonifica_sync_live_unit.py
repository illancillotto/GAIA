from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from app.models.wc_sync_job import WCSyncJob
from app.modules.elaborazioni.bonifica_oristanese.models import BonificaSyncRunRequest
from app.services.elaborazioni_bonifica_sync import (
    _build_job_report_summary,
    _parse_optional_iso_date,
    _resolve_date_window,
    _resolve_date_window_from_job,
    _resolve_entities,
    _validate_entity_dependencies,
    run_daily_bonifica_sync_job,
    run_operazioni_live_bonifica_sync_job,
)


class FakeDb:
    def __init__(self, user: object | None = None, *, scalar_results: list[object | None] | None = None) -> None:
        self.user = user
        self.scalar_results = list(scalar_results or [])

    def scalar(self, _statement):
        if self.scalar_results:
            return self.scalar_results.pop(0)
        return self.user


class FallbackDb(FakeDb):
    pass


def test_resolve_entities_accepts_single_string() -> None:
    request = BonificaSyncRunRequest(entities="reports")

    assert _resolve_entities(request) == ["reports"]


def test_resolve_entities_rejects_unknown_entity() -> None:
    request = BonificaSyncRunRequest.model_construct(entities=["reports", "unknown"])

    with pytest.raises(RuntimeError, match="unknown"):
        _resolve_entities(request)


def test_resolve_date_window_rejects_inverted_range() -> None:
    request = BonificaSyncRunRequest(
        entities=["reports"],
        date_from=date(2026, 7, 29),
        date_to=date(2026, 7, 28),
    )

    with pytest.raises(RuntimeError, match="date_from"):
        _resolve_date_window(request, "reports")


def test_parse_optional_iso_date_handles_supported_input_types() -> None:
    timestamp = datetime(2026, 7, 28, 9, 0, tzinfo=timezone.utc)
    direct_date = date(2026, 7, 27)

    assert _parse_optional_iso_date(timestamp) == date(2026, 7, 28)
    assert _parse_optional_iso_date(direct_date) == direct_date
    assert _parse_optional_iso_date("") is None
    assert _parse_optional_iso_date("not-a-date") is None


def test_resolve_date_window_from_job_ignores_non_date_aware_entity() -> None:
    job = WCSyncJob(entity="users", status="completed", params_json={"date_from": "2026-07-01", "date_to": "2026-07-02"})

    assert _resolve_date_window_from_job(job, "users") == (None, None)


def test_build_job_report_summary_uses_naive_finished_at_and_string_source_total() -> None:
    job = WCSyncJob(
        entity="reports",
        status="completed",
        started_at=datetime(2026, 7, 28, 9, 0, 0),
        finished_at=datetime(2026, 7, 28, 9, 5, 0),
        params_json={"date_from": "2026-07-27", "date_to": "2026-07-28", "source_total": "42"},
        records_synced=10,
        records_skipped=1,
        records_errors=0,
    )

    summary = _build_job_report_summary(job)

    assert summary["source_total"] == 42
    assert summary["duration_seconds"] == 300.0


def test_build_job_report_summary_uses_numeric_source_total_from_params() -> None:
    job = WCSyncJob(
        entity="reports",
        status="completed",
        started_at=datetime(2026, 7, 28, 9, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 7, 28, 9, 1, 0, tzinfo=timezone.utc),
        params_json={"source_total": 7.0},
    )

    summary = _build_job_report_summary(job)

    assert summary["source_total"] == 7


def test_validate_entity_dependencies_returns_when_vehicle_base_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync._has_vehicle_sync_base", lambda db: True)

    _validate_entity_dependencies(object(), ["refuels"])


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


def test_run_daily_bonifica_sync_job_falls_back_to_first_active_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync._expire_stale_running_jobs", lambda db: None)
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync._has_active_jobs", lambda db, entities: False)
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync._resolve_entities", lambda request: list(request.entities))

    seen = {}

    async def fake_run_bonifica_sync(db, current_user, request):
        seen["username"] = current_user.username
        seen["request"] = request
        return {"ok": True}

    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync.run_bonifica_sync", fake_run_bonifica_sync)

    db = FallbackDb(
        scalar_results=[
            None,
            SimpleNamespace(username="fallback-ops"),
        ]
    )

    result = asyncio.run(run_daily_bonifica_sync_job(db))

    assert result == {"ok": True}
    assert seen["username"] == "fallback-ops"
    assert seen["request"].entities == "all"


def test_run_daily_bonifica_sync_job_raises_without_active_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync._expire_stale_running_jobs", lambda db: None)

    db = FallbackDb(scalar_results=[None, None])

    with pytest.raises(RuntimeError, match="Nessun utente attivo"):
        asyncio.run(run_daily_bonifica_sync_job(db))


def test_run_operazioni_live_bonifica_sync_job_falls_back_to_first_active_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync._expire_stale_running_jobs", lambda db: None)
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync._has_active_jobs", lambda db, entities: False)
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync._resolve_entities", lambda request: list(request.entities))

    seen = {}

    async def fake_run_bonifica_sync(db, current_user, request):
        seen["username"] = current_user.username
        seen["request"] = request
        return {"ok": True}

    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync.run_bonifica_sync", fake_run_bonifica_sync)

    db = FallbackDb(
        scalar_results=[
            None,
            SimpleNamespace(username="fallback-live"),
        ]
    )

    result = asyncio.run(run_operazioni_live_bonifica_sync_job(db))

    assert result == {"ok": True}
    assert seen["username"] == "fallback-live"
    assert seen["request"].entities == ["reports", "refuels", "taken_charge", "warehouse_requests"]


def test_run_operazioni_live_bonifica_sync_job_raises_without_active_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync._expire_stale_running_jobs", lambda db: None)

    db = FallbackDb(scalar_results=[None, None])

    with pytest.raises(RuntimeError, match="Nessun utente attivo"):
        asyncio.run(run_operazioni_live_bonifica_sync_job(db))
