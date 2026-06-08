from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.wiki.models import WikiRequest
from app.modules.wiki.schemas import (
    WikiSupportAnalyticsCountRead,
    WikiSupportAnalyticsSeriesPointRead,
    WikiSupportAnalyticsSeriesResponse,
    WikiSupportAnalyticsSummaryRead,
)

router = APIRouter(tags=["Wiki"])


def _require_wiki_admin(current_user: ApplicationUser) -> None:
    if current_user.role not in ("admin", "super_admin"):
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso negato.")


def _count_rows(
    db: Session,
    *,
    start_date: date,
    column,
    limit: int = 6,
    include_null_label: str | None = None,
) -> list[WikiSupportAnalyticsCountRead]:
    if include_null_label:
        key_expr = func.coalesce(func.nullif(column, ""), include_null_label)
    else:
        key_expr = column
    rows = (
        db.query(key_expr.label("key"), func.count(WikiRequest.id).label("count"))
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .group_by(key_expr)
        .order_by(func.count(WikiRequest.id).desc(), key_expr.asc())
        .limit(limit)
        .all()
    )
    return [WikiSupportAnalyticsCountRead(key=str(row.key), count=int(row.count)) for row in rows if row.key]


@router.get("/support/analytics/summary", response_model=WikiSupportAnalyticsSummaryRead)
def get_wiki_support_analytics_summary(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiSupportAnalyticsSummaryRead:
    _require_wiki_admin(current_user)

    start_date = date.today() - timedelta(days=days - 1)

    total_requests = (
        db.query(func.count(WikiRequest.id))
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .scalar()
        or 0
    )
    open_requests = (
        db.query(func.count(WikiRequest.id))
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .filter(WikiRequest.status.notin_(("resolved", "duplicate", "rejected")))
        .scalar()
        or 0
    )
    assigned_requests = (
        db.query(func.count(WikiRequest.id))
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .filter(WikiRequest.assigned_to.isnot(None))
        .filter(WikiRequest.assigned_to != "")
        .scalar()
        or 0
    )
    resolved_requests = (
        db.query(func.count(WikiRequest.id))
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .filter(WikiRequest.status == "resolved")
        .scalar()
        or 0
    )
    urgent_requests = (
        db.query(func.count(WikiRequest.id))
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .filter(WikiRequest.priority == "urgent")
        .scalar()
        or 0
    )
    high_severity_requests = (
        db.query(func.count(WikiRequest.id))
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .filter(WikiRequest.severity.in_(("high", "critical")))
        .scalar()
        or 0
    )

    def _count_type(request_type: str) -> int:
        return (
            db.query(func.count(WikiRequest.id))
            .filter(func.date(WikiRequest.created_at) >= start_date)
            .filter(WikiRequest.request_type == request_type)
            .scalar()
            or 0
        )

    return WikiSupportAnalyticsSummaryRead(
        total_requests=int(total_requests),
        open_requests=int(open_requests),
        assigned_requests=int(assigned_requests),
        resolved_requests=int(resolved_requests),
        urgent_requests=int(urgent_requests),
        high_severity_requests=int(high_severity_requests),
        feature_requests=int(_count_type("feature_request")),
        bug_reports=int(_count_type("bug_report")),
        access_issues=int(_count_type("access_issue")),
        data_issues=int(_count_type("data_issue")),
        help_requests=int(_count_type("help_request")),
        top_request_types=_count_rows(db, start_date=start_date, column=WikiRequest.request_type, include_null_label="n/d"),
        top_modules=_count_rows(db, start_date=start_date, column=WikiRequest.module_key, include_null_label="Modulo non dichiarato"),
        top_statuses=_count_rows(db, start_date=start_date, column=WikiRequest.status, include_null_label="n/d"),
        top_priorities=_count_rows(db, start_date=start_date, column=WikiRequest.priority, include_null_label="n/d"),
        top_severities=_count_rows(db, start_date=start_date, column=WikiRequest.severity, include_null_label="n/d"),
        top_pages=_count_rows(db, start_date=start_date, column=WikiRequest.page_path, include_null_label="Pagina non dichiarata"),
        top_assignees=_count_rows(db, start_date=start_date, column=WikiRequest.assigned_to, include_null_label="Non assegnata"),
        top_creators=_count_rows(db, start_date=start_date, column=WikiRequest.created_by, include_null_label="Autore non dichiarato"),
        top_impact_scopes=_count_rows(db, start_date=start_date, column=WikiRequest.impact_scope, include_null_label="Impatto non dichiarato"),
    )


@router.get("/support/analytics/series", response_model=WikiSupportAnalyticsSeriesResponse)
def get_wiki_support_analytics_series(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiSupportAnalyticsSeriesResponse:
    _require_wiki_admin(current_user)

    start_date = date.today() - timedelta(days=days - 1)
    metric_date = func.date(WikiRequest.created_at)
    rows = (
        db.query(
            metric_date.label("metric_date"),
            func.count(WikiRequest.id).label("created_count"),
            func.sum(case((WikiRequest.status == "resolved", 1), else_=0)).label("resolved_count"),
            func.sum(case((WikiRequest.status.notin_(("resolved", "duplicate", "rejected")), 1), else_=0)).label("open_count"),
            func.sum(case((WikiRequest.request_type == "feature_request", 1), else_=0)).label("feature_request_count"),
            func.sum(case((WikiRequest.request_type == "bug_report", 1), else_=0)).label("bug_report_count"),
            func.sum(case((WikiRequest.request_type == "help_request", 1), else_=0)).label("help_request_count"),
            func.sum(case((WikiRequest.request_type == "access_issue", 1), else_=0)).label("access_issue_count"),
            func.sum(case((WikiRequest.request_type == "data_issue", 1), else_=0)).label("data_issue_count"),
            func.sum(case((WikiRequest.priority == "urgent", 1), else_=0)).label("urgent_count"),
            func.sum(case((WikiRequest.severity.in_(("high", "critical")), 1), else_=0)).label("high_severity_count"),
        )
        .filter(metric_date >= start_date)
        .group_by(metric_date)
        .order_by(metric_date.asc())
        .all()
    )
    items: list[WikiSupportAnalyticsSeriesPointRead] = []
    for row in rows:
        metric_date_value = row.metric_date if isinstance(row.metric_date, date) else date.fromisoformat(str(row.metric_date))
        items.append(
            WikiSupportAnalyticsSeriesPointRead(
                metric_date=metric_date_value,
                period_label=metric_date_value.strftime("%d/%m"),
                created_count=int(row.created_count or 0),
                resolved_count=int(row.resolved_count or 0),
                open_count=int(row.open_count or 0),
                feature_request_count=int(row.feature_request_count or 0),
                bug_report_count=int(row.bug_report_count or 0),
                help_request_count=int(row.help_request_count or 0),
                access_issue_count=int(row.access_issue_count or 0),
                data_issue_count=int(row.data_issue_count or 0),
                urgent_count=int(row.urgent_count or 0),
                high_severity_count=int(row.high_severity_count or 0),
            )
        )
    return WikiSupportAnalyticsSeriesResponse(days=days, items=items)
