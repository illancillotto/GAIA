"""Apply editable daily fields after GAIA or GaTe has authorized the change."""

from typing import Any

from sqlalchemy.orm import Session

from app.modules.presenze.models import PresenzeDailyRecord
from app.modules.presenze.services.manual_presence import validate_manual_km
from app.modules.presenze.services.meal_vouchers import apply_audited_manual_meal_voucher


def apply_manual_daily_fields(
    db: Session, record: PresenzeDailyRecord, values: dict[str, Any], actor_id: int, source: str
) -> None:
    validate_manual_km(db, record, values.get("km_value"))
    apply_audited_manual_meal_voucher(
        db, record, values.get("meal_voucher_manual"), actor_id, source
    )
    for field, value in values.items():
        if field != "meal_voucher_manual":
            setattr(record, field, value)
