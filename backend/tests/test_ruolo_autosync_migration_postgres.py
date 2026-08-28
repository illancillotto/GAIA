from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from app.modules.ruolo.models import RuoloImportJob, RuoloParticella
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.schema import CreateSchema, DropSchema

pytestmark = pytest.mark.postgres

ITEM_TABLE = "catasto_ruolo_autosync_items"


@pytest.fixture
def migration_connection() -> Iterator[Connection]:
    database_url = os.getenv("GAIA_TEST_POSTGRES_URL", "").strip()
    if not database_url:
        pytest.skip("GAIA_TEST_POSTGRES_URL non configurato")

    schema = f"test_ruolo_autosync_{uuid.uuid4().hex}"
    admin_engine = create_engine(database_url, pool_pre_ping=True)
    if admin_engine.dialect.name != "postgresql":
        admin_engine.dispose()
        pytest.skip("GAIA_TEST_POSTGRES_URL deve puntare a PostgreSQL")

    engine = None
    connection = None
    transaction = None
    schema_created = False
    try:
        with admin_engine.begin() as admin_connection:
            admin_connection.execute(CreateSchema(schema))
        schema_created = True
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            connect_args={"options": f"-csearch_path={schema},public"},
        )
        connection = engine.connect()
        transaction = connection.begin()
        _create_base_tables(connection)
    except OperationalError as exc:
        if transaction is not None and transaction.is_active:
            transaction.rollback()
        if connection is not None:
            connection.close()
        if engine is not None:
            engine.dispose()
        if schema_created:
            with admin_engine.begin() as cleanup_connection:
                cleanup_connection.execute(DropSchema(schema, cascade=True))
        admin_engine.dispose()
        pytest.skip(f"PostgreSQL di test non disponibile: {exc}")

    assert connection is not None
    assert transaction is not None
    assert engine is not None
    try:
        yield connection
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()
        engine.dispose()
        try:
            with admin_engine.begin() as cleanup_connection:
                cleanup_connection.execute(DropSchema(schema, cascade=True))
        finally:
            admin_engine.dispose()


def _create_base_tables(connection: Connection) -> None:
    connection.execute(
        text(
            "CREATE TABLE ruolo_particelle ("
            "id UUID PRIMARY KEY, "
            "cat_particella_id UUID NULL, "
            "created_at TIMESTAMPTZ NOT NULL DEFAULT now()"
            ")"
        )
    )
    connection.execute(
        text(
            "CREATE TABLE catasto_ruolo_autosync_items ("
            "id UUID PRIMARY KEY, "
            "user_id INTEGER NOT NULL, "
            "ruolo_particella_id UUID NOT NULL, "
            "cat_particella_id UUID NULL, "
            "status VARCHAR(32) NOT NULL, "
            "updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
            "created_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
            "CONSTRAINT uq_catasto_ruolo_autosync_item_user_particella "
            "UNIQUE (user_id, ruolo_particella_id)"
            ")"
        )
    )


def _revision_module() -> object:
    versions_path = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    return load_python_file(
        str(versions_path),
        "20260827_0900_ruolo_autosync_performance.py",
    )


def _run_migration(connection: Connection, operation_name: str) -> None:
    operation = getattr(_revision_module(), operation_name)
    with Operations.context(MigrationContext.configure(connection)):
        operation()


def test_ruolo_autosync_model_declares_the_migrated_source_index() -> None:
    source_indexes = {index.name for index in RuoloParticella.__table__.indexes}
    import_job_indexes = {index.name for index in RuoloImportJob.__table__.indexes}

    assert "ix_ruolo_particelle_created_at" in source_indexes
    assert "ix_ruolo_import_jobs_created_at" not in import_job_indexes


def test_ruolo_autosync_migration_deduplicates_and_round_trips(
    migration_connection: Connection,
) -> None:
    cat_particella_id = uuid.uuid4()
    rows = [
        {
            "id": uuid.uuid4(),
            "user_id": 7,
            "ruolo_particella_id": uuid.uuid4(),
            "cat_particella_id": cat_particella_id,
            "status": "pending",
        },
        {
            "id": uuid.uuid4(),
            "user_id": 7,
            "ruolo_particella_id": uuid.uuid4(),
            "cat_particella_id": cat_particella_id,
            "status": "completed",
        },
    ]
    migration_connection.execute(
        text(
            "INSERT INTO catasto_ruolo_autosync_items "
            "(id, user_id, ruolo_particella_id, cat_particella_id, status) "
            "VALUES (:id, :user_id, :ruolo_particella_id, :cat_particella_id, :status)"
        ),
        rows,
    )

    _run_migration(migration_connection, "upgrade")

    remaining = migration_connection.execute(
        text("SELECT id, status FROM catasto_ruolo_autosync_items")
    ).one()
    assert remaining == (rows[1]["id"], "completed")
    schema = migration_connection.scalar(text("SELECT current_schema()"))
    inspector = inspect(migration_connection)
    constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(ITEM_TABLE, schema=schema)
    }
    indexes = {
        index["name"]
        for index in inspector.get_indexes(ITEM_TABLE, schema=schema)
        if not index.get("duplicates_constraint")
    }
    assert "uq_catasto_ruolo_autosync_item_user_cat_particella" in constraints
    assert indexes == {
        "ix_catasto_ruolo_autosync_items_user_status",
        "ix_catasto_ruolo_autosync_items_user_updated",
    }
    source_indexes = {
        index["name"]
        for index in inspector.get_indexes("ruolo_particelle", schema=schema)
    }
    assert source_indexes == {"ix_ruolo_particelle_created_at"}

    with pytest.raises(IntegrityError), migration_connection.begin_nested():
        migration_connection.execute(
            text(
                "INSERT INTO catasto_ruolo_autosync_items "
                "(id, user_id, ruolo_particella_id, cat_particella_id, status) "
                "VALUES (:id, 7, :ruolo_particella_id, :cat_particella_id, 'pending')"
            ),
            {
                "id": uuid.uuid4(),
                "ruolo_particella_id": uuid.uuid4(),
                "cat_particella_id": cat_particella_id,
            },
        )

    _run_migration(migration_connection, "downgrade")
    _run_migration(migration_connection, "upgrade")
    assert _revision_module().down_revision == "20260826_1200"
