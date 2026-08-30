from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.catasto import (
    CatastoBatch,
    CatastoBatchKind,
    CatastoBatchStatus,
    CatastoDocument,
    CatastoVisuraRequest,
    CatastoVisuraRequestStatus,
)
from app.schemas.catasto import (
    CatastoAutoSyncDashboardResponse,
    CatastoAutoSyncDashboardSummaryResponse,
    CatastoAutoSyncEventResponse,
    CatastoAutoSyncHourlyResponse,
    CatastoBatchResponse,
)

PERIOD_HOURS = 24
RECENT_BATCH_LIMIT = 8
RECENT_EVENT_LIMIT = 20
AUTOSYNC_BATCH_KINDS = (
    CatastoBatchKind.RUOLO_AUTOSYNC.value,
    CatastoBatchKind.PERPETUAL_SYNC.value,
)
ACTIVE_BATCH_STATUSES = (
    CatastoBatchStatus.PENDING.value,
    CatastoBatchStatus.PROCESSING.value,
)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _batch_summary(db: Session, user_id: int) -> tuple[dict[str, int], int | None, datetime | None]:
    totals = db.execute(
        select(
            func.count(CatastoBatch.id),
            func.sum(case((CatastoBatch.status.in_(ACTIVE_BATCH_STATUSES), 1), else_=0)),
            func.sum(case((CatastoBatch.status == CatastoBatchStatus.COMPLETED.value, 1), else_=0)),
            func.sum(case((CatastoBatch.status == CatastoBatchStatus.FAILED.value, 1), else_=0)),
            func.max(func.coalesce(CatastoBatch.completed_at, CatastoBatch.started_at, CatastoBatch.created_at)),
        ).where(
            CatastoBatch.user_id == user_id,
            CatastoBatch.batch_kind.in_(AUTOSYNC_BATCH_KINDS),
        )
    ).one()
    durations = db.execute(
        select(CatastoBatch.started_at, CatastoBatch.completed_at).where(
            CatastoBatch.user_id == user_id,
            CatastoBatch.batch_kind.in_(AUTOSYNC_BATCH_KINDS),
            CatastoBatch.started_at.is_not(None),
            CatastoBatch.completed_at.is_not(None),
        )
    ).all()
    duration_values = [int((_as_utc(end) - _as_utc(start)).total_seconds()) for start, end in durations]
    counts = {
        "batches_total": int(totals[0] or 0),
        "batches_active": int(totals[1] or 0),
        "batches_completed": int(totals[2] or 0),
        "batches_failed": int(totals[3] or 0),
    }
    average_duration = round(sum(duration_values) / len(duration_values)) if duration_values else None
    return counts, average_duration, totals[4]


def _request_summary(db: Session, user_id: int) -> dict[str, int]:
    totals = db.execute(
        select(
            func.count(CatastoVisuraRequest.id),
            func.sum(case((CatastoVisuraRequest.status == CatastoVisuraRequestStatus.COMPLETED.value, 1), else_=0)),
            func.sum(case((CatastoVisuraRequest.status == CatastoVisuraRequestStatus.FAILED.value, 1), else_=0)),
            func.sum(case((CatastoVisuraRequest.last_error_code.is_not(None), 1), else_=0)),
        )
        .join(CatastoBatch, CatastoBatch.id == CatastoVisuraRequest.batch_id)
        .where(
            CatastoBatch.user_id == user_id,
            CatastoBatch.batch_kind.in_(AUTOSYNC_BATCH_KINDS),
        )
    ).one()
    document_count = db.scalar(
        select(func.count(CatastoDocument.id))
        .join(CatastoVisuraRequest, CatastoVisuraRequest.id == CatastoDocument.request_id)
        .join(CatastoBatch, CatastoBatch.id == CatastoVisuraRequest.batch_id)
        .where(
            CatastoBatch.user_id == user_id,
            CatastoBatch.batch_kind.in_(AUTOSYNC_BATCH_KINDS),
        )
    )
    return {
        "requests_total": int(totals[0] or 0),
        "requests_completed": int(totals[1] or 0),
        "requests_failed": int(totals[2] or 0),
        "requests_blocked": int(totals[3] or 0),
        "documents_downloaded": int(document_count or 0),
    }


def _recent_requests(db: Session, user_id: int, cutoff: datetime) -> list[CatastoVisuraRequest]:
    return list(
        db.scalars(
            select(CatastoVisuraRequest)
            .join(CatastoBatch, CatastoBatch.id == CatastoVisuraRequest.batch_id)
            .where(
                CatastoBatch.user_id == user_id,
                CatastoBatch.batch_kind.in_(AUTOSYNC_BATCH_KINDS),
                func.coalesce(CatastoVisuraRequest.processed_at, CatastoVisuraRequest.created_at) >= cutoff,
            )
            .order_by(func.coalesce(CatastoVisuraRequest.processed_at, CatastoVisuraRequest.created_at))
        ).all()
    )


def _hourly_rows(
    db: Session,
    requests: list[CatastoVisuraRequest],
    user_id: int,
    cutoff: datetime,
) -> list[CatastoAutoSyncHourlyResponse]:
    document_request_ids = set(
        db.scalars(
            select(CatastoDocument.request_id)
            .join(CatastoVisuraRequest, CatastoVisuraRequest.id == CatastoDocument.request_id)
            .join(CatastoBatch, CatastoBatch.id == CatastoVisuraRequest.batch_id)
            .where(
                CatastoBatch.user_id == user_id,
                CatastoBatch.batch_kind.in_(AUTOSYNC_BATCH_KINDS),
                CatastoDocument.created_at >= cutoff,
            )
        ).all()
    )
    buckets: dict[datetime, dict[str, int]] = {}
    for request in requests:
        timestamp = _as_utc(request.processed_at or request.created_at)
        hour = timestamp.replace(minute=0, second=0, microsecond=0)
        bucket = buckets.setdefault(hour, {"completed": 0, "failed": 0, "documents_downloaded": 0})
        if request.status == CatastoVisuraRequestStatus.COMPLETED.value:
            bucket["completed"] += 1
        if request.status == CatastoVisuraRequestStatus.FAILED.value:
            bucket["failed"] += 1
        if request.id in document_request_ids:
            bucket["documents_downloaded"] += 1
    return [CatastoAutoSyncHourlyResponse(hour=hour, **buckets[hour]) for hour in sorted(buckets)]


def _event_for_request(request: CatastoVisuraRequest) -> CatastoAutoSyncEventResponse:
    is_error = request.status == CatastoVisuraRequestStatus.FAILED.value or request.last_error_code is not None
    title = "Visura bloccata" if is_error else "Visura completata"
    return CatastoAutoSyncEventResponse(
        timestamp=request.processed_at or request.created_at,
        level="error" if is_error else "info",
        title=title,
        detail=request.error_message or request.current_operation,
        batch_id=request.batch_id,
        request_id=request.id,
    )


def _recent_batches(db: Session, user_id: int) -> list[CatastoBatchResponse]:
    rows = db.scalars(
        select(CatastoBatch)
        .where(
            CatastoBatch.user_id == user_id,
            CatastoBatch.batch_kind.in_(AUTOSYNC_BATCH_KINDS),
        )
        .order_by(CatastoBatch.created_at.desc())
        .limit(RECENT_BATCH_LIMIT)
    ).all()
    return [CatastoBatchResponse.model_validate(row) for row in rows]


def build_autosync_dashboard(db: Session, user_id: int) -> CatastoAutoSyncDashboardResponse:
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=PERIOD_HOURS)
    batch_counts, average_duration, batch_last_activity = _batch_summary(db, user_id)
    request_counts = _request_summary(db, user_id)
    requests = _recent_requests(db, user_id, cutoff)
    hourly = _hourly_rows(db, requests, user_id, cutoff)
    completed = sum(row.completed for row in hourly)
    observation_hours = 1.0
    if requests:
        timestamps = [_as_utc(row.processed_at or row.created_at) for row in requests]
        observation_hours = max(1.0, (max(timestamps) - min(timestamps)).total_seconds() / 3600)
    last_request_activity = max(
        (_as_utc(row.processed_at or row.created_at) for row in requests),
        default=None,
    )
    normalized_batch_activity = _as_utc(batch_last_activity) if batch_last_activity else None
    last_activity = max(
        (value for value in (normalized_batch_activity, last_request_activity) if value is not None),
        default=None,
    )
    events = [_event_for_request(row) for row in reversed(requests[-RECENT_EVENT_LIMIT:])]
    summary = CatastoAutoSyncDashboardSummaryResponse(
        **batch_counts,
        **request_counts,
        completed_per_hour=round(completed / observation_hours, 1),
        average_batch_duration_seconds=average_duration,
        last_activity_at=last_activity,
    )
    return CatastoAutoSyncDashboardResponse(
        summary=summary,
        hourly=hourly,
        recent_batches=_recent_batches(db, user_id),
        events=events,
    )
