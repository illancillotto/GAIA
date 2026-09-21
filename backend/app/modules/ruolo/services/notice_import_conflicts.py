"""Explicit, once-only decisions on import variants, never silent overwrites."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo.notice_import_models import NoticeImportRow
from app.modules.ruolo.notice_import_schemas import ConflictDecision
from app.modules.ruolo.notice_register_models import (
    NoticeDocument,
    NoticeEvidence,
    NoticeNotification,
)
from app.modules.ruolo.notice_register_schemas import OperatorChange
from app.modules.ruolo.services.notice_import import require_batch
from app.modules.ruolo.services.notice_register import (
    RegisterConflict,
    RegisterNotFound,
    _audit,
    _document,
    _reset_notification,
    _snapshot,
)


def _conflict_row(db: Session, batch_id: UUID, row_id: UUID, payload: ConflictDecision):
    batch = require_batch(db, batch_id)
    row = db.scalar(
        select(NoticeImportRow)
        .where(NoticeImportRow.id == row_id, NoticeImportRow.batch_id == batch_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise RegisterNotFound("Riga di importazione non trovata")
    if batch.status != "confirmed" or row.outcome != "conflict" or row.resolution is not None:
        raise RegisterConflict("La riga non e un conflitto aperto di un'importazione confermata")
    if row.fingerprint != payload.fingerprint:
        raise RegisterConflict("La variante non corrisponde alla riga visualizzata")
    original = db.get(NoticeDocument, row.document_id)
    document_id = original.reconciled_into_id or original.id
    if document_id != payload.document_id:
        raise RegisterConflict("Documento di confronto cambiato: ricaricare")
    return row


def resolve_conflict(
    db: Session, batch_id: UUID, row_id: UUID, payload: ConflictDecision, change: OperatorChange
):
    row = _conflict_row(db, batch_id, row_id, payload)
    document = _document(db, payload.document_id, change)
    notification = db.get(NoticeNotification, document.id)
    before = {"notification": _snapshot(notification), "resolution": None}
    evidence_id = None
    if payload.decision == "register_evidence":
        evidence_id = uuid4()
        db.add(
            NoticeEvidence(
                id=evidence_id,
                document_id=document.id,
                source_system="import_conflict",
                source_key=str(row.id),
                kind="variante_import_da_verificare",
                reference=f"Variante import {batch_id} | riga {row.row_number}",
                original_json={
                    "batch_id": str(batch_id),
                    "row_id": str(row.id),
                    "fingerprint": row.fingerprint,
                    "payload": row.payload,
                },
            )
        )
        _reset_notification(notification)
    row.resolution = {
        "decision": payload.decision,
        "actor_id": change.actor_id,
        "reason": change.reason,
        "decided_at": datetime.now(UTC).isoformat(),
        "document_id": str(document.id),
        "document_version": document.version + 1,
        "evidence_id": str(evidence_id) if evidence_id else None,
    }
    _audit(
        db,
        document,
        change,
        {
            "action": "resolve_import_conflict",
            "before_json": before,
            "after_json": {
                "batch_id": str(batch_id),
                "row_id": str(row.id),
                "fingerprint": row.fingerprint,
                "resolution": row.resolution,
                "notification": _snapshot(notification),
            },
        },
    )
    return document
