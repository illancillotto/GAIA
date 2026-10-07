"""Real additive migration and safe downgrade for the technician shift category."""

from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import test_presenze_operations_postgres as operations_tests
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.datetime_compat import UTC
from app.modules.presenze.models import PresenzeCollaborator
from app.modules.presenze.personnel_profile_models import PresenzePersonnelProfile
from app.modules.presenze.shift_worker_models import PresenzeShiftAssignment

operations_engine = operations_tests.operations_engine
pytestmark = pytest.mark.postgres


def test_personnel_migration_is_idempotent_and_rejects_destructive_downgrade(operations_engine):
    folder = str(Path(__file__).parents[1] / "alembic/versions")
    original = load_python_file(folder, "20261003_1200_presenze_shift_assignments.py")
    migration = load_python_file(folder, "20261007_1600_presenze_personnel_profiles.py")
    with operations_engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            original.upgrade()
            migration.upgrade()
            migration.upgrade()
        assert "presenze_personnel_profiles" in inspect(conn).get_table_names()
        check = next(
            x
            for x in inspect(conn).get_check_constraints("presenze_shift_assignments")
            if x["name"] == "ck_shift_assignment_type"
        )
        assert "tecnico_turnista" in check["sqltext"]
    with Session(operations_engine) as db:
        person = PresenzeCollaborator(
            id=uuid4(), employee_code="personnel-test", name="Test", application_user_id=1
        )
        db.add(person)
        db.flush()
        db.add(
            PresenzePersonnelProfile(
                collaborator_id=person.id,
                valid_from=date(2026, 1, 1),
                profile_type="tecnico_turnista",
                profile_label="Tecnico/Turnista",
                duty="Tecnico / Turnista",
                employment_relationship="avventizio",
                personnel_area="IMPIANTI",
                supervisor_user_id=1,
                shift_schedule_codes=["TELEC_1"],
                source_document_sha256="a" * 64,
                source_note="Attested test",
            )
        )
        db.add(
            PresenzeShiftAssignment(
                collaborator_id=person.id,
                date_from=date(2026, 10, 1),
                date_to=date(2026, 10, 31),
                shift_worker_type="tecnico_turnista",
                source="gaia",
                actor_user_id=1,
                requested_at=datetime(2026, 10, 1, tzinfo=UTC),
                command_id="technician-test",
            )
        )
        db.commit()
    with operations_engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            with pytest.raises(RuntimeError, match="Reconcile"):
                migration.downgrade()
        assert (
            conn.execute(text("SELECT count(*) FROM presenze_personnel_profiles")).scalar_one() == 1
        )
        conn.execute(text("DELETE FROM presenze_shift_assignments"))
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
        assert "presenze_personnel_profiles" not in inspect(conn).get_table_names()
