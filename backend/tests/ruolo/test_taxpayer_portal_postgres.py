"""Portal DDL and revision invalidation on real, isolated PostgreSQL."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.schema import CreateSchema, DropSchema


def test_portal_postgres_migration_invalidates_on_committed_changes_and_downgrades():
    url = os.getenv("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("GAIA_TEST_POSTGRES_URL richiesto per i trigger PostgreSQL")
    admin = create_engine(url)
    schema = f"portal_access_{uuid4().hex}"
    with admin.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = create_engine(
        url,
        connect_args={
            "options": f"-csearch_path={schema} -clock_timeout=5000 -cstatement_timeout=10000"
        },
    )
    versions = str(Path(__file__).parents[2] / "alembic" / "versions")
    revision = load_python_file(versions, "20260921_1700_notice_generation_revision.py")
    portal = load_python_file(versions, "20261027_1100_taxpayer_portal_access.py")
    table = "ruolo_taxpayer_portal_access"
    try:
        with (
            engine.begin() as connection,
            Operations.context(MigrationContext.configure(connection)),
        ):
            for name in revision.DEPENDENCY_TABLES:
                connection.execute(text(f"CREATE TABLE {name} (id integer PRIMARY KEY)"))
            revision.upgrade()
            portal.upgrade()
            assert table in inspect(connection).get_table_names()
            assert connection.execute(
                text(
                    "SELECT tgenabled FROM pg_trigger WHERE tgrelid = 'ruolo_taxpayer_portal_access'::regclass AND NOT tgisinternal"
                )
            ).scalars().all() == ["A", "A"]
        for operation in (
            "INSERT INTO ruolo_taxpayer_portal_access VALUES ('0000001', '01234567890', decode('01','hex'), repeat('a',64), now())",
            "UPDATE ruolo_taxpayer_portal_access SET pin_encrypted = decode('02','hex')",
            "DELETE FROM ruolo_taxpayer_portal_access",
            "TRUNCATE ruolo_taxpayer_portal_access",
        ):
            with engine.connect() as connection:
                before = connection.scalar(
                    text("SELECT revision FROM ruolo_notice_generation_revision")
                )
            with engine.begin() as connection:
                connection.execute(text("SET LOCAL session_replication_role = replica"))
                connection.execute(text(operation))
            with engine.connect() as connection:
                assert (
                    connection.scalar(text("SELECT revision FROM ruolo_notice_generation_revision"))
                    == before + 1
                )
        with (
            engine.begin() as connection,
            Operations.context(MigrationContext.configure(connection)),
        ):
            portal.downgrade()
            assert table not in inspect(connection).get_table_names()
            revision.downgrade()
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()
