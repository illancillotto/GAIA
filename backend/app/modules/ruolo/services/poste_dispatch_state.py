"""Shared lookups, transitions and audit trail of the Posta Online outbox."""

import hashlib
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo.poste_dispatch_models import (
    PosteDispatchEvent,
    PosteDispatchItem,
    PosteDispatchLot,
)

DRAFT_STATUSES = {
    "draft_creating",
    "draft_created",
    "draft_priced",
    "draft_uncertain",
    "cancel_requested",
}


class DispatchConflict(Exception):
    """The command does not fit the current state of the lot or item."""


class DispatchNotFound(Exception):
    """Lot or item does not exist."""


def get_lot(db: Session, lot_id: UUID, *, lock: bool = False) -> PosteDispatchLot:
    query = select(PosteDispatchLot).where(PosteDispatchLot.id == lot_id)
    lot = db.scalar(query.with_for_update() if lock else query)
    if lot is None:
        raise DispatchNotFound("Lotto Poste non trovato")
    return lot


def get_item(db: Session, lot_id: UUID, item_id: UUID) -> PosteDispatchItem:
    item = db.scalar(
        select(PosteDispatchItem)
        .where(PosteDispatchItem.id == item_id, PosteDispatchItem.lot_id == lot_id)
        .with_for_update()
    )
    if item is None:
        raise DispatchNotFound("Avviso del lotto Poste non trovato")
    return item


def record_event(db: Session, lot, item, kind: str, **values: Any) -> None:
    db.add(
        PosteDispatchEvent(
            lot_id=lot.id if lot is not None else item.lot_id,
            item_id=item.id if item is not None else None,
            kind=kind,
            **values,
        )
    )
    db.flush()


def transition(db: Session, item: PosteDispatchItem, status: str, kind: str, **values: Any) -> None:
    before = item.status
    item.status = status
    record_event(db, None, item, kind, from_status=before, to_status=status, **values)


def attach_artifact(item: PosteDispatchItem, artifact: bytes) -> None:
    item.artifact = artifact
    item.artifact_sha256 = hashlib.sha256(artifact).hexdigest()
    item.artifact_size = len(artifact)


def verified_artifact(item: PosteDispatchItem) -> bytes:
    """The bytes uploaded to Poste must be the snapshot taken when the lot was created."""
    if item.artifact is None or hashlib.sha256(item.artifact).hexdigest() != item.artifact_sha256:
        raise DispatchConflict("PDF del lotto mancante o alterato: bozza non creata")
    return item.artifact


def release(item: PosteDispatchItem, *, sent: bool = False) -> None:
    """Drop the PDF copy and keep its hash. A sent notice keeps its keys: no second shipment."""
    if not sent:
        item.active_key = None
        item.active_source_key = None
    item.artifact = None
