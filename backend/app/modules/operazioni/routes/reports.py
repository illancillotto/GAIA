"""Reports and Cases domain routes."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.reports import (
    FieldReport,
    FieldReportCategory,
    FieldReportSeverity,
    InternalCase,
    InternalCaseEvent,
    InternalCaseAssignmentHistory,
)

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
                "report_number": r.report_number,
                "title": r.title,
                "status": r.status,
                "created_at": r.created_at,
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
        "report_number": report.report_number,
        "title": report.title,
        "status": report.status,
    }


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
        "events": [
            {"event_type": e.event_type, "event_at": e.event_at, "note": e.note}
            for e in events
        ],
    }


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
