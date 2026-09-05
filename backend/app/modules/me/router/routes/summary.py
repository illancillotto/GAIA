from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.me.router.common import (
    _activity_duration_minutes,
    _daily_record_effective_extra_minutes,
    _daily_record_has_anomaly,
    _hours_from_minutes,
    _module_enabled,
    _resolve_period_bounds,
    _vehicle_session_km,
)
from app.modules.me.schemas import MeSummaryPresenzeMetrics, MeSummaryResponse
from app.modules.network.models import NetworkDevice
from app.modules.operazioni.models.activities import OperatorActivity
from app.modules.operazioni.models.reports import FieldReport, InternalCase
from app.modules.operazioni.models.vehicles import VehicleAssignment, VehicleUsageSession
from app.modules.presenze.models import PresenzeDailyRecord

router = APIRouter(prefix="/me")


# Preserve legacy callable layout so the complexity ratchet remains comparable.
# fmt: off
@router.get("/summary", response_model=MeSummaryResponse, response_model_exclude_none=True)
def get_me_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
) -> MeSummaryResponse:
    resolved_start, resolved_end = _resolve_period_bounds(period_start, period_end)

    ordinary_minutes = 0
    extra_minutes = 0
    absence_minutes = 0
    worked_days = 0
    anomaly_days = 0
    km_from_presenze = 0.0

    if _module_enabled(current_user, "presenze"):
        records = db.execute(
            select(PresenzeDailyRecord).where(
                PresenzeDailyRecord.application_user_id == current_user.id,
                PresenzeDailyRecord.work_date >= resolved_start,
                PresenzeDailyRecord.work_date <= resolved_end,
            )
        ).scalars().all()
        ordinary_minutes = sum(record.ordinary_minutes or 0 for record in records)
        extra_minutes = sum(_daily_record_effective_extra_minutes(record) for record in records)
        absence_minutes = sum(record.absence_minutes or 0 for record in records)
        worked_days = sum(1 for record in records if (record.ordinary_minutes or 0) > 0)
        anomaly_days = sum(1 for record in records if _daily_record_has_anomaly(record))
        km_from_presenze = float(sum(record.km_value or 0 for record in records))

    activities_count = 0
    activity_minutes = 0
    reports_count = 0
    assigned_cases_count = 0
    open_cases_count = 0
    closed_cases_count = 0
    vehicle_sessions_count = 0
    vehicle_km = 0.0

    if _module_enabled(current_user, "operazioni"):
        activities = db.execute(
            select(OperatorActivity).where(
                OperatorActivity.operator_user_id == current_user.id,
                func.date(OperatorActivity.started_at) >= resolved_start,
                func.date(OperatorActivity.started_at) <= resolved_end,
            )
        ).scalars().all()
        activities_count = len(activities)
        activity_minutes = sum(_activity_duration_minutes(activity) for activity in activities)

        reports_count = db.execute(
            select(func.count(FieldReport.id)).where(
                FieldReport.reporter_user_id == current_user.id,
                or_(
                    func.date(FieldReport.created_at).between(resolved_start, resolved_end),
                    FieldReport.client_created_at.is_(None),
                ),
            )
        ).scalar_one()

        assigned_cases = db.execute(
            select(InternalCase).where(
                InternalCase.assigned_to_user_id == current_user.id,
                func.date(InternalCase.created_at).between(resolved_start, resolved_end),
            )
        ).scalars().all()
        if not assigned_cases:
            assigned_cases = db.execute(
                select(InternalCase).where(InternalCase.assigned_to_user_id == current_user.id)
            ).scalars().all()
        assigned_cases_count = len(assigned_cases)
        open_cases_count = sum(1 for case in assigned_cases if case.status not in {"closed", "resolved"})
        closed_cases_count = sum(1 for case in assigned_cases if case.status in {"closed", "resolved"})

        vehicle_sessions = db.execute(
            select(VehicleUsageSession).where(
                or_(
                    VehicleUsageSession.actual_driver_user_id == current_user.id,
                    VehicleUsageSession.started_by_user_id == current_user.id,
                ),
                func.date(VehicleUsageSession.started_at) >= resolved_start,
                func.date(VehicleUsageSession.started_at) <= resolved_end,
            )
        ).scalars().all()
        vehicle_sessions_count = len(vehicle_sessions)
        vehicle_km = round(sum(_vehicle_session_km(session) for session in vehicle_sessions), 2)

    assigned_devices_count = 0
    active_vehicle_assignments_count = 0

    if _module_enabled(current_user, "rete"):
        assigned_devices_count = db.execute(
            select(func.count(NetworkDevice.id)).where(
                NetworkDevice.assigned_user_id == current_user.id,
                NetworkDevice.lifecycle_state != "retired",
            )
        ).scalar_one()

    if _module_enabled(current_user, "operazioni"):
        active_vehicle_assignments_count = db.execute(
            select(func.count(VehicleAssignment.id)).where(
                VehicleAssignment.operator_user_id == current_user.id,
                or_(VehicleAssignment.end_at.is_(None), func.date(VehicleAssignment.end_at) >= resolved_start),
            )
        ).scalar_one()

    return MeSummaryResponse(
        period_start=resolved_start,
        period_end=resolved_end,
        presenze=MeSummaryPresenzeMetrics(
            ordinary_hours=_hours_from_minutes(ordinary_minutes),
            extra_hours=_hours_from_minutes(extra_minutes),
            absence_hours=_hours_from_minutes(absence_minutes),
            worked_days=worked_days,
            anomaly_days=anomaly_days,
            km=km_from_presenze,
        ),
        ordinary_minutes=ordinary_minutes,
        extra_minutes=extra_minutes,
        absence_minutes=absence_minutes,
        worked_days=worked_days,
        anomaly_days=anomaly_days,
        km_from_presenze=km_from_presenze,
        activities_count=activities_count,
        activity_minutes=activity_minutes,
        reports_count=reports_count,
        assigned_cases_count=assigned_cases_count,
        open_cases_count=open_cases_count,
        closed_cases_count=closed_cases_count,
        vehicle_sessions_count=vehicle_sessions_count,
        vehicle_km=vehicle_km,
        assigned_devices_count=assigned_devices_count,
        active_vehicle_assignments_count=active_vehicle_assignments_count,
    )
# fmt: on
