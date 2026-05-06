from typing import Annotated
import uuid
from datetime import datetime, timezone
from io import BytesIO, StringIO
import csv
import mimetypes
from pathlib import Path
import secrets
import threading

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from openpyxl import Workbook
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_admin_user, require_module
from app.core.config import settings
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoDocument
from app.modules.utenze.models import (
    AnagraficaAuditLog,
    AnagraficaClassificationSource,
    AnagraficaCompany,
    AnagraficaDocType,
    AnagraficaDocument,
    AnagraficaImportJob,
    AnagraficaImportJobItem,
    AnagraficaImportJobItemStatus,
    AnagraficaPerson,
    AnagraficaPersonSnapshot,
    AnagraficaSubject,
    AnagraficaSubjectStatus,
    AnagraficaXlsxImportBatch,
    AnagraficaXlsxImportBatchStatus,
    BonificaUserStaging,
)
from app.modules.utenze.schemas import (
    AnagraficaAuditLogResponse,
    AnagraficaCatastoDocumentResponse,
    AnagraficaCompanyResponse,
    AnagraficaCsvImportResponse,
    AnagraficaDocumentSummaryBucketResponse,
    AnagraficaDocumentSummaryItemResponse,
    AnagraficaDocumentSummaryResponse,
    AnagraficaDocumentUpdateRequest,
    AnagraficaImportJobResponse,
    AnagraficaImportJobItemResponse,
    AnagraficaImportPreviewRequest,
    AnagraficaImportPreviewResponse,
    AnagraficaImportRunResponse,
    AnagraficaNasFolderCandidateResponse,
    AnagraficaCompanyPayload,
    AnagraficaPersonPayload,
    AnagraficaPersonResponse,
    AnagraficaPersonSnapshotResponse,
    AnagraficaPreviewDocumentResponse,
    AnagraficaResetRequest,
    AnagraficaResetResponse,
    AnagraficaSearchResultResponse,
    AnagraficaStatsResponse,
    AnagraficaModuleStatusResponse,
    AnagraficaSubjectCreateRequest,
    AnagraficaSubjectDetailResponse,
    AnagraficaSubjectNasImportStatusResponse,
    AnagraficaSubjectImportResponse,
    AnagraficaSubjectListItemResponse,
    AnagraficaSubjectListResponse,
    AnagraficaSubjectUpdateRequest,
    BonificaUserStagingBulkApproveRequest,
    BonificaUserStagingBulkApproveResponse,
    BonificaUserStagingListResponse,
    BonificaUserStagingResponse,
    RegistryImportJobDeletedResponse,
    XlsxImportBatchResponse,
    XlsxImportStartResponse,
)
from app.modules.utenze.services.import_service import (
    AnagraficaImportPreviewService,
    create_import_snapshot,
    create_manual_document,
    delete_registry_import_job,
    finalize_stuck_registry_import_job,
    import_subject_from_existing_registry,
    preview_import,
    queue_resume_registry_bulk_import_job,
    registry_job_completed_subject_ids,
    reset_anagrafica_data,
    start_registry_bulk_import_job,
)
from app.modules.utenze.services.csv_import_service import import_subjects_from_csv
from app.modules.utenze.services.nas_path_service import canonical_subject_nas_folder_path
from app.modules.utenze.services.person_history_service import snapshot_person_if_changed
from app.modules.utenze.services.xlsx_import_service import run_xlsx_import
from app.services.nas_connector import NasConnectorError, get_nas_client

router = APIRouter(tags=["utenze"])
RequireUtenzeModule = Depends(require_module("utenze"))


def get_anagrafica_import_service() -> AnagraficaImportPreviewService:
    return AnagraficaImportPreviewService(get_nas_client())


def _close_import_service(service: AnagraficaImportPreviewService) -> None:
    close = getattr(service.connector, "close", None)
    if callable(close):
        close()


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


def _require_registry_import_job_for_mutation(
    db: Session,
    job_id: uuid.UUID,
    current_user: ApplicationUser,
) -> AnagraficaImportJob:
    job = db.get(AnagraficaImportJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job non trovato")
    if job.letter != "REGISTRY":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Questa azione è disponibile solo per job REGISTRY (aggiornamento massivo da anagrafica).",
        )
    if job.requested_by_user_id != current_user.id and not current_user.is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Non hai permesso di modificare questo job")
    return job


@router.get("", response_model=AnagraficaModuleStatusResponse)
def get_anagrafica_module_status(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
) -> AnagraficaModuleStatusResponse:
    return {
        "module": "utenze",
        "enabled": True,
        "message": "GAIA Utenze module is enabled for the current user.",
        "username": current_user.username,
    }


@router.post("/import/preview", response_model=AnagraficaImportPreviewResponse)
def post_import_preview(
    payload: AnagraficaImportPreviewRequest,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
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
    _: Annotated[ApplicationUser, RequireUtenzeModule],
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


@router.post("/import/run-from-subjects", response_model=AnagraficaImportRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def post_import_run_from_subjects(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaImportRunResponse:
    try:
        job_id = start_registry_bulk_import_job(db, current_user)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    job = db.get(AnagraficaImportJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Impossibile creare il job di aggiornamento utenze")

    progress = _job_progress(db, job_id)
    generated_at = job.created_at

    return AnagraficaImportRunResponse.model_validate(
        {
            "job_id": str(job_id),
            "letter": "REGISTRY",
            "status": job.status,
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
            "generated_at": generated_at,
            "completed_at": job.completed_at,
            "log_json": job.log_json,
        }
    )


@router.get("/import/jobs", response_model=list[AnagraficaImportJobResponse])
def get_import_jobs(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> list[AnagraficaImportJobResponse]:
    jobs = db.scalars(select(AnagraficaImportJob).order_by(AnagraficaImportJob.created_at.desc())).all()
    return [_serialize_import_job(db, job) for job in jobs]


@router.get("/import/jobs/{job_id}", response_model=AnagraficaImportJobResponse)
def get_import_job(
    job_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaImportJobResponse:
    job = db.get(AnagraficaImportJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    return _serialize_import_job(db, job)


@router.post("/import/jobs/{job_id}/abort-registry", response_model=AnagraficaImportJobResponse)
def post_abort_registry_import_job(
    job_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaImportJobResponse:
    """Chiude job REGISTRY bloccati: marca gli item `processing` come falliti e ricalcola lo stato del job."""
    _require_registry_import_job_for_mutation(db, job_id, current_user)
    updated = finalize_stuck_registry_import_job(db, job_id, refresh=True)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job non trovato")
    return _serialize_import_job(db, updated)


@router.post("/import/jobs/{job_id}/resume-registry", response_model=AnagraficaImportRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def post_resume_registry_import_job(
    job_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaImportRunResponse:
    """Riprende un job REGISTRY: interrompe eventuali item bloccati in processing, poi elabora solo i soggetti non ancora completati."""
    _require_registry_import_job_for_mutation(db, job_id, current_user)

    total_subjects = int(db.scalar(select(func.count()).select_from(AnagraficaSubject)) or 0)
    completed_ids = registry_job_completed_subject_ids(db, job_id)
    if total_subjects == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nessun soggetto in anagrafica: impossibile riprendere il job.",
        )
    if len(completed_ids) >= total_subjects:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tutti i soggetti risultano già elaborati con esito positivo per questo job.",
        )

    job = queue_resume_registry_bulk_import_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job non trovato")

    progress = _job_progress(db, job_id)
    generated_at = job.created_at

    return AnagraficaImportRunResponse.model_validate(
        {
            "job_id": str(job_id),
            "letter": "REGISTRY",
            "status": job.status,
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
            "generated_at": generated_at,
            "completed_at": job.completed_at,
            "log_json": job.log_json,
        }
    )


@router.delete("/import/jobs/{job_id}", response_model=RegistryImportJobDeletedResponse)
def delete_registry_import_job_route(
    job_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> RegistryImportJobDeletedResponse:
    """Elimina dal database un job REGISTRY e tutti i relativi item (storico / job bloccati)."""
    _require_registry_import_job_for_mutation(db, job_id, current_user)
    deleted = delete_registry_import_job(db, job_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job non trovato")
    return RegistryImportJobDeletedResponse(deleted=True)


@router.post("/import/jobs/{job_id}/resume", response_model=AnagraficaImportRunResponse, status_code=status.HTTP_202_ACCEPTED)
def post_resume_import_job(
    job_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
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
    __: Annotated[ApplicationUser, RequireUtenzeModule],
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


@router.get("/bonifica-staging", response_model=BonificaUserStagingListResponse)
def get_bonifica_staging(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    search: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
) -> BonificaUserStagingListResponse:
    query = select(BonificaUserStaging).order_by(
        BonificaUserStaging.updated_at.desc(),
        BonificaUserStaging.created_at.desc(),
    )
    if review_status:
        query = query.where(BonificaUserStaging.review_status == review_status)

    tokens = [token.strip().lower() for token in (search or "").split() if token.strip()]
    for token in tokens:
        term = f"%{token}%"
        query = query.where(
            or_(
                func.lower(func.coalesce(BonificaUserStaging.username, "")).like(term),
                func.lower(func.coalesce(BonificaUserStaging.email, "")).like(term),
                func.lower(func.coalesce(BonificaUserStaging.business_name, "")).like(term),
                func.lower(func.coalesce(BonificaUserStaging.first_name, "")).like(term),
                func.lower(func.coalesce(BonificaUserStaging.last_name, "")).like(term),
                func.lower(func.coalesce(BonificaUserStaging.tax, "")).like(term),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return BonificaUserStagingListResponse(
        items=[_serialize_bonifica_staging(db, item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/bonifica-staging/bulk-approve", response_model=BonificaUserStagingBulkApproveResponse)
def bulk_approve_bonifica_staging(
    payload: BonificaUserStagingBulkApproveRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> BonificaUserStagingBulkApproveResponse:
    approved = 0
    skipped = 0
    errors: list[str] = []

    for raw_id in payload.ids:
        try:
            staging_id = uuid.UUID(raw_id)
        except ValueError:
            errors.append(f"{raw_id}: invalid uuid")
            continue

        staging = db.get(BonificaUserStaging, staging_id)
        if staging is None:
            errors.append(f"{raw_id}: staging item not found")
            continue
        if staging.review_status != "new":
            skipped += 1
            continue
        _approve_bonifica_staging_item(db, current_user, staging)
        approved += 1

    return BonificaUserStagingBulkApproveResponse(
        approved=approved,
        skipped=skipped,
        errors=errors,
    )


@router.get("/bonifica-staging/{staging_id}", response_model=BonificaUserStagingResponse)
def get_bonifica_staging_item(
    staging_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> BonificaUserStagingResponse:
    staging = _require_bonifica_staging_exists(db, staging_id)
    return _serialize_bonifica_staging(db, staging)


@router.post("/bonifica-staging/{staging_id}/approve", response_model=BonificaUserStagingResponse)
def approve_bonifica_staging_item(
    staging_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> BonificaUserStagingResponse:
    staging = _require_bonifica_staging_exists(db, staging_id)
    return _approve_bonifica_staging_item(db, current_user, staging)


@router.post("/bonifica-staging/{staging_id}/reject", response_model=BonificaUserStagingResponse)
def reject_bonifica_staging_item(
    staging_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> BonificaUserStagingResponse:
    staging = _require_bonifica_staging_exists(db, staging_id)
    staging.review_status = "rejected"
    staging.reviewed_by = current_user.id
    staging.reviewed_at = datetime.now(timezone.utc)
    db.add(staging)
    db.commit()
    return _serialize_bonifica_staging(db, staging)


@router.post("/subjects", response_model=AnagraficaSubjectDetailResponse, status_code=status.HTTP_201_CREATED)
def create_subject(
    payload: AnagraficaSubjectCreateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaSubjectDetailResponse:
    _validate_subject_payload(payload.subject_type, payload.person, payload.company)
    duplicate_identifier = _find_duplicate_codice_fiscale(db, payload.person, payload.company)
    if duplicate_identifier is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Esiste gia un utente registrato con codice fiscale {duplicate_identifier}.",
        )
    letter_norm = (payload.nas_folder_letter or "").strip().upper() or None
    computed_nas_path = canonical_subject_nas_folder_path(
        source_name_raw=payload.source_name_raw,
        nas_folder_letter=letter_norm,
    )
    external_ref = (payload.source_external_id or "").strip()
    subject = AnagraficaSubject(
        subject_type=payload.subject_type,
        status=AnagraficaSubjectStatus.ACTIVE.value,
        source_name_raw=payload.source_name_raw,
        source_external_id=external_ref or None,
        nas_folder_path=computed_nas_path,
        nas_folder_letter=letter_norm,
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
    _: Annotated[ApplicationUser, RequireUtenzeModule],
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


@router.post("/subjects/import-xlsx", response_model=XlsxImportStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def import_subjects_xlsx(
    file: Annotated[UploadFile, File()],
    background_tasks: BackgroundTasks,
    current_user: Annotated[ApplicationUser, Depends(require_admin_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> XlsxImportStartResponse:
    filename = (file.filename or "").strip()
    if not filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Il file deve essere un Excel (.xlsx)")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File Excel vuoto")

    batch = AnagraficaXlsxImportBatch(
        requested_by_user_id=current_user.id,
        filename=filename,
        status=AnagraficaXlsxImportBatchStatus.PENDING.value,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    batch_id = batch.id

    def _run_in_thread() -> None:
        from app.core.database import SessionLocal
        with SessionLocal() as session:
            run_xlsx_import(session, batch_id, file_bytes, current_user)

    background_tasks.add_task(_run_in_thread)

    return XlsxImportStartResponse(
        batch_id=str(batch_id),
        status=AnagraficaXlsxImportBatchStatus.PENDING.value,
        message=f"Import avviato per il file '{filename}'. Usa batch_id per monitorare l'avanzamento.",
    )


@router.get("/xlsx-import-batches", response_model=list[XlsxImportBatchResponse])
def get_xlsx_import_batches(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> list[XlsxImportBatchResponse]:
    batches = db.scalars(
        select(AnagraficaXlsxImportBatch).order_by(AnagraficaXlsxImportBatch.created_at.desc()).limit(20)
    ).all()
    return [_serialize_xlsx_batch(b) for b in batches]


@router.get("/xlsx-import-batches/{batch_id}", response_model=XlsxImportBatchResponse)
def get_xlsx_import_batch(
    batch_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> XlsxImportBatchResponse:
    batch = db.get(AnagraficaXlsxImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch non trovato")
    return _serialize_xlsx_batch(batch)


@router.get("/subjects/{subject_id}/audit-log", response_model=list[AnagraficaAuditLogResponse])
def get_subject_audit_log(
    subject_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AnagraficaAuditLogResponse]:
    _require_subject_exists(db, subject_id)
    entries = db.scalars(
        select(AnagraficaAuditLog)
        .where(AnagraficaAuditLog.subject_id == subject_id)
        .order_by(AnagraficaAuditLog.changed_at.desc())
        .limit(limit)
    ).all()
    return [
        AnagraficaAuditLogResponse.model_validate({
            "id": str(e.id),
            "subject_id": str(e.subject_id),
            "changed_by_user_id": e.changed_by_user_id,
            "action": e.action,
            "diff_json": e.diff_json,
            "changed_at": e.changed_at,
        })
        for e in entries
    ]


@router.get("/subjects/{subject_id}", response_model=AnagraficaSubjectDetailResponse)
def get_subject(
    subject_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaSubjectDetailResponse:
    return _build_subject_detail(db, subject_id)


@router.post("/subjects/{subject_id}/import-from-nas", response_model=AnagraficaSubjectImportResponse)
def post_import_subject_from_nas(
    subject_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AnagraficaImportPreviewService, Depends(get_anagrafica_import_service)],
) -> AnagraficaSubjectImportResponse:
    try:
        result = import_subject_from_existing_registry(
            db,
            current_user=current_user,
            subject_id=subject_id,
            service=service,
        )
    except ValueError as exc:
        db.rollback()
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(exc).lower() else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except NasConnectorError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return AnagraficaSubjectImportResponse(
        subject_id=str(result.subject_id),
        matched_folder_path=result.matched_folder_path,
        matched_folder_name=result.matched_folder_name,
        warning_count=result.warning_count,
        created_documents=result.created_documents,
        updated_documents=result.updated_documents,
        imported_at=result.imported_at,
    )


@router.get("/subjects/{subject_id}/nas-import-status", response_model=AnagraficaSubjectNasImportStatusResponse)
def get_subject_nas_import_status(
    subject_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AnagraficaImportPreviewService, Depends(get_anagrafica_import_service)],
) -> AnagraficaSubjectNasImportStatusResponse:
    try:
        subject = _require_subject_exists(db, subject_id)
        status_payload = service.get_subject_import_status(db, subject)
    except NasConnectorError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    finally:
        _close_import_service(service)

    return AnagraficaSubjectNasImportStatusResponse(
        can_import_from_nas=status_payload.can_import_from_nas,
        missing_in_nas=status_payload.missing_in_nas,
        matched_folder_path=status_payload.matched_folder_path,
        matched_folder_name=status_payload.matched_folder_name,
        total_files_in_nas=status_payload.total_files_in_nas,
        pending_files_in_nas=status_payload.pending_files_in_nas,
        message=status_payload.message,
    )


@router.get("/subjects/{subject_id}/nas-candidates", response_model=list[AnagraficaNasFolderCandidateResponse])
def get_subject_nas_candidates(
    subject_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AnagraficaImportPreviewService, Depends(get_anagrafica_import_service)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[AnagraficaNasFolderCandidateResponse]:
    try:
        subject = _require_subject_exists(db, subject_id)
        candidates = service.list_existing_subject_folder_candidates(db, subject, limit=limit)
    except NasConnectorError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    finally:
        _close_import_service(service)

    return [
        AnagraficaNasFolderCandidateResponse(
            folder_name=item.folder_name,
            letter=item.letter,
            nas_folder_path=item.nas_folder_path,
            score=item.score,
            subject_type=item.subject_type,
            confidence=item.confidence,
            requires_review=item.requires_review,
            codice_fiscale=item.codice_fiscale,
            partita_iva=item.partita_iva,
            ragione_sociale=item.ragione_sociale,
            cognome=item.cognome,
            nome=item.nome,
        )
        for item in candidates
    ]


@router.put("/subjects/{subject_id}", response_model=AnagraficaSubjectDetailResponse)
def update_subject(
    subject_id: uuid.UUID,
    payload: AnagraficaSubjectUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
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
    _: Annotated[ApplicationUser, RequireUtenzeModule],
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
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> list[AnagraficaPreviewDocumentResponse]:
    _require_subject_exists(db, subject_id)
    documents = db.scalars(
        select(AnagraficaDocument)
        .where(AnagraficaDocument.subject_id == subject_id)
        .order_by(AnagraficaDocument.created_at.desc())
    ).all()
    return [_build_document_response(item) for item in documents if not _should_skip_document(item)]


@router.post("/subjects/{subject_id}/documents/upload", response_model=AnagraficaPreviewDocumentResponse)
async def upload_subject_document(
    subject_id: uuid.UUID,
    file: Annotated[UploadFile, File()],
    doc_type: Annotated[str, Form()],
    notes: Annotated[str | None, Form()] = None,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)] = None,
    _: Annotated[ApplicationUser, RequireUtenzeModule] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> AnagraficaPreviewDocumentResponse:
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nome file mancante")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File vuoto")

    try:
        document = create_manual_document(
            db=db,
            current_user=current_user,
            subject_id=subject_id,
            filename=filename,
            file_bytes=file_bytes,
            doc_type=doc_type,
            mime_type=file.content_type,
            notes=notes,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except NasConnectorError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return _build_document_response(document)


@router.patch("/documents/{document_id}", response_model=AnagraficaPreviewDocumentResponse)
def patch_document(
    document_id: uuid.UUID,
    payload: AnagraficaDocumentUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
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
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
    delete_password: Annotated[str | None, Header(alias="X-GAIA-Delete-Password")] = None,
) -> None:
    expected_password = (settings.utenze_delete_password or settings.anagrafica_delete_password or "").strip()
    if expected_password:
        provided_password = (delete_password or "").strip()
        if not provided_password or not secrets.compare_digest(provided_password, expected_password):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Password di cancellazione non valida")

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


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    document = db.get(AnagraficaDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if not document.local_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File locale non disponibile per questo documento")

    local_path = Path(document.local_path)
    if not local_path.exists() or not local_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File documento non trovato sul server")

    media_type = document.mime_type or mimetypes.guess_type(document.filename)[0] or "application/octet-stream"
    return FileResponse(
        path=local_path,
        media_type=media_type,
        filename=document.filename,
    )


@router.post("/reset", response_model=AnagraficaResetResponse)
def post_reset_anagrafica(
    payload: AnagraficaResetRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaResetResponse:
    confirm_text = payload.confirm.strip().upper()
    if confirm_text not in {"RESET UTENZE", "RESET ANAGRAFICA"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Conferma non valida. Usa esattamente 'RESET UTENZE'.",
        )

    result = reset_anagrafica_data(db)
    return AnagraficaResetResponse(
        cleared_subject_links=result.cleared_subject_links,
        deleted_documents=result.deleted_documents,
        deleted_audit_logs=result.deleted_audit_logs,
        deleted_import_jobs=result.deleted_import_jobs,
        deleted_import_job_items=result.deleted_import_job_items,
        deleted_storage_files=result.deleted_storage_files,
    )


@router.get("/stats", response_model=AnagraficaStatsResponse)
def get_stats(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaStatsResponse:
    visible_document_condition = _visible_document_condition()

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
    total_documents = db.scalar(
        select(func.count()).select_from(AnagraficaDocument).where(visible_document_condition)
    ) or 0
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
        select(func.count())
        .select_from(AnagraficaDocument)
        .where(AnagraficaDocument.doc_type == AnagraficaDocType.ALTRO.value, visible_document_condition)
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


@router.get("/documents/summary", response_model=AnagraficaDocumentSummaryResponse)
def get_documents_summary(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaDocumentSummaryResponse:
    visible_document_condition = _visible_document_condition()

    total_documents = db.scalar(
        select(func.count()).select_from(AnagraficaDocument).where(visible_document_condition)
    ) or 0
    documents_unclassified = db.scalar(
        select(func.count())
        .select_from(AnagraficaDocument)
        .where(AnagraficaDocument.doc_type == AnagraficaDocType.ALTRO.value, visible_document_condition)
    ) or 0
    classified_documents = max(total_documents - documents_unclassified, 0)

    buckets = db.execute(
        select(AnagraficaDocument.doc_type, func.count())
        .where(visible_document_condition)
        .group_by(AnagraficaDocument.doc_type)
        .order_by(func.count().desc(), AnagraficaDocument.doc_type.asc())
    ).all()

    recent_unclassified_documents = db.scalars(
        select(AnagraficaDocument)
        .where(AnagraficaDocument.doc_type == AnagraficaDocType.ALTRO.value, visible_document_condition)
        .order_by(AnagraficaDocument.created_at.desc())
        .limit(12)
    ).all()

    recent_unclassified = []
    for document in recent_unclassified_documents:
        subject = db.get(AnagraficaSubject, document.subject_id)
        if subject is None:
            continue
        recent_unclassified.append(
            AnagraficaDocumentSummaryItemResponse(
                document_id=str(document.id),
                subject_id=str(subject.id),
                subject_display_name=_subject_display_name(db, subject),
                filename=document.filename,
                doc_type=document.doc_type,
                classification_source=document.classification_source,
                created_at=document.created_at,
            )
        )

    return AnagraficaDocumentSummaryResponse(
        total_documents=total_documents,
        documents_unclassified=documents_unclassified,
        classified_documents=classified_documents,
        by_doc_type=[
            AnagraficaDocumentSummaryBucketResponse(doc_type=str(doc_type), count=int(count))
            for doc_type, count in buckets
        ],
        recent_unclassified=recent_unclassified,
    )


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
            snapshot_person_if_changed(
                db,
                existing_person,
                person_payload,
                source_system=subject.source_system or "gaia",
                source_ref=subject.source_external_id,
            )
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


def _find_duplicate_codice_fiscale(
    db: Session,
    person: AnagraficaPersonPayload | None,
    company: AnagraficaCompanyPayload | None,
) -> str | None:
    if person is not None and person.codice_fiscale:
        normalized_cf = person.codice_fiscale.replace(" ", "").upper()
        existing_person = db.scalar(
            select(AnagraficaPerson).where(
                func.upper(func.replace(AnagraficaPerson.codice_fiscale, " ", "")) == normalized_cf
            )
        )
        if existing_person is not None:
            return normalized_cf

    if company is not None and company.codice_fiscale:
        normalized_cf = company.codice_fiscale.replace(" ", "").upper()
        existing_company = db.scalar(
            select(AnagraficaCompany).where(
                func.upper(func.replace(func.coalesce(AnagraficaCompany.codice_fiscale, ""), " ", "")) == normalized_cf
            )
        )
        if existing_company is not None:
            return normalized_cf

    return None


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


def _normalize_bonifica_tax(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.replace(" ", "").strip().upper()
    return normalized or None


def _staging_display_name(staging: BonificaUserStaging) -> str:
    if staging.business_name:
        return staging.business_name
    full_name = " ".join(part for part in [staging.last_name, staging.first_name] if part).strip()
    if full_name:
        return full_name
    return staging.username or f"Consorziato {staging.wc_id}"


def _serialize_bonifica_staging(db: Session, staging: BonificaUserStaging) -> BonificaUserStagingResponse:
    matched_subject_display_name = None
    if staging.matched_subject_id:
        subject = db.get(AnagraficaSubject, staging.matched_subject_id)
        if subject is not None:
            matched_subject_display_name = _subject_display_name(db, subject)
    return BonificaUserStagingResponse(
        id=str(staging.id),
        wc_id=staging.wc_id,
        username=staging.username,
        email=staging.email,
        user_type=staging.user_type,
        business_name=staging.business_name,
        first_name=staging.first_name,
        last_name=staging.last_name,
        tax=staging.tax,
        phone=staging.phone,
        mobile=staging.mobile,
        role=staging.role,
        enabled=staging.enabled,
        wc_synced_at=staging.wc_synced_at,
        review_status=staging.review_status,
        matched_subject_id=str(staging.matched_subject_id) if staging.matched_subject_id else None,
        matched_subject_display_name=matched_subject_display_name,
        mismatch_fields=staging.mismatch_fields,
        reviewed_by=staging.reviewed_by,
        reviewed_at=staging.reviewed_at,
        created_at=staging.created_at,
        updated_at=staging.updated_at,
    )


def _require_bonifica_staging_exists(db: Session, staging_id: uuid.UUID) -> BonificaUserStaging:
    staging = db.get(BonificaUserStaging, staging_id)
    if staging is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bonifica staging item not found")
    return staging


def _infer_staging_subject_type(staging: BonificaUserStaging) -> str:
    user_type = (staging.user_type or "").strip().lower()
    if user_type == "company" or staging.business_name:
        return "company"
    if user_type == "private" or staging.first_name or staging.last_name:
        return "person"
    return "unknown"


def _build_staging_person_payload(staging: BonificaUserStaging) -> AnagraficaPersonPayload:
    normalized_tax = _normalize_bonifica_tax(staging.tax)
    if normalized_tax is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Codice fiscale mancante nel record Bonifica")
    if not staging.first_name or not staging.last_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nome e cognome sono obbligatori per approvare un consorziato persona fisica")
    return AnagraficaPersonPayload(
        cognome=staging.last_name,
        nome=staging.first_name,
        codice_fiscale=normalized_tax,
        email=staging.email,
        telefono=staging.mobile or staging.phone,
        note="Creato da staging Bonifica Oristanese",
    )


def _build_staging_company_payload(staging: BonificaUserStaging) -> AnagraficaCompanyPayload:
    normalized_tax = _normalize_bonifica_tax(staging.tax)
    if normalized_tax is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Partita IVA / codice fiscale mancante nel record Bonifica")
    if not staging.business_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Ragione sociale mancante nel record Bonifica")
    company_cf = None if normalized_tax.isdigit() and len(normalized_tax) == 11 else normalized_tax
    return AnagraficaCompanyPayload(
        ragione_sociale=staging.business_name,
        partita_iva=normalized_tax,
        codice_fiscale=company_cf,
        email_pec=staging.email,
        telefono=staging.mobile or staging.phone,
        note="Creato da staging Bonifica Oristanese",
    )


def _approve_bonifica_staging_item(
    db: Session,
    current_user: ApplicationUser,
    staging: BonificaUserStaging,
) -> BonificaUserStagingResponse:
    if staging.review_status == "rejected":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Il record è stato rifiutato manualmente")

    subject_type = _infer_staging_subject_type(staging)
    source_name_raw = _staging_display_name(staging)

    if subject_type == "person":
        person_payload = _build_staging_person_payload(staging)
        company_payload = None
    elif subject_type == "company":
        person_payload = None
        company_payload = _build_staging_company_payload(staging)
    else:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Impossibile inferire il tipo soggetto dal record Bonifica")

    if staging.review_status == "new":
        subject = AnagraficaSubject(
            subject_type=subject_type,
            status=AnagraficaSubjectStatus.ACTIVE.value,
            source_system="whitecompany",
            source_external_id=str(staging.wc_id),
            source_name_raw=source_name_raw,
            requires_review=False,
            imported_at=datetime.now(timezone.utc),
        )
        db.add(subject)
        db.flush()
        _apply_subject_payload(db, subject, subject_type, person_payload, company_payload)
        _create_subject_audit(
            db,
            subject.id,
            current_user.id,
            "bonifica_staging_approved_create",
            {"wc_id": staging.wc_id, "review_status": staging.review_status},
        )
    else:
        if staging.matched_subject_id is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Il record staging non è collegato a un soggetto esistente")
        subject = _require_subject_exists(db, staging.matched_subject_id)
        if subject.subject_type != subject_type:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Il tipo soggetto GAIA non è compatibile con il record Bonifica",
            )
        subject.source_system = "whitecompany"
        subject.source_external_id = str(staging.wc_id)
        subject.source_name_raw = source_name_raw
        subject.status = AnagraficaSubjectStatus.ACTIVE.value
        subject.requires_review = False
        subject.imported_at = subject.imported_at or datetime.now(timezone.utc)
        _apply_subject_payload(db, subject, subject_type, person_payload, company_payload)
        _create_subject_audit(
            db,
            subject.id,
            current_user.id,
            "bonifica_staging_approved_update",
            {"wc_id": staging.wc_id, "review_status": staging.review_status},
        )

    staging.matched_subject_id = subject.id
    staging.review_status = "matched"
    staging.mismatch_fields = None
    staging.reviewed_by = current_user.id
    staging.reviewed_at = datetime.now(timezone.utc)
    db.add(staging)
    db.commit()
    return _serialize_bonifica_staging(db, staging)


def _build_subject_list_item(db: Session, subject: AnagraficaSubject) -> AnagraficaSubjectListItemResponse:
    display_name, codice_fiscale, partita_iva = _subject_identity_summary(db, subject)
    document_count = db.scalar(
        select(func.count())
        .select_from(AnagraficaDocument)
        .where(AnagraficaDocument.subject_id == subject.id, _visible_document_condition())
    ) or 0
    return AnagraficaSubjectListItemResponse(
        id=str(subject.id),
        subject_type=subject.subject_type,
        status=subject.status,
        source_system=subject.source_system,
        source_external_id=subject.source_external_id,
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


def _subject_identity_summary(db: Session, subject: AnagraficaSubject) -> tuple[str, str | None, str | None]:
    person = db.get(AnagraficaPerson, subject.id)
    company = db.get(AnagraficaCompany, subject.id)
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
    return display_name, codice_fiscale, partita_iva


def _subject_display_name(db: Session, subject: AnagraficaSubject) -> str:
    display_name, _, _ = _subject_identity_summary(db, subject)
    return display_name


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


def _should_skip_document(document: AnagraficaDocument) -> bool:
    return document.filename.strip().lower() == "thumbs.db"


def _visible_document_condition():
    return func.lower(func.trim(AnagraficaDocument.filename)) != "thumbs.db"


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


def _serialize_xlsx_batch(batch: AnagraficaXlsxImportBatch) -> XlsxImportBatchResponse:
    return XlsxImportBatchResponse.model_validate({
        "id": str(batch.id),
        "requested_by_user_id": batch.requested_by_user_id,
        "filename": batch.filename,
        "status": batch.status,
        "total_rows": batch.total_rows,
        "processed_rows": batch.processed_rows,
        "inserted": batch.inserted,
        "updated": batch.updated,
        "unchanged": batch.unchanged,
        "anomalies": batch.anomalies,
        "errors": batch.errors,
        "error_log": batch.error_log,
        "created_at": batch.created_at,
        "started_at": batch.started_at,
        "completed_at": batch.completed_at,
        "updated_at": batch.updated_at,
    })


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
    documents = [item for item in documents if not _should_skip_document(item)]
    audit_entries = db.scalars(
        select(AnagraficaAuditLog)
        .where(AnagraficaAuditLog.subject_id == subject_id)
        .order_by(AnagraficaAuditLog.changed_at.desc())
    ).all()
    person_snapshots = db.scalars(
        select(AnagraficaPersonSnapshot)
        .where(AnagraficaPersonSnapshot.subject_id == subject_id)
        .order_by(AnagraficaPersonSnapshot.collected_at.desc())
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
                    "anpr_id": person.anpr_id,
                    "stato_anpr": person.stato_anpr,
                    "data_decesso": person.data_decesso,
                    "luogo_decesso_comune": person.luogo_decesso_comune,
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
        source_system=subject.source_system,
        source_external_id=subject.source_external_id,
        source_name_raw=subject.source_name_raw,
        nas_folder_path=subject.nas_folder_path,
        nas_folder_letter=subject.nas_folder_letter,
        requires_review=subject.requires_review,
        imported_at=subject.imported_at,
        created_at=subject.created_at,
        updated_at=subject.updated_at,
        person=person_response,
        person_snapshots=[
            AnagraficaPersonSnapshotResponse.model_validate(
                {
                    "id": str(item.id),
                    "subject_id": str(item.subject_id),
                    "is_capacitas_history": item.is_capacitas_history,
                    "source_system": item.source_system,
                    "source_ref": item.source_ref,
                    "cognome": item.cognome,
                    "nome": item.nome,
                    "codice_fiscale": item.codice_fiscale,
                    "data_nascita": item.data_nascita,
                    "comune_nascita": item.comune_nascita,
                    "indirizzo": item.indirizzo,
                    "comune_residenza": item.comune_residenza,
                    "cap": item.cap,
                    "email": item.email,
                    "telefono": item.telefono,
                    "note": item.note,
                    "valid_from": item.valid_from,
                    "collected_at": item.collected_at,
                }
            )
            for item in person_snapshots
        ],
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
