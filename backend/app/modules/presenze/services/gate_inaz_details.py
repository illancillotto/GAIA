"""Publish the same INAZ diagnostics as GAIA, alongside its calculated outcome."""

from typing import Any

from app.modules.presenze.models import PresenzeDailyRecord
from app.modules.presenze.schemas import PresenzeDailyRecordResponse
from app.modules.presenze.services.daily_details import normalized_daily_detail
from app.modules.presenze.services.operational_quality import _record_has_inaz_anomaly

INAZ_RECORD_FIELDS = {
    "stato",
    "evidenze",
    "raw_weekday",
    "detail_status",
    "detail_programmed_schedule",
    "detail_effective_schedule",
    "detail_time_slots",
    "detail_schedule_type",
    "detail_theoretical_hours",
    "detail_absence_hours",
    "detail_day_summary",
    "detail_day_totals",
    "detail_requests",
    "detail_anomalies",
    "detail_punch_rows",
    "detail_text",
    "detail_error",
    "operational_status",
    "operational_formula_code",
    "operational_expected_minutes",
    "operational_worked_minutes",
    "operational_missing_minutes",
    "operational_mpe_minutes",
    "operational_notes",
}


def gate_inaz_detail_values(
    record: PresenzeDailyRecord, serialized: PresenzeDailyRecordResponse
) -> dict[str, Any]:
    detail = normalized_daily_detail(record)
    source = record.raw_payload_json if isinstance(record.raw_payload_json, dict) else {}
    return serialized.model_dump(mode="json", include=INAZ_RECORD_FIELDS) | {
        "status": serialized.operational_status,
        **{
            f"detail_{key}": value
            for key, value in detail.items()
            if key not in {"title", "punch_rows"}
        },
        "inaz_detail_punch_rows": detail["punch_rows"],
        "has_inaz_anomaly": _record_has_inaz_anomaly(record),
        # The scraper's title fallback can include the entire portal page, unrelated to this day.
        "inaz_source": {key: value for key, value in source.items() if key != "detail_title"},
    }
