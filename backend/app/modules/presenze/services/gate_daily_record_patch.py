"""Apply GATE daily edits through the same locked manual voucher audit."""

from sqlalchemy.orm import Session

from app.modules.presenze.gate_daily_record_schemas import GatePresenzeDailyRecordPatchRequest
from app.modules.presenze.models import PresenzeDailyRecord
from app.modules.presenze.services.gate_shift_assignment import apply_gate_shift_assignment
from app.modules.presenze.services.meal_vouchers import apply_audited_manual_meal_voucher


def apply_gate_daily_record_patch(
    db: Session,
    record: PresenzeDailyRecord,
    request: GatePresenzeDailyRecordPatchRequest,
    actor_id: int,
) -> None:
    if apply_gate_shift_assignment(db, record, request, actor_id):
        return
    values = request.model_dump(exclude_unset=True, exclude={"operator_note", "client_request_id"})
    enabled = values.pop("meal_voucher_manual", None)
    apply_audited_manual_meal_voucher(db, record, enabled, actor_id, "gate_console_mobile")
    for field, value in values.items():
        setattr(record, field, value)
