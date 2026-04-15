"""Reports and Cases domain routes."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.reports import (
    FieldReport,
    FieldReportAttachment,
    FieldReportCategory,
    FieldReportSeverity,
    InternalCase,
    InternalCaseAttachment,
    InternalCaseEvent,
    InternalCaseAssignmentHistory,
)
from app.modules.operazioni.models.attachments import Attachment

router = APIRouter(prefix="", tags=["operazioni/reports-cases"])


@router.get("/reports", response_model=dict)
def list_reports(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    reporter_user_id: int | None = None,
    team_id: UUID | None = None,
    vehicle_id: UUID | None = None,
    category_id: UUID | None = None,
    severity_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    has_case: bool | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    query = select(FieldReport)
    if reporter_user_id:
        query = query.where(FieldReport.reporter_user_id == reporter_user_id)
    if team_id:
        query = query.where(FieldReport.team_id == team_id)
    if vehicle_id:
        query = query.where(FieldReport.vehicle_id == vehicle_id)
    if category_id:
        query = query.where(FieldReport.category_id == category_id)
    if severity_id:
        query = query.where(FieldReport.severity_id == severity_id)
    if date_from:
        query = query.where(FieldReport.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.where(FieldReport.created_at <= datetime.fromisoformat(date_to))
    if has_case is not None:
        if has_case:
            query = query.where(FieldReport.internal_case_id.isnot(None))
        else:
            query = query.where(FieldReport.internal_case_id.is_(None))
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                FieldReport.report_number.ilike(term),
                FieldReport.external_code.ilike(term),
                FieldReport.title.ilike(term),
                FieldReport.description.ilike(term),
                FieldReport.reporter_name.ilike(term),
                FieldReport.assigned_responsibles.ilike(term),
                FieldReport.area_code.ilike(term),
            )
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_q) or 0
    items = db.scalars(
        query.order_by(FieldReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": str(r.id),
                "external_code": r.external_code,
                "report_number": r.report_number,
                "title": r.title,
                "description": r.description,
                "status": r.status,
                "created_at": r.created_at,
                "internal_case_id": str(r.internal_case_id) if r.internal_case_id else None,
            }
            for r in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if page_size else 0,
    }


@router.post("/reports", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_report(
    data: dict,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    report_number = f"REP-{datetime.now().strftime('%Y')}-{db.scalar(select(func.count(FieldReport.id))) + 1:06d}"

    report = FieldReport(
        report_number=report_number,
        reporter_user_id=current_user.id,
        created_by_user_id=current_user.id,
        server_received_at=datetime.now(),
        **{k: v for k, v in data.items() if k not in ("report_number",)},
    )
    db.add(report)
    db.flush()

    case_number = f"CAS-{datetime.now().strftime('%Y')}-{db.scalar(select(func.count(InternalCase.id))) + 1:06d}"
    case = InternalCase(
        case_number=case_number,
        source_report_id=report.id,
        title=report.title,
        description=report.description,
        category_id=report.category_id,
        severity_id=report.severity_id,
        created_by_user_id=current_user.id,
    )
    db.add(case)
    db.flush()

    report.internal_case_id = case.id
    report.status = "linked"

    case_event = InternalCaseEvent(
        internal_case_id=case.id,
        event_type="created",
        event_at=datetime.now(),
        actor_user_id=current_user.id,
        note="Pratica creata automaticamente dalla segnalazione",
    )
    db.add(case_event)
    db.commit()
    db.refresh(report)
    db.refresh(case)

    return {
        "report": {
            "id": str(report.id),
            "report_number": report.report_number,
            "status": report.status,
        },
        "case": {
            "id": str(case.id),
            "case_number": case.case_number,
            "status": case.status,
        },
    }


@router.get("/reports/{report_id}", response_model=dict)
def get_report(
    report_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    report = db.get(FieldReport, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Report not found"
        )
    return {
        "id": str(report.id),
        "external_code": report.external_code,
        "report_number": report.report_number,
        "title": report.title,
        "description": report.description,
        "status": report.status,
        "reporter_name": report.reporter_name,
        "area_code": report.area_code,
        "reporter_user_id": report.reporter_user_id,
        "team_id": str(report.team_id) if report.team_id else None,
        "vehicle_id": str(report.vehicle_id) if report.vehicle_id else None,
        "operator_activity_id": str(report.operator_activity_id)
        if report.operator_activity_id
        else None,
        "category_id": str(report.category_id),
        "severity_id": str(report.severity_id),
        "latitude": float(report.latitude) if report.latitude is not None else None,
        "longitude": float(report.longitude) if report.longitude is not None else None,
        "gps_accuracy_meters": float(report.gps_accuracy_meters)
        if report.gps_accuracy_meters is not None
        else None,
        "gps_source": report.gps_source,
        "assigned_responsibles": report.assigned_responsibles,
        "completion_time_text": report.completion_time_text,
        "completion_time_minutes": report.completion_time_minutes,
        "source_system": report.source_system,
        "internal_case_id": str(report.internal_case_id)
        if report.internal_case_id
        else None,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
        "server_received_at": report.server_received_at,
    }


@router.get("/reports/dashboard", response_model=dict)
def reports_dashboard(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = None,
    area_code: str | None = None,
    reporter_name: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    base_query = _apply_dashboard_filters(
        select(FieldReport),
        status_filter=status_filter,
        area_code=area_code,
        reporter_name=reporter_name,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )

    total = db.scalar(select(func.count()).select_from(base_query.subquery())) or 0
    reports = db.scalars(
        base_query.order_by(FieldReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    case_ids = [report.internal_case_id for report in reports if report.internal_case_id]
    case_lookup = {
        case.id: case
        for case in db.scalars(select(InternalCase).where(InternalCase.id.in_(case_ids))).all()
    } if case_ids else {}

    events_by_case: dict[UUID, list[InternalCaseEvent]] = defaultdict(list)
    if case_ids:
        events = db.scalars(
            select(InternalCaseEvent)
            .where(InternalCaseEvent.internal_case_id.in_(case_ids))
            .where(InternalCaseEvent.event_type != "imported")
            .order_by(InternalCaseEvent.event_at)
        ).all()
        for event in events:
            events_by_case[event.internal_case_id].append(event)

    by_status_rows = db.execute(
        _apply_dashboard_filters(
            select(FieldReport.status, func.count(FieldReport.id))
            .group_by(FieldReport.status),
            status_filter=status_filter,
            area_code=area_code,
            reporter_name=reporter_name,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
    ).all()
    by_status = {"open": 0, "in_progress": 0, "resolved": 0}
    for status_value, count in by_status_rows:
        by_status[str(status_value)] = count

    by_area_rows = db.execute(
        _apply_dashboard_filters(
            select(
                FieldReport.area_code.label("area"),
                func.count(FieldReport.id).label("count"),
            )
            .where(FieldReport.area_code.isnot(None))
            .group_by(FieldReport.area_code)
            .order_by(func.count(FieldReport.id).desc(), FieldReport.area_code.asc()),
            status_filter=status_filter,
            area_code=area_code,
            reporter_name=reporter_name,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
    ).all()

    by_reporter_rows = db.execute(
        _apply_dashboard_filters(
            select(
                FieldReport.reporter_name.label("name"),
                func.count(FieldReport.id).label("count"),
            )
            .where(FieldReport.reporter_name.isnot(None))
            .group_by(FieldReport.reporter_name)
            .order_by(func.count(FieldReport.id).desc(), FieldReport.reporter_name.asc()),
            status_filter=status_filter,
            area_code=area_code,
            reporter_name=reporter_name,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
    ).all()

    avg_completion_minutes = db.scalar(
        _apply_dashboard_filters(
            select(func.avg(FieldReport.completion_time_minutes)).where(
                FieldReport.completion_time_minutes.isnot(None),
                FieldReport.status == "resolved",
            ),
            status_filter=status_filter,
            area_code=area_code,
            reporter_name=reporter_name,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
    )

    total_with_events = db.scalar(
        _apply_dashboard_filters(
            select(func.count(func.distinct(FieldReport.id)))
            .join(InternalCase, InternalCase.id == FieldReport.internal_case_id)
            .join(InternalCaseEvent, InternalCaseEvent.internal_case_id == InternalCase.id)
            .where(InternalCaseEvent.event_type != "imported"),
            status_filter=status_filter,
            area_code=area_code,
            reporter_name=reporter_name,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
    ) or 0

    items = []
    for report in reports:
        case = case_lookup.get(report.internal_case_id) if report.internal_case_id else None
        case_events = events_by_case.get(report.internal_case_id, [])
        items.append(
            {
                "id": str(report.id),
                "external_code": report.external_code,
                "report_number": report.report_number,
                "title": report.title,
                "description": report.description,
                "status": report.status,
                "area_code": report.area_code,
                "reporter_name": report.reporter_name,
                "latitude": float(report.latitude) if report.latitude is not None else None,
                "longitude": float(report.longitude) if report.longitude is not None else None,
                "assigned_responsibles": report.assigned_responsibles,
                "completion_time_text": report.completion_time_text,
                "completion_time_minutes": report.completion_time_minutes,
                "created_at": report.created_at,
                "resolved_at": case.resolved_at if case else None,
                "source_system": report.source_system,
                "case_id": str(report.internal_case_id) if report.internal_case_id else None,
                "case_status": case.status if case else None,
                "events_count": len(case_events),
                "events": [
                    {
                        "event_type": event.event_type,
                        "event_at": event.event_at,
                        "note": event.note,
                    }
                    for event in case_events
                ],
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if page_size else 0,
        "aggregates": {
            "by_status": by_status,
            "by_area": [{"area": area, "count": count} for area, count in by_area_rows],
            "by_reporter": [
                {"name": name, "count": count} for name, count in by_reporter_rows
            ],
            "avg_completion_minutes": int(avg_completion_minutes)
            if avg_completion_minutes is not None
            else None,
            "total_with_events": total_with_events,
            "total_without_events": max(total - total_with_events, 0),
        },
    }


@router.get("/reports/{report_id}/attachments", response_model=list[dict])
def list_report_attachments(
    report_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    report = db.get(FieldReport, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Report not found"
        )

    rows = db.execute(
        select(FieldReportAttachment, Attachment)
        .join(Attachment, FieldReportAttachment.attachment_id == Attachment.id)
        .where(FieldReportAttachment.field_report_id == report_id)
        .where(Attachment.is_deleted == False)
        .order_by(FieldReportAttachment.created_at.desc())
    ).all()
    return [
        {
            "id": str(attachment.id),
            "original_filename": attachment.original_filename,
            "mime_type": attachment.mime_type,
            "attachment_type": attachment.attachment_type,
            "file_size_bytes": attachment.file_size_bytes,
            "created_at": attachment.created_at,
        }
        for _, attachment in rows
    ]


@router.get("/cases", response_model=dict)
def list_cases(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status"),
    assigned_to_user_id: int | None = None,
    assigned_team_id: UUID | None = None,
    severity_id: UUID | None = None,
    category_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    query = select(InternalCase)
    if status_filter:
        query = query.where(InternalCase.status == status_filter)
    if assigned_to_user_id:
        query = query.where(InternalCase.assigned_to_user_id == assigned_to_user_id)
    if assigned_team_id:
        query = query.where(InternalCase.assigned_team_id == assigned_team_id)
    if severity_id:
        query = query.where(InternalCase.severity_id == severity_id)
    if category_id:
        query = query.where(InternalCase.category_id == category_id)
    if date_from:
        query = query.where(
            InternalCase.created_at >= datetime.fromisoformat(date_from)
        )
    if date_to:
        query = query.where(InternalCase.created_at <= datetime.fromisoformat(date_to))
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                InternalCase.case_number.ilike(term),
                InternalCase.title.ilike(term),
                InternalCase.description.ilike(term),
                InternalCase.resolution_note.ilike(term),
            )
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_q) or 0
    items = db.scalars(
        query.order_by(InternalCase.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": str(c.id),
                "case_number": c.case_number,
                "title": c.title,
                "description": c.description,
                "status": c.status,
                "created_at": c.created_at,
            }
            for c in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if page_size else 0,
    }


@router.get("/cases/{case_id}", response_model=dict)
def get_case(
    case_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    case = db.get(InternalCase, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )
    events = db.scalars(
        select(InternalCaseEvent)
        .where(InternalCaseEvent.internal_case_id == case_id)
        .order_by(InternalCaseEvent.event_at)
    ).all()
    source_report = db.get(FieldReport, case.source_report_id)
    category = db.get(FieldReportCategory, case.category_id) if case.category_id else None
    severity = db.get(FieldReportSeverity, case.severity_id) if case.severity_id else None
    return {
        "id": str(case.id),
        "case_number": case.case_number,
        "status": case.status,
        "title": case.title,
        "description": case.description,
        "assigned_to_user_id": case.assigned_to_user_id,
        "assigned_team_id": str(case.assigned_team_id)
        if case.assigned_team_id
        else None,
        "acknowledged_at": case.acknowledged_at,
        "started_at": case.started_at,
        "resolved_at": case.resolved_at,
        "closed_at": case.closed_at,
        "resolution_note": case.resolution_note,
        "priority_rank": case.priority_rank,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "category": {
            "id": str(category.id),
            "name": category.name,
            "code": category.code,
        }
        if category
        else None,
        "severity": {
            "id": str(severity.id),
            "name": severity.name,
            "code": severity.code,
            "rank_order": severity.rank_order,
        }
        if severity
        else None,
        "source_report": {
            "id": str(source_report.id),
            "report_number": source_report.report_number,
            "title": source_report.title,
            "status": source_report.status,
        }
        if source_report
        else None,
        "events": [
            {"event_type": e.event_type, "event_at": e.event_at, "note": e.note}
            for e in events
        ],
    }


@router.get("/cases/{case_id}/attachments", response_model=list[dict])
def list_case_attachments(
    case_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    case = db.get(InternalCase, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )

    rows = db.execute(
        select(InternalCaseAttachment, Attachment)
        .join(Attachment, InternalCaseAttachment.attachment_id == Attachment.id)
        .where(InternalCaseAttachment.internal_case_id == case_id)
        .where(Attachment.is_deleted == False)
        .order_by(InternalCaseAttachment.created_at.desc())
    ).all()
    return [
        {
            "id": str(attachment.id),
            "original_filename": attachment.original_filename,
            "mime_type": attachment.mime_type,
            "attachment_type": attachment.attachment_type,
            "file_size_bytes": attachment.file_size_bytes,
            "created_at": attachment.created_at,
        }
        for _, attachment in rows
    ]


@router.post("/cases/{case_id}/assign", response_model=dict)
def assign_case(
    case_id: UUID,
    data: dict,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    case = db.get(InternalCase, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )

    if data.get("assigned_to_user_id"):
        case.assigned_to_user_id = data["assigned_to_user_id"]
    if data.get("assigned_team_id"):
        case.assigned_team_id = data["assigned_team_id"]
    if case.status == "open":
        case.status = "assigned"

    history = InternalCaseAssignmentHistory(
        internal_case_id=case.id,
        assigned_to_user_id=data.get("assigned_to_user_id"),
        assigned_team_id=data.get("assigned_team_id"),
        assigned_by_user_id=current_user.id,
        assigned_at=datetime.now(),
        note=data.get("note"),
    )
    db.add(history)

    event = InternalCaseEvent(
        internal_case_id=case.id,
        event_type="assigned",
        event_at=datetime.now(),
        actor_user_id=current_user.id,
        note=data.get("note"),
    )
    db.add(event)
    db.commit()
    db.refresh(case)
    return {"id": str(case.id), "status": case.status}


@router.post("/cases/{case_id}/acknowledge", response_model=dict)
def acknowledge_case(
    case_id: UUID,
    data: dict,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    case = db.get(InternalCase, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )
    case.acknowledged_at = datetime.now()
    if case.status == "assigned":
        case.status = "acknowledged"
    event = InternalCaseEvent(
        internal_case_id=case.id,
        event_type="acknowledged",
        event_at=datetime.now(),
        actor_user_id=current_user.id,
        note=data.get("note"),
    )
    db.add(event)
    db.commit()
    return {"id": str(case.id), "status": case.status}


@router.post("/cases/{case_id}/start", response_model=dict)
def start_case(
    case_id: UUID,
    data: dict,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    case = db.get(InternalCase, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )
    case.started_at = datetime.now()
    if case.status in ("acknowledged", "assigned"):
        case.status = "in_progress"
    event = InternalCaseEvent(
        internal_case_id=case.id,
        event_type="started",
        event_at=datetime.now(),
        actor_user_id=current_user.id,
        note=data.get("note"),
    )
    db.add(event)
    db.commit()
    return {"id": str(case.id), "status": case.status}


@router.post("/cases/{case_id}/resolve", response_model=dict)
def resolve_case(
    case_id: UUID,
    data: dict,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    case = db.get(InternalCase, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )
    case.resolved_at = datetime.now()
    case.resolution_note = data.get("resolution_note")
    if case.status == "in_progress":
        case.status = "resolved"
    event = InternalCaseEvent(
        internal_case_id=case.id,
        event_type="resolved",
        event_at=datetime.now(),
        actor_user_id=current_user.id,
        note=data.get("resolution_note"),
    )
    db.add(event)
    db.commit()
    return {"id": str(case.id), "status": case.status}


@router.post("/cases/{case_id}/close", response_model=dict)
def close_case(
    case_id: UUID,
    data: dict,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    case = db.get(InternalCase, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )
    case.closed_at = datetime.now()
    case.closed_by_user_id = current_user.id
    if data.get("resolution_note"):
        case.resolution_note = data["resolution_note"]
    if case.status in ("resolved", "in_progress"):
        case.status = "closed"
    event = InternalCaseEvent(
        internal_case_id=case.id,
        event_type="closed",
        event_at=datetime.now(),
        actor_user_id=current_user.id,
        note=data.get("note"),
    )
    db.add(event)
    db.commit()
    return {"id": str(case.id), "status": case.status}


@router.post("/cases/{case_id}/reopen", response_model=dict)
def reopen_case(
    case_id: UUID,
    data: dict,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    case = db.get(InternalCase, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )
    if case.status not in ("closed", "resolved"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Case cannot be reopened from current status",
        )
    case.status = "reopened"
    event = InternalCaseEvent(
        internal_case_id=case.id,
        event_type="reopened",
        event_at=datetime.now(),
        actor_user_id=current_user.id,
        note=data.get("note"),
    )
    db.add(event)
    db.commit()
    return {"id": str(case.id), "status": case.status}


@router.get("/cases/{case_id}/events", response_model=list[dict])
def get_case_events(
    case_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    events = db.scalars(
        select(InternalCaseEvent)
        .where(InternalCaseEvent.internal_case_id == case_id)
        .order_by(InternalCaseEvent.event_at)
    ).all()
    return [
        {
            "event_type": e.event_type,
            "event_at": e.event_at,
            "actor_user_id": e.actor_user_id,
            "note": e.note,
        }
        for e in events
    ]


@router.get("/lookups/report-categories", response_model=list[dict])
def get_report_categories(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    items = db.scalars(
        select(FieldReportCategory)
        .where(FieldReportCategory.is_active == True)
        .order_by(FieldReportCategory.sort_order)
    ).all()
    return [
        {"id": str(c.id), "code": c.code, "name": c.name, "description": c.description}
        for c in items
    ]


@router.get("/lookups/report-severities", response_model=list[dict])
def get_report_severities(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    items = db.scalars(
        select(FieldReportSeverity)
        .where(FieldReportSeverity.is_active == True)
        .order_by(FieldReportSeverity.rank_order)
    ).all()
    return [
        {
            "id": str(s.id),
            "code": s.code,
            "name": s.name,
            "rank_order": s.rank_order,
            "color_hex": s.color_hex,
        }
        for s in items
    ]


@router.get("/lookups/maintenance-types", response_model=list[dict])
def get_maintenance_types(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    from app.modules.operazioni.models.vehicles import VehicleMaintenanceType

    items = db.scalars(
        select(VehicleMaintenanceType).where(VehicleMaintenanceType.is_active == True)
    ).all()
    return [{"id": str(t.id), "code": t.code, "name": t.name} for t in items]


@router.get("/lookups/teams", response_model=list[dict])
def get_teams(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    from app.modules.operazioni.models.organizational import Team

    items = db.scalars(
        select(Team).where(Team.is_active == True).order_by(Team.name)
    ).all()
    return [{"id": str(t.id), "code": t.code, "name": t.name} for t in items]
