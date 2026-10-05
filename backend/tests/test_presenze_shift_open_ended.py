"""Ongoing assignments keep identity, precedence and bounded-edit semantics."""

from datetime import date, datetime
from types import SimpleNamespace

import pytest
import test_presenze_operations_postgres as operations_tests
from pydantic import ValidationError
from sqlalchemy import select
from test_presenze_api import (
    TestingSessionLocal,
    _create_user,
    _login,
    client,
    setup_database,  # noqa: F401 - isolated API fixture
)
from test_presenze_meal_vouchers import _record

from app.core.datetime_compat import UTC
from app.modules.presenze.models import PresenzeDailyRecord
from app.modules.presenze.services.shift_assignments import (
    ShiftAssignmentConflict,
    ShiftAssignmentOrigin,
    assignment_ranges_overlap,
    record_shift_assignment,
    shift_assignment_values,
)
from app.modules.presenze.shift_worker_models import PresenzeShiftAssignment
from app.modules.presenze.shift_worker_schemas import ShiftWorkerAssignmentRequest
from app.services.gate_mobile_sync import _apply_presenze_pending_action


@pytest.mark.parametrize("transport", ["lan", "outbound"])
def test_gate_ongoing_assignment_survives_transport_retry_and_future_month(transport):
    actor = _create_user("ongoing-" + transport)
    record_id, _ = _record(actor.id)
    payload = {
        "shift_worker_type": "acquaiolo",
        "date_from": "2026-09-01",
        "date_to": None,
        "gate_shift_requested_at": "2026-10-05T12:00:00Z",
        "gate_shift_command_id": "ongoing-" + transport,
    }
    for _ in range(2):
        if transport == "lan":
            response = client.post(
                f"/gate/presenze/giornaliere/{record_id}/patch",
                headers={"Authorization": "Bearer " + _login(actor.username)},
                json=payload,
            )
            assert response.status_code == 200, response.text
        else:
            with TestingSessionLocal() as db:
                _apply_presenze_pending_action(
                    db,
                    {
                        "id": "ongoing-action",
                        "action_type": "patch_daily_record",
                        "payload": {
                            **payload,
                            "record_id": str(record_id),
                            "gaia_user_id": actor.id,
                        },
                    },
                )
    with TestingSessionLocal() as db:
        assignment = db.scalars(select(PresenzeShiftAssignment)).one()
        assert assignment.date_to is None and assignment.source == "gate"
        record = db.get(PresenzeDailyRecord, record_id)
        record.work_date = date(2030, 1, 1)
        assert shift_assignment_values(record)["shift_worker_type"] == "acquaiolo"


@pytest.mark.parametrize("role", ["viewer", "operator"])
def test_ongoing_assignment_does_not_grant_owner_global_edit_permission(role):
    owner = _create_user("ongoing-owner", role=role)
    record_id, _ = _record(owner.id)
    response = client.post(
        f"/presenze/giornaliere/{record_id}/turnista",
        headers={"Authorization": "Bearer " + _login(owner.username)},
        json={"shift_worker_type": "acquaiolo", "date_from": "2026-09-01", "date_to": None},
    )
    assert response.status_code == 403
    with TestingSessionLocal() as db:
        assert db.scalars(select(PresenzeShiftAssignment)).all() == []


def test_admin_assigns_ongoing_shift_and_future_imports_inherit_it():
    actor = _create_user(username="ongoing-admin", role="admin")
    record_id, _ = _record(actor.id)
    headers = {"Authorization": "Bearer " + _login("ongoing-admin")}
    response = client.post(
        f"/presenze/giornaliere/{record_id}/turnista",
        headers=headers,
        json={"shift_worker_type": "acquaiolo", "date_from": "2026-09-01", "date_to": None},
    )
    assert response.status_code == 200
    assert response.json()["shift_worker_type"] == "acquaiolo"
    with TestingSessionLocal() as db:
        record = db.get(PresenzeDailyRecord, record_id)
        assignment = db.scalars(select(PresenzeShiftAssignment)).one()
        assert assignment.date_to is None and assignment.actor_user_id == actor.id
        for day, expected in [
            (date(2026, 8, 31), "none"),
            (date(2026, 9, 1), "acquaiolo"),
            (date(2028, 2, 29), "acquaiolo"),
        ]:
            record.work_date = day
            assert shift_assignment_values(record)["shift_worker_type"] == expected
        removal = ShiftWorkerAssignmentRequest(
            shift_worker_type="none", date_from=date(2027, 1, 1), date_to=None
        )
        origin = ShiftAssignmentOrigin(
            actor.id, "gate", datetime(2027, 1, 1, tzinfo=UTC), "ongoing-revoke"
        )
        record_shift_assignment(db, record, removal, origin=origin)
        record_shift_assignment(db, record, removal, origin=origin)
        assert len(db.scalars(select(PresenzeShiftAssignment)).all()) == 2
        assert shift_assignment_values(record)["shift_worker_type"] == "none"
        with pytest.raises(ShiftAssignmentConflict):
            record_shift_assignment(
                db,
                record,
                ShiftWorkerAssignmentRequest(
                    shift_worker_type="acquaiolo", date_from=date(2029, 1, 1), date_to=None
                ),
                origin=ShiftAssignmentOrigin(actor.id, "gaia", datetime.now(UTC), "conflict"),
            )


@pytest.mark.parametrize(
    "left_end,right_start,right_end,expected",
    [
        (None, date(2028, 1, 1), None, True),
        (date(2026, 9, 30), date(2026, 10, 1), None, False),
        (date(2026, 9, 30), date(2026, 9, 30), date(2026, 9, 30), True),
        (None, date(2026, 8, 1), date(2026, 8, 31), False),
    ],
)
def test_bounded_and_ongoing_overlap_is_inclusive(left_end, right_start, right_end, expected):
    left = SimpleNamespace(date_from=date(2026, 9, 1), date_to=left_end)
    right = SimpleNamespace(date_from=right_start, date_to=right_end)
    assert assignment_ranges_overlap(left, right) is expected


def test_ongoing_end_must_be_explicit_and_cannot_hide_invalid_start():
    for values in [
        {"date_from": "2026-09-01"},
        {"date_from": "2026-09-31", "date_to": None},
    ]:
        with pytest.raises(ValidationError):
            ShiftWorkerAssignmentRequest.model_validate(
                {"shift_worker_type": "acquaiolo", **values}
            )


@pytest.mark.postgres
def test_ongoing_migration_preserves_rows_and_rejects_lossy_downgrade(operations_engine):
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.util import load_python_file
    from sqlalchemy import inspect, text
    from sqlalchemy.orm import Session

    from app.modules.presenze.models import PresenzeCollaborator

    versions = str(Path(__file__).parents[1] / "alembic/versions")
    initial = load_python_file(versions, "20261003_1200_presenze_shift_assignments.py")
    ongoing = load_python_file(versions, "20261005_1500_open_ended_shift_assignments.py")
    with operations_engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            initial.upgrade()
            ongoing.upgrade()
        assert next(
            c
            for c in inspect(conn).get_columns("presenze_shift_assignments")
            if c["name"] == "date_to"
        )["nullable"]
    with Session(operations_engine) as db:
        person = PresenzeCollaborator(employee_code="ongoing", name="Test", owner_user_id=1)
        db.add(person)
        db.flush()
        db.add(
            PresenzeShiftAssignment(
                collaborator_id=person.id,
                date_from=date(2026, 9, 1),
                date_to=None,
                shift_worker_type="acquaiolo",
                source="gaia",
                actor_user_id=1,
                requested_at=datetime.now(UTC),
                command_id="migration-open",
            )
        )
        db.commit()
    with operations_engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            with pytest.raises(RuntimeError, match="Close ongoing"):
                ongoing.downgrade()
        assert (
            conn.execute(text("SELECT date_to FROM presenze_shift_assignments")).scalar_one()
            is None
        )
        conn.execute(text("UPDATE presenze_shift_assignments SET date_to = '2026-09-30'"))
        with Operations.context(MigrationContext.configure(conn)):
            ongoing.downgrade()
        assert not next(
            c
            for c in inspect(conn).get_columns("presenze_shift_assignments")
            if c["name"] == "date_to"
        )["nullable"]
        assert conn.execute(
            text("SELECT date_to FROM presenze_shift_assignments")
        ).scalar_one() == date(2026, 9, 30)
        with Operations.context(MigrationContext.configure(conn)):
            ongoing.upgrade()


operations_engine = operations_tests.operations_engine
