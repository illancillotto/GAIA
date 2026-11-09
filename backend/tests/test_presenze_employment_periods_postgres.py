"""Exercise additive DDL, real constraints, rollback and dated HR on PostgreSQL."""

from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
import test_presenze_operations_postgres as operations_tests
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.presenze.employment_models import PresenzeEmploymentPeriod
from app.modules.presenze.models import PresenzeCollaborator

operations_engine = operations_tests.operations_engine
pytestmark = pytest.mark.postgres


def test_period_migration_constraints_and_safe_rollback(operations_engine):
    migration = load_python_file(
        str(Path(__file__).parents[1] / "alembic/versions"),
        "20261106_1000_presenze_employment_periods.py",
    )
    with operations_engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
            migration.upgrade()
    cid = uuid4()
    with Session(operations_engine) as db:
        db.add(
            PresenzeCollaborator(
                id=cid, employee_code="synthetic", name="Synthetic", application_user_id=1
            )
        )
        db.commit()
        for fields in [
            dict(valid_to=date(2025, 12, 31)),
            dict(employment_relationship="unknown"),
            dict(collaborator_id=uuid4()),
            dict(actor_user_id=987654),
        ]:
            args = dict(
                collaborator_id=cid,
                valid_from=date(2026, 1, 1),
                valid_to=date(2026, 12, 31),
                employment_relationship="avventizio",
                source_document_sha256="a" * 64,
                source_note="Synthetic",
                actor_user_id=1,
            )
            db.add(PresenzeEmploymentPeriod(**(args | fields)))
            with pytest.raises(IntegrityError):
                db.flush()
            db.rollback()
        db.add(PresenzeEmploymentPeriod(**args))
        db.commit()
        db.add(PresenzeEmploymentPeriod(**args))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
    with operations_engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            with pytest.raises(RuntimeError, match="Reconcile"):
                migration.downgrade()
        conn.execute(PresenzeEmploymentPeriod.__table__.delete())
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
            migration.downgrade()
        assert PresenzeEmploymentPeriod.__tablename__ not in inspect(conn).get_table_names()
