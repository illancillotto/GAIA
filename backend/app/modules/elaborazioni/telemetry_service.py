from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from math import ceil
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoCredential, CatastoDocument, CatastoVisuraRequest
from app.modules.elaborazioni.telemetry_models import SisterPortalEvent
from app.modules.elaborazioni.telemetry_schemas import (
    SisterPortalAlert,
    SisterPortalCredentialMetric,
    SisterPortalDownloadTotals,
    SisterPortalErrorMetric,
    SisterPortalEventListResponse,
    SisterPortalHealthResponse,
    SisterPortalRecentEvent,
    SisterPortalStepMetric,
    SisterPortalTimelinePoint,
    SisterPortalTotals,
)

SUCCESS_OUTCOMES = {"success", "completed"}
ERROR_OUTCOMES = {"error", "failed", "timeout"}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _average(values: list[int]) -> int | None:
    return round(sum(values) / len(values)) if values else None


def _percentile_95(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(ceil(len(ordered) * 0.95) - 1, 0)]


def _success_rate(successes: int, errors: int) -> float:
    terminal = successes + errors
    return round(successes / terminal * 100, 1) if terminal else 0.0


def _to_recent(
    event: SisterPortalEvent,
    credential_label: str | None = None,
) -> SisterPortalRecentEvent:
    return SisterPortalRecentEvent(
        id=event.id,
        occurred_at=_as_utc(event.occurred_at),
        event_type=event.event_type,
        step=event.step,
        outcome=event.outcome,
        severity=event.severity,
        duration_ms=event.duration_ms,
        http_status=event.http_status,
        endpoint=event.endpoint,
        attempt=event.attempt,
        cooldown_seconds=event.cooldown_seconds,
        credential_id=event.credential_id,
        credential_label=credential_label,
        batch_id=event.batch_id,
        request_id=event.request_id,
    )


def _timeline(
    events: list[SisterPortalEvent], window_hours: int
) -> list[SisterPortalTimelinePoint]:
    grouped: dict[datetime, list[SisterPortalEvent]] = defaultdict(list)
    for event in events:
        occurred_at = _as_utc(event.occurred_at)
        bucket = (
            occurred_at.replace(minute=0, second=0, microsecond=0)
            if window_hours <= 48
            else occurred_at.replace(hour=0, minute=0, second=0, microsecond=0)
        )
        grouped[bucket].append(event)

    return [
        SisterPortalTimelinePoint(
            bucket=bucket,
            events=len(items),
            successes=sum(item.outcome in SUCCESS_OUTCOMES for item in items),
            errors=sum(item.outcome in ERROR_OUTCOMES for item in items),
            average_duration_ms=_average(
                [item.duration_ms for item in items if item.duration_ms is not None]
            ),
        )
        for bucket, items in sorted(grouped.items())
    ]


def _step_metrics(events: list[SisterPortalEvent]) -> list[SisterPortalStepMetric]:
    grouped: dict[str, list[SisterPortalEvent]] = defaultdict(list)
    for event in events:
        grouped[event.step].append(event)
    metrics = [
        SisterPortalStepMetric(
            step=step,
            events=len(items),
            successes=sum(item.outcome in SUCCESS_OUTCOMES for item in items),
            errors=sum(item.outcome in ERROR_OUTCOMES for item in items),
            average_duration_ms=_average(
                [item.duration_ms for item in items if item.duration_ms is not None]
            ),
            p95_duration_ms=_percentile_95(
                [item.duration_ms for item in items if item.duration_ms is not None]
            ),
        )
        for step, items in grouped.items()
    ]
    return sorted(metrics, key=lambda item: (-item.errors, -(item.p95_duration_ms or 0), item.step))


def _error_metrics(events: list[SisterPortalEvent]) -> list[SisterPortalErrorMetric]:
    grouped: dict[tuple[str, str, int | None], list[SisterPortalEvent]] = defaultdict(list)
    for event in events:
        if event.outcome in ERROR_OUTCOMES:
            grouped[(event.event_type, event.step, event.http_status)].append(event)
    metrics = [
        SisterPortalErrorMetric(
            event_type=key[0],
            step=key[1],
            http_status=key[2],
            count=len(items),
            last_seen_at=max(_as_utc(item.occurred_at) for item in items),
        )
        for key, items in grouped.items()
    ]
    return sorted(metrics, key=lambda item: (-item.count, item.event_type))[:20]


def _credential_labels(
    db: Session,
    events: list[SisterPortalEvent],
) -> dict[UUID, str]:
    credential_ids = {event.credential_id for event in events if event.credential_id is not None}
    return (
        dict(
            db.execute(
                select(CatastoCredential.id, CatastoCredential.label).where(
                    CatastoCredential.id.in_(credential_ids)
                )
            ).all()
        )
        if credential_ids
        else {}
    )


def _credential_metrics(
    events: list[SisterPortalEvent],
    labels: dict[UUID, str],
    downloads: dict[UUID | None, int],
) -> list[SisterPortalCredentialMetric]:
    grouped: dict[UUID | None, list[SisterPortalEvent]] = defaultdict(list)
    for event in events:
        grouped[event.credential_id].append(event)
    metrics = []
    for credential_id, items in grouped.items():
        successes = sum(item.outcome in SUCCESS_OUTCOMES for item in items)
        errors = sum(item.outcome in ERROR_OUTCOMES for item in items)
        metrics.append(
            SisterPortalCredentialMetric(
                credential_id=credential_id,
                label=labels.get(credential_id, "Sessione non associata"),
                events=len(items),
                successes=successes,
                errors=errors,
                downloads=downloads.get(credential_id, 0) if credential_id is not None else 0,
                success_rate=_success_rate(successes, errors),
                last_seen_at=max(_as_utc(item.occurred_at) for item in items),
            )
        )
    return sorted(metrics, key=lambda item: (-item.errors, item.label))


def _download_metrics(
    db: Session,
    *,
    user_id: int,
    since: datetime,
) -> tuple[SisterPortalDownloadTotals, dict[UUID | None, int]]:
    rows = db.execute(
        select(
            CatastoDocument.tipo_visura,
            CatastoDocument.content_request_type,
            CatastoDocument.request_type,
            CatastoVisuraRequest.sister_credential_id,
            func.count(CatastoDocument.id),
        )
        .outerjoin(
            CatastoVisuraRequest,
            CatastoVisuraRequest.id == CatastoDocument.request_id,
        )
        .where(
            CatastoDocument.user_id == user_id,
            CatastoDocument.created_at >= since,
        )
        .group_by(
            CatastoDocument.tipo_visura,
            CatastoDocument.content_request_type,
            CatastoDocument.request_type,
            CatastoVisuraRequest.sister_credential_id,
        )
    ).all()
    by_visura_type: dict[str, int] = defaultdict(int)
    by_request_type: dict[str, int] = defaultdict(int)
    by_credential: dict[UUID | None, int] = defaultdict(int)
    for visura_type, observed_request_type, requested_type, credential_id, count in rows:
        normalized_visura_type = (visura_type or "").strip() or "Non classificata"
        by_visura_type[normalized_visura_type] += count
        request_type = observed_request_type or requested_type or "NON_CLASSIFICATA"
        by_request_type[request_type.strip().upper()] += count
        by_credential[credential_id] += count
    return (
        SisterPortalDownloadTotals(
            total=sum(by_visura_type.values()),
            by_visura_type=dict(by_visura_type),
            by_request_type=dict(by_request_type),
        ),
        dict(by_credential),
    )


def _alerts(
    events: list[SisterPortalEvent],
    totals: SisterPortalTotals,
    generated_at: datetime,
) -> list[SisterPortalAlert]:
    candidates = (
        _server_error_alert(events),
        _error_rate_alert(events, totals, generated_at),
        _latency_alert(totals, generated_at),
        _cooldown_alert(events),
    )
    return [alert for alert in candidates if alert is not None]


def _server_error_alert(events: list[SisterPortalEvent]) -> SisterPortalAlert | None:
    server_errors = [
        event for event in events if event.http_status is not None and event.http_status >= 500
    ]
    if len(server_errors) < 3:
        return None
    return SisterPortalAlert(
        id="sister-http-5xx",
        severity="critical",
        title="Errori server SISTER ripetuti",
        detail=f"{len(server_errors)} risposte HTTP 5xx nella finestra selezionata.",
        active_since=min(_as_utc(event.occurred_at) for event in server_errors),
    )


def _error_rate_alert(
    events: list[SisterPortalEvent],
    totals: SisterPortalTotals,
    generated_at: datetime,
) -> SisterPortalAlert | None:
    terminal = totals.successes + totals.errors
    if not terminal or totals.errors / terminal < 0.2:
        return None
    active_since = min(
        (_as_utc(event.occurred_at) for event in events if event.outcome in ERROR_OUTCOMES),
        default=generated_at,
    )
    return SisterPortalAlert(
        id="sister-error-rate",
        severity="critical",
        title="Tasso di errore elevato",
        detail=f"{round(totals.errors / terminal * 100)}% delle esecuzioni terminali non e riuscito.",
        active_since=active_since,
    )


def _latency_alert(
    totals: SisterPortalTotals,
    generated_at: datetime,
) -> SisterPortalAlert | None:
    if totals.p95_duration_ms is None or totals.p95_duration_ms < 120_000:
        return None
    return SisterPortalAlert(
        id="sister-high-latency",
        severity="warning",
        title="Portale SISTER lento",
        detail=f"Il P95 dei tempi e {round(totals.p95_duration_ms / 1000)} secondi.",
        active_since=generated_at,
    )


def _cooldown_alert(events: list[SisterPortalEvent]) -> SisterPortalAlert | None:
    cooldowns = [event for event in events if event.cooldown_seconds]
    if not cooldowns:
        return None
    return SisterPortalAlert(
        id="sister-cooldown-active",
        severity="warning",
        title="Protezione dinamica attivata",
        detail=f"{len(cooldowns)} eventi di cooldown o pausa globale nella finestra.",
        active_since=min(_as_utc(event.occurred_at) for event in cooldowns),
    )


def _status(events: list[SisterPortalEvent], alerts: list[SisterPortalAlert]) -> str:
    if not events:
        return "unknown"
    if any(alert.severity == "critical" for alert in alerts):
        return "critical"
    if alerts:
        return "degraded"
    return "healthy"


def get_portal_health(
    db: Session,
    *,
    user_id: int,
    window_hours: int,
    now: datetime | None = None,
) -> SisterPortalHealthResponse:
    generated_at = _as_utc(now or datetime.now(UTC))
    since = generated_at - timedelta(hours=window_hours)
    events = list(
        db.scalars(
            select(SisterPortalEvent)
            .where(
                SisterPortalEvent.user_id == user_id,
                SisterPortalEvent.occurred_at >= since,
            )
            .order_by(SisterPortalEvent.occurred_at.desc())
        ).all()
    )
    credential_labels = _credential_labels(db, events)
    downloads, credential_downloads = _download_metrics(db, user_id=user_id, since=since)
    successes = sum(event.outcome in SUCCESS_OUTCOMES for event in events)
    errors = sum(event.outcome in ERROR_OUTCOMES for event in events)
    durations = [event.duration_ms for event in events if event.duration_ms is not None]
    totals = SisterPortalTotals(
        events=len(events),
        executions=len({event.run_id for event in events if event.run_id is not None}),
        successes=successes,
        errors=errors,
        retries=sum(event.event_type == "retry" for event in events),
        cooldowns=sum(event.event_type in {"cooldown", "global_pause"} for event in events),
        success_rate=_success_rate(successes, errors),
        average_duration_ms=_average(durations),
        p95_duration_ms=_percentile_95(durations),
    )
    alerts = _alerts(events, totals, generated_at)
    return SisterPortalHealthResponse(
        generated_at=generated_at,
        window_hours=window_hours,
        status=_status(events, alerts),
        totals=totals,
        downloads=downloads,
        timeline=_timeline(events, window_hours),
        steps=_step_metrics(events),
        errors=_error_metrics(events),
        credentials=_credential_metrics(events, credential_labels, credential_downloads),
        alerts=alerts,
        recent_events=[
            _to_recent(event, credential_labels.get(event.credential_id)) for event in events[:50]
        ],
    )


def list_portal_events(
    db: Session,
    *,
    user_id: int,
    window_hours: int,
    limit: int,
) -> SisterPortalEventListResponse:
    since = datetime.now(UTC) - timedelta(hours=window_hours)
    filters = (
        SisterPortalEvent.user_id == user_id,
        SisterPortalEvent.occurred_at >= since,
    )
    total = db.scalar(select(func.count(SisterPortalEvent.id)).where(*filters)) or 0
    events = db.scalars(
        select(SisterPortalEvent)
        .where(*filters)
        .order_by(SisterPortalEvent.occurred_at.desc())
        .limit(limit)
    ).all()
    credential_labels = _credential_labels(db, list(events))
    return SisterPortalEventListResponse(
        total=total,
        items=[_to_recent(event, credential_labels.get(event.credential_id)) for event in events],
    )


__all__ = ["get_portal_health", "list_portal_events"]
