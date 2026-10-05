"""Shared GATE range command, invoked by LAN and outbound pending actions."""

from app.modules.presenze.services.shift_assignments import (
    ShiftAssignmentOrigin,
    record_shift_assignment,
)
from app.modules.presenze.shift_worker_schemas import GateShiftWorkerAssignmentRequest


def apply_gate_shift_assignment(db, record, request, actor_id):
    if "shift_worker_type" not in request.model_fields_set:
        return False
    assignment = GateShiftWorkerAssignmentRequest.model_validate(request.model_dump())
    record_shift_assignment(
        db,
        record,
        assignment,
        origin=ShiftAssignmentOrigin(
            actor_id, "gate", assignment.gate_shift_requested_at, request.gate_shift_command_id
        ),
    )
    return True
