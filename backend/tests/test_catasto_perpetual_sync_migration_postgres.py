from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.schema import CreateSchema, DropSchema

pytestmark = pytest.mark.postgres


def _revision_module() -> object:
    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    return load_python_file(str(versions), "20260828_0900_catasto_perpetual_sync.py")


def _run_migration(connection: Connection, operation_name: str) -> None:
    with Operations.context(MigrationContext.configure(connection)):
        getattr(_revision_module(), operation_name)()


@pytest.fixture
def migration_engine() -> Iterator[Engine]:
    database_url = os.getenv("GAIA_TEST_POSTGRES_URL", "").strip()
    if not database_url:
        pytest.skip("GAIA_TEST_POSTGRES_URL non configurato")
    schema = f"test_catasto_perpetual_{uuid.uuid4().hex}"
    admin = create_engine(database_url, pool_pre_ping=True)
    if admin.dialect.name != "postgresql":
        admin.dispose()
        pytest.skip("GAIA_TEST_POSTGRES_URL deve puntare a PostgreSQL")
    engine = None
    try:
        with admin.begin() as connection:
            connection.execute(CreateSchema(schema))
        engine = create_engine(
            database_url, pool_pre_ping=True,
            connect_args={"options": f"-csearch_path={schema},public"},
        )
        with engine.begin() as connection:
            for statement in (
                "CREATE TABLE application_users (id INTEGER PRIMARY KEY)",
                "CREATE TABLE ruolo_particelle (id UUID PRIMARY KEY)",
                "CREATE TABLE catasto_batches (id UUID PRIMARY KEY)",
                "CREATE TABLE catasto_visure_requests (id UUID PRIMARY KEY)",
                "CREATE TABLE catasto_ruolo_autosync_config (id UUID PRIMARY KEY)",
            ):
                connection.execute(text(statement))
    except OperationalError as exc:
        if engine is not None:
            engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()
        pytest.skip(f"PostgreSQL di test non disponibile: {exc}")
    assert engine is not None
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()


def test_perpetual_sync_migration_round_trip(migration_engine: Engine) -> None:
    with migration_engine.begin() as connection:
        _run_migration(connection, "upgrade")
    inspector = inspect(migration_engine)
    assert "catasto_perpetual_sync_items" in inspector.get_table_names()
    config_columns = {
        column["name"] for column in inspector.get_columns("catasto_ruolo_autosync_config")
    }
    assert {"credential_ids", "primary_enabled", "secondary_enabled", "batch_size"} <= config_columns
    with migration_engine.begin() as connection:
        _run_migration(connection, "downgrade")
        _run_migration(connection, "upgrade")
    assert _revision_module().down_revision == "20260827_1100"


def test_perpetual_sync_migration_contract_on_sqlite(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'perpetual-migration.db'}")
    with engine.begin() as connection:
        for statement in (
            "CREATE TABLE application_users (id INTEGER PRIMARY KEY)",
            "CREATE TABLE ruolo_particelle (id CHAR(32) PRIMARY KEY)",
            "CREATE TABLE catasto_batches (id CHAR(32) PRIMARY KEY)",
            "CREATE TABLE catasto_visure_requests (id CHAR(32) PRIMARY KEY)",
            "CREATE TABLE catasto_ruolo_autosync_config (id CHAR(32) PRIMARY KEY)",
        ):
            connection.execute(text(statement))
        _run_migration(connection, "upgrade")
    assert "catasto_perpetual_sync_items" in inspect(engine).get_table_names()
    assert "last_planner_at" in {
        column["name"] for column in inspect(engine).get_columns("catasto_ruolo_autosync_config")
    }
    assert {
        "ix_catasto_perpetual_sync_items_ruolo_particella_id",
        "ix_catasto_perpetual_sync_items_cat_particella_id",
        "ix_catasto_perpetual_sync_items_subject_id",
        "ix_catasto_perpetual_sync_items_linked_batch_id",
        "ix_catasto_perpetual_sync_items_linked_request_id",
        "ix_catasto_perpetual_sync_items_retry_after",
    } <= {
        index["name"]
        for index in inspect(engine).get_indexes("catasto_perpetual_sync_items")
    }
    with engine.begin() as connection:
        _run_migration(connection, "downgrade")
    assert "catasto_perpetual_sync_items" not in inspect(engine).get_table_names()
    engine.dispose()
