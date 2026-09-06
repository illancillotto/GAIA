"""The additive migration must not renew recovery for existing requests."""

import importlib.util
import os
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


@pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
def test_recovery_migration_keeps_historical_dates_unknown(dialect):
    root = Path(__file__).resolve().parents[4]
    path = root / "backend/alembic/versions/20260905_1100_sister_recovery_window.py"
    spec = importlib.util.spec_from_file_location("recovery_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    url = "sqlite://" if dialect == "sqlite" else os.getenv("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("GAIA_TEST_POSTGRES_URL not configured")
    engine = create_engine(url)
    assert engine.dialect.name == dialect
    with engine.connect() as connection:
        # Temporary table and rollback isolate the probe from application tables.
        connection.execute(
            text("CREATE TEMPORARY TABLE catasto_visure_requests (id INTEGER PRIMARY KEY)")
        )
        connection.execute(text("INSERT INTO catasto_visure_requests (id) VALUES (1)"))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        row = connection.execute(
            text("SELECT id, sister_first_submitted_at FROM catasto_visure_requests")
        ).one()
        assert tuple(row) == (1, None)
        if dialect == "postgresql":
            columns = inspect(connection).get_columns("catasto_visure_requests")
            assert columns[1]["type"].timezone is True
        migration.downgrade()
        assert [
            column["name"] for column in inspect(connection).get_columns("catasto_visure_requests")
        ] == ["id"]
        assert connection.execute(text("SELECT id FROM catasto_visure_requests")).scalar_one() == 1
        connection.rollback()
    engine.dispose()
