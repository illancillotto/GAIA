"""Exercise the additive association migration and database constraints in isolation."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateSchema, DropSchema

pytestmark = pytest.mark.postgres


def test_association_migration_constraints_and_guarded_rollback():
    url = os.environ["GAIA_TEST_POSTGRES_URL"]
    schema = "test_team_organization_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(CreateSchema(schema))
    engine = create_engine(url, connect_args={"options": "-csearch_path=" + schema})
    migration = load_python_file(
        str(Path(__file__).parents[1] / "alembic/versions"),
        "20261107_0900_presenze_team_org_unit.py",
    )
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE application_users (id integer PRIMARY KEY)"))
            conn.execute(text("CREATE TABLE organization_teams (id uuid PRIMARY KEY)"))
            conn.execute(text("CREATE TABLE org_unit (id uuid PRIMARY KEY)"))
            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()
        team, unit = uuid4(), uuid4()
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO application_users VALUES (1)"))
            conn.execute(text("INSERT INTO organization_teams VALUES (:id)"), {"id": team})
            conn.execute(text("INSERT INTO org_unit VALUES (:id)"), {"id": unit})
        insert = text(
            "INSERT INTO presenze_team_organization (team_id, org_unit_id, updated_by_user_id) VALUES (:team, :unit, :actor)"
        )
        for fields in [
            dict(team=uuid4(), unit=unit, actor=1),
            dict(team=team, unit=uuid4(), actor=1),
            dict(team=team, unit=unit, actor=2),
        ]:
            with pytest.raises(IntegrityError), engine.begin() as conn:
                conn.execute(insert, fields)
        with engine.begin() as conn:
            conn.execute(insert, dict(team=team, unit=unit, actor=1))
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(insert, dict(team=team, unit=unit, actor=1))
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError, match="Unlink"):
                    migration.downgrade()
            conn.execute(text("DELETE FROM application_users WHERE id=1"))
            assert (
                conn.scalar(text("SELECT updated_by_user_id FROM presenze_team_organization"))
                is None
            )
            conn.execute(text("DELETE FROM org_unit WHERE id=:id"), {"id": unit})
            assert conn.scalar(text("SELECT count(*) FROM presenze_team_organization")) == 0
            with Operations.context(MigrationContext.configure(conn)):
                migration.downgrade()
            assert "presenze_team_organization" not in inspect(conn).get_table_names()
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(DropSchema(schema, cascade=True))
        admin.dispose()
