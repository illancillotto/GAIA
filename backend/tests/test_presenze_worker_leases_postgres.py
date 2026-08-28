from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from app.core.datetime_compat import UTC
from app.models.application_user import (
    ApplicationUser,  # noqa: F401 - resolve ORM FK metadata
)
from app.modules.presenze.models import PresenzeSyncJob
from app.modules.presenze.services import sync_runtime
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.schema import CreateSchema, DropSchema

pytestmark = pytest.mark.postgres


def _revision_module() -> object:
    versions_path = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    return load_python_file(
        str(versions_path),
        "20260827_1000_presenze_worker_leases.py",
    )


def _run_migration(connection: Connection, operation_name: str) -> None:
    operation = getattr(_revision_module(), operation_name)
    with Operations.context(MigrationContext.configure(connection)):
        operation()


def _create_base_table(connection: Connection) -> None:
    connection.execute(
        text(
            "CREATE TABLE presenze_sync_jobs ("
            "id UUID PRIMARY KEY, "
            "status VARCHAR(20) NOT NULL, "
            "requested_by_user_id INTEGER NOT NULL, "
            "credential_id INTEGER NULL, "
            "import_job_id UUID NULL, "
            "period_start DATE NOT NULL, "
            "period_end DATE NOT NULL, "
            "collaborator_limit INTEGER NULL, "
            "records_imported INTEGER NOT NULL DEFAULT 0, "
            "records_skipped INTEGER NOT NULL DEFAULT 0, "
            "records_errors INTEGER NOT NULL DEFAULT 0, "
            "json_artifact_path VARCHAR(500) NULL, "
            "worker_log_path VARCHAR(500) NULL, "
            "worker_pid INTEGER NULL, "
            "attempt_count INTEGER NOT NULL DEFAULT 0, "
            "max_attempts INTEGER NOT NULL DEFAULT 3, "
            "error_detail TEXT NULL, "
            "params_json JSON NULL, "
            "created_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
            "started_at TIMESTAMPTZ NULL, "
            "finished_at TIMESTAMPTZ NULL"
            ")"
        )
    )


@pytest.fixture
def lease_engine() -> Iterator[Engine]:
    database_url = os.getenv("GAIA_TEST_POSTGRES_URL", "").strip()
    if not database_url:
        pytest.skip("GAIA_TEST_POSTGRES_URL non configurato")

    schema = f"test_presenze_leases_{uuid.uuid4().hex}"
    admin_engine = create_engine(database_url, pool_pre_ping=True)
    if admin_engine.dialect.name != "postgresql":
        admin_engine.dispose()
        pytest.skip("GAIA_TEST_POSTGRES_URL deve puntare a PostgreSQL")

    engine = None
    schema_created = False
    try:
        with admin_engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        schema_created = True
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            connect_args={"options": f"-csearch_path={schema},public"},
        )
        with engine.begin() as connection:
            _create_base_table(connection)
    except OperationalError as exc:
        if engine is not None:
            engine.dispose()
        if schema_created:
            with admin_engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
        admin_engine.dispose()
        pytest.skip(f"PostgreSQL di test non disponibile: {exc}")

    assert engine is not None
    try:
        yield engine
    finally:
        engine.dispose()
        try:
            with admin_engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
        finally:
            admin_engine.dispose()


def test_presenze_lease_migration_is_additive_and_round_trips(
    lease_engine: Engine,
) -> None:
    job_id = uuid.uuid4()
    with lease_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO presenze_sync_jobs "
                "(id, status, requested_by_user_id, period_start, period_end) "
                "VALUES (:id, 'pending', 7, '2026-08-01', '2026-08-31')"
            ),
            {"id": job_id},
        )
        _run_migration(connection, "upgrade")

    inspector = inspect(lease_engine)
    columns = {column["name"] for column in inspector.get_columns("presenze_sync_jobs")}
    indexes = {index["name"] for index in inspector.get_indexes("presenze_sync_jobs")}
    assert {
        "worker_id",
        "lease_token",
        "lease_generation",
        "heartbeat_at",
        "lease_expires_at",
        "retry_not_before",
        "priority",
    }.issubset(columns)
    assert {
        "ix_presenze_sync_jobs_worker_id",
        "ix_presenze_sync_jobs_claim",
        "ix_presenze_sync_jobs_lease_expiry",
    }.issubset(indexes)
    with lease_engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT lease_generation, priority FROM presenze_sync_jobs WHERE id = :id"
            ),
            {"id": job_id},
        ).one() == (0, 100)

    with lease_engine.begin() as connection:
        _run_migration(connection, "downgrade")
        _run_migration(connection, "upgrade")
    assert _revision_module().down_revision == "20260827_0900"


def test_presenze_claim_skips_locked_job_and_respects_fair_order(
    lease_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    with lease_engine.begin() as connection:
        _run_migration(connection, "upgrade")
    Session = sessionmaker(bind=lease_engine, expire_on_commit=False)
    oldest = PresenzeSyncJob(
        status="pending",
        requested_by_user_id=7,
        credential_id=1,
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        priority=10,
        created_at=datetime.now(UTC) - timedelta(hours=2),
    )
    second = PresenzeSyncJob(
        status="pending",
        requested_by_user_id=7,
        credential_id=1,
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        priority=10,
        created_at=datetime.now(UTC) - timedelta(hours=1),
    )
    with Session.begin() as seed:
        seed.add_all([oldest, second])

    locker = Session()
    claimant = Session()
    monkeypatch.setattr(sync_runtime.settings, "presenze_sync_artifacts_path", str(tmp_path))
    try:
        locked = locker.scalar(
            select(PresenzeSyncJob)
            .where(PresenzeSyncJob.id == oldest.id)
            .with_for_update()
        )
        assert locked is not None

        claimed = sync_runtime.claim_next_pending_sync_job(
            claimant,
            worker_pid=1234,
            worker_instance_id="postgres-worker",
        )

        assert claimed is not None
        assert claimed.id == second.id
        assert claimed.worker_id == "postgres-worker"
        assert claimed.lease_token is not None
    finally:
        locker.rollback()
        locker.close()
        claimant.close()


def test_presenze_lease_generation_fences_stale_postgres_owner(
    lease_engine: Engine,
) -> None:
    with lease_engine.begin() as connection:
        _run_migration(connection, "upgrade")
    Session = sessionmaker(bind=lease_engine, expire_on_commit=False)
    lease_token = uuid.uuid4()
    job = PresenzeSyncJob(
        status="running",
        requested_by_user_id=7,
        credential_id=1,
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        worker_id="worker-a",
        lease_token=lease_token,
        lease_generation=1,
        lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    with Session.begin() as seed:
        seed.add(job)

    stale_session = Session()
    recovery_session = Session()
    try:
        stale_owner = stale_session.get(PresenzeSyncJob, job.id)
        recovered = recovery_session.get(PresenzeSyncJob, job.id)
        assert stale_owner is not None
        assert recovered is not None

        recovered.lease_generation += 1
        recovered.status = "pending"
        sync_runtime.clear_sync_job_lease(recovered)
        recovery_session.commit()

        stale_owner.status = "completed"
        with pytest.raises(StaleDataError):
            stale_session.commit()
    finally:
        stale_session.rollback()
        stale_session.close()
        recovery_session.close()
