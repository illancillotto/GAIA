from __future__ import annotations

import calendar
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyRecord, PresenzeEventSummary
from app.modules.presenze.router import _serialize_daily_record
from app.modules.presenze.schemas import PresenzeEventSummaryResponse
from app.modules.presenze.services.parser import extract_detail_payload
from app.modules.network.models import NetworkDevice
from app.modules.network.router import _resolve_device_label
from app.modules.operazioni.models.activities import ActivityCatalog, OperatorActivity
from app.modules.operazioni.models.reports import FieldReport, FieldReportCategory, FieldReportSeverity, InternalCase
from app.modules.operazioni.models.vehicles import Vehicle, VehicleAssignment, VehicleUsageSession
from app.modules.me.schemas import (
    MeAssignedDeviceItem,
    MeAssignedDeviceListResponse,
    MeCapabilitiesResponse,
    MeModuleStatusResponse,
    MeOperazioniActivityItem,
    MeOperazioniActivityListResponse,
    MeOperazioniCaseItem,
    MeOperazioniCaseListResponse,
    MeOperazioniReportItem,
    MeOperazioniReportListResponse,
    MeOperazioniSummaryCategoryItem,
    MeOperazioniSummaryResponse,
    MeOperazioniSummaryStatusItem,
    MePresenzeDailyRecordListResponse,
    MePresenzeDailyRecordResponse,
    MePresenzeStatusResponse,
    MePresenzeSummaryResponse,
    MeSummaryPresenzeMetrics,
    MeSummaryResponse,
    MeVehicleAssignmentItem,
    MeVehicleAssignmentListResponse,
    MeVehicleUsageSessionItem,
    MeVehicleUsageSessionListResponse,
)

router = APIRouter(prefix="/me", tags=["me"])
RequirePresenzeModule = Depends(require_module("presenze"))
RequireOperazioniModule = Depends(require_module("operazioni"))
RequireNetworkModule = Depends(require_module("rete"))


def _module_enabled(current_user: ApplicationUser, module_name: str) -> bool:
    return current_user.is_super_admin or module_name in current_user.enabled_modules


def _get_mapped_collaborator(db: Session, current_user: ApplicationUser) -> PresenzeCollaborator | None:
    return db.execute(
        select(PresenzeCollaborator)
        .where(PresenzeCollaborator.application_user_id == current_user.id)
        .order_by(
            PresenzeCollaborator.is_active.desc(),
            PresenzeCollaborator.last_seen_at.desc().nullslast(),
            PresenzeCollaborator.created_at.desc(),
        )
        .limit(1)
    ).scalar_one_or_none()


def _get_self_daily_record_or_404(db: Session, record_id: uuid.UUID, current_user: ApplicationUser) -> PresenzeDailyRecord:
    record = db.execute(
        select(PresenzeDailyRecord).where(
            PresenzeDailyRecord.id == record_id,
            PresenzeDailyRecord.application_user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily record not found")
    return record


def _current_month_bounds() -> tuple[date, date]:
    today = date.today()
    start = today.replace(day=1)
    end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    return start, end


def _resolve_period_bounds(period_start: date | None, period_end: date | None) -> tuple[date, date]:
    default_start, default_end = _current_month_bounds()
    resolved_start = period_start or default_start
    resolved_end = period_end or default_end
    if resolved_start > resolved_end:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid period range")
    return resolved_start, resolved_end


def _activity_duration_minutes(activity: OperatorActivity) -> int:
    if activity.duration_minutes_calculated is not None:
        return activity.duration_minutes_calculated
    return activity.duration_minutes_declared or 0


def _vehicle_session_km(session: VehicleUsageSession) -> float:
    if session.route_distance_km is not None:
        return float(session.route_distance_km)
    if session.end_odometer_km is not None:
        return float(session.end_odometer_km - session.start_odometer_km)
    if session.km_start is not None and session.km_end is not None:
        return float(session.km_end - session.km_start)
    return 0.0


def _daily_record_effective_extra_minutes(record: PresenzeDailyRecord) -> int:
    effective_straordinario = (
        record.override_straordinario_minutes
        if record.override_straordinario_minutes is not None
        else record.straordinario_minutes
    )
    effective_mpe = record.override_mpe_minutes if record.override_mpe_minutes is not None else record.mpe_minutes
    return (effective_straordinario or 0) + (effective_mpe or 0)


def _daily_record_has_anomaly(record: PresenzeDailyRecord) -> bool:
    detail = extract_detail_payload(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else {}
    anomalies = detail.get("anomalies") or []
    detail_status = str(detail.get("status") or "").lower()
    stato = str(record.stato or "").lower()
    return bool(anomalies or "anom" in detail_status or "anom" in stato)


def _hours_from_minutes(minutes: int) -> float:
    return round(minutes / 60, 2)


def _serialize_assigned_device(device: NetworkDevice) -> MeAssignedDeviceItem:
    resolved_label, _ = _resolve_device_label(device)
    return MeAssignedDeviceItem(
        id=device.id,
        ip_address=device.ip_address,
        hostname=device.hostname,
        display_name=device.display_name,
        resolved_label=resolved_label,
        lifecycle_state=device.lifecycle_state,
        status=device.status,
        device_type=device.device_type,
        operating_system=device.operating_system,
        asset_label=device.asset_label,
        location_hint=device.location_hint,
        last_seen_at=device.last_seen_at,
        updated_at=device.updated_at,
    )


@router.get("", response_model=MeModuleStatusResponse, response_model_exclude_none=True)
def get_me_status(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
) -> MeModuleStatusResponse:
    return MeModuleStatusResponse(
        module="me",
        enabled=True,
        username=current_user.username,
        capabilities=MeCapabilitiesResponse(
            presenze=_module_enabled(current_user, "presenze"),
            operazioni=_module_enabled(current_user, "operazioni"),
            network=_module_enabled(current_user, "rete"),
        ),
        message="GAIA self-service user module is enabled for the current user.",
    )


@router.get("/presenze", response_model=MePresenzeStatusResponse)
def get_me_presenze_status(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> MePresenzeStatusResponse:
    collaborator = _get_mapped_collaborator(db, current_user)
    if collaborator is None:
        return MePresenzeStatusResponse(
            module="presenze",
            enabled=True,
            mapped=False,
            message="No Presenze collaborator is currently mapped to the current user.",
        )

    return MePresenzeStatusResponse(
        module="presenze",
        enabled=True,
        mapped=True,
        collaborator_id=collaborator.id,
        collaborator_name=collaborator.name,
        employee_code=collaborator.employee_code,
        message="Presenze self-service data is available for the current user.",
    )


@router.get("/presenze/daily-records", response_model=MePresenzeDailyRecordListResponse)
def list_me_presenze_daily_records(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=31, ge=1, le=200),
) -> MePresenzeDailyRecordListResponse:
    stmt = select(PresenzeDailyRecord).where(PresenzeDailyRecord.application_user_id == current_user.id)
    count_stmt = select(func.count(PresenzeDailyRecord.id)).where(PresenzeDailyRecord.application_user_id == current_user.id)

    if collaborator_id is not None:
        stmt = stmt.where(PresenzeDailyRecord.collaborator_id == collaborator_id)
        count_stmt = count_stmt.where(PresenzeDailyRecord.collaborator_id == collaborator_id)
    if date_from is not None:
        stmt = stmt.where(PresenzeDailyRecord.work_date >= date_from)
        count_stmt = count_stmt.where(PresenzeDailyRecord.work_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(PresenzeDailyRecord.work_date <= date_to)
        count_stmt = count_stmt.where(PresenzeDailyRecord.work_date <= date_to)
    if q:
        term = f"%{q.strip()}%"
        filters = or_(
            PresenzeDailyRecord.evidenze.ilike(term),
            PresenzeDailyRecord.stato.ilike(term),
            PresenzeDailyRecord.request_description.ilike(term),
            PresenzeDailyRecord.request_status.ilike(term),
            PresenzeDailyRecord.request_authorized_by.ilike(term),
            PresenzeDailyRecord.resolved_absence_cause.ilike(term),
        )
        stmt = stmt.where(filters)
        count_stmt = count_stmt.where(filters)

    rows = db.execute(
        stmt.order_by(PresenzeDailyRecord.work_date.asc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    return MePresenzeDailyRecordListResponse(
        items=[_serialize_daily_record(db, row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/presenze/daily-records/{record_id}", response_model=MePresenzeDailyRecordResponse)
def get_me_presenze_daily_record(
    record_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> MePresenzeDailyRecordResponse:
    return MePresenzeDailyRecordResponse.model_validate(_serialize_daily_record(db, _get_self_daily_record_or_404(db, record_id, current_user)))


@router.get("/presenze/summary", response_model=MePresenzeSummaryResponse)
def get_me_presenze_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    period_start: date = Query(...),
    period_end: date = Query(...),
) -> MePresenzeSummaryResponse:
    items = db.execute(
        select(PresenzeEventSummary)
        .where(
            PresenzeEventSummary.application_user_id == current_user.id,
            PresenzeEventSummary.period_start == period_start,
            PresenzeEventSummary.period_end == period_end,
        )
        .order_by(PresenzeEventSummary.description.asc())
    ).scalars().all()

    return MePresenzeSummaryResponse(
        period_start=period_start,
        period_end=period_end,
        items=[PresenzeEventSummaryResponse.model_validate(item) for item in items],
    )


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


@router.get("/assets/devices", response_model=MeAssignedDeviceListResponse)
def list_me_assigned_devices(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireNetworkModule],
) -> MeAssignedDeviceListResponse:
    devices = db.execute(
        select(NetworkDevice)
        .where(NetworkDevice.assigned_user_id == current_user.id)
        .order_by(NetworkDevice.last_seen_at.desc())
    ).scalars().all()
    return MeAssignedDeviceListResponse(items=[_serialize_assigned_device(device) for device in devices], total=len(devices))


@router.get("/assets/vehicle-assignments", response_model=MeVehicleAssignmentListResponse)
def list_me_vehicle_assignments(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireOperazioniModule],
) -> MeVehicleAssignmentListResponse:
    rows = db.execute(
        select(VehicleAssignment, Vehicle.name, Vehicle.plate_number, Vehicle.vehicle_type)
        .join(Vehicle, Vehicle.id == VehicleAssignment.vehicle_id)
        .where(VehicleAssignment.operator_user_id == current_user.id)
        .order_by(VehicleAssignment.start_at.desc())
    ).all()
    now = date.today()
    return MeVehicleAssignmentListResponse(
        items=[
            MeVehicleAssignmentItem(
                id=assignment.id,
                vehicle_id=assignment.vehicle_id,
                vehicle_name=vehicle_name,
                vehicle_plate_number=plate_number,
                vehicle_type=vehicle_type,
                assignment_target_type=assignment.assignment_target_type,
                start_at=assignment.start_at,
                end_at=assignment.end_at,
                reason=assignment.reason,
                notes=assignment.notes,
                is_active=assignment.end_at is None or assignment.end_at.date() >= now,
            )
            for assignment, vehicle_name, plate_number, vehicle_type in rows
        ],
        total=len(rows),
    )
