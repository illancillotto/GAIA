from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from app.modules.wiki.models import WikiConversation, WikiConversationDailyMetric, WikiConversationEvent
from app.modules.wiki.services.conversation_governance import get_or_create_wiki_conversation_governance_config
from app.modules.wiki.services.conversations import (
    _build_conversation_audit_stats,
    _derive_review_reason_with_config,
    _needs_review_with_config,
)
from app.modules.wiki.services.review_rules import WikiConversationReviewConfig

_DIMENSION_FIELDS = ("global", "status", "priority", "assigned_to", "review_reason")


@dataclass(slots=True, frozen=True)
class WikiConversationMetricCountReadModel:
    key: str
    count: int


@dataclass(slots=True, frozen=True)
class WikiConversationMetricsSummaryReadModel:
    total_threads: int
    created_count: int
    closed_count: int
    open_count: int
    in_review_count: int
    waiting_user_count: int
    resolved_count: int
    high_priority_count: int
    needs_review_count: int
    review_entered_count: int
    reassigned_count: int
    reopened_count: int
    avg_time_to_review_hours: int
    avg_time_to_resolve_hours: int
    avg_open_to_review_hours: int
    avg_review_to_resolve_hours: int
    avg_waiting_user_hours: int
    data_complete_from: str | None
    last_backfill_at: datetime | None
    top_statuses: list[WikiConversationMetricCountReadModel]
    top_priorities: list[WikiConversationMetricCountReadModel]
    top_owners: list[WikiConversationMetricCountReadModel]
    top_review_reasons: list[WikiConversationMetricCountReadModel]
    top_event_types: list[WikiConversationMetricCountReadModel]


@dataclass(slots=True, frozen=True)
class WikiConversationMetricsSeriesPointReadModel:
    metric_date: str
    period_label: str
    created_count: int
    closed_count: int
    open_count: int
    in_review_count: int
    waiting_user_count: int
    resolved_count: int
    high_priority_count: int
    needs_review_count: int
    denied_threads_count: int
    fallback_threads_count: int
    no_match_threads_count: int
    review_entered_count: int
    reassigned_count: int
    reopened_count: int
    avg_time_to_review_hours: int
    avg_time_to_resolve_hours: int
    avg_open_to_review_hours: int
    avg_review_to_resolve_hours: int
    avg_waiting_user_hours: int


def _average_hours(values: list[int]) -> int:
    if not values:
        return 0
    return int(round(sum(values) / len(values)))


def _to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _day_bounds(metric_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(metric_date, time.min, UTC)
    end = datetime.combine(metric_date, time.max, UTC)
    return start, end


def _start_of_week(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _start_of_month(value: date) -> date:
    return value.replace(day=1)


def _period_label(period_type: str, period_start: date) -> str:
    if period_type == "week":
        return f"Week {period_start.isoformat()}"
    if period_type == "month":
        return period_start.strftime("%Y-%m")
    return period_start.isoformat()


def _dimension_key(conversation: WikiConversation, review_reason: str | None, dimension_type: str) -> str | None:
    if dimension_type == "global":
        return None
    if dimension_type == "status":
        return conversation.status
    if dimension_type == "priority":
        return conversation.priority
    if dimension_type == "assigned_to":
        return conversation.assigned_to or "unassigned"
    if dimension_type == "review_reason":
        return review_reason or "n/d"
    raise ValueError(f"Unsupported dimension type: {dimension_type}")


def _hours_between(start: datetime | None, end: datetime | None) -> int:
    if start is None or end is None:
        return 0
    start = _to_utc(start)
    end = _to_utc(end)
    if start is None or end is None:
        return 0
    return max(int(round((end - start).total_seconds() / 3600)), 0)


def refresh_wiki_conversation_daily_metrics(
    db: Session,
    *,
    start_date: date,
    end_date: date,
) -> None:
    db.execute(
        delete(WikiConversationDailyMetric).where(
            WikiConversationDailyMetric.metric_date >= start_date,
            WikiConversationDailyMetric.metric_date <= end_date,
        )
    )
    conversations = db.scalars(select(WikiConversation)).all()
    audit_stats = _build_conversation_audit_stats(db)
    governance = get_or_create_wiki_conversation_governance_config(db)
    review_config = WikiConversationReviewConfig(
        fallback_heavy_threshold=governance.fallback_heavy_threshold,
        no_match_repeated_threshold=governance.no_match_repeated_threshold,
        high_latency_ms_threshold=governance.high_latency_ms_threshold,
    )
    event_rows = db.execute(
        select(
            WikiConversationEvent.conversation_id,
            WikiConversationEvent.event_type,
            WikiConversationEvent.created_at,
            WikiConversationEvent.from_status,
            WikiConversationEvent.to_status,
        ).order_by(WikiConversationEvent.created_at.asc())
    ).all()
    event_rows_by_conversation: dict[object, list[object]] = defaultdict(list)
    for row in event_rows:
        event_rows_by_conversation[row.conversation_id].append(row)

    day = start_date
    while day <= end_date:
        day_start, day_end = _day_bounds(day)
        for dimension_type in _DIMENSION_FIELDS:
            buckets: dict[str | None, dict[str, object]] = defaultdict(
                lambda: {
                    "created_count": 0,
                    "closed_count": 0,
                    "open_count": 0,
                    "in_review_count": 0,
                    "waiting_user_count": 0,
                    "resolved_count": 0,
                    "high_priority_count": 0,
                    "needs_review_count": 0,
                    "denied_threads_count": 0,
                    "fallback_threads_count": 0,
                    "no_match_threads_count": 0,
                    "review_entered_count": 0,
                    "reassigned_count": 0,
                    "reopened_count": 0,
                    "review_hours_total": 0,
                    "review_hours_samples": 0,
                    "resolve_hours_total": 0,
                    "resolve_hours_samples": 0,
                    "open_to_review_samples": [],
                    "review_to_resolve_samples": [],
                    "waiting_user_samples": [],
                }
            )

            for conversation in conversations:
                created_at = _to_utc(conversation.created_at)
                resolved_at = _to_utc(conversation.resolved_at)
                last_reviewed_at = _to_utc(conversation.last_reviewed_at)
                if created_at is None or created_at > day_end:
                    continue
                review_reason = _derive_review_reason_with_config(conversation, audit_stats, review_config=review_config)
                key = _dimension_key(conversation, review_reason, dimension_type)
                bucket = buckets[key]

                if day_start <= created_at <= day_end:
                    bucket["created_count"] += 1
                if resolved_at and day_start <= resolved_at <= day_end:
                    bucket["closed_count"] += 1
                    bucket["resolve_hours_total"] += _hours_between(created_at, resolved_at)
                    bucket["resolve_hours_samples"] += 1
                if last_reviewed_at and day_start <= last_reviewed_at <= day_end:
                    bucket["review_hours_total"] += _hours_between(created_at, last_reviewed_at)
                    bucket["review_hours_samples"] += 1
                open_review_started_at = None
                latest_in_review_started_at = None
                waiting_started_at = None
                for event in event_rows_by_conversation.get(conversation.id, []):
                    event_created_at = _to_utc(event.created_at)
                    if event_created_at is None:
                        continue
                    if event_created_at > day_end:
                        break
                    if event.event_type == "status_changed":
                        if event.to_status == "in_review":
                            if open_review_started_at is None:
                                open_review_started_at = event_created_at
                            latest_in_review_started_at = event_created_at
                            if day_start <= event_created_at <= day_end:
                                bucket["review_entered_count"] += 1
                        if event.from_status == "resolved" and event.to_status == "open" and day_start <= event_created_at <= day_end:
                            bucket["reopened_count"] += 1
                        if event.to_status == "waiting_user":
                            waiting_started_at = event_created_at
                        elif event.from_status == "waiting_user" and waiting_started_at is not None:
                            cast_waiting = bucket["waiting_user_samples"]
                            cast_waiting.append(_hours_between(waiting_started_at, event_created_at))
                            waiting_started_at = None
                        if event.to_status == "resolved" and latest_in_review_started_at is not None:
                            cast_review = bucket["review_to_resolve_samples"]
                            cast_review.append(_hours_between(latest_in_review_started_at, event_created_at))
                    if event.event_type == "assignment_changed" and day_start <= event_created_at <= day_end:
                        bucket["reassigned_count"] += 1
                if open_review_started_at is not None:
                    cast_open_review = bucket["open_to_review_samples"]
                    cast_open_review.append(_hours_between(created_at, open_review_started_at))

                is_visible_in_snapshot = resolved_at is None or resolved_at > day_end or conversation.status == "resolved"
                if not is_visible_in_snapshot:
                    continue

                bucket[f"{conversation.status}_count"] += 1
                if conversation.priority == "high":
                    bucket["high_priority_count"] += 1
                if _needs_review_with_config(conversation, audit_stats, review_config=review_config):
                    bucket["needs_review_count"] += 1
                if audit_stats.denied_count.get(conversation.id, 0) > 0:
                    bucket["denied_threads_count"] += 1
                if audit_stats.fallback_count.get(conversation.id, 0) > 0:
                    bucket["fallback_threads_count"] += 1
                if audit_stats.no_match_count.get(conversation.id, 0) > 0:
                    bucket["no_match_threads_count"] += 1

            for key, bucket in buckets.items():
                db.add(
                    WikiConversationDailyMetric(
                        metric_date=day,
                        dimension_type=dimension_type,
                        dimension_key=key,
                        created_count=bucket["created_count"],
                        closed_count=bucket["closed_count"],
                        open_count=bucket["open_count"],
                        in_review_count=bucket["in_review_count"],
                        waiting_user_count=bucket["waiting_user_count"],
                        resolved_count=bucket["resolved_count"],
                        high_priority_count=bucket["high_priority_count"],
                        needs_review_count=bucket["needs_review_count"],
                        denied_threads_count=bucket["denied_threads_count"],
                        fallback_threads_count=bucket["fallback_threads_count"],
                        no_match_threads_count=bucket["no_match_threads_count"],
                        review_entered_count=bucket["review_entered_count"],
                        reassigned_count=bucket["reassigned_count"],
                        reopened_count=bucket["reopened_count"],
                        avg_time_to_review_hours=int(round(bucket["review_hours_total"] / bucket["review_hours_samples"])) if bucket["review_hours_samples"] else 0,
                        avg_time_to_resolve_hours=int(round(bucket["resolve_hours_total"] / bucket["resolve_hours_samples"])) if bucket["resolve_hours_samples"] else 0,
                        avg_open_to_review_hours=_average_hours(bucket["open_to_review_samples"]),
                        avg_review_to_resolve_hours=_average_hours(bucket["review_to_resolve_samples"]),
                        avg_waiting_user_hours=_average_hours(bucket["waiting_user_samples"]),
                    )
                )
        day += timedelta(days=1)
    db.commit()


def refresh_recent_wiki_conversation_daily_metrics(db: Session, *, days: int = 35) -> None:
    end_date = date.today()
    start_date = end_date - timedelta(days=max(days - 1, 0))
    refresh_wiki_conversation_daily_metrics(db, start_date=start_date, end_date=end_date)


def _latest_dimension_counts(db: Session, *, dimension_type: str, metric_date: date) -> list[WikiConversationMetricCountReadModel]:
    rows = db.execute(
        select(
            func.coalesce(WikiConversationDailyMetric.dimension_key, "global").label("key"),
            WikiConversationDailyMetric.open_count,
            WikiConversationDailyMetric.in_review_count,
            WikiConversationDailyMetric.waiting_user_count,
            WikiConversationDailyMetric.resolved_count,
            WikiConversationDailyMetric.needs_review_count,
        )
        .where(
            WikiConversationDailyMetric.metric_date == metric_date,
            WikiConversationDailyMetric.dimension_type == dimension_type,
        )
    ).all()
    counts: list[WikiConversationMetricCountReadModel] = []
    for row in rows:
        if dimension_type == "review_reason":
            value = int(row.needs_review_count or 0)
        elif dimension_type == "status":
            value = int((row.open_count or 0) + (row.in_review_count or 0) + (row.waiting_user_count or 0) + (row.resolved_count or 0))
        else:
            value = int((row.open_count or 0) + (row.in_review_count or 0) + (row.waiting_user_count or 0) + (row.resolved_count or 0))
        counts.append(WikiConversationMetricCountReadModel(key=row.key, count=value))
    return sorted(counts, key=lambda item: (-item.count, item.key))


def get_wiki_conversation_metrics_summary(
    db: Session,
    *,
    days: int = 30,
) -> WikiConversationMetricsSummaryReadModel:
    refresh_recent_wiki_conversation_daily_metrics(db, days=days)
    governance = get_or_create_wiki_conversation_governance_config(db)
    end_date = date.today()
    start_date = end_date - timedelta(days=max(days - 1, 0))
    rows = db.scalars(
        select(WikiConversationDailyMetric).where(
            WikiConversationDailyMetric.metric_date >= start_date,
            WikiConversationDailyMetric.metric_date <= end_date,
            WikiConversationDailyMetric.dimension_type == "global",
        ).order_by(WikiConversationDailyMetric.metric_date.asc())
    ).all()
    latest = rows[-1] if rows else None
    total_threads = db.scalar(select(func.count()).select_from(WikiConversation)) or 0
    top_event_counts = Counter[str]()
    event_rows = db.execute(
        select(WikiConversationEvent.event_type, func.count().label("count"))
        .where(
            WikiConversationEvent.created_at >= datetime.combine(start_date, time.min, UTC),
            WikiConversationEvent.created_at <= datetime.combine(end_date, time.max, UTC),
        )
        .group_by(WikiConversationEvent.event_type)
    ).all()
    for row in event_rows:
        top_event_counts[row.event_type] = int(row.count or 0)
    return WikiConversationMetricsSummaryReadModel(
        total_threads=int(total_threads),
        created_count=sum(item.created_count for item in rows),
        closed_count=sum(item.closed_count for item in rows),
        open_count=latest.open_count if latest else 0,
        in_review_count=latest.in_review_count if latest else 0,
        waiting_user_count=latest.waiting_user_count if latest else 0,
        resolved_count=latest.resolved_count if latest else 0,
        high_priority_count=latest.high_priority_count if latest else 0,
        needs_review_count=latest.needs_review_count if latest else 0,
        review_entered_count=sum(item.review_entered_count for item in rows),
        reassigned_count=sum(item.reassigned_count for item in rows),
        reopened_count=sum(item.reopened_count for item in rows),
        avg_time_to_review_hours=latest.avg_time_to_review_hours if latest else 0,
        avg_time_to_resolve_hours=latest.avg_time_to_resolve_hours if latest else 0,
        avg_open_to_review_hours=latest.avg_open_to_review_hours if latest else 0,
        avg_review_to_resolve_hours=latest.avg_review_to_resolve_hours if latest else 0,
        avg_waiting_user_hours=latest.avg_waiting_user_hours if latest else 0,
        data_complete_from=governance.data_complete_from.isoformat() if governance.data_complete_from else None,
        last_backfill_at=governance.last_backfill_at,
        top_statuses=_latest_dimension_counts(db, dimension_type="status", metric_date=end_date)[:5],
        top_priorities=_latest_dimension_counts(db, dimension_type="priority", metric_date=end_date)[:5],
        top_owners=_latest_dimension_counts(db, dimension_type="assigned_to", metric_date=end_date)[:5],
        top_review_reasons=_latest_dimension_counts(db, dimension_type="review_reason", metric_date=end_date)[:5],
        top_event_types=[
            WikiConversationMetricCountReadModel(key=key, count=count)
            for key, count in sorted(top_event_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
        ],
    )


def get_wiki_conversation_metrics_series(
    db: Session,
    *,
    dimension_type: str = "global",
    dimension_key: str | None = None,
    days: int = 30,
    granularity: str = "day",
) -> list[WikiConversationMetricsSeriesPointReadModel]:
    refresh_recent_wiki_conversation_daily_metrics(db, days=days)
    end_date = date.today()
    start_date = end_date - timedelta(days=max(days - 1, 0))
    rows = db.scalars(
        select(WikiConversationDailyMetric)
        .where(
            WikiConversationDailyMetric.metric_date >= start_date,
            WikiConversationDailyMetric.metric_date <= end_date,
            WikiConversationDailyMetric.dimension_type == dimension_type,
            WikiConversationDailyMetric.dimension_key == (dimension_key if dimension_type != "global" else None),
        )
        .order_by(WikiConversationDailyMetric.metric_date.asc())
    ).all()
    if granularity == "day":
        return [
            WikiConversationMetricsSeriesPointReadModel(
                metric_date=row.metric_date.isoformat(),
                period_label=row.metric_date.isoformat(),
                created_count=row.created_count,
                closed_count=row.closed_count,
                open_count=row.open_count,
                in_review_count=row.in_review_count,
                waiting_user_count=row.waiting_user_count,
                resolved_count=row.resolved_count,
                high_priority_count=row.high_priority_count,
                needs_review_count=row.needs_review_count,
                denied_threads_count=row.denied_threads_count,
                fallback_threads_count=row.fallback_threads_count,
                no_match_threads_count=row.no_match_threads_count,
                review_entered_count=row.review_entered_count,
                reassigned_count=row.reassigned_count,
                reopened_count=row.reopened_count,
                avg_time_to_review_hours=row.avg_time_to_review_hours,
                avg_time_to_resolve_hours=row.avg_time_to_resolve_hours,
                avg_open_to_review_hours=row.avg_open_to_review_hours,
                avg_review_to_resolve_hours=row.avg_review_to_resolve_hours,
                avg_waiting_user_hours=row.avg_waiting_user_hours,
            )
            for row in rows
        ]

    period_type = "week" if granularity == "week" else "month"
    grouped: dict[date, dict[str, int]] = defaultdict(
        lambda: {
            "created_count": 0,
            "closed_count": 0,
            "open_count": 0,
            "in_review_count": 0,
            "waiting_user_count": 0,
            "resolved_count": 0,
            "high_priority_count": 0,
            "needs_review_count": 0,
            "denied_threads_count": 0,
            "fallback_threads_count": 0,
            "no_match_threads_count": 0,
            "review_entered_count": 0,
            "reassigned_count": 0,
            "reopened_count": 0,
            "review_total": 0,
            "review_samples": 0,
            "resolve_total": 0,
            "resolve_samples": 0,
            "open_review_total": 0,
            "open_review_samples": 0,
            "review_resolve_total": 0,
            "review_resolve_samples": 0,
            "waiting_total": 0,
            "waiting_samples": 0,
        }
    )
    for row in rows:
        period_start = _start_of_week(row.metric_date) if period_type == "week" else _start_of_month(row.metric_date)
        bucket = grouped[period_start]
        bucket["created_count"] += row.created_count
        bucket["closed_count"] += row.closed_count
        bucket["open_count"] = row.open_count
        bucket["in_review_count"] = row.in_review_count
        bucket["waiting_user_count"] = row.waiting_user_count
        bucket["resolved_count"] = row.resolved_count
        bucket["high_priority_count"] = row.high_priority_count
        bucket["needs_review_count"] = row.needs_review_count
        bucket["denied_threads_count"] = row.denied_threads_count
        bucket["fallback_threads_count"] = row.fallback_threads_count
        bucket["no_match_threads_count"] = row.no_match_threads_count
        bucket["review_entered_count"] += row.review_entered_count
        bucket["reassigned_count"] += row.reassigned_count
        bucket["reopened_count"] += row.reopened_count
        if row.avg_time_to_review_hours:
            bucket["review_total"] += row.avg_time_to_review_hours
            bucket["review_samples"] += 1
        if row.avg_time_to_resolve_hours:
            bucket["resolve_total"] += row.avg_time_to_resolve_hours
            bucket["resolve_samples"] += 1
        if row.avg_open_to_review_hours:
            bucket["open_review_total"] += row.avg_open_to_review_hours
            bucket["open_review_samples"] += 1
        if row.avg_review_to_resolve_hours:
            bucket["review_resolve_total"] += row.avg_review_to_resolve_hours
            bucket["review_resolve_samples"] += 1
        if row.avg_waiting_user_hours:
            bucket["waiting_total"] += row.avg_waiting_user_hours
            bucket["waiting_samples"] += 1
    return [
        WikiConversationMetricsSeriesPointReadModel(
            metric_date=period_start.isoformat(),
            period_label=_period_label(period_type, period_start),
            created_count=bucket["created_count"],
            closed_count=bucket["closed_count"],
            open_count=bucket["open_count"],
            in_review_count=bucket["in_review_count"],
            waiting_user_count=bucket["waiting_user_count"],
            resolved_count=bucket["resolved_count"],
            high_priority_count=bucket["high_priority_count"],
            needs_review_count=bucket["needs_review_count"],
            denied_threads_count=bucket["denied_threads_count"],
            fallback_threads_count=bucket["fallback_threads_count"],
            no_match_threads_count=bucket["no_match_threads_count"],
            review_entered_count=bucket["review_entered_count"],
            reassigned_count=bucket["reassigned_count"],
            reopened_count=bucket["reopened_count"],
            avg_time_to_review_hours=int(round(bucket["review_total"] / bucket["review_samples"])) if bucket["review_samples"] else 0,
            avg_time_to_resolve_hours=int(round(bucket["resolve_total"] / bucket["resolve_samples"])) if bucket["resolve_samples"] else 0,
            avg_open_to_review_hours=int(round(bucket["open_review_total"] / bucket["open_review_samples"])) if bucket["open_review_samples"] else 0,
            avg_review_to_resolve_hours=int(round(bucket["review_resolve_total"] / bucket["review_resolve_samples"])) if bucket["review_resolve_samples"] else 0,
            avg_waiting_user_hours=int(round(bucket["waiting_total"] / bucket["waiting_samples"])) if bucket["waiting_samples"] else 0,
        )
        for period_start, bucket in sorted(grouped.items(), key=lambda item: item[0])
    ]
