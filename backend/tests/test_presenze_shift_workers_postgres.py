"""Real PostgreSQL migration and serialized shift assignment retries."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

import pytest
import test_presenze_operations_postgres as operations_tests
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core.datetime_compat import UTC
from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyRecord
from app.modules.presenze.services.shift_assignments import (
    ShiftAssignmentConflict,
    ShiftAssignmentOrigin,
    record_shift_assignment,
    shift_assignment_values,
)
from app.modules.presenze.shift_worker_models import PresenzeShiftAssignment
from app.modules.presenze.shift_worker_schemas import ShiftWorkerAssignmentRequest

operations_engine = operations_tests.operations_engine
pytestmark = pytest.mark.postgres


def test_shift_migration_and_concurrent_retry_preserve_gate_authority(operations_engine):
    migration = load_python_file(
        str(Path(__file__).parents[1] / "alembic/versions"),
        "20261003_1200_presenze_shift_assignments.py",
    )
    with operations_engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
        assert len(inspect(conn).get_check_constraints("presenze_shift_assignments")) == 3
    with Session(operations_engine) as db:
        person = PresenzeCollaborator(employee_code="shift-test", name="Test", owner_user_id=1)
        db.add(person)
        db.flush()
        day = PresenzeDailyRecord(
            collaborator_id=person.id,
            owner_user_id=1,
            work_date=date(2026, 10, 1),
            ordinary_minutes=420,
        )
        db.add(day)
        db.commit()
        record_id = day.id
    request = ShiftWorkerAssignmentRequest(
        shift_worker_type="telecontrollo",
        date_from=date(2026, 10, 1),
        date_to=date(2026, 10, 31),
    )
    origin = ShiftAssignmentOrigin(1, "gate", datetime(2026, 10, 1, tzinfo=UTC), "pg-retry")

    def retry():
        with Session(operations_engine) as db:
            record_shift_assignment(
                db, db.get(PresenzeDailyRecord, record_id), request, origin=origin
            )
            db.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(retry) for _ in range(2)]
        for future in futures:
            future.result(timeout=15)
    with Session(operations_engine) as db:
        day = db.get(PresenzeDailyRecord, record_id)
        assert len(db.scalars(select(PresenzeShiftAssignment)).all()) == 1
        assert shift_assignment_values(day)["shift_worker_type"] == "telecontrollo"
        with pytest.raises(ShiftAssignmentConflict):
            record_shift_assignment(
                db,
                day,
                request,
                origin=ShiftAssignmentOrigin(1, "gaia", datetime.now(UTC), "gaia-overlap"),
            )
        db.rollback()
        assert day.ordinary_minutes == 420
    with operations_engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
        assert "presenze_shift_assignments" not in inspect(conn).get_table_names()
        assert conn.execute(select(PresenzeDailyRecord.ordinary_minutes)).scalar_one() == 420
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
