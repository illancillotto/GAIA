"""Bounded refill of a running campaign without replacing remote requests."""

from collections.abc import Iterable
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoBatch, CatastoPerpetualSyncItem, CatastoVisuraRequest
from app.services.elaborazioni_batches import ValidatedVisuraRow

OPEN_STATUSES = ("pending", "processing", "awaiting_captcha")
MAX_OPEN_REQUESTS = 100
UTC = timezone.utc  # noqa: UP017 - Shared worker imports must support Python 3.10.


def _validated_row(index: int, item: CatastoPerpetualSyncItem) -> ValidatedVisuraRow:
    return ValidatedVisuraRow(
        row_index=index,
        search_mode=item.search_mode,
        comune=item.comune,
        comune_codice=item.comune_codice,
        catasto=item.catasto,
        sezione=item.sezione,
        foglio=item.foglio,
        particella=item.particella,
        subalterno=item.subalterno,
        tipo_visura=item.tipo_visura,
        purpose="perpetual_sync",
        target_ruolo_particella_id=item.ruolo_particella_id,
        subject_kind=item.subject_kind,
        subject_id=item.subject_identifier,
        request_type=item.request_type,
        intestazione=item.intestazione,
    )


def _link_items(
    items: Iterable[CatastoPerpetualSyncItem],
    batch: CatastoBatch,
    requests: list[CatastoVisuraRequest],
    now: datetime,
) -> None:
    for item, request in zip(items, requests, strict=True):
        item.status = "queued"
        item.linked_batch_id = batch.id
        item.linked_request_id = request.id
        item.last_enqueued_at = now
        item.retry_after = None
        item.last_error_message = None


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _is_deferred_recovery(request: CatastoVisuraRequest, now: datetime) -> bool:
    if not (
        request.status == "pending"
        and request.execution_token is None
        and request.sister_remote_state in {"submitted", "pending", "ready"}
        and request.sister_remote_request_id
        and request.sister_remote_request_url
        and request.sister_credential_id
        and request.sister_first_submitted_at
        and request.retry_not_before
    ):
        return False
    submitted = _utc(request.sister_first_submitted_at)
    retry = _utc(request.retry_not_before)
    return submitted <= now < submitted + timedelta(hours=24) and retry > now


def lock_refill_capacity(db: Session, batch: CatastoBatch, limit: int, now: datetime) -> int:
    if batch.status != "processing" or batch.completed_at is not None:
        return 0
    query = select(CatastoVisuraRequest).where(
        CatastoVisuraRequest.batch_id == batch.id,
        CatastoVisuraRequest.status.in_(OPEN_STATUSES),
    )
    count = db.scalar(select(func.count()).select_from(query.subquery()))
    requests = list(
        db.scalars(
            query.with_for_update(skip_locked=True).execution_options(populate_existing=True)
        )
    )
    # A locked/claimed row must not look like spare capacity to the planner.
    if not requests or len(requests) != count:
        return 0
    if not all(_is_deferred_recovery(request, now) for request in requests):
        return 0
    return max(0, min(max(limit, 1), MAX_OPEN_REQUESTS) - len(requests))


def append_validated_requests(
    db: Session, batch: CatastoBatch, rows: list
) -> list[CatastoVisuraRequest]:
    last_index = (
        db.scalar(
            select(func.max(CatastoVisuraRequest.row_index)).where(
                CatastoVisuraRequest.batch_id == batch.id,
            )
        )
        or 0
    )
    requests = []
    for offset, row in enumerate(rows, start=1):
        values = asdict(row)
        values["row_index"] = last_index + offset
        requests.append(CatastoVisuraRequest(batch_id=batch.id, user_id=batch.user_id, **values))
    db.add_all(requests)
    db.flush()
    batch.total_items = db.scalar(
        select(func.count(CatastoVisuraRequest.id)).where(
            CatastoVisuraRequest.batch_id == batch.id,
        )
    )
    return requests
