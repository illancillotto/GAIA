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
    RequireOperazioniModule,
    _activity_duration_minutes,
    _resolve_period_bounds,
    _vehicle_session_km,
)
from app.modules.me.schemas import (
    MeOperazioniActivityItem,
    MeOperazioniActivityListResponse,
    MeOperazioniCaseItem,
    MeOperazioniCaseListResponse,
    MeOperazioniReportItem,
    MeOperazioniReportListResponse,
    MeOperazioniSummaryCategoryItem,
    MeOperazioniSummaryResponse,
    MeOperazioniSummaryStatusItem,
    MeVehicleUsageSessionItem,
    MeVehicleUsageSessionListResponse,
)
from app.modules.operazioni.models.activities import ActivityCatalog, OperatorActivity
from app.modules.operazioni.models.reports import (
    FieldReport,
    FieldReportCategory,
    FieldReportSeverity,
    InternalCase,
)
from app.modules.operazioni.models.vehicles import Vehicle, VehicleUsageSession

router = APIRouter(prefix="/me")


# Preserve legacy callable layout so the complexity ratchet remains comparable.
# fmt: off
@router.get("/operazioni/summary", response_model=MeOperazioniSummaryResponse)
def get_me_operazioni_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireOperazioniModule],
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
) -> MeOperazioniSummaryResponse:
    resolved_start, resolved_end = _resolve_period_bounds(period_start, period_end)

    activities = db.execute(
        select(OperatorActivity, ActivityCatalog.category)
        .join(ActivityCatalog, ActivityCatalog.id == OperatorActivity.activity_catalog_id)
        .where(
            OperatorActivity.operator_user_id == current_user.id,
            func.date(OperatorActivity.started_at) >= resolved_start,
            func.date(OperatorActivity.started_at) <= resolved_end,
        )
        .order_by(OperatorActivity.started_at.desc())
    ).all()

    activity_status_counts: dict[str, int] = {}
    activity_category_counts: dict[str, int] = {}
    activity_minutes = 0
    for activity, category in activities:
        activity_minutes += _activity_duration_minutes(activity)
        activity_status_counts[activity.status] = activity_status_counts.get(activity.status, 0) + 1
        category_key = category or "Senza categoria"
        activity_category_counts[category_key] = activity_category_counts.get(category_key, 0) + 1

    reports_count = db.execute(
        select(func.count(FieldReport.id)).where(
            FieldReport.reporter_user_id == current_user.id,
            or_(
                func.date(FieldReport.created_at).between(resolved_start, resolved_end),
                FieldReport.client_created_at.is_(None),
            ),
        )
    ).scalar_one()

    cases = db.execute(
        select(InternalCase).where(
            InternalCase.assigned_to_user_id == current_user.id,
            func.date(InternalCase.created_at) >= resolved_start,
            func.date(InternalCase.created_at) <= resolved_end,
        )
    ).scalars().all()
    if not cases:
        cases = db.execute(select(InternalCase).where(InternalCase.assigned_to_user_id == current_user.id)).scalars().all()

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
    distinct_vehicles = {session.vehicle_id for session in vehicle_sessions}

    return MeOperazioniSummaryResponse(
        period_start=resolved_start,
        period_end=resolved_end,
        activities_count=len(activities),
        activity_minutes=activity_minutes,
        reports_count=reports_count,
        assigned_cases_count=len(cases),
        open_cases_count=sum(1 for case in cases if case.status not in {"closed", "resolved"}),
        closed_cases_count=sum(1 for case in cases if case.status in {"closed", "resolved"}),
        vehicle_sessions_count=len(vehicle_sessions),
        vehicle_km=round(sum(_vehicle_session_km(session) for session in vehicle_sessions), 2),
        distinct_vehicles_count=len(distinct_vehicles),
        activity_statuses=[
            MeOperazioniSummaryStatusItem(status=status_key, count=count)
            for status_key, count in sorted(activity_status_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        activity_categories=[
            MeOperazioniSummaryCategoryItem(category=category_key, count=count)
            for category_key, count in sorted(activity_category_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
    )


@router.get("/operazioni/activities", response_model=MeOperazioniActivityListResponse)
def list_me_operazioni_activities(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireOperazioniModule],
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
) -> MeOperazioniActivityListResponse:
    resolved_start, resolved_end = _resolve_period_bounds(period_start, period_end)
    filters = (
        OperatorActivity.operator_user_id == current_user.id,
        func.date(OperatorActivity.started_at) >= resolved_start,
        func.date(OperatorActivity.started_at) <= resolved_end,
    )

    total = db.execute(select(func.count(OperatorActivity.id)).where(*filters)).scalar_one()
    rows = db.execute(
        select(
            OperatorActivity,
            ActivityCatalog.name,
            ActivityCatalog.category,
            Vehicle.name,
            Vehicle.plate_number,
        )
        .join(ActivityCatalog, ActivityCatalog.id == OperatorActivity.activity_catalog_id)
        .outerjoin(Vehicle, Vehicle.id == OperatorActivity.vehicle_id)
        .where(*filters)
        .order_by(OperatorActivity.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return MeOperazioniActivityListResponse(
        items=[
            MeOperazioniActivityItem(
                id=activity.id,
                activity_catalog_id=activity.activity_catalog_id,
                activity_name=activity_name,
                activity_category=activity_category,
                vehicle_id=activity.vehicle_id,
                vehicle_name=vehicle_name,
                vehicle_plate_number=plate_number,
                status=activity.status,
                started_at=activity.started_at,
                ended_at=activity.ended_at,
                duration_minutes=_activity_duration_minutes(activity),
                text_note=activity.text_note,
                review_outcome=activity.review_outcome,
                review_note=activity.review_note,
                submitted_at=activity.submitted_at,
                created_at=activity.created_at,
            )
            for activity, activity_name, activity_category, vehicle_name, plate_number in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/operazioni/reports", response_model=MeOperazioniReportListResponse)
def list_me_operazioni_reports(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireOperazioniModule],
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
) -> MeOperazioniReportListResponse:
    resolved_start, resolved_end = _resolve_period_bounds(period_start, period_end)
    filters = (
        FieldReport.reporter_user_id == current_user.id,
        func.date(FieldReport.created_at) >= resolved_start,
        func.date(FieldReport.created_at) <= resolved_end,
    )
    total = db.execute(select(func.count(FieldReport.id)).where(*filters)).scalar_one()
    if total == 0:
        filters = (FieldReport.reporter_user_id == current_user.id,)
        total = db.execute(select(func.count(FieldReport.id)).where(*filters)).scalar_one()
    rows = db.execute(
        select(
            FieldReport,
            FieldReportCategory.name,
            FieldReportSeverity.name,
            Vehicle.name,
            Vehicle.plate_number,
        )
        .join(FieldReportCategory, FieldReportCategory.id == FieldReport.category_id)
        .join(FieldReportSeverity, FieldReportSeverity.id == FieldReport.severity_id)
        .outerjoin(Vehicle, Vehicle.id == FieldReport.vehicle_id)
        .where(*filters)
        .order_by(FieldReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return MeOperazioniReportListResponse(
        items=[
            MeOperazioniReportItem(
                id=report.id,
                report_number=report.report_number,
                title=report.title,
                description=report.description,
                status=report.status,
                category_name=category_name,
                severity_name=severity_name,
                vehicle_name=vehicle_name,
                vehicle_plate_number=plate_number,
                created_at=report.created_at,
                updated_at=report.updated_at,
            )
            for report, category_name, severity_name, vehicle_name, plate_number in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/operazioni/cases", response_model=MeOperazioniCaseListResponse)
def list_me_operazioni_cases(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireOperazioniModule],
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
) -> MeOperazioniCaseListResponse:
    resolved_start, resolved_end = _resolve_period_bounds(period_start, period_end)
    filters = (
        InternalCase.assigned_to_user_id == current_user.id,
        func.date(InternalCase.created_at) >= resolved_start,
        func.date(InternalCase.created_at) <= resolved_end,
    )
    total = db.execute(select(func.count(InternalCase.id)).where(*filters)).scalar_one()
    if total == 0:
        filters = (InternalCase.assigned_to_user_id == current_user.id,)
        total = db.execute(select(func.count(InternalCase.id)).where(*filters)).scalar_one()
    rows = db.execute(
        select(
            InternalCase,
            FieldReportCategory.name,
            FieldReportSeverity.name,
            FieldReport.report_number,
        )
        .outerjoin(FieldReportCategory, FieldReportCategory.id == InternalCase.category_id)
        .outerjoin(FieldReportSeverity, FieldReportSeverity.id == InternalCase.severity_id)
        .outerjoin(FieldReport, FieldReport.id == InternalCase.source_report_id)
        .where(*filters)
        .order_by(InternalCase.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return MeOperazioniCaseListResponse(
        items=[
            MeOperazioniCaseItem(
                id=case.id,
                case_number=case.case_number,
                title=case.title,
                status=case.status,
                priority_rank=case.priority_rank,
                category_name=category_name,
                severity_name=severity_name,
                source_report_number=source_report_number,
                created_at=case.created_at,
                updated_at=case.updated_at,
                started_at=case.started_at,
                resolved_at=case.resolved_at,
                closed_at=case.closed_at,
            )
            for case, category_name, severity_name, source_report_number in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/operazioni/vehicle-sessions", response_model=MeVehicleUsageSessionListResponse)
def list_me_vehicle_sessions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireOperazioniModule],
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
) -> MeVehicleUsageSessionListResponse:
    resolved_start, resolved_end = _resolve_period_bounds(period_start, period_end)
    filters = (
        or_(
            VehicleUsageSession.actual_driver_user_id == current_user.id,
            VehicleUsageSession.started_by_user_id == current_user.id,
        ),
        func.date(VehicleUsageSession.started_at) >= resolved_start,
        func.date(VehicleUsageSession.started_at) <= resolved_end,
    )
    total = db.execute(select(func.count(VehicleUsageSession.id)).where(*filters)).scalar_one()
    rows = db.execute(
        select(VehicleUsageSession, Vehicle.name, Vehicle.plate_number)
        .join(Vehicle, Vehicle.id == VehicleUsageSession.vehicle_id)
        .where(*filters)
        .order_by(VehicleUsageSession.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return MeVehicleUsageSessionListResponse(
        items=[
            MeVehicleUsageSessionItem(
                id=session.id,
                vehicle_id=session.vehicle_id,
                vehicle_name=vehicle_name,
                vehicle_plate_number=plate_number,
                status=session.status,
                started_at=session.started_at,
                ended_at=session.ended_at,
                km=round(_vehicle_session_km(session), 2),
                notes=session.notes,
                operator_name=session.operator_name,
                created_at=session.created_at,
            )
            for session, vehicle_name, plate_number in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
# fmt: on
