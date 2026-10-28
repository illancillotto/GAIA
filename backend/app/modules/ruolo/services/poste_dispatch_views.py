"""Read models of the Posta Online outbox for the operator page."""

from collections import defaultdict
from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.ruolo.poste_dispatch_models import (
    PosteDispatchEvent,
    PosteDispatchItem,
    PosteDispatchLot,
)
from app.modules.ruolo.poste_dispatch_schemas import (
    PosteDispatchEventOut,
    PosteDispatchItemOut,
    PosteDispatchJobOut,
    PosteDispatchLotDetail,
    PosteDispatchLotSummary,
)
from app.modules.ruolo.services.poste_dispatch import active_job
from app.modules.ruolo.services.poste_dispatch_state import get_lot

DRAFT_LIFETIME = timedelta(days=7)
_LIVE_DRAFTS = ("draft_created", "draft_priced")


def _counts(db: Session, lot_ids: list[UUID]) -> tuple[dict, dict]:
    counts: dict[UUID, dict[str, int]] = defaultdict(dict)
    prices: dict[UUID, float] = defaultdict(float)
    rows = db.execute(
        select(
            PosteDispatchItem.lot_id,
            PosteDispatchItem.status,
            func.count(),
            func.coalesce(func.sum(PosteDispatchItem.price_amount), 0),
        )
        .where(PosteDispatchItem.lot_id.in_(lot_ids))
        .group_by(PosteDispatchItem.lot_id, PosteDispatchItem.status)
    )
    for lot_id, status, count, price in rows:
        counts[lot_id][status] = count
        if status in _LIVE_DRAFTS:
            prices[lot_id] += float(price)
    return counts, prices


def _summary(lot: PosteDispatchLot, counts: dict, prices: dict) -> dict:
    return {
        "id": lot.id,
        "title": lot.title,
        "status": lot.status,
        "created_by": lot.created_by,
        "created_at": lot.created_at,
        "counts": counts.get(lot.id, {}),
        "priced_total": round(prices.get(lot.id, 0.0), 2),
    }


def list_lots(
    db: Session, *, page: int, page_size: int
) -> tuple[list[PosteDispatchLotSummary], int]:
    total = db.scalar(select(func.count()).select_from(PosteDispatchLot)) or 0
    lots = list(
        db.scalars(
            select(PosteDispatchLot)
            .order_by(PosteDispatchLot.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    counts, prices = _counts(db, [lot.id for lot in lots])
    return [PosteDispatchLotSummary(**_summary(lot, counts, prices)) for lot in lots], total


def lot_detail(db: Session, lot_id: UUID) -> PosteDispatchLotDetail:
    lot = get_lot(db, lot_id)
    items = list(
        db.scalars(
            select(PosteDispatchItem)
            .where(PosteDispatchItem.lot_id == lot_id)
            .order_by(PosteDispatchItem.created_at, PosteDispatchItem.shipment_name)
        )
    )
    events = db.scalars(
        select(PosteDispatchEvent)
        .where(PosteDispatchEvent.lot_id == lot_id)
        .order_by(PosteDispatchEvent.created_at.desc())
        .limit(30)
    )
    created = [
        item.draft_created_at
        for item in items
        if item.status in _LIVE_DRAFTS and item.draft_created_at
    ]
    job = active_job(db, lot_id)
    counts, prices = _counts(db, [lot_id])
    return PosteDispatchLotDetail(
        **_summary(lot, counts, prices),
        postal_options=lot.postal_options,
        portal_snapshot=lot.portal_snapshot,
        draft_expires_at=min(created) + DRAFT_LIFETIME if created else None,
        active_job=PosteDispatchJobOut.model_validate(job, from_attributes=True) if job else None,
        items=[PosteDispatchItemOut.model_validate(item) for item in items],
        events=[PosteDispatchEventOut.model_validate(event) for event in events],
    )


def item_document(db: Session, lot_id: UUID, item_id: UUID) -> bytes | None:
    return db.scalar(
        select(PosteDispatchItem.artifact).where(
            PosteDispatchItem.id == item_id, PosteDispatchItem.lot_id == lot_id
        )
    )
