from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import RequireAdmin, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import (
    WikiTelemetryCountRead,
    WikiTelemetryPruneResponse,
    WikiTelemetryRefreshResponse,
    WikiTelemetryRetentionRead,
    WikiTelemetryScheduleRead,
    WikiTelemetrySeriesPointRead,
    WikiTelemetrySeriesResponse,
    WikiTelemetrySummaryResponse,
)
from app.modules.wiki.services.telemetry import (
    export_wiki_telemetry_series_csv,
    get_wiki_telemetry_series,
    get_wiki_telemetry_summary,
    prune_wiki_telemetry_data,
    refresh_recent_wiki_daily_metrics,
)

router = APIRouter(prefix="/telemetry", tags=["Wiki Telemetry"])


@router.get("/summary", response_model=WikiTelemetrySummaryResponse, dependencies=[RequireAdmin])
def get_summary(
    _: Annotated[ApplicationUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    days: int = Query(30, ge=7, le=180),
) -> WikiTelemetrySummaryResponse:
    summary = get_wiki_telemetry_summary(db, days=days)
    return WikiTelemetrySummaryResponse(
        total=summary.total,
        success_count=summary.success_count,
        denied_count=summary.denied_count,
        no_match_count=summary.no_match_count,
        docs_only_count=summary.docs_only_count,
        live_count=summary.live_count,
        logic_count=summary.logic_count,
        hybrid_count=summary.hybrid_count,
        avg_latency_ms=summary.avg_latency_ms,
        top_tools=[WikiTelemetryCountRead(key=item.key, count=item.count) for item in summary.top_tools],
        top_modules=[WikiTelemetryCountRead(key=item.key, count=item.count) for item in summary.top_modules],
        top_modes=[WikiTelemetryCountRead(key=item.key, count=item.count) for item in summary.top_modes],
        top_fallback_reasons=[
            WikiTelemetryCountRead(key=item.key, count=item.count) for item in summary.top_fallback_reasons
        ],
    )


@router.get("/series", response_model=WikiTelemetrySeriesResponse, dependencies=[RequireAdmin])
def get_series(
    _: Annotated[ApplicationUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    dimension_type: str = Query("global"),
    dimension_key: str | None = Query(None),
    days: int = Query(30, ge=7, le=180),
    granularity: str = Query("day", pattern="^(day|week|month)$"),
) -> WikiTelemetrySeriesResponse:
    items = get_wiki_telemetry_series(
        db,
        dimension_type=dimension_type,
        dimension_key=dimension_key,
        days=days,
        granularity=granularity,
    )
    return WikiTelemetrySeriesResponse(
        dimension_type=dimension_type,
        dimension_key=dimension_key,
        days=days,
        granularity=granularity,
        items=[
            WikiTelemetrySeriesPointRead(
                metric_date=item.metric_date,
                period_label=item.period_label,
                total=item.total,
                denied_count=item.denied_count,
                no_match_count=item.no_match_count,
                docs_only_count=item.docs_only_count,
                live_count=item.live_count,
                logic_count=item.logic_count,
                hybrid_count=item.hybrid_count,
                avg_latency_ms=item.avg_latency_ms,
            )
            for item in items
        ],
    )


@router.get("/series/export", dependencies=[RequireAdmin])
def export_series(
    _: Annotated[ApplicationUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    dimension_type: str = Query("global"),
    dimension_key: str | None = Query(None),
    days: int = Query(30, ge=7, le=180),
    granularity: str = Query("day", pattern="^(day|week|month)$"),
) -> Response:
    csv_content = export_wiki_telemetry_series_csv(
        db,
        dimension_type=dimension_type,
        dimension_key=dimension_key,
        days=days,
        granularity=granularity,
    )
    filename = f"wiki-telemetry-{dimension_type}-{granularity}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/refresh", response_model=WikiTelemetryRefreshResponse, dependencies=[RequireAdmin])
def refresh_telemetry(
    _: Annotated[ApplicationUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    days: int = Query(settings.wiki_telemetry_schedule_lookback_days, ge=7, le=180),
) -> WikiTelemetryRefreshResponse:
    refresh_recent_wiki_daily_metrics(db, days=days)
    return WikiTelemetryRefreshResponse(status="ok", days=days)


@router.get("/schedule", response_model=WikiTelemetryScheduleRead, dependencies=[RequireAdmin])
def get_schedule(
    _: Annotated[ApplicationUser, Depends(get_current_user)],
) -> WikiTelemetryScheduleRead:
    return WikiTelemetryScheduleRead(
        enabled=settings.wiki_telemetry_schedule_enabled,
        cron=settings.wiki_telemetry_schedule_cron,
        timezone=settings.wiki_telemetry_schedule_timezone,
        lookback_days=settings.wiki_telemetry_schedule_lookback_days,
    )


@router.get("/retention", response_model=WikiTelemetryRetentionRead, dependencies=[RequireAdmin])
def get_retention(
    _: Annotated[ApplicationUser, Depends(get_current_user)],
) -> WikiTelemetryRetentionRead:
    return WikiTelemetryRetentionRead(
        audit_retention_days=settings.wiki_audit_retention_days,
        daily_retention_days=settings.wiki_telemetry_daily_retention_days,
        period_retention_days=settings.wiki_telemetry_period_retention_days,
    )


@router.post("/prune", response_model=WikiTelemetryPruneResponse, dependencies=[RequireAdmin])
def prune_telemetry(
    _: Annotated[ApplicationUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WikiTelemetryPruneResponse:
    deleted_audit_rows, deleted_daily_rows, deleted_period_rows = prune_wiki_telemetry_data(
        db,
        audit_retention_days=settings.wiki_audit_retention_days,
        daily_retention_days=settings.wiki_telemetry_daily_retention_days,
        period_retention_days=settings.wiki_telemetry_period_retention_days,
    )
    return WikiTelemetryPruneResponse(
        status="ok",
        deleted_audit_rows=deleted_audit_rows,
        deleted_daily_rows=deleted_daily_rows,
        deleted_period_rows=deleted_period_rows,
    )
