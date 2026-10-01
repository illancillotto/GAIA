"""Record an idempotent manual voucher change after locking the daily record."""

from datetime import datetime

from app.core.datetime_compat import UTC
from app.modules.presenze.models import PresenzeDailyRecord


def record_manual_meal_voucher_change(
    record: PresenzeDailyRecord, enabled: bool, actor_id: int, source: str
) -> None:
    previous = bool(record.meal_voucher_manual)
    if previous == enabled:
        return
    record.meal_voucher_manual = enabled
    record.meal_voucher_audit = [
        *(record.meal_voucher_audit or []),
        {
            "at": datetime.now(UTC).isoformat(),
            "actor_user_id": actor_id,
            "previous": previous,
            "enabled": enabled,
            "source": source,
        },
    ]
