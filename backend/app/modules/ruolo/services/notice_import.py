"""Staging, provenance and atomic/idempotent import confirmation."""

from collections import Counter
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.ruolo.notice_import_models import NoticeImportBatch, NoticeImportRow
from app.modules.ruolo.notice_import_schemas import ImportRowFilters, ImportSnapshot
from app.modules.ruolo.notice_register_api_schemas import Pagination
from app.modules.ruolo.services.notice_import_excel import PARSER_VERSION, digest
from app.modules.ruolo.services.notice_import_register import classify_row, publish_row
from app.modules.ruolo.services.notice_register import RegisterConflict, RegisterNotFound


def require_batch(db: Session, batch_id: UUID, *, lock: bool = False):
    query = select(NoticeImportBatch).where(NoticeImportBatch.id == batch_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    batch = db.scalar(query)
    if batch is None:
        raise RegisterNotFound("Importazione non trovata")
    return batch


def stage_import(db: Session, snapshot: ImportSnapshot, actor_id: int):
    checksum = digest(snapshot.content)
    existing = db.scalar(
        select(NoticeImportBatch).where(
            NoticeImportBatch.source == snapshot.source, NoticeImportBatch.digest == checksum
        )
    )
    if existing is not None:
        return existing
    batch = NoticeImportBatch(
        source=snapshot.source,
        digest=checksum,
        filename=snapshot.filename[:255],
        content=snapshot.content,
        parser_version=PARSER_VERSION,
        actor_id=actor_id,
        summary=snapshot.summary,
    )
    db.add(batch)
    db.flush()
    seen = {}
    outcomes = Counter()
    for values in snapshot.rows:
        row = NoticeImportRow(batch_id=batch.id, **values)
        row.outcome = classify_row(db, batch, row)
        if row.outcome == "new" and row.source_key in seen:
            row.outcome = "duplicate" if seen[row.source_key] == row.fingerprint else "conflict"
        seen.setdefault(row.source_key, row.fingerprint)
        outcomes[row.outcome] += 1
        db.add(row)
    batch.summary = {**snapshot.summary, "outcomes": dict(outcomes)}
    db.flush()
    return batch


def confirm_import(db: Session, batch_id: UUID, checksum: str, actor_id: int, reason: str):
    batch = require_batch(db, batch_id, lock=True)
    if checksum != batch.digest:
        raise RegisterConflict("Anteprima non corrispondente al file conservato")
    if batch.status == "confirmed":
        return batch
    batch.confirmed_by, batch.reason = actor_id, reason
    rows = db.scalars(
        select(NoticeImportRow)
        .where(NoticeImportRow.batch_id == batch.id)
        .order_by(NoticeImportRow.row_number)
    ).all()
    for row in rows:
        publish_row(db, batch, row)
    batch.status = "confirmed"
    batch.confirmed_at = datetime.now(UTC)
    batch.summary = {**batch.summary, "outcomes": dict(Counter(row.outcome for row in rows))}
    db.flush()
    return batch


def list_imports(db: Session, pagination: Pagination, batch_id: UUID | None = None):
    model = NoticeImportBatch if batch_id is None else NoticeImportRow
    query = select(model)
    if batch_id is not None:
        require_batch(db, batch_id)
        query = query.where(NoticeImportRow.batch_id == batch_id)
        if isinstance(pagination, ImportRowFilters) and pagination.review != "all":
            query = query.where(NoticeImportRow.outcome == "conflict")
            # JSON null and SQL NULL must both count as an unresolved row.
            resolved = NoticeImportRow.resolution["decision"].as_string().is_not(None)
            query = query.where(resolved if pagination.review == "resolved" else ~resolved)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    order = (
        (NoticeImportBatch.created_at.desc(), NoticeImportBatch.id)
        if batch_id is None
        else (NoticeImportRow.row_number,)
    )
    items = db.scalars(
        query.order_by(*order)
        .offset((pagination.page - 1) * pagination.page_size)
        .limit(pagination.page_size)
    ).all()
    return {"items": items, "total": total, **pagination.model_dump()}
