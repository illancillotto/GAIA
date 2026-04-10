"""Dashboard endpoints for Operazioni field reports."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.reports import FieldReport, InternalCase, InternalCaseEvent
from app.modules.operazioni.services.parsing import parse_date_filter

router = APIRouter(prefix="", tags=["operazioni/reports-dashboard"])


def _apply_dashboard_filters(
    query,
    *,
    status_filter: str | None = None,
    area_code: str | None = None,
    reporter_name: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    if status_filter:
        statuses = [item.strip() for item in status_filter.split(",") if item.strip()]
        if statuses:
            query = query.where(FieldReport.status.in_(statuses))
    if area_code:
        query = query.where(FieldReport.area_code == area_code)
    if reporter_name:
        query = query.where(FieldReport.reporter_name.ilike(f"%{reporter_name.strip()}%"))
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                FieldReport.title.ilike(term),
                FieldReport.description.ilike(term),
                FieldReport.external_code.ilike(term),
                FieldReport.report_number.ilike(term),
                FieldReport.reporter_name.ilike(term),
                FieldReport.assigned_responsibles.ilike(term),
            )
        )
    parsed_from = parse_date_filter(date_from)
    if parsed_from:
        query = query.where(FieldReport.created_at >= parsed_from)
    parsed_to = parse_date_filter(date_to, end_of_day=True)
    if parsed_to:
        query = query.where(FieldReport.created_at <= parsed_to)
    return query


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
    case_lookup = (
        {
            case.id: case
            for case in db.scalars(select(InternalCase).where(InternalCase.id.in_(case_ids))).all()
        }
        if case_ids
        else {}
    )

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
            select(FieldReport.status, func.count(FieldReport.id)).group_by(FieldReport.status),
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
            select(FieldReport.area_code.label("area"), func.count(FieldReport.id).label("count"))
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
            select(FieldReport.reporter_name.label("name"), func.count(FieldReport.id).label("count"))
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

    total_with_events = (
        db.scalar(
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
        )
        or 0
    )

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
            "by_reporter": [{"name": name, "count": count} for name, count in by_reporter_rows],
            "avg_completion_minutes": int(avg_completion_minutes) if avg_completion_minutes is not None else None,
            "total_with_events": total_with_events,
            "total_without_events": max(total - total_with_events, 0),
        },
    }
