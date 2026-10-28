"""State changes reported by the Poste worker, one item per transaction.

The worker observes the portal; these functions only write what it saw. A
draft becomes "sent" only through the archive reconciliation.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem, PosteDispatchLot
from app.modules.ruolo.services.poste_dispatch_address import suggestion_label
from app.modules.ruolo.services.poste_dispatch_state import (
    DRAFT_STATUSES,
    get_lot,
    record_event,
    release,
    transition,
    verified_artifact,
)

DRAFT_READY_STATUSES = ("address_ok", "draft_error", "draft_missing")
PRICED_LABEL = "PREZZATO"


@dataclass(frozen=True)
class WorkItem:
    id: UUID
    shipment_name: str
    status: str
    recipient: dict[str, str]
    poste_address: dict[str, Any] | None
    poste_draft_id: str | None


@dataclass(frozen=True)
class DraftRow:
    """One row of the Poste "Verifica e invia" table."""

    draft_id: str
    name: str
    status: str
    price: Decimal | None


def lot_items(db: Session, lot_id: UUID, statuses: tuple[str, ...]) -> list[WorkItem]:
    get_lot(db, lot_id)
    rows = db.scalars(
        select(PosteDispatchItem)
        .where(PosteDispatchItem.lot_id == lot_id, PosteDispatchItem.status.in_(statuses))
        .order_by(PosteDispatchItem.created_at, PosteDispatchItem.shipment_name)
    )
    return [
        WorkItem(
            row.id,
            row.shipment_name,
            row.status,
            dict(row.recipient),
            row.poste_address,
            row.poste_draft_id,
        )
        for row in rows
    ]


def _item(db: Session, item_id: UUID) -> PosteDispatchItem:
    return db.scalar(
        select(PosteDispatchItem).where(PosteDispatchItem.id == item_id).with_for_update()
    )


def artifact_for_upload(db: Session, item_id: UUID) -> bytes:
    return verified_artifact(_item(db, item_id))


def record_address(
    db: Session,
    item_id: UUID,
    *,
    job_id: int,
    suggestion: dict[str, str] | None,
    reason: str,
    labels: list[str],
) -> None:
    item = _item(db, item_id)
    if item.status != "address_pending":
        return
    if suggestion is None:
        item.address_review = {"reason": reason, "suggestions": labels[:5]}
        transition(
            db,
            item,
            "address_review",
            "address_not_found",
            job_id=job_id,
            detail=item.address_review,
        )
        return
    item.poste_address = {"mode": "directory", **suggestion, "label": suggestion_label(suggestion)}
    item.address_review = None
    transition(
        db,
        item,
        "address_ok",
        "address_found",
        job_id=job_id,
        detail={"label": item.poste_address["label"]},
    )


def mark_draft_creating(db: Session, item_id: UUID, *, job_id: int) -> bool:
    """Persisted before CONTINUA: an interrupted submission is never retried blindly."""
    item = _item(db, item_id)
    if item.status not in DRAFT_READY_STATUSES:
        return False
    item.error_detail = None
    transition(db, item, "draft_creating", "draft_submitting", job_id=job_id)
    return True


def _apply_row(db: Session, item: PosteDispatchItem, row: DraftRow, job_id: int) -> None:
    item.poste_draft_id, item.poste_status, item.price_amount = row.draft_id, row.status, row.price
    item.draft_created_at = item.draft_created_at or datetime.now(UTC)
    if item.status == "cancel_requested":
        return
    status = "draft_priced" if row.status.upper() == PRICED_LABEL else "draft_created"
    if status != item.status:
        transition(
            db,
            item,
            status,
            "draft_observed",
            job_id=job_id,
            detail={"draft_id": row.draft_id, "poste_status": row.status},
        )


def record_draft_row(db: Session, item_id: UUID, *, job_id: int, row: DraftRow) -> None:
    _apply_row(db, _item(db, item_id), row, job_id)


def record_draft_failure(
    db: Session, item_id: UUID, *, job_id: int, submitted: bool, error: str
) -> None:
    item = _item(db, item_id)
    if item.status not in ("draft_creating", *DRAFT_READY_STATUSES):
        return
    item.error_detail = error[:1000]
    status = "draft_uncertain" if submitted else "draft_error"
    transition(db, item, status, "draft_failed", job_id=job_id, detail={"submitted": submitted})


def _foreign(rows: list[DraftRow], names: set[str]) -> list[dict[str, Any]]:
    return [
        {"draft_id": row.draft_id, "name": row.name, "status": row.status}
        for row in rows
        if row.name not in names
    ]


def apply_drafts_snapshot(
    db: Session, lot_id: UUID, *, job_id: int, rows: list[DraftRow]
) -> list[UUID]:
    """Update the lot from "Verifica e invia"; return the items no longer among the drafts."""
    lot: PosteDispatchLot = get_lot(db, lot_id, lock=True)
    by_name: dict[str, list[DraftRow]] = {}
    for row in rows:
        by_name.setdefault(row.name, []).append(row)
    items = db.scalars(
        select(PosteDispatchItem).where(
            PosteDispatchItem.lot_id == lot_id, PosteDispatchItem.status.in_(DRAFT_STATUSES)
        )
    ).all()
    missing, duplicates = [], []
    for item in items:
        matches = by_name.get(item.shipment_name, [])
        if len(matches) == 1:
            _apply_row(db, item, matches[0], job_id)
        elif matches:
            item.error_detail = (
                "Più bozze Poste con lo stesso nome: eliminare quelle in più prima di INVIA"
            )
            duplicates.append(item.shipment_name)
        else:
            missing.append(item.id)
    gaia_names = set(
        db.scalars(
            select(PosteDispatchItem.shipment_name).where(PosteDispatchItem.lot_id == lot_id)
        )
    )
    lot.portal_snapshot = {
        "checked_at": datetime.now(UTC).isoformat(),
        "job_id": job_id,
        "drafts_total": len(rows),
        "foreign_drafts": _foreign(rows, gaia_names),
        "duplicate_names": duplicates,
    }
    db.flush()
    return missing


def record_missing(db: Session, item_id: UUID, *, job_id: int) -> None:
    """Neither among the drafts nor in the archive: expired after 7 days or deleted on Poste."""
    item = _item(db, item_id)
    item.poste_draft_id, item.poste_status = None, None
    if item.status == "cancel_requested":
        release(item)
        transition(db, item, "cancelled", "draft_gone_cancelled", job_id=job_id)
        return
    transition(db, item, "draft_missing", "draft_missing", job_id=job_id)


def record_deleted(db: Session, item_id: UUID, *, job_id: int) -> None:
    item = _item(db, item_id)
    release(item)
    transition(
        db,
        item,
        "cancelled",
        "draft_deleted",
        job_id=job_id,
        detail={"draft_id": item.poste_draft_id},
    )


def record_anomaly(db: Session, item_id: UUID, *, job_id: int, message: str) -> None:
    """Keep the status: the operator must look at Poste before anything else happens."""
    item = _item(db, item_id)
    item.error_detail = message[:1000]
    record_event(db, None, item, "portal_anomaly", job_id=job_id, detail={"message": message})
