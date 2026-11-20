"""Exercise the additive constraints and reject a lossy downgrade."""

from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import create_engine, inspect, text


@pytest.mark.parametrize(
    ("file", "new_area", "prior_areas"),
    [
        ("20261007_1800_catasto_personnel_area.py", "CATASTO", "'AGRARIO', 'IMPIANTI'"),
        (
            "20261120_1200_amministrativa_personnel_area.py",
            "AMMINISTRATIVA",
            "'AGRARIO', 'IMPIANTI', 'CATASTO'",
        ),
    ],
)
def test_area_migration_preserves_existing_data_and_guards_downgrade(file, new_area, prior_areas):
    migration = load_python_file(
        str(Path(__file__).parents[1] / "alembic/versions"),
        file,
    )
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        for table, constraint, nullable in migration.CONSTRAINTS:
            condition = f"personnel_area IN ({prior_areas})"
            if nullable:
                condition = "personnel_area IS NULL OR " + condition
            conn.execute(
                text(
                    f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, personnel_area TEXT, "
                    f"CONSTRAINT {constraint} CHECK ({condition}))"
                )
            )
            conn.execute(text(f"INSERT INTO {table} VALUES (1, 'AGRARIO')"))
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
        for table, _, _ in migration.CONSTRAINTS:
            assert (
                conn.execute(text(f"SELECT personnel_area FROM {table} WHERE id=1")).scalar_one()
                == "AGRARIO"
            )
            conn.execute(text(f"INSERT INTO {table} VALUES (2, :area)"), {"area": new_area})
            assert new_area in inspect(conn).get_check_constraints(table)[0]["sqltext"]
        with Operations.context(MigrationContext.configure(conn)):
            with pytest.raises(RuntimeError, match=f"Reconcile {new_area.title()}"):
                migration.downgrade()
        for table, _, _ in migration.CONSTRAINTS:
            conn.execute(text(f"DELETE FROM {table} WHERE id=2"))
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
        for table, _, _ in migration.CONSTRAINTS:
            assert new_area not in inspect(conn).get_check_constraints(table)[0]["sqltext"]
