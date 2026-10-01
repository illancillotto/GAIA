"""Keep INAZ diagnostics, excluding only an OREM fully covered by union leave."""

from typing import Any

from app.modules.presenze.models import PresenzeDailyRecord
from app.modules.presenze.services.inaz_absences import union_leave_covers_day
from app.modules.presenze.services.parser import extract_detail_payload


def normalized_daily_detail(record: PresenzeDailyRecord) -> dict[str, Any]:
    detail = extract_detail_payload(
        record.raw_payload_json if isinstance(record.raw_payload_json, dict) else {}
    )
    if union_leave_covers_day(record):
        detail["anomalies"] = [
            item for item in detail["anomalies"] if not is_missing_hours_anomaly(item)
        ]
    return detail


def is_missing_hours_anomaly(item: dict[str, Any]) -> bool:
    code = item.get("code") or item.get("anomaliagiornata") or ""
    return str(code).split("-", 1)[0].strip().upper() == "OREM"


def normalized_daily_absence_cause(record: PresenzeDailyRecord) -> str | None:
    from app.modules.presenze.services.parser import resolve_absence_cause

    imported = resolve_absence_cause(
        record.raw_payload_json if isinstance(record.raw_payload_json, dict) else {}
    )
    if imported == "permesso_sindacale":
        return imported
    return record.resolved_absence_cause or imported


def classification_breakdown_values(classification: object, prefix: str = "") -> dict[str, int]:
    """Shared classified time buckets for daily API and canonical GATE export."""
    fields = (
        "ordinary_night_minutes",
        "overtime_day_minutes",
        "overtime_night_minutes",
        "overtime_festive_minutes",
        "overtime_festive_night_minutes",
        "shift_festive_day_minutes",
        "shift_night_minutes",
        "shift_festive_night_minutes",
    )
    return {f"{prefix}{field}": getattr(classification, field) for field in fields}
