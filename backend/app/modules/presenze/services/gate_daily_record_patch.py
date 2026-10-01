"""Apply GATE daily edits through the same locked manual voucher audit."""

from sqlalchemy.orm import Session

from app.modules.presenze.gate_daily_record_schemas import GatePresenzeDailyRecordPatchRequest
from app.modules.presenze.models import PresenzeDailyRecord
from app.modules.presenze.services.meal_voucher_audit import record_manual_meal_voucher_change
from app.modules.presenze.services.meal_vouchers import lock_manual_meal_voucher_record


def apply_gate_daily_record_patch(
    db: Session,
    record: PresenzeDailyRecord,
    request: GatePresenzeDailyRecordPatchRequest,
    actor_id: int,
) -> None:
    values = request.model_dump(exclude_unset=True, exclude={"operator_note", "client_request_id"})
    enabled = values.pop("meal_voucher_manual", None)
    if enabled is not None:
        locked = lock_manual_meal_voucher_record(db, record)
        record_manual_meal_voucher_change(locked, enabled, actor_id, "gate_console_mobile")
    for field, value in values.items():
        setattr(record, field, value)
