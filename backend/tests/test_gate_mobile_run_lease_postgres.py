"""Exercise exclusion and process-death recovery against a disposable PostgreSQL schema."""

import asyncio
import multiprocessing
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.modules.operazioni.models.gate_mobile_sync_run import GateMobileSyncRun
from app.services import gate_mobile_sync as sync
from app.services.gate_mobile_run_lease import GATE_MOBILE_SYNC_LOCK, GateMobileSyncBusy

pytestmark = pytest.mark.postgres


def _engine(url, schema):
    return create_engine(url, connect_args={"options": "-csearch_path=" + schema})


def _hold_cycle(url, schema, ready):
    engine = _engine(url, schema)

    async def stop_after_claim(_db, **_kwargs):
        ready.set()
        await asyncio.Event().wait()

    sync.run_gate_mobile_sync_once = stop_after_claim
    with Session(engine) as db:
        asyncio.run(
            sync.execute_gate_mobile_sync(
                db, app_settings=_settings(), trigger_source="fixture_owner"
            )
        )


def _settings():
    return sync.Settings(
        _env_file=None,
        DATABASE_URL="sqlite://",
        JWT_SECRET_KEY="fixture-secret",
        GATE_MOBILE_SYNC_ENABLED=True,
    )


def test_runner_death_releases_exclusive_lease_and_preserves_history(monkeypatch, tmp_path):
    monkeypatch.setenv("GATE_MOBILE_SYNC_LOCK_PATH", str(tmp_path / "outbound.lock"))
    url = os.environ.get("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set GAIA_TEST_POSTGRES_URL for the disposable schema")
    schema = "test_gate_outbound_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(CreateSchema(schema))
    engine = _engine(url, schema)
    ctx = multiprocessing.get_context("spawn")
    ready = ctx.Event()
    owner = ctx.Process(target=_hold_cycle, args=(url, schema, ready))
    try:
        GateMobileSyncRun.__table__.create(engine)
        with Session(engine) as db:
            db.add(
                GateMobileSyncRun(
                    trigger_source="legacy", status="running", started_at=datetime.now(UTC)
                )
            )
            db.commit()
        with engine.begin() as lease, Session(engine) as db:
            lease.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": GATE_MOBILE_SYNC_LOCK})
            with pytest.raises(GateMobileSyncBusy):
                asyncio.run(sync.execute_gate_mobile_sync(db, app_settings=_settings()))
        owner.start()
        assert ready.wait(30)
        with Session(engine) as db, pytest.raises(GateMobileSyncBusy):
            asyncio.run(sync.execute_gate_mobile_sync(db, app_settings=_settings()))
        with Session(engine) as db:
            rows = db.scalars(select(GateMobileSyncRun)).all()
            assert len(rows) == 2
            assert {r.status for r in rows} == {"running"}
            previous = next(row for row in rows if row.trigger_source == "fixture_owner")
            assert db.scalar(
                text("SELECT pg_terminate_backend(:pid, 5000)"), {"pid": previous.lease_backend_pid}
            )
        with Session(engine) as db, pytest.raises(GateMobileSyncBusy):
            asyncio.run(sync.execute_gate_mobile_sync(db, app_settings=_settings()))
        owner.kill()
        owner.join(15)
        assert owner.exitcode == -9
        calls = []

        async def complete(*_args, **_kwargs):
            calls.append("cycle")
            # Killing only the advisory session after admission must leave the
            # committed outbound result observable to the caller.
            with Session(engine) as observer:
                owner_db_pid = observer.scalar(
                    select(GateMobileSyncRun.lease_backend_pid).where(
                        GateMobileSyncRun.trigger_source == "manual_cli"
                    )
                )
                assert observer.scalar(
                    text("SELECT pg_terminate_backend(:pid, 5000)"), {"pid": owner_db_pid}
                )
            return sync.GateMobileSyncReport([], 0, 0, 0)

        monkeypatch.setattr(sync, "run_gate_mobile_sync_once", complete)
        with Session(engine) as db:
            result = asyncio.run(sync.execute_gate_mobile_sync(db, app_settings=_settings()))
            assert result.status == "succeeded"
            rows = {r.trigger_source: r for r in db.scalars(select(GateMobileSyncRun))}
            assert rows["legacy"].status == "running"
            assert rows["legacy"].lease_backend_pid is None
            assert rows["fixture_owner"].error_kind == "worker_interrupted"
            assert rows["fixture_owner"].finished_at is not None
            assert rows["fixture_owner"].lease_backend_pid is not None
            assert rows["manual_cli"].id == result.run_id
            assert calls == ["cycle"]
    finally:
        if owner.is_alive():
            owner.kill()
            owner.join(10)
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(DropSchema(schema, cascade=True))
        admin.dispose()


def test_receipt_and_domain_commits_rollback_together_on_postgres():
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.util import load_python_file
    from sqlalchemy import inspect

    from app.modules.operazioni.models.gate_mobile_sync_run import GateMobileActionReceipt
    from app.services.gate_mobile_action_receipt import apply_once

    url = os.environ.get("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set GAIA_TEST_POSTGRES_URL for the disposable schema")
    schema = "test_gate_receipt_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(CreateSchema(schema))
    engine = _engine(url, schema)
    migration = load_python_file(
        str(Path(__file__).parents[1] / "alembic/versions"),
        "20261119_1200_gate_mobile_run_lease.py",
    )
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE gate_mobile_sync_run (id integer PRIMARY KEY)"))
            conn.execute(text("CREATE TABLE fixture_mutation (n integer)"))
            conn.execute(text("INSERT INTO gate_mobile_sync_run VALUES (1)"))
            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()
            # Compatibility with the old writer's insert and read projections.
            conn.execute(text("INSERT INTO gate_mobile_sync_run(id) VALUES (2)"))
            assert conn.execute(
                text("SELECT id FROM gate_mobile_sync_run ORDER BY id")
            ).scalars().all() == [1, 2]
        action = {"action_type": "fixture", "payload_json": {"field": "value"}}

        def apply_then_fail(domain, _action):
            domain.execute(text("INSERT INTO fixture_mutation VALUES(1)"))
            domain.commit()
            raise RuntimeError("fixture: interrupted before receipt")

        with Session(engine) as db:
            with pytest.raises(RuntimeError, match="before receipt"):
                apply_once(db, action, "id", action["payload_json"], apply_then_fail)
            db.rollback()
            assert db.scalar(text("SELECT COUNT(*) FROM fixture_mutation")) == 0
            assert db.get(GateMobileActionReceipt, "id") is None

        def apply_success(domain, _action):
            domain.execute(text("INSERT INTO fixture_mutation VALUES(1)"))
            domain.commit()
            return {"ack": "value"}

        for _ in range(2):
            with Session(engine) as db:
                assert apply_once(db, action, "id", action["payload_json"], apply_success) == {
                    "ack": "value"
                }
        with engine.begin() as conn:
            assert conn.scalar(text("SELECT count(*) FROM fixture_mutation")) == 1
            with Operations.context(MigrationContext.configure(conn)):
                migration.downgrade()
            assert "gate_mobile_action_receipt" not in inspect(conn).get_table_names()
            assert conn.scalar(text("SELECT count(*) FROM gate_mobile_sync_run")) == 2
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(DropSchema(schema, cascade=True))
        admin.dispose()
