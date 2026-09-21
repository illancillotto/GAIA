"""Compensating reconciliation command, refusing dependent subsequent changes."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo.notice_import_models import NoticeImportBatch, NoticeImportRow
from app.modules.ruolo.notice_register_api_schemas import ReconciliationInput
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeAudit,
    NoticeEvidence,
    NoticeNotification,
    NoticePosition,
)
from app.modules.ruolo.notice_register_schemas import OperatorChange
from app.modules.ruolo.services.notice_reconciliation import move_events
from app.modules.ruolo.services.notice_register import (
    RegisterConflict,
    _audit,
    _document,
    _reset_notification,
    _reset_position_review,
    _scope_snapshot,
    _snapshot,
)


def _manifest(db: Session, source, target):
    source_event = db.scalar(
        select(NoticeAudit).where(
            NoticeAudit.document_id == source.id,
            NoticeAudit.version == source.version,
        )
    )
    target_event = db.scalar(
        select(NoticeAudit).where(
            NoticeAudit.document_id == target.id,
            NoticeAudit.version == target.version,
        )
    )
    if source_event.action != "reconcile_poste" or target_event.action != "reconcile_poste":
        raise RegisterConflict(
            "Modifiche successive alla riconciliazione: serve una revisione dedicata"
        )
    if source_event.after_json != target_event.after_json:
        raise RegisterConflict("La destinazione ha altre riconciliazioni successive")
    dependent_import = db.scalar(
        select(NoticeImportRow.id)
        .join(NoticeImportBatch)
        .where(
            NoticeImportBatch.source == source.source_system,
            NoticeImportRow.source_key == source.source_key,
            NoticeImportRow.document_id == target.id,
        )
        .limit(1)
    )
    if dependent_import is not None:
        raise RegisterConflict(
            "Nuovi import dipendono dalla riconciliazione: serve una revisione dedicata"
        )
    return source_event


def undo_reconciliation(
    db: Session, source_id: UUID, payload: ReconciliationInput, change: OperatorChange
):
    target_id = payload.target_document_id
    if source_id == target_id:
        raise ValueError("Sorgente e destinazione devono essere diverse")
    target_change = change.model_copy(update={"expected_version": payload.target_version})
    changes = {source_id: change, target_id: target_change}
    documents = {
        key: _document(db, key, changes[key], allow_reconciled=key == source_id)
        for key in sorted(changes)
    }
    source, target = documents[source_id], documents[target_id]
    if source.reconciled_into_id != target_id:
        raise RegisterConflict("Riconciliazione non piu attiva o destinazione diversa")
    event = _manifest(db, source, target)
    attempts = list(
        db.scalars(
            select(NoticeAttempt).where(
                NoticeAttempt.id.in_(
                    [UUID(value) for value in event.after_json["attempt_ids"]],
                )
            )
        )
    )
    evidence = list(
        db.scalars(
            select(NoticeEvidence).where(
                NoticeEvidence.id.in_(
                    [UUID(value) for value in event.after_json["evidence_ids"]],
                )
            )
        )
    )
    positions = list(
        db.scalars(select(NoticePosition).where(NoticePosition.document_id == target_id))
    )
    source_notification = db.get(NoticeNotification, source_id)
    before = {
        "reconciliation_audit_id": str(event.id),
        "reconciled_into_id": str(target_id),
        "source_notification": _snapshot(source_notification),
        "target_scope": [_scope_snapshot(db, p) for p in positions],
    }
    _reset_notification(source_notification)
    for position in positions:
        _reset_position_review(db, position)
    db.flush()
    move_events(db, attempts, evidence, source_id)
    source.reconciled_into_id = None
    audit = {
        "action": "undo_reconciliation",
        "before_json": before,
        "after_json": {
            "source_id": str(source_id),
            "target_id": str(target_id),
            "attempt_ids": event.after_json["attempt_ids"],
            "evidence_ids": event.after_json["evidence_ids"],
            "reconciled_into_id": None,
            "source_notification": _snapshot(source_notification),
            "target_scope": [_scope_snapshot(db, p) for p in positions],
        },
    }
    _audit(db, source, change, audit)
    _audit(db, target, target_change, audit)
    return source
