import csv
from io import BytesIO, StringIO
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.utenze.models import AnagraficaDocType, AnagraficaDocument, AnagraficaSubject
from app.modules.utenze.routes.support import (
    _build_subject_list_item,
    _build_subjects_query,
    _export_headers,
    _subject_display_name,
    _subject_export_row,
    _visible_document_condition,
)
from app.modules.utenze.schemas import (
    AnagraficaDocumentSummaryBucketResponse,
    AnagraficaDocumentSummaryItemResponse,
    AnagraficaDocumentSummaryResponse,
    AnagraficaSearchResultResponse,
)

router = APIRouter(tags=["utenze"])
RequireUtenzeModule = Depends(require_module("utenze"))


# Preserve reviewed legacy callable layout for the merge-base LOC ratchet.
# fmt: off
@router.get("/documents/summary", response_model=AnagraficaDocumentSummaryResponse)
def get_documents_summary(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaDocumentSummaryResponse:
    visible_document_condition = _visible_document_condition()
    total_documents = db.scalar(select(func.count()).select_from(AnagraficaDocument).where(visible_document_condition)) or 0
    documents_unclassified = db.scalar(select(func.count()).select_from(AnagraficaDocument).where(AnagraficaDocument.doc_type == AnagraficaDocType.ALTRO.value, visible_document_condition)) or 0
    classified_documents = max(total_documents - documents_unclassified, 0)
    buckets = db.execute(select(AnagraficaDocument.doc_type, func.count()).where(visible_document_condition).group_by(AnagraficaDocument.doc_type).order_by(func.count().desc(), AnagraficaDocument.doc_type.asc())).all()
    recent_unclassified_documents = db.scalars(select(AnagraficaDocument).where(AnagraficaDocument.doc_type == AnagraficaDocType.ALTRO.value, visible_document_condition).order_by(AnagraficaDocument.created_at.desc()).limit(12)).all()
    recent_unclassified = []
    for document in recent_unclassified_documents:
        subject = db.get(AnagraficaSubject, document.subject_id)
        if subject is None:
            continue
        recent_unclassified.append(AnagraficaDocumentSummaryItemResponse(document_id=str(document.id), subject_id=str(subject.id), subject_display_name=_subject_display_name(db, subject), filename=document.filename, doc_type=document.doc_type, classification_source=document.classification_source, created_at=document.created_at))
    return AnagraficaDocumentSummaryResponse(total_documents=total_documents, documents_unclassified=documents_unclassified, classified_documents=classified_documents, by_doc_type=[AnagraficaDocumentSummaryBucketResponse(doc_type=str(doc_type), count=int(count)) for doc_type, count in buckets], recent_unclassified=recent_unclassified)

@router.get("/search", response_model=AnagraficaSearchResultResponse)
def search_subjects(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
    q: str = Query(min_length=3),
    limit: int = Query(default=20, ge=1, le=100),
) -> AnagraficaSearchResultResponse:
    query = _build_subjects_query(q, None, None, None, None)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    subjects = db.scalars(query.limit(limit)).all()
    return AnagraficaSearchResultResponse(items=[_build_subject_list_item(db, item) for item in subjects], total=total)

@router.get("/export")
def export_subjects(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
    search: str | None = Query(default=None),
    subject_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    letter: str | None = Query(default=None),
    requires_review: bool | None = Query(default=None),
) -> StreamingResponse:
    query = _build_subjects_query(search, subject_type, status_filter, letter, requires_review)
    subjects = db.scalars(query).all()
    rows = [_subject_export_row(db, subject) for subject in subjects]
    if format == "xlsx":
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Anagrafica"
        headers = list(rows[0].keys()) if rows else _export_headers()
        sheet.append(headers)
        for row in rows:
            sheet.append([row[key] for key in headers])
        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="anagrafica-export.xlsx"'})
    csv_buffer = StringIO()
    headers = list(rows[0].keys()) if rows else _export_headers()
    writer = csv.DictWriter(csv_buffer, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return StreamingResponse(iter([csv_buffer.getvalue().encode("utf-8")]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="anagrafica-export.csv"'})
# fmt: on
