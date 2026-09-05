import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_admin_user, require_module
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.utenze.models import (
    AnagraficaAuditLog,
    AnagraficaDocument,
    AnagraficaPaymentNotice,
    AnagraficaSubject,
    AnagraficaSubjectStatus,
    AnagraficaXlsxImportBatch,
    AnagraficaXlsxImportBatchStatus,
)
from app.modules.utenze.routes.subject_detail import _build_subject_detail
from app.modules.utenze.routes.support import (
    _apply_subject_payload,
    _build_document_response,
    _close_import_service,
    _create_subject_audit,
    _find_duplicate_codice_fiscale,
    _require_subject_exists,
    _serialize_xlsx_batch,
    _should_skip_document,
    _validate_subject_payload,
    get_anagrafica_import_service,
)
from app.modules.utenze.schemas import (
    AnagraficaAuditLogResponse,
    AnagraficaCsvImportResponse,
    AnagraficaNasFolderCandidateResponse,
    AnagraficaPaymentNoticePdfResponse,
    AnagraficaPaymentNoticeResponse,
    AnagraficaPreviewDocumentResponse,
    AnagraficaSubjectCreateRequest,
    AnagraficaSubjectDetailResponse,
    AnagraficaSubjectImportResponse,
    AnagraficaSubjectNasImportStatusResponse,
    AnagraficaSubjectUpdateRequest,
    XlsxImportBatchResponse,
    XlsxImportStartResponse,
)
from app.modules.utenze.services.csv_import_service import import_subjects_from_csv
from app.modules.utenze.services.import_service import (
    AnagraficaImportPreviewService,
    create_manual_document,
    import_subject_from_existing_registry,
)
from app.modules.utenze.services.nas_path_service import canonical_subject_nas_folder_path
from app.modules.utenze.services.xlsx_import_service import run_xlsx_import
from app.services.elaborazioni_capacitas_incass import classify_payment_notice
from app.services.nas_connector import NasConnectorError

router = APIRouter(tags=["utenze"])
RequireUtenzeModule = Depends(require_module("utenze"))


# Preserve reviewed legacy callable layout for the merge-base LOC ratchet.
# fmt: off
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Il file deve essere un CSV")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="File CSV vuoto")

    try:
        result = import_subjects_from_csv(db, current_user=current_user, file_bytes=file_bytes)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Il file deve essere un Excel (.xlsx)")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="File Excel vuoto")

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

@router.get("/subjects/{subject_id}/payment-notices", response_model=list[AnagraficaPaymentNoticeResponse])
def get_subject_payment_notices(
    subject_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=300),
) -> list[AnagraficaPaymentNoticeResponse]:
    _require_subject_exists(db, subject_id)
    notices = db.scalars(
        select(AnagraficaPaymentNotice)
        .where(AnagraficaPaymentNotice.subject_id == subject_id)
        .order_by(
            AnagraficaPaymentNotice.anno.desc().nullslast(),
            AnagraficaPaymentNotice.data_scadenza.desc().nullslast(),
            AnagraficaPaymentNotice.updated_at.desc(),
        )
        .limit(limit)
    ).all()
    payload: list[AnagraficaPaymentNoticeResponse] = []
    for notice in notices:
        pdf_links = [
            AnagraficaPaymentNoticePdfResponse.model_validate(item)
            for item in (notice.pdf_links_json or [])
            if isinstance(item, dict)
        ]
        payload.append(
            AnagraficaPaymentNoticeResponse.model_validate(
                {
                    "id": str(notice.id),
                    "subject_id": str(notice.subject_id) if notice.subject_id else None,
                    "source_system": notice.source_system,
                    "source_notice_id": notice.source_notice_id,
                    "source_internal_id": notice.source_internal_id,
                    "codice_fiscale": notice.codice_fiscale,
                    "partita_iva": notice.partita_iva,
                    "display_name": notice.display_name,
                    "anno": notice.anno,
                    "stato_code": notice.stato_code,
                    "stato_label": notice.stato_label,
                    "data_scadenza": notice.data_scadenza,
                    "data_pagamento": notice.data_pagamento,
                    "tipo_anagrafica": notice.tipo_anagrafica,
                    "ultimo_invio": notice.ultimo_invio,
                    "lista_id": notice.lista_id,
                    "lista_descrizione": notice.lista_descrizione,
                    "indirizzo": notice.indirizzo,
                    "cap": notice.cap,
                    "citta": notice.citta,
                    "provincia": notice.provincia,
                    "importo_carico": notice.importo_carico,
                    "importo_sgravio": notice.importo_sgravio,
                    "importo_riscosso": notice.importo_riscosso,
                    "importo_residuo": notice.importo_residuo,
                    "importo_riporto": notice.importo_riporto,
                    "importo_rateizzato": notice.importo_rateizzato,
                    "importo_annullato": notice.importo_annullato,
                    "payment_status": classify_payment_notice(notice),
                    "detail_url": notice.detail_url,
                    "detail_info_text": notice.detail_info_text,
                    "pdf_links": pdf_links,
                    "synced_at": notice.synced_at,
                    "created_at": notice.created_at,
                    "updated_at": notice.updated_at,
                }
            )
        )
    return payload

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
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(exc).lower() else status.HTTP_422_UNPROCESSABLE_CONTENT
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Nome file mancante")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="File vuoto")

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
# fmt: on
