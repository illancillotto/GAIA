from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyRecord,
)
from app.modules.presenze.router.common import RequirePresenzeModule
from app.modules.presenze.router.helpers.access import _can_view_all_inaz_data
from app.modules.presenze.router.helpers.daily_records import (
    _build_classification_map,
    _record_uses_recovery_day,
)
from app.modules.presenze.schemas import (
    PresenzeDashboardSummaryResponse,
)
from app.modules.presenze.services.parser import (
    extract_detail_payload,
)
from app.modules.presenze.services.visibility_policy import (
    collaborator_visibility_filter,
    daily_record_visibility_filter,
    resolve_presenze_visibility,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

router = APIRouter(prefix="/presenze")

@router.get("/dashboard/summary", response_model=PresenzeDashboardSummaryResponse)
def get_dashboard_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    period_start: date = Query(...),
    period_end: date = Query(...),
) -> PresenzeDashboardSummaryResponse:
    collaborator_stmt = select(PresenzeCollaborator)
    collaborator_count_stmt = select(func.count(PresenzeCollaborator.id))
    record_stmt = select(PresenzeDailyRecord).where(
        PresenzeDailyRecord.work_date >= period_start,
        PresenzeDailyRecord.work_date <= period_end,
    )
    record_count_stmt = select(func.count(PresenzeDailyRecord.id)).where(
        PresenzeDailyRecord.work_date >= period_start,
        PresenzeDailyRecord.work_date <= period_end,
    )

    if not _can_view_all_inaz_data(current_user):
        visibility = resolve_presenze_visibility(db, current_user)
        collaborator_filter = collaborator_visibility_filter(visibility)
        record_filter = daily_record_visibility_filter(visibility)
        collaborator_stmt = collaborator_stmt.where(collaborator_filter)
        collaborator_count_stmt = collaborator_count_stmt.where(collaborator_filter)
        record_stmt = record_stmt.where(record_filter)
        record_count_stmt = record_count_stmt.where(record_filter)

    collaborators_total = db.execute(collaborator_count_stmt).scalar_one()
    mapped_collaborators_total = db.execute(
        collaborator_count_stmt.where(PresenzeCollaborator.application_user_id.is_not(None))
    ).scalar_one()
    daily_records_total = db.execute(record_count_stmt).scalar_one()

    records = db.execute(record_stmt.order_by(PresenzeDailyRecord.work_date.asc())).scalars().all()

    ordinary_minutes_total = 0
    absence_minutes_total = 0
    extra_minutes_total = 0
    straordinario_minutes_total = 0
    maggior_presenza_minutes_total = 0
    km_total = 0
    trasferta_minutes_total = 0
    trasferta_days_total = 0
    trasferta_montano_days_total = 0
    anomaly_total = 0
    special_day_total = 0
    recovery_days_matured_total = 0
    recovery_days_used_total = 0
    worked_days_total = 0
    absence_days_total = 0
    justified_days_total = 0
    active_collaborator_ids: set[uuid.UUID] = set()
    cause_stats: dict[str, int] = {}
    schedule_stats: dict[str, int] = {}
    classification_by_record_id = _build_classification_map(db, records)

    for record in records:
        classification = classification_by_record_id.get(record.id)
        active_collaborator_ids.add(record.collaborator_id)
        ordinary_minutes_total += record.ordinary_minutes or 0
        absence_minutes_total += record.absence_minutes or 0
        effective_straordinario = (
            record.override_straordinario_minutes
            if record.override_straordinario_minutes is not None
            else record.straordinario_minutes or 0
        )
        effective_mpe = record.override_mpe_minutes if record.override_mpe_minutes is not None else record.mpe_minutes or 0
        straordinario_minutes_total += effective_straordinario
        maggior_presenza_minutes_total += effective_mpe
        extra_minutes_total += effective_straordinario + effective_mpe
        km_total += record.km_value or 0
        trasferta_minutes_total += record.trasferta_minutes or 0
        if (record.trasferta_minutes or 0) > 0 or record.trasferta_montano:
            trasferta_days_total += 1
        if record.trasferta_montano:
            trasferta_montano_days_total += 1
        if (record.ordinary_minutes or 0) > 0:
            worked_days_total += 1
        if (record.absence_minutes or 0) > 0:
            absence_days_total += 1
        if (record.justified_minutes or 0) > 0:
            justified_days_total += 1

        detail = extract_detail_payload(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else {}
        anomalies = detail.get("anomalies") or []
        detail_status = str(detail.get("status") or "").lower()
        stato = str(record.stato or "").lower()
        if anomalies or "anom" in detail_status or "anom" in stato:
            anomaly_total += 1
        if classification is not None and classification.special_day:
            special_day_total += 1
        if classification is not None and classification.grants_recovery_day:
            recovery_days_matured_total += 1
        if _record_uses_recovery_day(record):
            recovery_days_used_total += 1

        cause = (record.resolved_absence_cause or "").strip().lower()
        if cause:
            cause_stats[cause] = (cause_stats.get(cause) or 0) + 1

        schedule_code = (record.schedule_code or "").strip()
        if not schedule_code and isinstance(detail.get("programmed_schedule"), str):
            schedule_code = str(detail["programmed_schedule"]).split(" - ")[0].strip()
        if schedule_code:
            schedule_stats[schedule_code] = (schedule_stats.get(schedule_code) or 0) + 1

    top_schedule_stats = [
        {"code": code, "count": count}
        for code, count in sorted(schedule_stats.items(), key=lambda item: (-item[1], item[0]))[:4]
    ]

    return PresenzeDashboardSummaryResponse(
        period_start=period_start,
        period_end=period_end,
        collaborators_total=collaborators_total,
        mapped_collaborators_total=mapped_collaborators_total,
        active_collaborators_total=len(active_collaborator_ids),
        daily_records_total=daily_records_total,
        ordinary_minutes_total=ordinary_minutes_total,
        absence_minutes_total=absence_minutes_total,
        extra_minutes_total=extra_minutes_total,
        straordinario_minutes_total=straordinario_minutes_total,
        maggior_presenza_minutes_total=maggior_presenza_minutes_total,
        km_total=km_total,
        trasferta_minutes_total=trasferta_minutes_total,
        trasferta_days_total=trasferta_days_total,
        trasferta_montano_days_total=trasferta_montano_days_total,
        anomaly_total=anomaly_total,
        special_day_total=special_day_total,
        recovery_days_matured_total=recovery_days_matured_total,
        recovery_days_used_total=recovery_days_used_total,
        recovery_days_balance_total=recovery_days_matured_total - recovery_days_used_total,
        worked_days_total=worked_days_total,
        absence_days_total=absence_days_total,
        justified_days_total=justified_days_total,
        cause_stats=cause_stats,
        schedule_stats=top_schedule_stats,
    )

# fmt: on
