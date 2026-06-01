from __future__ import annotations

from collections import defaultdict
import csv
from dataclasses import dataclass
from datetime import date, timedelta
from io import StringIO

from sqlalchemy import case, delete, desc, func, select
from sqlalchemy.orm import Session

from app.modules.wiki.models import WikiTelemetryDailyMetric, WikiTelemetryPeriodMetric, WikiToolAuditLog

_DIMENSION_COLUMNS = {
    "global": None,
    "module": WikiToolAuditLog.module_key,
    "tool": WikiToolAuditLog.tool_name,
    "mode": WikiToolAuditLog.mode,
    "intent": WikiToolAuditLog.intent,
    "fallback_reason": WikiToolAuditLog.fallback_reason,
}


@dataclass(slots=True, frozen=True)
class WikiTelemetryCountReadModel:
    key: str
    count: int


@dataclass(slots=True, frozen=True)
class WikiTelemetrySeriesPointReadModel:
    metric_date: str
    period_label: str
    total: int
    denied_count: int
    no_match_count: int
    docs_only_count: int
    live_count: int
    logic_count: int
    hybrid_count: int
    avg_latency_ms: int


@dataclass(slots=True, frozen=True)
class WikiTelemetrySummaryReadModel:
    total: int
    success_count: int
    denied_count: int
    no_match_count: int
    docs_only_count: int
    live_count: int
    logic_count: int
    hybrid_count: int
    avg_latency_ms: int
    top_tools: list[WikiTelemetryCountReadModel]
    top_modules: list[WikiTelemetryCountReadModel]
    top_modes: list[WikiTelemetryCountReadModel]
    top_fallback_reasons: list[WikiTelemetryCountReadModel]


def _start_of_week(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _start_of_month(value: date) -> date:
    return value.replace(day=1)


def _format_period_label(period_type: str, period_start: date) -> str:
    if period_type == "week":
        return f"Week {period_start.isoformat()}"
    if period_type == "month":
        return period_start.strftime("%Y-%m")
    return period_start.isoformat()


def _coerce_day(value: object) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"Unsupported day value: {value!r}")


def refresh_wiki_daily_metrics(
    db: Session,
    *,
    start_date: date,
    end_date: date,
) -> None:
    day_expr = func.date(WikiToolAuditLog.created_at)
    db.execute(
        delete(WikiTelemetryDailyMetric).where(
            WikiTelemetryDailyMetric.metric_date >= start_date,
            WikiTelemetryDailyMetric.metric_date <= end_date,
        )
    )

    for dimension_type, column in _DIMENSION_COLUMNS.items():
        dimension_expr = func.coalesce(column, "n/d").label("dimension_key") if column is not None else None
        select_columns = [
            day_expr.label("metric_date"),
            func.count().label("total"),
            func.coalesce(func.sum(case((WikiToolAuditLog.success == 1, 1), else_=0)), 0).label("success_count"),
            func.coalesce(func.sum(case((WikiToolAuditLog.success == 0, 1), else_=0)), 0).label("denied_count"),
            func.coalesce(func.sum(case((WikiToolAuditLog.found == 0, 1), else_=0)), 0).label("no_match_count"),
            func.coalesce(func.sum(case((WikiToolAuditLog.mode == "docs_only", 1), else_=0)), 0).label("docs_only_count"),
            func.coalesce(func.sum(case((WikiToolAuditLog.mode == "live_data", 1), else_=0)), 0).label("live_count"),
            func.coalesce(func.sum(case((WikiToolAuditLog.mode == "logic", 1), else_=0)), 0).label("logic_count"),
            func.coalesce(func.sum(case((WikiToolAuditLog.mode == "hybrid", 1), else_=0)), 0).label("hybrid_count"),
            func.coalesce(func.avg(WikiToolAuditLog.latency_ms), 0).label("avg_latency_ms"),
        ]
        if dimension_expr is not None:
            select_columns.insert(1, dimension_expr)

        query = (
            select(*select_columns)
            .where(day_expr >= start_date.isoformat(), day_expr <= end_date.isoformat())
            .group_by(day_expr, *( [dimension_expr] if dimension_expr is not None else [] ))
            .order_by(day_expr)
        )
        rows = db.execute(query).all()
        for row in rows:
            db.add(
                WikiTelemetryDailyMetric(
                    metric_date=_coerce_day(row.metric_date),
                    dimension_type=dimension_type,
                    dimension_key=None if dimension_type == "global" else row.dimension_key,
                    total=int(row.total or 0),
                    success_count=int(row.success_count or 0),
                    denied_count=int(row.denied_count or 0),
                    no_match_count=int(row.no_match_count or 0),
                    docs_only_count=int(row.docs_only_count or 0),
                    live_count=int(row.live_count or 0),
                    logic_count=int(row.logic_count or 0),
                    hybrid_count=int(row.hybrid_count or 0),
                    avg_latency_ms=int(round(float(row.avg_latency_ms or 0))),
                )
            )
    db.commit()
    refresh_wiki_period_metrics(db, start_date=start_date, end_date=end_date, period_type="week")
    refresh_wiki_period_metrics(db, start_date=start_date, end_date=end_date, period_type="month")


def refresh_recent_wiki_daily_metrics(db: Session, *, days: int = 30) -> None:
    end_date = date.today()
    start_date = end_date - timedelta(days=max(days - 1, 0))
    refresh_wiki_daily_metrics(db, start_date=start_date, end_date=end_date)


def refresh_wiki_period_metrics(
    db: Session,
    *,
    start_date: date,
    end_date: date,
    period_type: str,
) -> None:
    if period_type not in {"week", "month"}:
        raise ValueError(f"Unsupported period type: {period_type}")

    start_period = _start_of_week(start_date) if period_type == "week" else _start_of_month(start_date)
    end_period = _start_of_week(end_date) if period_type == "week" else _start_of_month(end_date)
    db.execute(
        delete(WikiTelemetryPeriodMetric).where(
            WikiTelemetryPeriodMetric.period_type == period_type,
            WikiTelemetryPeriodMetric.period_start >= start_period,
            WikiTelemetryPeriodMetric.period_start <= end_period,
        )
    )

    daily_rows = db.scalars(
        select(WikiTelemetryDailyMetric).where(
            WikiTelemetryDailyMetric.metric_date >= start_date,
            WikiTelemetryDailyMetric.metric_date <= end_date,
        )
    ).all()

    grouped: dict[tuple[date, str, str | None], dict[str, int]] = defaultdict(
        lambda: {
            "total": 0,
            "success_count": 0,
            "denied_count": 0,
            "no_match_count": 0,
            "docs_only_count": 0,
            "live_count": 0,
            "logic_count": 0,
            "hybrid_count": 0,
            "latency_sum": 0,
            "days": 0,
        }
    )
    for row in daily_rows:
        period_start = _start_of_week(row.metric_date) if period_type == "week" else _start_of_month(row.metric_date)
        key = (period_start, row.dimension_type, row.dimension_key)
        bucket = grouped[key]
        bucket["total"] += row.total
        bucket["success_count"] += row.success_count
        bucket["denied_count"] += row.denied_count
        bucket["no_match_count"] += row.no_match_count
        bucket["docs_only_count"] += row.docs_only_count
        bucket["live_count"] += row.live_count
        bucket["logic_count"] += row.logic_count
        bucket["hybrid_count"] += row.hybrid_count
        bucket["latency_sum"] += row.avg_latency_ms
        bucket["days"] += 1

    for (period_start, dimension_type, dimension_key), bucket in grouped.items():
        avg_latency_ms = int(round(bucket["latency_sum"] / max(bucket["days"], 1)))
        db.add(
            WikiTelemetryPeriodMetric(
                period_type=period_type,
                period_start=period_start,
                dimension_type=dimension_type,
                dimension_key=dimension_key,
                total=bucket["total"],
                success_count=bucket["success_count"],
                denied_count=bucket["denied_count"],
                no_match_count=bucket["no_match_count"],
                docs_only_count=bucket["docs_only_count"],
                live_count=bucket["live_count"],
                logic_count=bucket["logic_count"],
                hybrid_count=bucket["hybrid_count"],
                avg_latency_ms=avg_latency_ms,
            )
        )
    db.commit()


def get_wiki_telemetry_series(
    db: Session,
    *,
    dimension_type: str = "global",
    dimension_key: str | None = None,
    days: int = 30,
    granularity: str = "day",
) -> list[WikiTelemetrySeriesPointReadModel]:
    end_date = date.today()
    start_date = end_date - timedelta(days=max(days - 1, 0))
    refresh_wiki_daily_metrics(db, start_date=start_date, end_date=end_date)
    if granularity == "day":
        query = (
            select(WikiTelemetryDailyMetric)
            .where(
                WikiTelemetryDailyMetric.metric_date >= start_date,
                WikiTelemetryDailyMetric.metric_date <= end_date,
                WikiTelemetryDailyMetric.dimension_type == dimension_type,
            )
            .order_by(WikiTelemetryDailyMetric.metric_date.asc())
        )
        if dimension_type != "global":
            query = query.where(WikiTelemetryDailyMetric.dimension_key == (dimension_key or "n/d"))
        rows = db.scalars(query).all()
        return [
            WikiTelemetrySeriesPointReadModel(
                metric_date=row.metric_date.isoformat(),
                period_label=row.metric_date.isoformat(),
                total=row.total,
                denied_count=row.denied_count,
                no_match_count=row.no_match_count,
                docs_only_count=row.docs_only_count,
                live_count=row.live_count,
                logic_count=row.logic_count,
                hybrid_count=row.hybrid_count,
                avg_latency_ms=row.avg_latency_ms,
            )
            for row in rows
        ]

    period_type = "week" if granularity == "week" else "month"
    refresh_wiki_period_metrics(db, start_date=start_date, end_date=end_date, period_type=period_type)
    query = (
        select(WikiTelemetryPeriodMetric)
        .where(
            WikiTelemetryPeriodMetric.period_type == period_type,
            WikiTelemetryPeriodMetric.period_start >= (_start_of_week(start_date) if period_type == "week" else _start_of_month(start_date)),
            WikiTelemetryPeriodMetric.period_start <= (_start_of_week(end_date) if period_type == "week" else _start_of_month(end_date)),
            WikiTelemetryPeriodMetric.dimension_type == dimension_type,
        )
        .order_by(WikiTelemetryPeriodMetric.period_start.asc())
    )
    if dimension_type != "global":
        query = query.where(WikiTelemetryPeriodMetric.dimension_key == (dimension_key or "n/d"))
    rows = db.scalars(query).all()
    return [
        WikiTelemetrySeriesPointReadModel(
            metric_date=row.period_start.isoformat(),
            period_label=_format_period_label(period_type, row.period_start),
            total=row.total,
            denied_count=row.denied_count,
            no_match_count=row.no_match_count,
            docs_only_count=row.docs_only_count,
            live_count=row.live_count,
            logic_count=row.logic_count,
            hybrid_count=row.hybrid_count,
            avg_latency_ms=row.avg_latency_ms,
        )
        for row in rows
    ]


def _top_dimension_counts(
    db: Session,
    *,
    dimension_type: str,
    days: int,
) -> list[WikiTelemetryCountReadModel]:
    end_date = date.today()
    start_date = end_date - timedelta(days=max(days - 1, 0))
    rows = db.execute(
        select(
            func.coalesce(WikiTelemetryDailyMetric.dimension_key, "n/d").label("key"),
            func.coalesce(func.sum(WikiTelemetryDailyMetric.total), 0).label("count"),
        )
        .where(
            WikiTelemetryDailyMetric.metric_date >= start_date,
            WikiTelemetryDailyMetric.metric_date <= end_date,
            WikiTelemetryDailyMetric.dimension_type == dimension_type,
        )
        .group_by(func.coalesce(WikiTelemetryDailyMetric.dimension_key, "n/d"))
        .order_by(desc("count"), func.coalesce(WikiTelemetryDailyMetric.dimension_key, "n/d"))
        .limit(5)
    ).all()
    return [WikiTelemetryCountReadModel(key=row.key, count=int(row.count or 0)) for row in rows]


def get_wiki_telemetry_summary(db: Session, *, days: int = 30) -> WikiTelemetrySummaryReadModel:
    end_date = date.today()
    start_date = end_date - timedelta(days=max(days - 1, 0))
    refresh_wiki_daily_metrics(db, start_date=start_date, end_date=end_date)

    row = db.execute(
        select(
            func.coalesce(func.sum(WikiTelemetryDailyMetric.total), 0).label("total"),
            func.coalesce(func.sum(WikiTelemetryDailyMetric.success_count), 0).label("success_count"),
            func.coalesce(func.sum(WikiTelemetryDailyMetric.denied_count), 0).label("denied_count"),
            func.coalesce(func.sum(WikiTelemetryDailyMetric.no_match_count), 0).label("no_match_count"),
            func.coalesce(func.sum(WikiTelemetryDailyMetric.docs_only_count), 0).label("docs_only_count"),
            func.coalesce(func.sum(WikiTelemetryDailyMetric.live_count), 0).label("live_count"),
            func.coalesce(func.sum(WikiTelemetryDailyMetric.logic_count), 0).label("logic_count"),
            func.coalesce(func.sum(WikiTelemetryDailyMetric.hybrid_count), 0).label("hybrid_count"),
            func.coalesce(func.avg(WikiTelemetryDailyMetric.avg_latency_ms), 0).label("avg_latency_ms"),
        ).where(
            WikiTelemetryDailyMetric.metric_date >= start_date,
            WikiTelemetryDailyMetric.metric_date <= end_date,
            WikiTelemetryDailyMetric.dimension_type == "global",
        )
    ).one()

    return WikiTelemetrySummaryReadModel(
        total=int(row.total or 0),
        success_count=int(row.success_count or 0),
        denied_count=int(row.denied_count or 0),
        no_match_count=int(row.no_match_count or 0),
        docs_only_count=int(row.docs_only_count or 0),
        live_count=int(row.live_count or 0),
        logic_count=int(row.logic_count or 0),
        hybrid_count=int(row.hybrid_count or 0),
        avg_latency_ms=int(round(float(row.avg_latency_ms or 0))),
        top_tools=_top_dimension_counts(db, dimension_type="tool", days=days),
        top_modules=_top_dimension_counts(db, dimension_type="module", days=days),
        top_modes=_top_dimension_counts(db, dimension_type="mode", days=days),
        top_fallback_reasons=_top_dimension_counts(db, dimension_type="fallback_reason", days=days),
    )


def export_wiki_telemetry_series_csv(
    db: Session,
    *,
    dimension_type: str = "global",
    dimension_key: str | None = None,
    days: int = 30,
    granularity: str = "day",
) -> str:
    items = get_wiki_telemetry_series(
        db,
        dimension_type=dimension_type,
        dimension_key=dimension_key,
        days=days,
        granularity=granularity,
    )
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "dimension_type",
            "dimension_key",
            "granularity",
            "metric_date",
            "period_label",
            "total",
            "denied_count",
            "no_match_count",
            "docs_only_count",
            "live_count",
            "logic_count",
            "hybrid_count",
            "avg_latency_ms",
        ]
    )
    for item in items:
        writer.writerow(
            [
                dimension_type,
                dimension_key or "",
                granularity,
                item.metric_date,
                item.period_label,
                item.total,
                item.denied_count,
                item.no_match_count,
                item.docs_only_count,
                item.live_count,
                item.logic_count,
                item.hybrid_count,
                item.avg_latency_ms,
            ]
        )
    return buffer.getvalue()


def prune_wiki_telemetry_data(
    db: Session,
    *,
    audit_retention_days: int,
    daily_retention_days: int,
    period_retention_days: int,
) -> tuple[int, int, int]:
    audit_cutoff = date.today() - timedelta(days=max(audit_retention_days, 1))
    daily_cutoff = date.today() - timedelta(days=max(daily_retention_days, 1))
    period_cutoff = date.today() - timedelta(days=max(period_retention_days, 1))

    deleted_audit_rows = db.execute(
        delete(WikiToolAuditLog).where(func.date(WikiToolAuditLog.created_at) < audit_cutoff.isoformat())
    ).rowcount or 0
    deleted_daily_rows = db.execute(
        delete(WikiTelemetryDailyMetric).where(WikiTelemetryDailyMetric.metric_date < daily_cutoff)
    ).rowcount or 0
    deleted_period_rows = db.execute(
        delete(WikiTelemetryPeriodMetric).where(WikiTelemetryPeriodMetric.period_start < period_cutoff)
    ).rowcount or 0
    db.commit()
    return int(deleted_audit_rows), int(deleted_daily_rows), int(deleted_period_rows)
