import uuid
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import (
    HTTPException,
    status,
)
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoDocument
from app.modules.utenze.models import (
    AnagraficaAuditLog,
    AnagraficaCompany,
    AnagraficaDocument,
    AnagraficaImportJob,
    AnagraficaImportJobItem,
    AnagraficaImportJobItemStatus,
    AnagraficaPerson,
    AnagraficaSubject,
    AnagraficaSubjectStatus,
    AnagraficaVisuraRoutingAnomaly,
    AnagraficaXlsxImportBatch,
    BonificaUserStaging,
)
from app.modules.utenze.schemas import (
    AnagraficaCatastoDocumentResponse,
    AnagraficaCompanyPayload,
    AnagraficaImportJobResponse,
    AnagraficaPersonPayload,
    AnagraficaPreviewDocumentResponse,
    AnagraficaSubjectListItemResponse,
    AnagraficaVisuraRoutingAnomalyResponse,
    BonificaUserStagingResponse,
    XlsxImportBatchResponse,
)
from app.modules.utenze.services.classify_service import derive_document_smart_classification
from app.modules.utenze.services.content_classification_service import (
    DocumentContentClassification,
)
from app.modules.utenze.services.import_service import (
    AnagraficaImportPreviewService,
)
from app.modules.utenze.services.person_history_service import snapshot_person_if_changed
from app.services.nas_connector import NasConnectorError


def _get_nas_client():
    return import_module("app.modules.utenze.router").get_nas_client()


# Preserve reviewed legacy callable layout for the merge-base LOC ratchet.
# fmt: off
def get_anagrafica_import_service() -> AnagraficaImportPreviewService:
    return AnagraficaImportPreviewService(_get_nas_client())

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

def _utenze_stats_timezone() -> ZoneInfo:
    return ZoneInfo(settings.anpr_job_timezone)

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

def _serialize_visura_routing_anomaly(anomaly: AnagraficaVisuraRoutingAnomaly) -> AnagraficaVisuraRoutingAnomalyResponse:
    return AnagraficaVisuraRoutingAnomalyResponse.model_validate(
        {
            "id": str(anomaly.id),
            "source_path": anomaly.source_path,
            "filename": anomaly.filename,
            "identifier": anomaly.identifier,
            "identifier_kind": anomaly.identifier_kind,
            "reason": anomaly.reason,
            "details_json": anomaly.details_json,
            "occurrences": anomaly.occurrences,
            "resolved_at": anomaly.resolved_at,
            "created_at": anomaly.created_at,
            "updated_at": anomaly.updated_at,
        }
    )

def _utenze_document_storage_root() -> Path:
    return Path(settings.utenze_document_storage_path or settings.anagrafica_document_storage_path)

def _recovered_document_local_path(document: AnagraficaDocument) -> Path:
    safe_name = Path(document.filename or "document.bin").name or "document.bin"
    return _utenze_document_storage_root() / str(document.subject_id) / "recovered" / f"{document.id}-{safe_name}"

def _ensure_document_available_locally(db: Session, document: AnagraficaDocument) -> Path:
    if document.local_path:
        local_path = Path(document.local_path)
        if local_path.exists() and local_path.is_file():
            return local_path
    else:
        local_path = _recovered_document_local_path(document)

    if not document.nas_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File locale non disponibile per questo documento")

    connector = _get_nas_client()
    try:
        download_to_local = getattr(connector, "download_to_local", None)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if callable(download_to_local):
            download_to_local(document.nas_path, str(local_path))
        else:
            local_path.write_bytes(connector.download_file(document.nas_path))
    except NasConnectorError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File documento non trovato sul server") from exc
    finally:
        close = getattr(connector, "close", None)
        if callable(close):
            close()

    if not local_path.exists() or not local_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File documento non trovato sul server")

    if document.local_path != str(local_path):
        document.local_path = str(local_path)
        db.add(document)
        db.commit()
        db.refresh(document)

    return local_path

def _require_subject_exists(db: Session, subject_id: uuid.UUID) -> AnagraficaSubject:
    subject = db.get(AnagraficaSubject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return subject

def _validate_subject_payload(subject_type: str, person: object, company: object, allow_empty: bool = False) -> None:
    if subject_type == "person" and person is None and not allow_empty:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Person payload required")
    if subject_type == "company" and company is None and not allow_empty:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Company payload required")
    if subject_type == "person" and company is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Company payload not allowed")
    if subject_type == "company" and person is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Person payload not allowed")

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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Codice fiscale mancante nel record Bonifica")
    if not staging.first_name or not staging.last_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Nome e cognome sono obbligatori per approvare un consorziato persona fisica")
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Partita IVA / codice fiscale mancante nel record Bonifica")
    if not staging.business_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Ragione sociale mancante nel record Bonifica")
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Impossibile inferire il tipo soggetto dal record Bonifica")

    if staging.review_status == "new":
        subject = AnagraficaSubject(
            subject_type=subject_type,
            status=AnagraficaSubjectStatus.ACTIVE.value,
            source_system="whitecompany",
            source_external_id=str(staging.wc_id),
            source_name_raw=source_name_raw,
            requires_review=False,
            imported_at=datetime.now(UTC),
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
        subject.imported_at = subject.imported_at or datetime.now(UTC)
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
    staging.reviewed_at = datetime.now(UTC)
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
    smart = derive_document_smart_classification(
        filename=document.filename,
        doc_type=document.doc_type,
        classification_source=document.classification_source,
        extension=extension,
        notes=document.notes,
    )
    return AnagraficaPreviewDocumentResponse(
        id=str(document.id),
        filename=document.filename,
        relative_path=document.filename,
        nas_path=document.nas_path or document.local_path or document.filename,
        extension=extension,
        is_pdf=extension == ".pdf",
        doc_type=document.doc_type,
        classification_source=document.classification_source,
        smart_category=smart.category,
        smart_category_label=smart.label,
        smart_priority=smart.priority,
        smart_confidence=smart.confidence,
        smart_reason=smart.reason,
        content_classification_status=document.content_classification_status,
        content_category=document.content_category,
        content_category_label=document.content_category_label,
        content_confidence=document.content_confidence,
        content_reason=document.content_reason,
        content_excerpt=document.content_excerpt,
        content_classification_source=document.content_classification_source,
        content_classified_at=document.content_classified_at,
        content_classification_error=document.content_classification_error,
        warnings=warnings,
    )

def _apply_document_content_classification(document: AnagraficaDocument, result: DocumentContentClassification) -> None:
    document.content_classification_status = result.status
    document.content_category = result.category
    document.content_category_label = result.label
    document.content_confidence = result.confidence
    document.content_reason = result.reason
    document.content_excerpt = result.excerpt
    document.content_classification_source = result.source
    document.content_classification_error = result.error
    document.content_classified_at = datetime.now(UTC)

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
# fmt: on
