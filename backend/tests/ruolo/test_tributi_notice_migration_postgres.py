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
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError
from sqlalchemy.schema import CreateSchema, DropSchema

pytestmark = pytest.mark.postgres

NOTICE_TABLE = "ruolo_tributi_notice_numbers"
ITEM_TABLE = "ruolo_tributi_reminder_batch_items"


@pytest.fixture
def migration_connection() -> Iterator[Connection]:
    database_url = os.getenv("GAIA_TEST_POSTGRES_URL", "").strip()
    if not database_url:
        pytest.skip("GAIA_TEST_POSTGRES_URL non configurato")

    schema = f"test_notice_migration_{uuid.uuid4().hex}"
    admin_engine = create_engine(database_url, pool_pre_ping=True)
    if admin_engine.dialect.name != "postgresql":
        admin_engine.dispose()
        pytest.skip("GAIA_TEST_POSTGRES_URL deve puntare a PostgreSQL")

    engine = None
    connection = None
    transaction = None
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
        connection = engine.connect()
        transaction = connection.begin()
        connection.execute(
            text(
                "CREATE TABLE ruolo_tributi_reminder_batch_items (id UUID PRIMARY KEY)"
            )
        )
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


def _revision_module() -> object:
    versions_path = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    return load_python_file(
        str(versions_path),
        "20260825_1100_ruolo_tributi_notice_numbers.py",
    )


def _run_migration(connection: Connection, operation_name: str) -> None:
    revision = _revision_module()
    operation = getattr(revision, operation_name)
    with Operations.context(MigrationContext.configure(connection)):
        operation()


def _assert_upgraded_schema(connection: Connection, schema: str) -> None:
    inspector = inspect(connection)
    assert inspector.has_table(NOTICE_TABLE, schema=schema)
    assert "notice_number_id" in {
        column["name"] for column in inspector.get_columns(ITEM_TABLE, schema=schema)
    }
    assert {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(NOTICE_TABLE, schema=schema)
    } == {
        "uq_ruolo_tributi_notice_identity",
        "uq_ruolo_tributi_notice_number",
        "uq_ruolo_tributi_notice_year_progressive",
    }
    explicit_indexes = {
        index["name"]
        for index in inspector.get_indexes(NOTICE_TABLE, schema=schema)
        if not index.get("duplicates_constraint")
    }
    assert explicit_indexes == {
        "ix_ruolo_tributi_notice_numbers_emission_year",
        "ix_ruolo_tributi_notice_numbers_status",
    }
    foreign_keys = inspector.get_foreign_keys(ITEM_TABLE, schema=schema)
    notice_foreign_key = next(
        foreign_key
        for foreign_key in foreign_keys
        if foreign_key["name"]
        == "fk_ruolo_tributi_reminder_batch_items_notice_number_id"
    )
    assert notice_foreign_key["referred_table"] == NOTICE_TABLE
    assert notice_foreign_key["options"]["ondelete"] == "RESTRICT"


def test_notice_number_migration_upgrade_downgrade_upgrade(
    migration_connection: Connection,
) -> None:
    assert _revision_module().down_revision == "20260824_1000"
    schema = migration_connection.scalar(text("SELECT current_schema()"))
    assert isinstance(schema, str)

    _run_migration(migration_connection, "upgrade")
    _assert_upgraded_schema(migration_connection, schema)

    _run_migration(migration_connection, "downgrade")
    inspector = inspect(migration_connection)
    assert not inspector.has_table(NOTICE_TABLE, schema=schema)
    assert "notice_number_id" not in {
        column["name"] for column in inspector.get_columns(ITEM_TABLE, schema=schema)
    }

    _run_migration(migration_connection, "upgrade")
    _assert_upgraded_schema(migration_connection, schema)
