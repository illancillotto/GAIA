"""Publish immutable staged rows into the register, never overwrite reviewed data."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo.notice_import_models import NoticeImportBatch, NoticeImportRow
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeAudit,
    NoticeDocument,
    NoticeEvidence,
    NoticeNotification,
    NoticePosition,
    NoticeRecovery,
)


def imported_document(
    db: Session, batch: NoticeImportBatch, row: NoticeImportRow, *, lock: bool = False
):
    query = select(NoticeDocument).where(
        NoticeDocument.source_system == batch.source,
        NoticeDocument.source_key == row.source_key,
    )
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    return db.scalar(query)


def classify_row(db: Session, batch: NoticeImportBatch, row: NoticeImportRow) -> str:
    return _classify(imported_document(db, batch, row), row)


def _classify(existing: NoticeDocument | None, row: NoticeImportRow) -> str:
    if existing is None:
        return "new"
    if existing.original_json.get("import_fingerprint") == row.fingerprint:
        return "duplicate"
    return "conflict"


def _positions(db: Session, document: NoticeDocument, values: list[dict]):
    for value in values:
        position = NoticePosition(id=uuid4(), document_id=document.id, **value)
        db.add(position)
        db.flush()
        db.add(NoticeRecovery(position_id=position.id, state="da_verificare"))


def _evidence(
    db: Session, document: NoticeDocument, batch: NoticeImportBatch, row: NoticeImportRow
):
    attempt_id = None
    payload = row.payload
    if "registered_mail_id" in payload:
        attempt_id = uuid4()
        sent_at = payload["sent_at"]
        db.add(
            NoticeAttempt(
                id=attempt_id,
                document_id=document.id,
                source_system=batch.source,
                source_key=row.source_key,
                channel="raccomandata",
                tracking_code=payload["tracking_code"],
                registered_mail_id=UUID(payload["registered_mail_id"]),
                sent_at=datetime.fromisoformat(sent_at) if sent_at else None,
            )
        )
        db.flush()
    db.add(
        NoticeEvidence(
            id=uuid4(),
            document_id=document.id,
            attempt_id=attempt_id,
            source_system=batch.source,
            source_key=row.source_key,
            kind="import_da_verificare",
            reference=f"Import {batch.id} | {payload['sheet']} | riga {row.row_number}",
            original_json={"batch_id": str(batch.id), "row_id": str(row.id), **payload},
        )
    )


def publish_row(db: Session, batch: NoticeImportBatch, row: NoticeImportRow):
    existing = imported_document(db, batch, row, lock=True)
    row.outcome = _classify(existing, row)
    if existing is not None:
        row.document_id = existing.reconciled_into_id or existing.id
        return
    payload = row.payload
    document = NoticeDocument(
        id=uuid4(),
        source_system=batch.source,
        source_key=row.source_key,
        document_number=payload["document_number"],
        tax_code=payload["tax_code"],
        original_json={
            "import_fingerprint": row.fingerprint,
            "batch_id": str(batch.id),
            "row_id": str(row.id),
            **payload,
        },
        version=1,
    )
    db.add(document)
    db.flush()
    _positions(db, document, payload["positions"])
    db.add(NoticeNotification(document_id=document.id, state="da_verificare"))
    _evidence(db, document, batch, row)
    db.add(
        NoticeAudit(
            document_id=document.id,
            version=1,
            actor_id=batch.confirmed_by,
            reason=batch.reason,
            action="import_document",
            before_json={},
            after_json={
                "batch_id": str(batch.id),
                "row_id": str(row.id),
                "fingerprint": row.fingerprint,
            },
        )
    )
    row.document_id, row.outcome = document.id, "imported"
    db.flush()
