from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.modules.elaborazioni import domande_irrigue_autosync_scheduler as scheduler_module


def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "capacitas_domande_irrigue_autosync_enabled": True,
        "capacitas_domande_irrigue_autosync_interval_minutes": 10,
        "capacitas_domande_irrigue_autosync_credential_id": 7,
        "capacitas_domande_irrigue_autosync_chunk_size": 2,
        "capacitas_domande_irrigue_autosync_window_enabled": True,
        "capacitas_domande_irrigue_autosync_start_hour": 20,
        "capacitas_domande_irrigue_autosync_end_hour": 6,
        "capacitas_domande_irrigue_autosync_timezone": "UTC",
        "capacitas_domande_irrigue_autosync_include_details": True,
        "capacitas_domande_irrigue_autosync_throttle_ms": 250,
    }
    for name, value in values.items():
        monkeypatch.setattr(scheduler_module.settings, name, value)


def _state(**values):
    defaults = {
        "cursor": None,
        "pending_cursor": None,
        "pending_job_id": None,
        "cycle_key": None,
        "completed_cycle_key": None,
        "processed_identifiers": 0,
        "cycle_started_at": None,
        "cycle_completed_at": None,
        "last_error": None,
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def test_window_context_uses_start_date_for_overnight_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _settings(monkeypatch)

    assert scheduler_module._window_context(datetime(2026, 9, 5, 21, tzinfo=UTC)) == (
        True,
        "2026-09-05",
    )
    assert scheduler_module._window_context(datetime(2026, 9, 6, 2, tzinfo=UTC)) == (
        True,
        "2026-09-05",
    )
    assert scheduler_module._window_context(datetime(2026, 9, 6, 12, tzinfo=UTC))[0] is False

    monkeypatch.setattr(
        scheduler_module.settings, "capacitas_domande_irrigue_autosync_start_hour", 8
    )
    monkeypatch.setattr(
        scheduler_module.settings, "capacitas_domande_irrigue_autosync_end_hour", 18
    )
    assert scheduler_module._window_context(datetime(2026, 9, 6, 9, tzinfo=UTC))[0] is True
    monkeypatch.setattr(
        scheduler_module.settings, "capacitas_domande_irrigue_autosync_window_enabled", False
    )
    assert scheduler_module._window_context(datetime(2026, 9, 6, 23, tzinfo=UTC)) == (
        True,
        "2026-09-06",
    )


def test_window_zone_falls_back_to_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch)
    monkeypatch.setattr(
        scheduler_module.settings, "capacitas_domande_irrigue_autosync_timezone", "Invalid/Zone"
    )

    assert scheduler_module._window_zone().key == "UTC"


def test_load_state_creates_singleton_and_identifier_query_supports_cursor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _settings(monkeypatch)
    db = MagicMock()
    db.get.return_value = None

    state = scheduler_module._load_state(db)

    assert state.id == 1
    db.add.assert_called_once_with(state)
    db.commit.assert_called_once_with()
    db.execute.return_value.scalars.return_value.all.return_value = ["AAA", "BBB"]
    assert scheduler_module._next_identifiers(db, "000") == ["AAA", "BBB"]
    db.scalar.return_value = None
    assert scheduler_module._has_configured_credential(db, 7) is False


def test_reconcile_pending_job_advances_only_after_terminal_success() -> None:
    assert scheduler_module._reconcile_pending_job(MagicMock(), _state()) is False
    state = _state(pending_job_id=11, pending_cursor="XYZ")
    active_db = MagicMock()
    active_db.get.return_value = SimpleNamespace(status="processing")

    assert scheduler_module._reconcile_pending_job(active_db, state) is True
    assert state.cursor is None
    active_db.commit.assert_not_called()

    success_db = MagicMock()
    success_db.get.return_value = SimpleNamespace(
        status="succeeded",
        payload_json={"searches": [{"q": "A"}, {"q": "XYZ"}]},
        error_detail=None,
    )
    assert scheduler_module._reconcile_pending_job(success_db, state) is False
    assert state.cursor == "XYZ"
    assert state.processed_identifiers == 2
    assert state.pending_job_id is None


def test_reconcile_failed_job_keeps_cursor_for_retry() -> None:
    state = _state(cursor="AAA", pending_job_id=12, pending_cursor="CCC")
    db = MagicMock()
    db.get.return_value = SimpleNamespace(status="failed", error_detail="remote error")

    assert scheduler_module._reconcile_pending_job(db, state) is False
    assert state.cursor == "AAA"
    assert state.pending_job_id is None
    assert state.last_error == "remote error"

    missing_state = _state(pending_job_id=13, pending_cursor="DDD")
    db.get.return_value = None
    scheduler_module._reconcile_pending_job(db, missing_state)
    assert missing_state.last_error == "Job autosync non trovato"


def test_autosync_guard_conditions(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch)
    db = MagicMock()
    monkeypatch.setattr(
        scheduler_module.settings, "capacitas_domande_irrigue_autosync_enabled", False
    )
    assert scheduler_module.run_domande_irrigue_autosync(db) == 0

    monkeypatch.setattr(
        scheduler_module.settings, "capacitas_domande_irrigue_autosync_enabled", True
    )
    monkeypatch.setattr(scheduler_module, "_window_context", lambda _now=None: (False, "cycle"))
    assert scheduler_module.run_domande_irrigue_autosync(db) == 0

    monkeypatch.setattr(scheduler_module, "_window_context", lambda _now=None: (True, "cycle"))
    monkeypatch.setattr(
        scheduler_module.settings, "capacitas_domande_irrigue_autosync_credential_id", None
    )
    assert scheduler_module.run_domande_irrigue_autosync(db) == 0

    monkeypatch.setattr(
        scheduler_module.settings, "capacitas_domande_irrigue_autosync_credential_id", 7
    )
    monkeypatch.setattr(scheduler_module, "_has_configured_credential", lambda _db, _id: False)
    assert scheduler_module.run_domande_irrigue_autosync(db) == 0


def test_autosync_skips_completed_cycle_pending_checkpoint_and_active_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _settings(monkeypatch)
    db = MagicMock()
    monkeypatch.setattr(scheduler_module, "_window_context", lambda _now=None: (True, "cycle"))
    monkeypatch.setattr(scheduler_module, "_has_configured_credential", lambda _db, _id: True)
    monkeypatch.setattr(scheduler_module, "has_available_credential", lambda _db, _id: True)

    monkeypatch.setattr(
        scheduler_module, "_load_state", lambda _db: _state(completed_cycle_key="cycle")
    )
    assert scheduler_module.run_domande_irrigue_autosync(db) == 0

    monkeypatch.setattr(scheduler_module, "_load_state", lambda _db: _state())
    monkeypatch.setattr(scheduler_module, "_reconcile_pending_job", lambda _db, _state: True)
    assert scheduler_module.run_domande_irrigue_autosync(db) == 0

    monkeypatch.setattr(scheduler_module, "_reconcile_pending_job", lambda _db, _state: False)
    db.scalar.return_value = 99
    assert scheduler_module.run_domande_irrigue_autosync(db) == 0


def test_autosync_materializes_exact_identifier_chunk(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch)
    state = _state()
    db = MagicMock()
    db.scalar.return_value = None
    monkeypatch.setattr(scheduler_module, "_window_context", lambda _now=None: (True, "2026-09-05"))
    monkeypatch.setattr(scheduler_module, "_has_configured_credential", lambda _db, _id: True)
    monkeypatch.setattr(scheduler_module, "has_available_credential", lambda _db, _id: True)
    monkeypatch.setattr(scheduler_module, "_load_state", lambda _db: state)
    monkeypatch.setattr(scheduler_module, "_reconcile_pending_job", lambda _db, _state: False)
    monkeypatch.setattr(scheduler_module, "_next_identifiers", lambda _db, _cursor: ["AAA", "BBB"])
    captured = []

    def create_job(_db, *, requested_by_user_id, credential_id, payload):
        captured.append((requested_by_user_id, credential_id, payload))
        return SimpleNamespace(id=91)

    monkeypatch.setattr(scheduler_module, "create_domande_irrigue_sync_job", create_job)

    assert scheduler_module.run_domande_irrigue_autosync(db) == 91
    requested_by, credential_id, payload = captured[0]
    assert requested_by is None
    assert credential_id == 7
    assert [search.q for search in payload.searches] == ["AAA", "BBB"]
    assert payload.trigger == "autosync"
    assert payload.role_anno_campagna is None
    assert payload.run_anomaly_checks is False
    assert state.pending_job_id == 91
    assert state.pending_cursor == "BBB"


def test_autosync_closes_cycle_and_runs_anomalies_once(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch)
    state = _state(cursor="ZZZ", cycle_key="2026-09-05", processed_identifiers=14)
    db = MagicMock()
    db.scalar.return_value = None
    monkeypatch.setattr(scheduler_module, "_window_context", lambda _now=None: (True, "2026-09-05"))
    monkeypatch.setattr(scheduler_module, "_has_configured_credential", lambda _db, _id: True)
    monkeypatch.setattr(scheduler_module, "has_available_credential", lambda _db, _id: True)
    monkeypatch.setattr(scheduler_module, "_load_state", lambda _db: state)
    monkeypatch.setattr(scheduler_module, "_reconcile_pending_job", lambda _db, _state: False)
    monkeypatch.setattr(scheduler_module, "_next_identifiers", lambda _db, _cursor: [])
    scan = MagicMock(return_value=SimpleNamespace(opened=1, updated=2, closed=3))
    monkeypatch.setattr(scheduler_module, "scan_domande_irrigue_anomalies", scan)

    assert scheduler_module.run_domande_irrigue_autosync(db) == 0
    scan.assert_called_once_with(db)
    assert state.cursor is None
    assert state.completed_cycle_key == "2026-09-05"


@pytest.mark.anyio
async def test_register_domande_irrigue_autosync_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch)
    scheduler = AsyncIOScheduler(timezone="UTC")

    await scheduler_module.register_domande_irrigue_autosync_scheduler(scheduler, lambda: None)

    job = scheduler.get_job("capacitas_domande_irrigue_autosync")
    assert job is not None
    assert job.max_instances == 1
    assert job.coalesce is True


@pytest.mark.anyio
async def test_scheduler_wrapper_closes_generator_database(monkeypatch: pytest.MonkeyPatch) -> None:
    db = MagicMock()

    def get_db():
        yield db

    monkeypatch.setattr(scheduler_module, "run_domande_irrigue_autosync", lambda current_db: 0)
    await scheduler_module._run_job_wrapper(get_db)

    db.close.assert_called_once_with()


@pytest.mark.anyio
async def test_scheduler_wrapper_handles_failure_and_async_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class AsyncDb:
        closed = False

        async def close(self) -> None:
            self.closed = True

    db = AsyncDb()
    monkeypatch.setattr(
        scheduler_module,
        "run_domande_irrigue_autosync",
        lambda _db: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    await scheduler_module._run_job_wrapper(lambda: db)

    assert db.closed is True


@pytest.mark.anyio
async def test_register_scheduler_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        scheduler_module.settings, "capacitas_domande_irrigue_autosync_enabled", False
    )
    scheduler = AsyncIOScheduler(timezone="UTC")

    await scheduler_module.register_domande_irrigue_autosync_scheduler(scheduler, lambda: None)

    assert scheduler.get_job("capacitas_domande_irrigue_autosync") is None
