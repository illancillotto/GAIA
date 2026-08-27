from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from app.models.catasto import CatastoBatch
from sqlalchemy import JSON, create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.schema import CreateSchema, DropSchema

pytestmark = pytest.mark.postgres


def _revision_module() -> object:
    versions_path = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    return load_python_file(
        str(versions_path),
        "20260827_1100_catasto_batch_credential_allowlist.py",
    )


def _run_migration(connection: Connection, operation_name: str) -> None:
    operation = getattr(_revision_module(), operation_name)
    with Operations.context(MigrationContext.configure(connection)):
        operation()


@pytest.fixture
def migration_engine() -> Iterator[Engine]:
    database_url = os.getenv("GAIA_TEST_POSTGRES_URL", "").strip()
    if not database_url:
        pytest.skip("GAIA_TEST_POSTGRES_URL non configurato")

    schema = f"test_catasto_batch_allowlist_{uuid.uuid4().hex}"
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
            connection.execute(text("CREATE TABLE catasto_batches (id UUID PRIMARY KEY)"))
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


def test_allowlist_metadata_matches_migration_contract() -> None:
    column = CatastoBatch.__table__.c.credential_ids

    assert isinstance(column.type, JSON)
    assert column.nullable is True


def test_allowlist_migration_preserves_rows_and_round_trips(
    migration_engine: Engine,
) -> None:
    batch_id = uuid.uuid4()
    credential_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    with migration_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO catasto_batches (id) VALUES (:id)"),
            {"id": batch_id},
        )
        _run_migration(connection, "upgrade")

    inspector = inspect(migration_engine)
    columns = {column["name"]: column for column in inspector.get_columns("catasto_batches")}
    assert isinstance(columns["credential_ids"]["type"], JSON)
    assert columns["credential_ids"]["nullable"] is True

    with migration_engine.begin() as connection:
        assert connection.scalar(
            text("SELECT credential_ids FROM catasto_batches WHERE id = :id"),
            {"id": batch_id},
        ) is None
        connection.execute(
            text(
                "UPDATE catasto_batches "
                "SET credential_ids = CAST(:credential_ids AS JSON) "
                "WHERE id = :id"
            ),
            {"credential_ids": json.dumps(credential_ids), "id": batch_id},
        )
        assert connection.scalar(
            text("SELECT credential_ids FROM catasto_batches WHERE id = :id"),
            {"id": batch_id},
        ) == credential_ids
        _run_migration(connection, "downgrade")
        _run_migration(connection, "upgrade")

    assert "credential_ids" in {
        column["name"] for column in inspect(migration_engine).get_columns("catasto_batches")
    }
    assert _revision_module().down_revision == "20260827_1000"
