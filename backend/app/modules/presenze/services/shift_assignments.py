"""Persist manual shift assignments; GATE edits outrank GAIA and INAZ."""

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, object_session

from app.core.datetime_compat import UTC
from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyRecord
from app.modules.presenze.shift_worker_models import PresenzeShiftAssignment
from app.modules.presenze.shift_worker_schemas import ShiftWorkerAssignmentRequest


class ShiftAssignmentConflict(ValueError):
    pass


@dataclass(frozen=True)
class ShiftAssignmentOrigin:
    actor_id: int
    source: str
    requested_at: datetime
    command_id: str


def record_shift_assignment(
    db: Session,
    record: PresenzeDailyRecord,
    request: ShiftWorkerAssignmentRequest,
    *,
    origin: ShiftAssignmentOrigin,
):
    actor_id, source, requested_at, command_id = (
        origin.actor_id,
        origin.source,
        origin.requested_at,
        origin.command_id,
    )
    # Lock the collaborator to serialize competing assignments and command retries.
    db.scalar(
        select(PresenzeCollaborator)
        .where(PresenzeCollaborator.id == record.collaborator_id)
        .with_for_update()
    )
    if (
        db.scalar(
            select(PresenzeShiftAssignment).where(PresenzeShiftAssignment.command_id == command_id)
        )
        is not None
    ):
        return
    assignments = _assignments(db, record.collaborator_id)
    if source == "gaia" and any(
        row.source == "gate"
        and assignment_ranges_overlap(row, request)
        for row in assignments
    ):
        raise ShiftAssignmentConflict("Assegnazione gestita da GATE: modificarla da GATE")
    db.add(
        PresenzeShiftAssignment(
            collaborator_id=record.collaborator_id,
            date_from=request.date_from,
            date_to=request.date_to,
            shift_worker_type=request.shift_worker_type,
            actor_user_id=actor_id,
            source=source,
            requested_at=requested_at.astimezone(UTC),
            command_id=command_id,
        )
    )
    db.flush()
    db.info.pop("presenze_shift_assignments", None)


def _assignments(db, collaborator_id):
    return db.scalars(
        select(PresenzeShiftAssignment).where(
            PresenzeShiftAssignment.collaborator_id == collaborator_id
        )
    ).all()


def shift_assignment_values(record):
    db = object_session(record) if isinstance(record, PresenzeDailyRecord) else None
    if db is None:
        return {
            "shift_worker_type": getattr(record, "shift_worker_type", "none"),
            "shift_worker_source": getattr(record, "shift_worker_source", None),
            "shift_rules_version": "shift-v1",
        }
    cache = db.info.setdefault("presenze_shift_assignments", {})
    key = record.collaborator_id
    if key not in cache:
        cache[key] = _assignments(db, key)
    matching = [row for row in cache[key] if assignment_covers_date(row, record.work_date)]
    winner = max(
        matching,
        key=lambda row: (
            row.source == "gate",
            row.requested_at.replace(tzinfo=UTC),
            row.command_id,
        ),
        default=None,
    )
    return {
        "shift_worker_type": winner.shift_worker_type if winner else "none",
        "shift_worker_source": winner.source if winner else None,
        "shift_rules_version": "shift-v1",
    }


def assignment_covers_date(assignment, work_date: date) -> bool:
    return assignment.date_from <= work_date <= (assignment.date_to or date.max)


def assignment_ranges_overlap(left, right) -> bool:
    return (
        left.date_from <= (right.date_to or date.max)
        and right.date_from <= (left.date_to or date.max)
    )
