from __future__ import annotations

import os
import threading
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.schema import CreateSchema, DropSchema

pytestmark = pytest.mark.postgres

AUDIT_TABLE = "presenze_collaborator_mapping_audit"
COLLABORATOR_TABLE = "presenze_collaborators"
UNIQUE_INDEX = "uq_presenze_collaborators_application_user_id"


@pytest.fixture
def postgres_engine() -> Iterator[Engine]:
    database_url = os.getenv("GAIA_TEST_POSTGRES_URL", "").strip()
    if not database_url:
        pytest.skip("GAIA_TEST_POSTGRES_URL non configurato")
    schema = f"test_presenze_mapping_{uuid.uuid4().hex}"
    admin_engine = create_engine(database_url, pool_pre_ping=True)
    if admin_engine.dialect.name != "postgresql":
        admin_engine.dispose()
        pytest.skip("GAIA_TEST_POSTGRES_URL deve puntare a PostgreSQL")

    engine: Engine | None = None
    schema_created = False
    try:
        with admin_engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        schema_created = True
        engine = create_engine(
            database_url,
            pool_size=4,
            max_overflow=0,
            pool_pre_ping=True,
            connect_args={"options": f"-csearch_path={schema},public"},
        )
        with engine.begin() as connection:
            _create_base_tables(connection)
    except (OperationalError, SQLAlchemyError) as exc:
        if engine is not None:
            engine.dispose()
        if schema_created:
            with admin_engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
        admin_engine.dispose()
        if isinstance(exc, OperationalError):
            pytest.skip(f"PostgreSQL di test non disponibile: {exc}")
        raise

    assert engine is not None
    try:
        yield engine
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin_engine.dispose()


def _create_base_tables(connection: Connection) -> None:
    connection.execute(text("CREATE TABLE application_users (id INTEGER PRIMARY KEY)"))
    connection.execute(
        text(
            "CREATE TABLE presenze_collaborators ("
            "id UUID PRIMARY KEY, "
            "application_user_id INTEGER NULL REFERENCES application_users(id) ON DELETE SET NULL"
            ")"
        )
    )


def _revision_module() -> object:
    versions_path = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    return load_python_file(
        str(versions_path),
        "20260826_1100_presenze_mapping_integrity_audit.py",
    )


def _run_migration(connection: Connection, operation_name: str) -> None:
    operation = getattr(_revision_module(), operation_name)
    with Operations.context(MigrationContext.configure(connection)):
        operation()


def _assert_upgraded_schema(connection: Connection) -> None:
    schema = connection.scalar(text("SELECT current_schema()"))
    assert isinstance(schema, str)
    inspector = inspect(connection)
    assert inspector.has_table(AUDIT_TABLE, schema=schema)
    assert {column["name"] for column in inspector.get_columns(AUDIT_TABLE, schema=schema)} == {
        "id",
        "collaborator_id",
        "previous_application_user_id",
        "new_application_user_id",
        "changed_by_user_id",
        "changed_by_username",
        "action",
        "source",
        "reason",
        "created_at",
    }
    indexes = {
        index["name"]: index
        for index in inspector.get_indexes(COLLABORATOR_TABLE, schema=schema)
    }
    assert indexes[UNIQUE_INDEX]["unique"] is True
    assert (
        "application_user_id IS NOT NULL"
        in indexes[UNIQUE_INDEX]["dialect_options"]["postgresql_where"]
    )


def test_presenze_mapping_migration_upgrade_downgrade_upgrade(postgres_engine: Engine) -> None:
    assert _revision_module().down_revision == "20260826_1000"
    with postgres_engine.begin() as connection:
        _run_migration(connection, "upgrade")
        _assert_upgraded_schema(connection)
        _run_migration(connection, "downgrade")
        schema = connection.scalar(text("SELECT current_schema()"))
        assert isinstance(schema, str)
        inspector = inspect(connection)
        assert not inspector.has_table(AUDIT_TABLE, schema=schema)
        assert UNIQUE_INDEX not in {
            index["name"]
            for index in inspector.get_indexes(COLLABORATOR_TABLE, schema=schema)
        }
        _run_migration(connection, "upgrade")
        _assert_upgraded_schema(connection)


def test_presenze_mapping_unique_index_survives_real_postgres_contention(
    postgres_engine: Engine,
) -> None:
    user_id = 1
    collaborator_ids = [uuid.uuid4(), uuid.uuid4()]
    with postgres_engine.begin() as connection:
        _run_migration(connection, "upgrade")
        connection.execute(text("INSERT INTO application_users (id) VALUES (:id)"), {"id": user_id})
        connection.execute(
            text("INSERT INTO presenze_collaborators (id) VALUES (:id)"),
            [{"id": collaborator_id} for collaborator_id in collaborator_ids],
        )

    barrier = threading.Barrier(2, timeout=15)

    def map_identity(collaborator_id: uuid.UUID) -> str:
        try:
            with postgres_engine.begin() as connection:
                barrier.wait()
                connection.execute(
                    text(
                        "UPDATE presenze_collaborators "
                        "SET application_user_id = :user_id WHERE id = :collaborator_id"
                    ),
                    {"user_id": user_id, "collaborator_id": collaborator_id},
                )
            return "mapped"
        except IntegrityError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(map_identity, collaborator_ids))

    assert sorted(results) == ["conflict", "mapped"]
    with postgres_engine.connect() as connection:
        mapped_ids = connection.scalars(
            text(
                "SELECT id FROM presenze_collaborators "
                "WHERE application_user_id = :user_id"
            ),
            {"user_id": user_id},
        ).all()
    assert len(mapped_ids) == 1
