from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoBatch, CatastoCredential, CatastoVisuraRequest
from app.modules.elaborazioni.telemetry_models import SisterPortalEvent

TERMINAL_STATUSES = {"completed", "failed", "skipped", "not_found"}
BATCH_TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _round_rate(value: float) -> float:
    return round(value, 2)


def _load_execution_history(
    db: Session,
    batch_id: UUID,
) -> tuple[datetime | None, dict[UUID, int], dict[UUID, set[UUID]]]:
    event_rows = db.execute(
        select(
            SisterPortalEvent.credential_id,
            SisterPortalEvent.request_id,
            SisterPortalEvent.occurred_at,
        ).where(
            SisterPortalEvent.batch_id == batch_id,
            SisterPortalEvent.event_type == "execution_start",
        )
    ).all()

    execution_counts: dict[UUID, int] = defaultdict(int)
    request_ids_by_credential: dict[UUID, set[UUID]] = defaultdict(set)
    first_execution_at: datetime | None = None
    for credential_id, request_id, occurred_at in event_rows:
        event_at = _as_utc(occurred_at)
        if event_at is not None and (first_execution_at is None or event_at < first_execution_at):
            first_execution_at = event_at
        if credential_id is None:
            continue
        execution_counts[credential_id] += 1
        if request_id is not None:
            request_ids_by_credential[credential_id].add(request_id)

    return first_execution_at, execution_counts, request_ids_by_credential


def _build_credential_usage(
    db: Session,
    requests: list[CatastoVisuraRequest],
    execution_counts: dict[UUID, int],
    request_ids_by_credential: dict[UUID, set[UUID]],
) -> list[dict[str, object]]:
    for request in requests:
        if request.sister_credential_id is not None:
            request_ids_by_credential[request.sister_credential_id].add(request.id)

    credential_ids = set(request_ids_by_credential) | set(execution_counts)
    credentials = {
        credential.id: credential
        for credential in db.scalars(
            select(CatastoCredential).where(CatastoCredential.id.in_(credential_ids))
        ).all()
    } if credential_ids else {}

    credential_usage = []
    for credential_id in credential_ids:
        credential = credentials.get(credential_id)
        credential_usage.append(
            {
                "credential_id": credential_id,
                "label": credential.label if credential is not None else "Credenziale rimossa",
                "sister_username": credential.sister_username if credential is not None else None,
                "request_count": len(request_ids_by_credential[credential_id]),
                "execution_count": max(
                    execution_counts[credential_id],
                    len(request_ids_by_credential[credential_id]),
                ),
            }
        )
    credential_usage.sort(key=lambda item: (str(item["label"]).casefold(), str(item["credential_id"])))
    return credential_usage


def _resolve_duration_seconds(
    batch: CatastoBatch,
    first_execution_at: datetime | None,
    now: datetime | None,
) -> int:
    started_at = _as_utc(batch.started_at)
    if first_execution_at is not None and (started_at is None or first_execution_at < started_at):
        started_at = first_execution_at
    if started_at is None:
        return 0
    completed_at = _as_utc(batch.completed_at) if batch.status in BATCH_TERMINAL_STATUSES else None
    end_at = completed_at or _as_utc(now) or datetime.now(timezone.utc)
    return max(round((end_at - started_at).total_seconds()), 0)


def _build_performance_metrics(
    requests: list[CatastoVisuraRequest],
    duration_seconds: int,
) -> dict[str, object]:
    processed_items = sum(request.status in TERMINAL_STATUSES for request in requests)
    completed_items = sum(request.status == "completed" for request in requests)
    total_items = len(requests)
    remaining_items = max(total_items - processed_items, 0)
    total_attempts = sum(max(request.attempts, 0) for request in requests)
    attempted_items = sum(request.attempts > 0 for request in requests)
    elapsed_hours = duration_seconds / 3600

    return {
        "duration_seconds": duration_seconds,
        "processed_items": processed_items,
        "remaining_items": remaining_items,
        "progress_percent": round(processed_items / total_items * 100, 1) if total_items else 0.0,
        "success_rate_percent": round(completed_items / processed_items * 100, 1) if processed_items else None,
        "completed_per_hour": _round_rate(completed_items / elapsed_hours) if elapsed_hours > 0 else None,
        "processed_per_hour": _round_rate(processed_items / elapsed_hours) if elapsed_hours > 0 else None,
        "estimated_remaining_seconds": (
            max(round(duration_seconds / processed_items * remaining_items), 0)
            if processed_items and remaining_items
            else 0 if remaining_items == 0
            else None
        ),
        "total_attempts": total_attempts,
        "average_attempts": round(total_attempts / attempted_items, 2) if attempted_items else 0.0,
    }


def build_batch_statistics(
    db: Session,
    batch: CatastoBatch,
    requests: Iterable[CatastoVisuraRequest],
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    request_items = list(requests)
    first_execution_at, execution_counts, request_ids_by_credential = _load_execution_history(db, batch.id)
    duration_seconds = _resolve_duration_seconds(batch, first_execution_at, now)
    statistics = _build_performance_metrics(request_items, duration_seconds)
    statistics["duration_seconds"] = duration_seconds
    statistics["credentials_used"] = _build_credential_usage(
        db,
        request_items,
        execution_counts,
        request_ids_by_credential,
    )
    return statistics


__all__ = ["build_batch_statistics"]
