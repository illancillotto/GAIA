from typing import Annotated
import uuid
from io import BytesIO, StringIO
import csv

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoDocument
from app.modules.anagrafica.models import (
    AnagraficaAuditLog,
    AnagraficaClassificationSource,
    AnagraficaCompany,
    AnagraficaDocType,
    AnagraficaDocument,
    AnagraficaImportJob,
    AnagraficaImportJobItem,
    AnagraficaImportJobItemStatus,
    AnagraficaPerson,
    AnagraficaSubject,
    AnagraficaSubjectStatus,
)
from app.modules.anagrafica.schemas import (
    AnagraficaAuditLogResponse,
    AnagraficaCatastoDocumentResponse,
    AnagraficaCompanyResponse,
    AnagraficaCsvImportResponse,
    AnagraficaDocumentUpdateRequest,
    AnagraficaImportJobResponse,
    AnagraficaImportJobItemResponse,
    AnagraficaImportPreviewRequest,
    AnagraficaImportPreviewResponse,
    AnagraficaImportRunResponse,
    AnagraficaPersonResponse,
    AnagraficaPreviewDocumentResponse,
    AnagraficaSearchResultResponse,
    AnagraficaStatsResponse,
    AnagraficaModuleStatusResponse,
    AnagraficaSubjectCreateRequest,
    AnagraficaSubjectDetailResponse,
    AnagraficaSubjectListItemResponse,
    AnagraficaSubjectListResponse,
    AnagraficaSubjectUpdateRequest,
)
from app.modules.anagrafica.services.import_service import (
    AnagraficaImportPreviewService,
    create_import_snapshot,
    preview_import,
)
from app.modules.anagrafica.services.csv_import_service import import_subjects_from_csv
from app.services.nas_connector import NasConnectorError, get_nas_client

router = APIRouter(prefix="/anagrafica", tags=["anagrafica"])
RequireAnagraficaModule = Depends(require_module("anagrafica"))


def get_anagrafica_import_service() -> AnagraficaImportPreviewService:
    return AnagraficaImportPreviewService(get_nas_client())


def _job_progress(db: Session, job_id: uuid.UUID) -> dict[str, int]:
    items = db.scalars(select(AnagraficaImportJobItem).where(AnagraficaImportJobItem.job_id == job_id)).all()
    return {
        "pending_items": sum(1 for item in items if item.status == AnagraficaImportJobItemStatus.PENDING.value),
        "running_items": sum(1 for item in items if item.status == AnagraficaImportJobItemStatus.PROCESSING.value),
        "completed_items": sum(1 for item in items if item.status == AnagraficaImportJobItemStatus.COMPLETED.value),
        "failed_items": sum(1 for item in items if item.status == AnagraficaImportJobItemStatus.FAILED.value),
    }


def _serialize_import_job(db: Session, job: AnagraficaImportJob) -> AnagraficaImportJobResponse:
    items = db.scalars(
        select(AnagraficaImportJobItem)
        .where(AnagraficaImportJobItem.job_id == job.id)
        .order_by(
            AnagraficaImportJobItem.status.asc(),
            AnagraficaImportJobItem.updated_at.desc(),
            AnagraficaImportJobItem.folder_name.asc(),
        )
        .limit(200)
    ).all()
    payload = {
        "job_id": str(job.id),
        "requested_by_user_id": job.requested_by_user_id,
        "letter": job.letter,
        "status": job.status,
        "total_folders": job.total_folders,
        "imported_ok": job.imported_ok,
        "imported_errors": job.imported_errors,
        "warning_count": job.warning_count,
        "log_json": job.log_json,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "updated_at": job.updated_at,
        **_job_progress(db, job.id),
        "items": [
            {
                "id": str(item.id),
                "subject_id": str(item.subject_id) if item.subject_id else None,
                "letter": item.letter,
                "folder_name": item.folder_name,
                "nas_folder_path": item.nas_folder_path,
                "status": item.status,
                "attempt_count": item.attempt_count,
                "warning_count": item.warning_count,
                "documents_created": item.documents_created,
                "documents_updated": item.documents_updated,
                "payload_json": item.payload_json,
                "last_error": item.last_error,
                "started_at": item.started_at,
                "completed_at": item.completed_at,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in items
        ],
    }
    return AnagraficaImportJobResponse.model_validate(payload)


@router.get("", response_model=AnagraficaModuleStatusResponse)
def get_anagrafica_module_status(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireAnagraficaModule],
) -> AnagraficaModuleStatusResponse:
    return {
        "module": "anagrafica",
        "enabled": True,
        "message": "GAIA Anagrafica module is enabled for the current user.",
        "username": current_user.username,
    }


@router.post("/import/preview", response_model=AnagraficaImportPreviewResponse)
def post_import_preview(
    payload: AnagraficaImportPreviewRequest,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireAnagraficaModule],
    service: Annotated[AnagraficaImportPreviewService, Depends(get_anagrafica_import_service)],
) -> AnagraficaImportPreviewResponse:
    try:
        return AnagraficaImportPreviewResponse.model_validate(preview_import(payload.letter, service=service))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except NasConnectorError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/import/run", response_model=AnagraficaImportRunResponse, status_code=status.HTTP_202_ACCEPTED)
def post_import_run(
    payload: AnagraficaImportPreviewRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireAnagraficaModule],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AnagraficaImportPreviewService, Depends(get_anagrafica_import_service)],
) -> AnagraficaImportRunResponse:
    try:
        result = create_import_snapshot(db, current_user=current_user, letter=payload.letter, service=service)
        return AnagraficaImportRunResponse.model_validate(
            {
                "job_id": str(result.job_id),
                "letter": result.letter,
                "status": result.status,
                "total_folders": result.total_folders,
                "imported_ok": result.imported_ok,
                "imported_errors": result.imported_errors,
                "warning_count": result.warning_count,
                "pending_items": 0,
                "running_items": 0,
                "completed_items": result.imported_ok,
                "failed_items": result.imported_errors,
                "created_subjects": 0,
                "updated_subjects": 0,
                "created_documents": 0,
                "updated_documents": 0,
                "generated_at": result.generated_at,
                "completed_at": result.completed_at,
                "log_json": result.log_json,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except NasConnectorError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/import/jobs", response_model=list[AnagraficaImportJobResponse])
def get_import_jobs(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireAnagraficaModule],
    db: Annotated[Session, Depends(get_db)],
) -> list[AnagraficaImportJobResponse]:
    jobs = db.scalars(select(AnagraficaImportJob).order_by(AnagraficaImportJob.created_at.desc())).all()
    return [_serialize_import_job(db, job) for job in jobs]


@router.get("/import/jobs/{job_id}", response_model=AnagraficaImportJobResponse)
def get_import_job(
    job_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireAnagraficaModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaImportJobResponse:
    job = db.get(AnagraficaImportJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    return _serialize_import_job(db, job)


@router.post("/import/jobs/{job_id}/resume", response_model=AnagraficaImportRunResponse, status_code=status.HTTP_202_ACCEPTED)
def post_resume_import_job(
    job_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireAnagraficaModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaImportRunResponse:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Resume import Anagrafica temporaneamente sospeso. Usare solo la preview.",
    )

    job = db.get(AnagraficaImportJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    if job.requested_by_user_id != current_user.id and not current_user.is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Import job access denied")

    session_factory = sessionmaker(bind=db.get_bind(), autoflush=False, autocommit=False)
    background_tasks.add_task(
        process_import_job_async,
        job.id,
        current_user.id,
        None if job.letter == "ALL" else job.letter,
        session_factory,
    )
    progress = _job_progress(db, job.id)
    return AnagraficaImportRunResponse.model_validate(
        {
            "job_id": str(job.id),
            "letter": job.letter or "ALL",
            "status": "running",
            "total_folders": job.total_folders,
            "imported_ok": job.imported_ok,
            "imported_errors": job.imported_errors,
            "warning_count": job.warning_count,
            "pending_items": progress["pending_items"],
            "running_items": progress["running_items"],
            "completed_items": progress["completed_items"],
            "failed_items": progress["failed_items"],
            "created_subjects": 0,
            "updated_subjects": 0,
            "created_documents": 0,
            "updated_documents": 0,
            "generated_at": job.created_at,
            "completed_at": None,
            "log_json": job.log_json,
        }
    )


@router.get("/subjects", response_model=AnagraficaSubjectListResponse)
def get_subjects(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireAnagraficaModule],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    search: str | None = Query(default=None),
    subject_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    letter: str | None = Query(default=None),
    requires_review: bool | None = Query(default=None),
) -> AnagraficaSubjectListResponse:
    query = _build_subjects_query(search, subject_type, status_filter, letter, requires_review)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    subjects = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return AnagraficaSubjectListResponse(
        items=[_build_subject_list_item(db, subject) for subject in subjects],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/subjects", response_model=AnagraficaSubjectDetailResponse, status_code=status.HTTP_201_CREATED)
def create_subject(
    payload: AnagraficaSubjectCreateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireAnagraficaModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaSubjectDetailResponse:
    _validate_subject_payload(payload.subject_type, payload.person, payload.company)
    subject = AnagraficaSubject(
        subject_type=payload.subject_type,
        status=AnagraficaSubjectStatus.ACTIVE.value,
        source_name_raw=payload.source_name_raw,
        nas_folder_path=payload.nas_folder_path,
        nas_folder_letter=(payload.nas_folder_letter or "").strip().upper() or None,
        requires_review=payload.requires_review,
    )
    db.add(subject)
    db.flush()
    _apply_subject_payload(db, subject, payload.subject_type, payload.person, payload.company)
    _create_subject_audit(
        db,
        subject.id,
        current_user.id,
        "manual_created",
        {"subject_type": payload.subject_type, "source_name_raw": payload.source_name_raw},
    )
    db.commit()
    return _build_subject_detail(db, subject.id)


@router.post("/subjects/import-csv", response_model=AnagraficaCsvImportResponse)
async def import_subjects_csv(
    file: Annotated[UploadFile, File()],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireAnagraficaModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaCsvImportResponse:
    filename = (file.filename or "").lower()
    if filename and not filename.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Il file deve essere un CSV")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File CSV vuoto")

    try:
        result = import_subjects_from_csv(db, current_user=current_user, file_bytes=file_bytes)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return AnagraficaCsvImportResponse.model_validate(
        {
            "total_rows": result.total_rows,
            "created_subjects": result.created_subjects,
            "updated_subjects": result.updated_subjects,
            "skipped_rows": result.skipped_rows,
            "errors": [
                {
                    "row_number": item.row_number,
                    "message": item.message,
                    "codice_fiscale": item.codice_fiscale,
                }
                for item in result.errors
            ],
        }
    )


@router.get("/subjects/{subject_id}", response_model=AnagraficaSubjectDetailResponse)
def get_subject(
    subject_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireAnagraficaModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaSubjectDetailResponse:
    return _build_subject_detail(db, subject_id)


@router.put("/subjects/{subject_id}", response_model=AnagraficaSubjectDetailResponse)
def update_subject(
    subject_id: uuid.UUID,
    payload: AnagraficaSubjectUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireAnagraficaModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaSubjectDetailResponse:
    subject = db.get(AnagraficaSubject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    if payload.source_name_raw is not None:
        subject.source_name_raw = payload.source_name_raw
    if payload.status is not None:
        subject.status = payload.status
    if payload.nas_folder_path is not None:
        subject.nas_folder_path = payload.nas_folder_path
    if payload.nas_folder_letter is not None:
        subject.nas_folder_letter = payload.nas_folder_letter.strip().upper() or None
    if payload.requires_review is not None:
        subject.requires_review = payload.requires_review

    _validate_subject_payload(subject.subject_type, payload.person, payload.company, allow_empty=True)
    if payload.person is not None or payload.company is not None:
        _apply_subject_payload(db, subject, subject.subject_type, payload.person, payload.company)

    db.add(subject)
    _create_subject_audit(
        db,
        subject.id,
        current_user.id,
        "manual_updated",
        {"status": subject.status, "requires_review": subject.requires_review},
    )
    db.commit()
    return _build_subject_detail(db, subject_id)


@router.delete("/subjects/{subject_id}", response_model=AnagraficaSubjectDetailResponse)
def deactivate_subject(
    subject_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireAnagraficaModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaSubjectDetailResponse:
    subject = db.get(AnagraficaSubject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    subject.status = AnagraficaSubjectStatus.INACTIVE.value
    db.add(subject)
    _create_subject_audit(db, subject.id, current_user.id, "deactivated", {"status": subject.status})
    db.commit()
    return _build_subject_detail(db, subject_id)


@router.get("/subjects/{subject_id}/documents", response_model=list[AnagraficaPreviewDocumentResponse])
def get_subject_documents(
    subject_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireAnagraficaModule],
    db: Annotated[Session, Depends(get_db)],
) -> list[AnagraficaPreviewDocumentResponse]:
    _require_subject_exists(db, subject_id)
    documents = db.scalars(
        select(AnagraficaDocument)
        .where(AnagraficaDocument.subject_id == subject_id)
        .order_by(AnagraficaDocument.created_at.desc())
    ).all()
    return [_build_document_response(item) for item in documents]


@router.patch("/documents/{document_id}", response_model=AnagraficaPreviewDocumentResponse)
def patch_document(
    document_id: uuid.UUID,
    payload: AnagraficaDocumentUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireAnagraficaModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaPreviewDocumentResponse:
    document = db.get(AnagraficaDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if payload.doc_type is not None:
        document.doc_type = payload.doc_type
        document.classification_source = AnagraficaClassificationSource.MANUAL.value
    if payload.notes is not None:
        document.notes = payload.notes
    db.add(document)
    _create_subject_audit(
        db,
        document.subject_id,
        current_user.id,
        "document_updated",
        {"document_id": str(document.id), "doc_type": document.doc_type, "notes": document.notes},
    )
    db.commit()
    db.refresh(document)
    return _build_document_response(document)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireAnagraficaModule],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    document = db.get(AnagraficaDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    subject_id = document.subject_id
    db.delete(document)
    _create_subject_audit(
        db,
        subject_id,
        current_user.id,
        "document_deleted",
        {"document_id": str(document_id)},
    )
    db.commit()


@router.get("/stats", response_model=AnagraficaStatsResponse)
def get_stats(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireAnagraficaModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaStatsResponse:
    total_subjects = db.scalar(select(func.count()).select_from(AnagraficaSubject)) or 0
    total_persons = db.scalar(
        select(func.count()).select_from(AnagraficaSubject).where(AnagraficaSubject.subject_type == "person")
    ) or 0
    total_companies = db.scalar(
        select(func.count()).select_from(AnagraficaSubject).where(AnagraficaSubject.subject_type == "company")
    ) or 0
    total_unknown = db.scalar(
        select(func.count()).select_from(AnagraficaSubject).where(AnagraficaSubject.subject_type == "unknown")
    ) or 0
    total_documents = db.scalar(select(func.count()).select_from(AnagraficaDocument)) or 0
    requires_review = db.scalar(
        select(func.count()).select_from(AnagraficaSubject).where(AnagraficaSubject.requires_review.is_(True))
    ) or 0
    active_subjects = db.scalar(
        select(func.count()).select_from(AnagraficaSubject).where(AnagraficaSubject.status == "active")
    ) or 0
    inactive_subjects = db.scalar(
        select(func.count()).select_from(AnagraficaSubject).where(AnagraficaSubject.status == "inactive")
    ) or 0
    documents_unclassified = db.scalar(
        select(func.count()).select_from(AnagraficaDocument).where(AnagraficaDocument.doc_type == AnagraficaDocType.ALTRO.value)
    ) or 0
    letter_rows = db.execute(
        select(AnagraficaSubject.nas_folder_letter, func.count())
        .group_by(AnagraficaSubject.nas_folder_letter)
        .order_by(AnagraficaSubject.nas_folder_letter.asc())
    ).all()
    by_letter = {letter or "?": total for letter, total in letter_rows}
    return AnagraficaStatsResponse(
        total_subjects=total_subjects,
        total_persons=total_persons,
        total_companies=total_companies,
        total_unknown=total_unknown,
        total_documents=total_documents,
        requires_review=requires_review,
        active_subjects=active_subjects,
        inactive_subjects=inactive_subjects,
        documents_unclassified=documents_unclassified,
        by_letter=by_letter,
    )


@router.get("/search", response_model=AnagraficaSearchResultResponse)
def search_subjects(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireAnagraficaModule],
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
    __: Annotated[ApplicationUser, RequireAnagraficaModule],
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
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="anagrafica-export.xlsx"'},
        )

    csv_buffer = StringIO()
    headers = list(rows[0].keys()) if rows else _export_headers()
    writer = csv.DictWriter(csv_buffer, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return StreamingResponse(
        iter([csv_buffer.getvalue().encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="anagrafica-export.csv"'},
    )


def _require_subject_exists(db: Session, subject_id: uuid.UUID) -> AnagraficaSubject:
    subject = db.get(AnagraficaSubject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return subject


def _validate_subject_payload(subject_type: str, person: object, company: object, allow_empty: bool = False) -> None:
    if subject_type == "person" and person is None and not allow_empty:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Person payload required")
    if subject_type == "company" and company is None and not allow_empty:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Company payload required")
    if subject_type == "person" and company is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Company payload not allowed")
    if subject_type == "company" and person is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Person payload not allowed")


def _apply_subject_payload(db: Session, subject: AnagraficaSubject, subject_type: str, person: object, company: object) -> None:
    existing_person = db.get(AnagraficaPerson, subject.id)
    existing_company = db.get(AnagraficaCompany, subject.id)
    if subject_type == "person":
        if existing_company is not None:
            db.delete(existing_company)
        if person is not None:
            person_payload = person.model_dump()  # type: ignore[union-attr]
            model = existing_person or AnagraficaPerson(subject_id=subject.id, **person_payload)
            for key, value in person_payload.items():
                setattr(model, key, value)
            db.add(model)
    elif subject_type == "company":
        if existing_person is not None:
            db.delete(existing_person)
        if company is not None:
            company_payload = company.model_dump()  # type: ignore[union-attr]
            model = existing_company or AnagraficaCompany(subject_id=subject.id, **company_payload)
            for key, value in company_payload.items():
                setattr(model, key, value)
            db.add(model)
    else:
        if existing_person is not None:
            db.delete(existing_person)
        if existing_company is not None:
            db.delete(existing_company)
    db.flush()


def _build_subjects_query(
    search: str | None,
    subject_type: str | None,
    status_filter: str | None,
    letter: str | None,
    requires_review: bool | None,
):
    query = select(AnagraficaSubject).order_by(AnagraficaSubject.updated_at.desc(), AnagraficaSubject.created_at.desc())
    if subject_type:
        query = query.where(AnagraficaSubject.subject_type == subject_type)
    if status_filter:
        query = query.where(AnagraficaSubject.status == status_filter)
    if letter:
        query = query.where(AnagraficaSubject.nas_folder_letter == letter.strip().upper())
    if requires_review is not None:
        query = query.where(AnagraficaSubject.requires_review == requires_review)
    tokens = [token.strip().lower() for token in (search or "").split() if token.strip()]
    for token in tokens:
        term = f"%{token}%"
        person_subject_ids = select(AnagraficaPerson.subject_id).where(
            or_(
                func.lower(AnagraficaPerson.cognome).like(term),
                func.lower(AnagraficaPerson.nome).like(term),
                func.lower(AnagraficaPerson.codice_fiscale).like(term),
            )
        )
        company_subject_ids = select(AnagraficaCompany.subject_id).where(
            or_(
                func.lower(AnagraficaCompany.ragione_sociale).like(term),
                func.lower(AnagraficaCompany.partita_iva).like(term),
                func.lower(func.coalesce(AnagraficaCompany.codice_fiscale, "")).like(term),
            )
        )
        document_subject_ids = select(AnagraficaDocument.subject_id).where(
            or_(
                func.lower(AnagraficaDocument.filename).like(term),
                func.lower(func.coalesce(AnagraficaDocument.nas_path, "")).like(term),
            )
        )
        query = query.where(
            or_(
                func.lower(AnagraficaSubject.source_name_raw).like(term),
                AnagraficaSubject.id.in_(person_subject_ids),
                AnagraficaSubject.id.in_(company_subject_ids),
                AnagraficaSubject.id.in_(document_subject_ids),
            )
        )
    return query


def _create_subject_audit(
    db: Session,
    subject_id: uuid.UUID,
    changed_by_user_id: int | None,
    action: str,
    diff_json: dict[str, object],
) -> None:
    db.add(
        AnagraficaAuditLog(
            subject_id=subject_id,
            changed_by_user_id=changed_by_user_id,
            action=action,
            diff_json=diff_json,
        )
    )
    db.flush()


def _build_subject_list_item(db: Session, subject: AnagraficaSubject) -> AnagraficaSubjectListItemResponse:
    person = db.get(AnagraficaPerson, subject.id)
    company = db.get(AnagraficaCompany, subject.id)
    document_count = db.scalar(
        select(func.count()).select_from(AnagraficaDocument).where(AnagraficaDocument.subject_id == subject.id)
    ) or 0
    display_name = subject.source_name_raw
    codice_fiscale = None
    partita_iva = None
    if person is not None:
        display_name = f"{person.cognome} {person.nome}".strip()
        codice_fiscale = person.codice_fiscale
    elif company is not None:
        display_name = company.ragione_sociale
        codice_fiscale = company.codice_fiscale
        partita_iva = company.partita_iva
    return AnagraficaSubjectListItemResponse(
        id=str(subject.id),
        subject_type=subject.subject_type,
        status=subject.status,
        source_name_raw=subject.source_name_raw,
        display_name=display_name,
        codice_fiscale=codice_fiscale,
        partita_iva=partita_iva,
        nas_folder_path=subject.nas_folder_path,
        nas_folder_letter=subject.nas_folder_letter,
        requires_review=subject.requires_review,
        imported_at=subject.imported_at,
        document_count=document_count,
        created_at=subject.created_at,
        updated_at=subject.updated_at,
    )


def _build_document_response(document: AnagraficaDocument) -> AnagraficaPreviewDocumentResponse:
    extension = None
    if document.filename and "." in document.filename:
        extension = f".{document.filename.rsplit('.', maxsplit=1)[1].lower()}"
    warnings = []
    if document.notes:
        warnings = [item.strip() for item in document.notes.split(",") if item.strip()]
    return AnagraficaPreviewDocumentResponse(
        id=str(document.id),
        filename=document.filename,
        relative_path=document.filename,
        nas_path=document.nas_path or document.local_path or document.filename,
        extension=extension,
        is_pdf=extension == ".pdf",
        doc_type=document.doc_type,
        classification_source=document.classification_source,
        warnings=warnings,
    )


def _export_headers() -> list[str]:
    return [
        "id",
        "subject_type",
        "status",
        "display_name",
        "codice_fiscale",
        "partita_iva",
        "nas_folder_letter",
        "nas_folder_path",
        "requires_review",
        "document_count",
        "imported_at",
        "updated_at",
    ]


def _subject_export_row(db: Session, subject: AnagraficaSubject) -> dict[str, object]:
    item = _build_subject_list_item(db, subject)
    return {
        "id": item.id,
        "subject_type": item.subject_type,
        "status": item.status,
        "display_name": item.display_name,
        "codice_fiscale": item.codice_fiscale or "",
        "partita_iva": item.partita_iva or "",
        "nas_folder_letter": item.nas_folder_letter or "",
        "nas_folder_path": item.nas_folder_path or "",
        "requires_review": item.requires_review,
        "document_count": item.document_count,
        "imported_at": item.imported_at.isoformat() if item.imported_at else "",
        "updated_at": item.updated_at.isoformat(),
    }


def _build_catasto_correlations(db: Session, person: AnagraficaPerson | None) -> list[AnagraficaCatastoDocumentResponse]:
    if person is None or not person.codice_fiscale:
        return []
    documents = db.scalars(
        select(CatastoDocument)
        .where(CatastoDocument.codice_fiscale == person.codice_fiscale)
        .order_by(CatastoDocument.created_at.desc())
        .limit(20)
    ).all()
    return [
        AnagraficaCatastoDocumentResponse(
            id=str(item.id),
            request_id=str(item.request_id) if item.request_id else None,
            comune=item.comune,
            foglio=item.foglio,
            particella=item.particella,
            subalterno=item.subalterno,
            catasto=item.catasto,
            tipo_visura=item.tipo_visura,
            filename=item.filename,
            codice_fiscale=item.codice_fiscale,
            created_at=item.created_at,
        )
        for item in documents
    ]


def _build_subject_detail(db: Session, subject_id: uuid.UUID) -> AnagraficaSubjectDetailResponse:
    subject = _require_subject_exists(db, subject_id)
    person = db.get(AnagraficaPerson, subject_id)
    company = db.get(AnagraficaCompany, subject_id)
    documents = db.scalars(
        select(AnagraficaDocument)
        .where(AnagraficaDocument.subject_id == subject_id)
        .order_by(AnagraficaDocument.created_at.desc())
    ).all()
    audit_entries = db.scalars(
        select(AnagraficaAuditLog)
        .where(AnagraficaAuditLog.subject_id == subject_id)
        .order_by(AnagraficaAuditLog.changed_at.desc())
    ).all()
    person_response = None
    company_response = None
    if person is not None:
        person_response = AnagraficaPersonResponse.model_validate(
            {
                "subject_id": str(person.subject_id),
                "cognome": person.cognome,
                "nome": person.nome,
                "codice_fiscale": person.codice_fiscale,
                "data_nascita": person.data_nascita,
                "comune_nascita": person.comune_nascita,
                "indirizzo": person.indirizzo,
                "comune_residenza": person.comune_residenza,
                "cap": person.cap,
                "email": person.email,
                "telefono": person.telefono,
                "note": person.note,
                "created_at": person.created_at,
                "updated_at": person.updated_at,
            }
        )
    if company is not None:
        company_response = AnagraficaCompanyResponse.model_validate(
            {
                "subject_id": str(company.subject_id),
                "ragione_sociale": company.ragione_sociale,
                "partita_iva": company.partita_iva,
                "codice_fiscale": company.codice_fiscale,
                "forma_giuridica": company.forma_giuridica,
                "sede_legale": company.sede_legale,
                "comune_sede": company.comune_sede,
                "cap": company.cap,
                "email_pec": company.email_pec,
                "telefono": company.telefono,
                "note": company.note,
                "created_at": company.created_at,
                "updated_at": company.updated_at,
            }
        )
    catasto_documents = _build_catasto_correlations(db, person)
    return AnagraficaSubjectDetailResponse(
        id=str(subject.id),
        subject_type=subject.subject_type,
        status=subject.status,
        source_name_raw=subject.source_name_raw,
        nas_folder_path=subject.nas_folder_path,
        nas_folder_letter=subject.nas_folder_letter,
        requires_review=subject.requires_review,
        imported_at=subject.imported_at,
        created_at=subject.created_at,
        updated_at=subject.updated_at,
        person=person_response,
        company=company_response,
        documents=[_build_document_response(item) for item in documents],
        audit_log=[
            AnagraficaAuditLogResponse.model_validate(
                {
                    "id": str(item.id),
                    "subject_id": str(item.subject_id),
                    "changed_by_user_id": item.changed_by_user_id,
                    "action": item.action,
                    "diff_json": item.diff_json,
                    "changed_at": item.changed_at,
                }
            )
            for item in audit_entries
        ],
        catasto_documents=catasto_documents,
    )
