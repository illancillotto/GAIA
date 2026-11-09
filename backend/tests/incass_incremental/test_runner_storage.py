import asyncio
import importlib.util
import os
import runpy
import sys
from contextlib import asynccontextmanager, contextmanager
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.models.capacitas import CapacitasInCassSyncJob
from app.modules.elaborazioni.capacitas.incremental import runner as r
from app.modules.elaborazioni.capacitas.incremental.config import IncrementalSettings
from app.modules.elaborazioni.capacitas.incremental.journal import begin_cycle
from app.modules.elaborazioni.capacitas.incremental.models import IncrementalHead
from app.modules.elaborazioni.capacitas.incremental.storage import pipeline_lease

from .conftest import NOW
from .test_cycle_journal import deps


def test_daily_process_retry_and_off(db, config, monkeypatch):
    assert asyncio.run(r.tick(IncrementalSettings(mode="off"))) == {"status": "off"}
    dependencies = deps()
    dependencies.client = None
    dependencies.portal = SimpleNamespace(requests=3)

    @asynccontextmanager
    async def fake_deps(_config):
        yield dependencies

    monkeypatch.setattr(r, "dependencies", fake_deps)
    result = asyncio.run(r.process(db, config, NOW, 0))
    assert result["status"] == "validated" and result["report"]["rows_by_year"] == {"2025": 1}
    assert asyncio.run(r.process(db, config, NOW, 0))["status"] == "validated"
    assert not r.should_attempt(SimpleNamespace(status="invalid"), config, NOW)
    assert not r.should_attempt(
        SimpleNamespace(status="partial", attempts=config.max_attempts), config, NOW
    )
    assert not r.should_attempt(
        SimpleNamespace(status="partial", attempts=1, report={"attempted_at": NOW.isoformat()}),
        config,
        NOW,
    )
    assert r.should_attempt(
        SimpleNamespace(
            status="partial",
            attempts=1,
            report={"attempted_at": (NOW - timedelta(hours=2)).isoformat()},
        ),
        config,
        NOW,
    )
    # A validated cycle can continue an active outbox without reexporting.
    monkeypatch.setattr(r, "pending_changes", lambda *a: [1])
    monkeypatch.setattr(r, "drain", AsyncMock(return_value=2))
    cfg = config.model_copy(update={"mode": "active"})
    monkeypatch.setattr(r, "require_shadow_history", lambda *a: None)
    cycle = db.get(r.begin_cycle(db, config, NOW).__class__, result["cycle"])
    cycle.mode = "active"
    db.commit()
    assert asyncio.run(r.process(db, cfg, NOW, 0))["report"]["completed_this_attempt"] == 2


def test_tick_window_lease_and_existing_jobs(db, config, monkeypatch):
    monkeypatch.setattr(r, "is_incass_autosync_within_operation_window", lambda now: False)
    assert asyncio.run(r.tick(config, NOW))["status"] == "outside_window"
    monkeypatch.setattr(r, "is_incass_autosync_within_operation_window", lambda now: True)

    @contextmanager
    def lease(_engine):
        yield False

    monkeypatch.setattr(r, "pipeline_lease", lease)
    assert asyncio.run(r.tick(config, NOW))["status"] == "busy"

    @contextmanager
    def acquired(_engine):
        yield True

    @contextmanager
    def session():
        yield db

    monkeypatch.setattr(r, "pipeline_lease", acquired)
    monkeypatch.setattr(r, "SessionLocal", session)
    monkeypatch.setattr(r, "process", AsyncMock(return_value={"status": "processed"}))
    assert asyncio.run(r.tick(config))["status"] == "processed"
    db.add(CapacitasInCassSyncJob(status="pending", mode="subjects_sync", payload_json={}))
    db.commit()
    assert asyncio.run(r.tick(config, NOW))["status"] == "legacy_job_busy"


def test_active_requires_distinct_shadow_days(db, config):
    cfg = config.model_copy(update={"mode": "active", "min_shadow_cycles": 2})
    from app.modules.elaborazioni.capacitas.incremental.normalize import SnapshotInvalid

    with pytest.raises(SnapshotInvalid, match="insufficient_shadow_days"):
        r.require_shadow_history(db, cfg)
    for offset in range(2):
        cycle = begin_cycle(db, config, NOW + timedelta(days=offset))
        cycle.status = "validated"
        db.commit()
    r.require_shadow_history(db, cfg)


def test_lazy_portal_and_dependencies(config, monkeypatch):
    calls = []
    manager = SimpleNamespace(
        get_http_client=lambda: SimpleNamespace(event_hooks={"request": calls})
    )
    portal = SimpleNamespace(
        open=AsyncMock(return_value=manager), close=AsyncMock(), relogin=AsyncMock()
    )
    monkeypatch.setattr(r, "CapacitasPortal", lambda *a: portal)
    exports = SimpleNamespace(
        list_ricerca_years=AsyncMock(return_value=["2025"]),
        export_ricerca_avvisi=AsyncMock(return_value="xlsx"),
    )
    client = SimpleNamespace(
        fetch_notice_detail=AsyncMock(return_value="detail"),
        fetch_notice_partitario=AsyncMock(return_value="partitario"),
    )
    monkeypatch.setattr(r, "InCassExportClient", lambda *a, **kw: exports)
    monkeypatch.setattr(r, "InCassClient", lambda *a: client)
    lazy = r.LazyPortal(config)

    async def exercise():
        assert await lazy.list_ricerca_years() == ["2025"]
        assert await lazy.export_ricerca_avvisi("2025") == "xlsx"
        assert await lazy.fetch_notice_detail("key") == "detail"
        assert await lazy.fetch_notice_partitario("key") == "partitario"
        await lazy.refresh_session()
        await calls[0](None)
        assert lazy.requests == 1
        monkeypatch.setattr(r, "drive_credentials_from_settings", lambda: "credentials")
        monkeypatch.setattr(r, "GoogleDriveClient", lambda *a: "drive")
        async with r.dependencies(config) as deps:
            assert deps.drive == "drive"

    asyncio.run(exercise())
    assert portal.open.await_count == 1 and portal.close.await_count == 1


def test_run_cli_success_error_poll_and_entrypoint(config, monkeypatch):
    monkeypatch.setattr(r, "tick", AsyncMock(return_value={"status": "off"}))
    asyncio.run(r.run(config, once=True))
    monkeypatch.setattr(r, "tick", AsyncMock(side_effect=TimeoutError("private")))
    with pytest.raises(TimeoutError):
        asyncio.run(r.run(config, once=True))

    class StopPoll(Exception):
        pass

    monkeypatch.setattr(r.asyncio, "sleep", AsyncMock(side_effect=StopPoll))
    with pytest.raises(StopPoll):
        asyncio.run(r.run(config))
    # Exercise the real __main__ route, with off mode and a one-shot heartbeat.
    monkeypatch.setenv("INCASS_INCREMENTAL_MODE", "off")
    monkeypatch.setattr(sys, "argv", ["runner", "--once"])

    async def heartbeat(coroutine, _heartbeat):
        await coroutine

    monkeypatch.setattr("app.worker_health.run_with_heartbeat", heartbeat)
    monkeypatch.delitem(sys.modules, r.__name__)
    runpy.run_module(r.__name__, run_name="__main__")
    with pytest.raises(SystemExit):
        asyncio.run(r.main(["--once", "--revision", "-1"]))
    with pytest.raises(SystemExit):
        asyncio.run(r.main(["--once", "--revision", "10000"]))


def migration_module():
    path = (
        Path(__file__).resolve().parents[2] / "alembic/versions/20261109_1000_incass_incremental.py"
    )
    spec = importlib.util.spec_from_file_location("incass_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_reversible_and_model_registry(monkeypatch):
    import app.db.base as registry

    assert "incass_incremental_cycles" in registry.Base.metadata.tables
    engine = create_engine("sqlite://")
    module = migration_module()
    with engine.begin() as connection:
        monkeypatch.setattr(module, "op", Operations(MigrationContext.configure(connection)))
        module.upgrade()
        assert connection.scalar(select(IncrementalHead.id)) == 1
        module.downgrade()
        assert not inspect(connection).get_table_names()
    engine.dispose()
    with pytest.raises(RuntimeError, match="requires_postgresql"):
        with pipeline_lease(engine):
            pass


def test_real_postgres_lease_migration_and_rollback(monkeypatch):
    url = os.getenv("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("requires disposable PostgreSQL")
    engine = create_engine(url)
    schema = "incass_test_" + uuid4().hex
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    isolated = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    module = migration_module()
    try:
        with isolated.begin() as connection:
            monkeypatch.setattr(module, "op", Operations(MigrationContext.configure(connection)))
            module.upgrade()
        with pipeline_lease(isolated) as first:
            assert first
            with pipeline_lease(isolated) as second:
                assert not second
        with pytest.raises(RuntimeError):
            with pipeline_lease(isolated) as third:
                assert third
                raise RuntimeError("crash releases session lease")
        with pipeline_lease(isolated) as fourth:
            assert fourth
        with Session(isolated) as db:
            config = IncrementalSettings(mode="shadow", credential_id=1)
            begin_cycle(db, config, NOW)
            db.get(IncrementalHead, 1).cycle_id = "not-existent"
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
            assert db.get(IncrementalHead, 1).cycle_id is None
        with isolated.begin() as connection:
            monkeypatch.setattr(module, "op", Operations(MigrationContext.configure(connection)))
            module.downgrade()
            assert not inspect(connection).get_table_names()
    finally:
        isolated.dispose()
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()
