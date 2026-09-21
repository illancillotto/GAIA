"""Manual Poste reconciliation. Originals and source identities are never merged."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo.notice_register_api_schemas import ReconciliationInput
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeDocument,
    NoticeEvidence,
    NoticeNotification,
    NoticePosition,
)
from app.modules.ruolo.notice_register_schemas import OperatorChange
from app.modules.ruolo.services.notice_register import (
    _audit,
    _document,
    _reset_notification,
    _reset_position_review,
    _scope_snapshot,
    _snapshot,
)


def _transfer_events(db: Session, source_id: UUID, target_id: UUID) -> dict:
    attempts = list(db.scalars(select(NoticeAttempt).where(NoticeAttempt.document_id == source_id)))
    evidence = list(
        db.scalars(select(NoticeEvidence).where(NoticeEvidence.document_id == source_id))
    )
    before = {
        "attempts": [_snapshot(a) for a in attempts],
        "evidence": [_snapshot(e) for e in evidence],
    }
    move_events(db, attempts, evidence, target_id)
    return before


def move_events(db: Session, attempts: list, evidence: list, target_id: UUID) -> None:
    links = {item.id: item.attempt_id for item in evidence}
    # Detach the composite FK before moving either side; no deferred constraints required.
    for item in evidence:
        item.attempt_id = None
    db.flush()
    for item in evidence:
        item.document_id = target_id
    db.flush()
    for attempt in attempts:
        attempt.document_id = target_id
    db.flush()
    for item in evidence:
        item.attempt_id = links[item.id]
    db.flush()


def reconcile_poste(
    db: Session, source_id: UUID, payload: ReconciliationInput, change: OperatorChange
) -> NoticeDocument:
    target_id = payload.target_document_id
    if source_id == target_id:
        raise ValueError("Scegliere un documento diverso dalla scheda Poste")
    target_change = change.model_copy(update={"expected_version": payload.target_version})
    changes = {source_id: change, target_id: target_change}
    # A deterministic lock order serializes two-source and opposite-direction requests.
    documents = {key: _document(db, key, changes[key]) for key in sorted(changes)}
    source, target = documents[source_id], documents[target_id]
    source_positions = list(
        db.scalars(select(NoticePosition).where(NoticePosition.document_id == source_id))
    )
    target_positions = list(
        db.scalars(select(NoticePosition).where(NoticePosition.document_id == target_id))
    )
    if source.source_system != "poste_db" or source_positions:
        raise ValueError("Riconciliazione consentita solo per schede Poste prive di posizioni")
    if target.source_system == "poste_db" or not target_positions:
        raise ValueError("La destinazione deve essere un documento non Poste con posizioni annuali")
    source_notification = db.get(NoticeNotification, source_id)
    before = {
        "source_id": str(source_id),
        "target_id": str(target_id),
        "source_notification": _snapshot(source_notification),
        "target_scope": [_scope_snapshot(db, p) for p in target_positions],
    }
    _reset_notification(source_notification)
    for position in target_positions:
        _reset_position_review(db, position)
    db.flush()
    before.update(_transfer_events(db, source_id, target_id))
    after = {
        "source_id": str(source_id),
        "target_id": str(target_id),
        "attempt_ids": [a["id"] for a in before["attempts"]],
        "evidence_ids": [e["id"] for e in before["evidence"]],
        "source_notification": _snapshot(source_notification),
        "target_scope": [_scope_snapshot(db, p) for p in target_positions],
    }
    source.reconciled_into_id = target_id
    event = {"action": "reconcile_poste", "before_json": before, "after_json": after}
    _audit(db, source, change, event)
    _audit(db, target, target_change, event)
    return target
