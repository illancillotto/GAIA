"""AG is a presentation of an unworked day, never a credit of hours or pay."""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import object_session

from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
)
from app.modules.presenze.services.daily_details import (
    is_missing_hours_anomaly,
    normalized_daily_absence_cause,
    normalized_daily_detail,
)
from app.modules.presenze.services.employment_periods import employment_period_values

AVVENTIZIO_NO_PUNCHES_LABEL = "Assenza di timbrature (Avventizio)"


def avventizio_absence_values(record, classification=None, quality=None, *, today=None):
    values = employment_period_values(record)
    if values.get("employment_relationship") != "avventizio":
        return values
    today = today or datetime.now(ZoneInfo("Europe/Rome")).date()
    if record.work_date >= today or not avventizio_unworked_record(record):
        return values
    classification, quality = avventizio_day_context(record, classification, quality)
    if not avventizio_unworked_day(classification, quality):
        return values
    return values | {
        "avventizio_no_punches": True,
        "attendance_note": AVVENTIZIO_NO_PUNCHES_LABEL,
        "resolved_absence_cause": "assenza_giustificata",
        "absence_cause": "assenza_giustificata",
        "export_absence_code": "AG",
        "operational_status": avventizio_operational_status(record),
        "operational_missing_minutes": 0,
        "missing_minutes": 0,
        "operational_notes": [AVVENTIZIO_NO_PUNCHES_LABEL, *quality.notes],
    }


def avventizio_unworked_day(classification, quality):
    if classification is None or quality is None:
        return False
    return (
        not classification.special_day
        and (quality.expected_minutes or 0) > 0
        and not any(
            (minutes or 0) > 0
            for minutes in (classification.ordinary_minutes, classification.extra_minutes)
        )
    )


def avventizio_operational_status(record):
    detail = normalized_daily_detail(record)
    technical = detail.get("error") or any(
        not is_missing_hours_anomaly(item) for item in detail.get("anomalies", ())
    )
    return "in_analysis" if technical else "ok"


def avventizio_unworked_record(record):
    detail = normalized_daily_detail(record)
    if normalized_daily_absence_cause(record) not in (None, "assenza_da_giustificare") or getattr(
        record, "request_description", None
    ):
        return False
    if detail.get("requests") or detail.get("punch_rows"):
        return False
    fields = (
        "ordinary_minutes",
        "mpe_minutes",
        "straordinario_minutes",
        "override_mpe_minutes",
        "override_straordinario_minutes",
        "justified_minutes",
    )
    if any((getattr(record, key, None) or 0) > 0 for key in fields):
        return False
    db = object_session(record) if isinstance(record, PresenzeDailyRecord) else None
    if db is None:
        return not getattr(record, "punches", ())
    return (
        db.scalar(
            select(PresenzeDailyPunch.id)
            .where(PresenzeDailyPunch.daily_record_id == record.id)
            .limit(1)
        )
        is None
    )


def avventizio_day_context(record, classification, quality):
    from app.modules.presenze.services.operational_quality import build_daily_operational_quality
    from app.modules.presenze.services.schedule_engine import (
        build_schedule_context,
        classify_daily_record,
    )

    db = object_session(record) if isinstance(record, PresenzeDailyRecord) else None
    if classification is not None and quality is not None:
        return classification, quality
    if db is None:
        return classification, quality
    collaborator = db.get(PresenzeCollaborator, record.collaborator_id)
    if classification is None:
        context = build_schedule_context(
            db,
            collaborator_ids=[record.collaborator_id],
            date_from=record.work_date,
            date_to=record.work_date,
        )
        classification = classify_daily_record(collaborator, record, [], context)
    if quality is None:
        quality = build_daily_operational_quality(
            collaborator, record, [], classification=classification
        )
    return classification, quality
