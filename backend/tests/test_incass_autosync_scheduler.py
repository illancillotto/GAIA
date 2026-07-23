from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytest

from app.modules.elaborazioni import incass_autosync_scheduler


@pytest.mark.anyio
async def test_register_incass_autosync_scheduler_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    monkeypatch.setattr("app.core.config.settings.capacitas_incass_autosync_enabled", False)

    await incass_autosync_scheduler.register_incass_autosync_scheduler(scheduler, lambda: None)

    assert scheduler.get_job("capacitas_incass_autosync") is None


@pytest.mark.anyio
async def test_register_incass_autosync_scheduler_adds_job(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    monkeypatch.setattr("app.core.config.settings.capacitas_incass_autosync_enabled", True)
    monkeypatch.setattr("app.core.config.settings.capacitas_incass_autosync_interval_minutes", 15)
    monkeypatch.setattr("app.core.config.settings.capacitas_incass_autosync_stale_after_hours", 6)

    await incass_autosync_scheduler.register_incass_autosync_scheduler(scheduler, lambda: None)

    job = scheduler.get_job("capacitas_incass_autosync")
    assert job is not None
    assert job.max_instances == 1
    assert job.coalesce is True


def test_run_incass_autosync_harvest_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        def scalar(self, _statement):
            raise AssertionError("DB should not be queried while disabled")

    monkeypatch.setattr("app.core.config.settings.capacitas_incass_autosync_enabled", False)

    assert incass_autosync_scheduler.run_incass_autosync_harvest(FakeDb()) == 0  # type: ignore[arg-type]


def test_run_incass_autosync_harvest_skips_outside_operation_window(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        def scalar(self, _statement):
            raise AssertionError("DB should not be queried outside the inCASS autosync window")

    monkeypatch.setattr("app.core.config.settings.capacitas_incass_autosync_enabled", True)
    monkeypatch.setattr(incass_autosync_scheduler, "is_incass_autosync_within_operation_window", lambda: False)

    assert incass_autosync_scheduler.run_incass_autosync_harvest(FakeDb()) == 0  # type: ignore[arg-type]


def test_run_incass_autosync_harvest_skips_when_active_job_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        def scalar(self, _statement):
            return 42

    monkeypatch.setattr("app.core.config.settings.capacitas_incass_autosync_enabled", True)
    monkeypatch.setattr(incass_autosync_scheduler, "is_incass_autosync_within_operation_window", lambda: True)
    monkeypatch.setattr(
        incass_autosync_scheduler,
        "create_incass_ruolo_harvest_jobs",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("harvest should not run")),
    )

    assert incass_autosync_scheduler.run_incass_autosync_harvest(FakeDb()) == 0  # type: ignore[arg-type]


def test_run_incass_autosync_harvest_skips_without_active_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        def scalar(self, _statement):
            return None

    monkeypatch.setattr("app.core.config.settings.capacitas_incass_autosync_enabled", True)
    monkeypatch.setattr(incass_autosync_scheduler, "is_incass_autosync_within_operation_window", lambda: True)
    monkeypatch.setattr(
        incass_autosync_scheduler,
        "create_incass_ruolo_harvest_jobs",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("harvest should not run")),
    )

    assert incass_autosync_scheduler.run_incass_autosync_harvest(FakeDb()) == 0  # type: ignore[arg-type]


def test_run_incass_autosync_harvest_queues_stale_subjects(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        scalar_calls = 0

        def scalar(self, _statement):
            self.scalar_calls += 1
            if self.scalar_calls == 1:
                return None
            return 7

    captured_payloads = []

    def fake_create(_db, *, requested_by_user_id, payload):
        captured_payloads.append((requested_by_user_id, payload))
        assert payload.stale_synced_before is not None
        assert isinstance(payload.stale_synced_before, datetime)
        return SimpleNamespace(total_jobs=2, total_subjects=5)

    monkeypatch.setattr("app.core.config.settings.capacitas_incass_autosync_enabled", True)
    monkeypatch.setattr("app.core.config.settings.capacitas_incass_autosync_stale_after_hours", 12)
    monkeypatch.setattr("app.core.config.settings.capacitas_incass_autosync_credential_id", 7)
    monkeypatch.setattr("app.core.config.settings.capacitas_incass_autosync_anno", 2025)
    monkeypatch.setattr("app.core.config.settings.capacitas_incass_autosync_chunk_size", 50)
    monkeypatch.setattr("app.core.config.settings.capacitas_incass_autosync_limit_subjects", 200)
    monkeypatch.setattr("app.core.config.settings.capacitas_incass_autosync_throttle_ms", 100)
    monkeypatch.setattr(incass_autosync_scheduler, "is_incass_autosync_within_operation_window", lambda: True)
    monkeypatch.setattr(incass_autosync_scheduler, "create_incass_ruolo_harvest_jobs", fake_create)

    assert incass_autosync_scheduler.run_incass_autosync_harvest(FakeDb()) == 2  # type: ignore[arg-type]
    requested_by_user_id, payload = captured_payloads[0]
    assert requested_by_user_id is None
    assert payload.credential_id == 7
    assert payload.anno == 2025
    assert payload.chunk_size == 50
    assert payload.limit_subjects == 200
    assert payload.include_details is False
    assert payload.include_partitario is False
    assert payload.include_details_for_new_notices is True
    assert payload.include_partitario_for_new_notices is True
    assert payload.throttle_ms == 100


@pytest.mark.anyio
async def test_run_job_wrapper_closes_generator_db(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        closed = False

        def close(self) -> None:
            self.closed = True

    fake_db = FakeDb()

    def fake_get_db():
        yield fake_db

    monkeypatch.setattr(incass_autosync_scheduler, "run_incass_autosync_harvest", lambda db: 1)

    await incass_autosync_scheduler._run_job_wrapper(fake_get_db)

    assert fake_db.closed is True


@pytest.mark.anyio
async def test_run_job_wrapper_closes_async_db_after_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDb:
        closed = False

        async def close(self) -> None:
            self.closed = True

    fake_db = FakeDb()

    def fail_harvest(_db) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(incass_autosync_scheduler, "run_incass_autosync_harvest", fail_harvest)

    await incass_autosync_scheduler._run_job_wrapper(lambda: fake_db)

    assert fake_db.closed is True
