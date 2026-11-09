"""Atomic promotion of validated snapshots and the durable per-notice outbox."""

from datetime import datetime

from sqlalchemy import select

from app.modules.elaborazioni.capacitas.incremental.diff import make_plan, validate_collection
from app.modules.elaborazioni.capacitas.incremental.models import (
    IncrementalChange,
    IncrementalCycle,
    IncrementalHead,
)
from app.modules.elaborazioni.capacitas.incremental.normalize import SnapshotInvalid


def begin_cycle(db, config, now: datetime, revision: int = 0):
    cycle_id = f"{config.slot(now).strftime('%Y-%m-%dT%H')}-{revision:04d}"
    cycle = db.get(IncrementalCycle, cycle_id)
    if cycle is None:
        cycle = IncrementalCycle(id=cycle_id, acquired_at=now, mode=config.mode)
        db.add(cycle)
        db.commit()
    if cycle.mode != config.mode:
        raise SnapshotInvalid("cycle_mode_immutable")
    return cycle


def promote(db, cycle, config, now: datetime) -> None:
    if cycle.status == "validated":
        return
    head = db.get(IncrementalHead, 1, with_for_update=True)
    old = db.get(IncrementalCycle, head.cycle_id) if head.cycle_id else None
    if old and cycle.id <= old.id:
        raise SnapshotInvalid("obsolete_cycle")
    cycle.rows = validate_collection(cycle.artifacts, cycle.expected, old, config)
    changes, report = make_plan(cycle, old, head, config, now)
    db.add_all(changes)
    cycle.report = {**cycle.report, **report, "fallback": "legacy_autosync_unchanged"}
    cycle.status = "validated"
    head.cycle_id = cycle.id
    if head.full_audit_at is None:
        head.full_audit_at = now
    db.commit()  # Signatures, changes and pointer become visible together.


def pending_changes(db, limit: int):
    return db.scalars(
        select(IncrementalChange)
        .where(IncrementalChange.status == "pending")
        .order_by(IncrementalChange.cycle_id, IncrementalChange.notice_key)
        .limit(limit)
    ).all()
