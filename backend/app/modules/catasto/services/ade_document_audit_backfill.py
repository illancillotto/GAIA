from __future__ import annotations

from collections import Counter
from pathlib import Path
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoDocument, CatastoVisuraRequest
from app.modules.catasto.services.ade_document_audit import (
    apply_document_audit,
    audit_visura_pdf,
    expected_document_request_type,
)


def backfill_document_audits(
    db: Session,
    *,
    batch_id: UUID | None = None,
    limit: int | None = None,
    force: bool = False,
    dry_run: bool = True,
    commit_every: int = 100,
) -> Counter[str]:
    _validate_options(limit, commit_every)
    statement = _document_statement(batch_id=batch_id, limit=limit, force=force)
    documents = list(db.scalars(statement).all())
    counters = _audit_documents(db, documents, dry_run=dry_run, commit_every=commit_every)
    counters["selected"] = len(documents)
    if dry_run:
        db.rollback()
    counters["updated"] = 0 if dry_run else counters["audited"]
    return counters


def _validate_options(limit: int | None, commit_every: int) -> None:
    if limit is not None and limit <= 0:
        raise ValueError("limit must be greater than zero")
    if commit_every <= 0:
        raise ValueError("commit_every must be greater than zero")


def _document_statement(*, batch_id: UUID | None, limit: int | None, force: bool):
    statement = (
        select(CatastoDocument)
        .outerjoin(CatastoVisuraRequest, CatastoVisuraRequest.id == CatastoDocument.request_id)
        .where(CatastoDocument.search_mode == "immobile")
        .order_by(CatastoDocument.created_at, CatastoDocument.id)
    )
    if batch_id is not None:
        statement = statement.where(CatastoVisuraRequest.batch_id == batch_id)
    if not force:
        statement = statement.where(
            and_(
                CatastoDocument.content_request_type.is_(None),
                CatastoDocument.parcel_classification.is_(None),
                CatastoDocument.parcel_suppressed_at.is_(None),
                CatastoDocument.content_metadata_json.is_(None),
            )
        )
    if limit is not None:
        statement = statement.limit(limit)
    return statement


def _audit_documents(
    db: Session,
    documents: list[CatastoDocument],
    *,
    dry_run: bool,
    commit_every: int,
) -> Counter[str]:
    counters: Counter[str] = Counter()
    pending_writes = 0
    for document in documents:
        file_path = Path(document.filepath)
        if not file_path.is_file():
            counters["missing_file"] += 1
            continue
        try:
            expected_type = expected_document_request_type(document.request_type, document.tipo_visura)
            payload = audit_visura_pdf(file_path, expected_type)
        except Exception:
            counters["audit_failed"] += 1
            continue
        counters[f"classification:{payload.get('classification') or 'unknown'}"] += 1
        counters["audited"] += 1
        if dry_run:
            continue
        apply_document_audit(document, payload)
        pending_writes += 1
        if pending_writes >= commit_every:
            db.commit()
            pending_writes = 0

    if not dry_run and pending_writes:
        db.commit()
    return counters


__all__ = ["backfill_document_audits"]
