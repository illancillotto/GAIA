from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timezone
import logging
import mimetypes
from pathlib import Path, PurePosixPath
import re
from uuid import UUID

import httpx
from sqlalchemy import exists, delete, or_, select
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.capacitas import CapacitasInCassSyncJob
from app.modules.elaborazioni.capacitas.apps.incass.client import (
    CapacitasInCassSessionExpiredError,
    InCassClient,
)
from app.modules.elaborazioni.capacitas.models import (
    CapacitasInCassMailingContactRow,
    CapacitasInCassMailingData,
    CapacitasInCassMailingReceiptParent,
    CapacitasInCassMailingShipmentRow,
    CapacitasInCassNoticePdf,
    CapacitasInCassNoticeRow,
    CapacitasObjManDocument,
    CapacitasInCassRuoloHarvestRequest,
    CapacitasInCassRuoloHarvestResponse,
    CapacitasInCassSyncItemResult,
    CapacitasInCassSyncJobCreateRequest,
    CapacitasInCassSyncJobOut,
    CapacitasInCassSyncJobResult,
)
from app.modules.ruolo.models import RuoloAvviso
from app.modules.utenze.models import (
    AnagraficaCompany,
    AnagraficaClassificationSource,
    AnagraficaDocType,
    AnagraficaDocument,
    AnagraficaPaymentNotice,
    AnagraficaPerson,
    AnagraficaStorageType,
    AnagraficaSubject,
)
from app.services.nas_connector import get_nas_client

UTC = timezone.utc
logger = logging.getLogger(__name__)
TERMINAL_JOB_STATUSES = {"succeeded", "completed_with_errors", "failed", "cancelled"}
ACTIVE_JOB_STATUSES = {"pending", "processing", "queued_resume"}
INCASS_RETRY_DELAYS_SEC = (1, 3)
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._ -]+")


@dataclass(frozen=True, slots=True)
class PaymentNoticeSyncStatus:
    status: str
    previous_status: str | None
    changed: bool
    newly_paid: bool


def create_incass_sync_job(
    db: Session,
    *,
    requested_by_user_id: int | None,
    credential_id: int | None,
    payload: CapacitasInCassSyncJobCreateRequest,
) -> CapacitasInCassSyncJob:
    job = CapacitasInCassSyncJob(
        credential_id=credential_id or payload.credential_id,
        requested_by_user_id=requested_by_user_id,
        status="pending",
        mode="subjects_sync",
        payload_json=payload.model_dump(mode="json"),
        result_json=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_incass_sync_jobs(db: Session) -> list[CapacitasInCassSyncJob]:
    return list(db.scalars(select(CapacitasInCassSyncJob).order_by(CapacitasInCassSyncJob.id.desc())).all())


def get_incass_sync_job(db: Session, job_id: int) -> CapacitasInCassSyncJob | None:
    return db.get(CapacitasInCassSyncJob, job_id)


def delete_incass_sync_job(db: Session, job: CapacitasInCassSyncJob) -> None:
    db.delete(job)
    db.commit()


def serialize_incass_sync_job(job: CapacitasInCassSyncJob) -> CapacitasInCassSyncJobOut:
    return CapacitasInCassSyncJobOut.model_validate(job)


def load_incass_ruolo_subject_ids(
    db: Session,
    *,
    anno: int | None,
    limit_subjects: int | None,
    exclude_synced_subjects: bool,
    stale_synced_before: datetime | None = None,
) -> list[UUID]:
    stmt = (
        select(RuoloAvviso.subject_id)
        .where(RuoloAvviso.subject_id.is_not(None))
        .group_by(RuoloAvviso.subject_id)
        .order_by(RuoloAvviso.subject_id)
    )
    if anno is not None:
        stmt = stmt.where(RuoloAvviso.anno_tributario == anno)
    if exclude_synced_subjects:
        synced_notice_exists = exists(
            select(AnagraficaPaymentNotice.id).where(
                AnagraficaPaymentNotice.subject_id == RuoloAvviso.subject_id,
                AnagraficaPaymentNotice.source_system == "incass",
            )
        )
        stmt = stmt.where(~synced_notice_exists)
    if stale_synced_before is not None:
        fresh_notice_exists = exists(
            select(AnagraficaPaymentNotice.id).where(
                AnagraficaPaymentNotice.subject_id == RuoloAvviso.subject_id,
                AnagraficaPaymentNotice.source_system == "incass",
                AnagraficaPaymentNotice.synced_at >= stale_synced_before,
            )
        )
        stmt = stmt.where(~fresh_notice_exists)
    if limit_subjects is not None:
        stmt = stmt.limit(limit_subjects)
    return [value for value in db.scalars(stmt).all() if value is not None]


def create_incass_ruolo_harvest_jobs(
    db: Session,
    *,
    requested_by_user_id: int | None,
    payload: CapacitasInCassRuoloHarvestRequest,
) -> CapacitasInCassRuoloHarvestResponse:
    subject_ids = load_incass_ruolo_subject_ids(
        db,
        anno=payload.anno,
        limit_subjects=payload.limit_subjects,
        exclude_synced_subjects=payload.exclude_synced_subjects,
        stale_synced_before=payload.stale_synced_before,
    )
    already_queued_subject_ids = _load_active_incass_subject_ids(db)
    subject_ids = [subject_id for subject_id in subject_ids if subject_id not in already_queued_subject_ids]
    job_ids: list[int] = []
    for index in range(0, len(subject_ids), payload.chunk_size):
        chunk = subject_ids[index:index + payload.chunk_size]
        if not chunk:  # pragma: no cover - chunk_size is validated as >= 1.
            continue
        job = create_incass_sync_job(
            db,
            requested_by_user_id=requested_by_user_id,
            credential_id=payload.credential_id,
            payload=CapacitasInCassSyncJobCreateRequest(
                credential_id=payload.credential_id,
                subject_ids=chunk,
                include_details=payload.include_details,
                include_partitario=payload.include_partitario,
                include_mailing_list=payload.include_mailing_list,
                download_mailing_receipts=payload.download_mailing_receipts,
                continue_on_error=payload.continue_on_error,
                throttle_ms=payload.throttle_ms,
            ),
        )
        job_ids.append(job.id)
    return CapacitasInCassRuoloHarvestResponse(
        anno=payload.anno,
        chunk_size=payload.chunk_size,
        total_subjects=len(subject_ids),
        total_jobs=len(job_ids),
        job_ids=job_ids,
        credential_id=payload.credential_id,
        exclude_synced_subjects=payload.exclude_synced_subjects,
        stale_synced_before=payload.stale_synced_before,
    )


def prepare_incass_sync_jobs_for_recovery(db: Session) -> list[int]:
    jobs = db.scalars(
        select(CapacitasInCassSyncJob).where(
            CapacitasInCassSyncJob.status == "processing",
            CapacitasInCassSyncJob.completed_at.is_(None),
        )
    ).all()
    recovered: list[int] = []
    for job in jobs:
        job.status = "queued_resume"
        job.started_at = None
        job.completed_at = None
        job.error_detail = "Recuperato dopo riavvio worker"
        if isinstance(job.result_json, dict):
            resume_count = int(job.result_json.get("resume_count", 0) or 0) + 1
            job.result_json = {
                **job.result_json,
                "resume_reason": "backend_restart",
                "resume_count": resume_count,
            }
        recovered.append(job.id)
    return recovered


def expire_stale_incass_sync_jobs(db: Session) -> None:
    jobs = db.scalars(
        select(CapacitasInCassSyncJob).where(
            CapacitasInCassSyncJob.status == "processing",
            CapacitasInCassSyncJob.completed_at.isnot(None),
        )
    ).all()
    for job in jobs:
        if job.status not in TERMINAL_JOB_STATUSES:
            job.status = "failed"
            job.error_detail = job.error_detail or "Job in stato incoerente"
    if jobs:
        db.commit()


async def run_incass_sync_job(
    db: Session,
    client: InCassClient,
    job: CapacitasInCassSyncJob,
) -> CapacitasInCassSyncJob:
    payload = CapacitasInCassSyncJobCreateRequest.model_validate(job.payload_json or {})
    subjects = _resolve_subjects(db, payload)
    if not subjects:
        job.status = "failed"
        job.error_detail = "Nessun soggetto con codice fiscale o partita IVA disponibile per il sync inCASS"
        job.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(job)
        return job

    await client.warmup_search_page()

    item_results_map = _load_existing_item_results(job)
    succeeded_subject_ids = {
        subject_id
        for subject_id, item in item_results_map.items()
        if item.status == "succeeded"
    }

    for subject, identifier, display_name in subjects:
        subject_key = str(subject.id)
        if subject_key in succeeded_subject_ids:
            continue
        try:
            item_result = await _sync_incass_subject(
                client=client,
                db=db,
                subject_id=subject.id,
                identifier=identifier,
                display_name=display_name,
                include_details=payload.include_details,
                include_partitario=payload.include_partitario,
                include_mailing_list=payload.include_mailing_list,
                download_mailing_receipts=payload.download_mailing_receipts,
                throttle_ms=payload.throttle_ms,
            )
            item_results_map[subject_key] = item_result
            db.commit()
        except Exception as exc:
            db.rollback()
            item_results_map[subject_key] = CapacitasInCassSyncItemResult(
                subject_id=subject_key,
                identifier=identifier,
                display_name=display_name,
                status="failed",
                error=str(exc),
            )
        finally:
            _update_incass_job_progress(job, item_results_map)
            db.commit()

        if item_results_map[subject_key].status == "succeeded":
            succeeded_subject_ids.add(subject_key)

        if item_results_map[subject_key].status == "failed":
            if not payload.continue_on_error:
                job.status = "failed"
                job.error_detail = item_results_map[subject_key].error
                job.completed_at = datetime.now(UTC)
                db.commit()
                db.refresh(job)
                return job

    result_payload = _build_incass_job_result(item_results_map)
    failed_subjects = result_payload.failed_subjects
    job.result_json = result_payload.model_dump(mode="json")
    job.status = "completed_with_errors" if failed_subjects > 0 else "succeeded"
    job.completed_at = datetime.now(UTC)
    job.error_detail = None if failed_subjects == 0 else f"{failed_subjects} soggetti falliti durante il sync inCASS"
    db.commit()
    db.refresh(job)
    return job


def _load_active_incass_subject_ids(db: Session) -> set[UUID]:
    queued: set[UUID] = set()
    jobs = db.scalars(
        select(CapacitasInCassSyncJob).where(CapacitasInCassSyncJob.status.in_(tuple(ACTIVE_JOB_STATUSES)))
    ).all()
    for job in jobs:
        if not isinstance(job.payload_json, dict):
            continue
        raw_subject_ids = job.payload_json.get("subject_ids")
        if not isinstance(raw_subject_ids, list):
            continue
        for raw_subject_id in raw_subject_ids:
            try:
                queued.add(UUID(str(raw_subject_id)))
            except (TypeError, ValueError):
                continue
    return queued


def _load_existing_item_results(job: CapacitasInCassSyncJob) -> dict[str, CapacitasInCassSyncItemResult]:
    if not isinstance(job.result_json, dict):
        return {}
    try:
        parsed = CapacitasInCassSyncJobResult.model_validate(job.result_json)
    except Exception:
        return {}
    return {item.subject_id: item for item in parsed.items}


def _build_incass_job_result(
    item_results_map: dict[str, CapacitasInCassSyncItemResult],
) -> CapacitasInCassSyncJobResult:
    items = list(item_results_map.values())
    items.sort(key=lambda item: item.subject_id)
    return CapacitasInCassSyncJobResult(
        items=items,
        processed_subjects=len(items),
        failed_subjects=sum(1 for item in items if item.status == "failed"),
        notices_found=sum(item.notices_found for item in items),
        notices_synced=sum(item.notices_synced for item in items),
        paid_notices=sum(item.paid_notices for item in items),
        partial_notices=sum(item.partial_notices for item in items),
        unpaid_notices=sum(item.unpaid_notices for item in items),
        payment_status_changed=sum(item.payment_status_changed for item in items),
        newly_paid_notices=sum(item.newly_paid_notices for item in items),
        notice_pdfs_downloaded=sum(item.notice_pdfs_downloaded for item in items),
        mailing_contacts_synced=sum(item.mailing_contacts_synced for item in items),
        mailing_shipments_synced=sum(item.mailing_shipments_synced for item in items),
        mailing_receipts_downloaded=sum(item.mailing_receipts_downloaded for item in items),
    )


def _update_incass_job_progress(
    job: CapacitasInCassSyncJob,
    item_results_map: dict[str, CapacitasInCassSyncItemResult],
) -> None:
    job.result_json = _build_incass_job_result(item_results_map).model_dump(mode="json")


async def _sync_incass_subject(
    *,
    client: InCassClient,
    db: Session,
    subject_id: UUID,
    identifier: str,
    display_name: str,
    include_details: bool,
    include_partitario: bool,
    include_mailing_list: bool,
    download_mailing_receipts: bool,
    throttle_ms: int,
) -> CapacitasInCassSyncItemResult:
    result = await _run_incass_retryable(
        client,
        lambda: client.search_notices(identifier),
        label=f"search_notices:{identifier}",
    )
    synced_for_subject = 0
    paid_notices = 0
    partial_notices = 0
    unpaid_notices = 0
    payment_status_changed = 0
    newly_paid_notices = 0
    notice_pdfs_downloaded_total = 0
    for row in result.rows:
        detail_info_text: str | None = None
        detail_info_html: str | None = None
        detail_payload: dict[str, object] | None = None
        pdf_links_json: list[dict[str, str | None]] = []
        notice_pdfs_downloaded = 0
        if include_details and row.avviso:
            detail = await _run_incass_retryable(
                client,
                lambda: client.fetch_notice_detail(row.avviso),
                label=f"fetch_notice_detail:{row.avviso}",
            )
            detail_info_text = detail.info_text
            detail_info_html = detail.info_html
            detail_payload = detail.model_dump(mode="json")
            pdf_links_json = [pdf.model_dump(mode="json") for pdf in detail.pdf_links]
            pdf_links_json, notice_pdfs_downloaded = await _download_notice_pdfs(
                client=client,
                db=db,
                subject_id=subject_id,
                row=row,
                pdf_links=detail.pdf_links,
                referer=detail.detail_url,
            )
        if include_partitario and row.avviso:
            partitario = await _run_incass_retryable(
                client,
                lambda: client.fetch_notice_partitario(row.avviso),
                label=f"fetch_notice_partitario:{row.avviso}",
            )
            if partitario is not None:
                partitario_text = partitario.info_text
                if partitario_text:
                    detail_info_text = (
                        f"{detail_info_text}\n\n{partitario_text}".strip()
                        if detail_info_text
                        else partitario_text
                    )
                detail_payload = {
                    **(detail_payload or {}),
                    "partitario": partitario.model_dump(mode="json"),
                }

        sync_status = _upsert_payment_notice(
            db,
            subject_id=subject_id,
            identifier=identifier,
            display_name=display_name,
            row=row,
            detail_info_html=detail_info_html,
            detail_info_text=detail_info_text,
            pdf_links_json=pdf_links_json,
            detail_payload=detail_payload,
        )
        if sync_status is not None:
            if sync_status.status == "paid":
                paid_notices += 1
            elif sync_status.status == "partial":
                partial_notices += 1
            else:
                unpaid_notices += 1
            if sync_status.changed:
                payment_status_changed += 1
            if sync_status.newly_paid:
                newly_paid_notices += 1
        synced_for_subject += 1
        notice_pdfs_downloaded_total += notice_pdfs_downloaded
        if throttle_ms > 0:
            await asyncio.sleep(throttle_ms / 1000)

    mailing_contacts_synced = 0
    mailing_shipments_synced = 0
    mailing_receipts_downloaded = 0
    if include_mailing_list:
        mailing_data, mailing_receipts_downloaded = await _sync_incass_mailing_data(
            client=client,
            db=db,
            subject_id=subject_id,
            identifier=identifier,
            download_receipts=download_mailing_receipts,
            throttle_ms=throttle_ms,
        )
        mailing_contacts_synced = len(mailing_data.contacts)
        mailing_shipments_synced = len(mailing_data.shipments)
        db.flush()
        _merge_mailing_data_into_payment_notices(db, subject_id=subject_id, mailing_data=mailing_data)

    return CapacitasInCassSyncItemResult(
        subject_id=str(subject_id),
        identifier=identifier,
        display_name=display_name,
        status="succeeded",
        notices_found=result.total,
        notices_synced=synced_for_subject,
        paid_notices=paid_notices,
        partial_notices=partial_notices,
        unpaid_notices=unpaid_notices,
        payment_status_changed=payment_status_changed,
        newly_paid_notices=newly_paid_notices,
        notice_pdfs_downloaded=notice_pdfs_downloaded_total,
        mailing_contacts_synced=mailing_contacts_synced,
        mailing_shipments_synced=mailing_shipments_synced,
        mailing_receipts_downloaded=mailing_receipts_downloaded,
    )


async def _download_notice_pdfs(
    *,
    client: InCassClient,
    db: Session,
    subject_id: UUID,
    row: CapacitasInCassNoticeRow,
    pdf_links: list[CapacitasInCassNoticePdf],
    referer: str | None,
) -> tuple[list[dict[str, str | None]], int]:
    enriched_links: list[dict[str, str | None]] = []
    downloaded = 0
    for pdf in pdf_links:
        item = pdf.model_dump(mode="json")
        existing_document = _find_notice_pdf_document(db, subject_id=subject_id, row=row, pdf=pdf)
        if existing_document is not None:
            existing_document = _ensure_notice_pdf_document_on_nas(db, existing_document)
            item.update(_notice_pdf_document_link(existing_document))
            enriched_links.append(item)
            continue
        try:
            file_bytes = await _run_incass_retryable(
                client,
                lambda pdf_url=pdf.url: client.download_notice_pdf(pdf_url, referer=referer),
                label=f"download_notice_pdf:{row.avviso or pdf.url}",
            )
            stored = _store_notice_pdf_document(
                db,
                subject_id=subject_id,
                row=row,
                pdf=pdf,
                file_bytes=file_bytes,
            )
            if stored is not None:
                item.update(stored)
                downloaded += 1
        except Exception as exc:
            logger.warning("Download PDF avviso inCASS non riuscito avviso=%s url=%s: %s", row.avviso, pdf.url, exc)
            item["download_error"] = str(exc)
        enriched_links.append(item)
    return enriched_links, downloaded


async def _sync_incass_mailing_data(
    *,
    client: InCassClient,
    db: Session,
    subject_id: UUID,
    identifier: str,
    download_receipts: bool,
    throttle_ms: int,
) -> tuple[CapacitasInCassMailingData, int]:
    await _run_incass_retryable(
        client,
        client.warmup_mailing_list_page,
        label="warmup_mailing_list_page",
    )
    subjects = await _run_incass_retryable(
        client,
        lambda: client.search_mailing_subjects(identifier),
        label=f"search_mailing_subjects:{identifier}",
    )
    data = CapacitasInCassMailingData(subjects=subjects)
    downloaded = 0

    for mailing_subject in subjects:
        if not mailing_subject.external_id:
            continue
        contacts = await _run_incass_retryable(
            client,
            lambda subject_external_id=mailing_subject.external_id: client.fetch_mailing_contacts(subject_external_id),
            label=f"fetch_mailing_contacts:{mailing_subject.external_id}",
        )
        data.contacts.extend(contacts)
        for contact in contacts:
            _apply_mailing_contact_to_subject(db, subject_id=subject_id, contact=contact)
            if not contact.email:
                continue
            shipments = await _run_incass_retryable(
                client,
                lambda email=contact.email: client.fetch_mailing_shipments(email),
                label=f"fetch_mailing_shipments:{contact.email}",
            )
            data.shipments.extend(shipments)
            for shipment in shipments:
                if shipment.status_code == 0:
                    continue
                parents = await _run_incass_retryable(
                    client,
                    lambda shipment=shipment: client.fetch_mailing_receipt_parents(shipment),
                    label=f"fetch_mailing_receipt_parents:{shipment.external_id}",
                )
                if shipment.external_id:
                    data.receipt_parents_by_shipment_id[shipment.external_id] = parents
                for parent in parents:
                    documents = await _run_incass_retryable(
                        client,
                        lambda parent=parent: client.fetch_objman_documents(parent),
                        label=f"fetch_objman_documents:{parent.parent_id}",
                    )
                    data.receipt_documents_by_parent_id[parent.parent_id] = documents
                    if not download_receipts:
                        continue
                    for document in documents:
                        file_bytes = await _run_incass_retryable(
                            client,
                            lambda document=document: client.download_objman_document(document),
                            label=f"download_objman_document:{document.object_id}",
                        )
                        if _store_mailing_receipt_document(
                            db,
                            subject_id=subject_id,
                            shipment=shipment,
                            receipt_parent=parent,
                            document=document,
                            file_bytes=file_bytes,
                        ):
                            downloaded += 1
                if throttle_ms > 0:
                    await asyncio.sleep(throttle_ms / 1000)
    return data, downloaded


def _apply_mailing_contact_to_subject(
    db: Session,
    *,
    subject_id: UUID,
    contact: CapacitasInCassMailingContactRow,
) -> None:
    email = _normalize_email(contact.email)
    if not email:
        return
    person = db.get(AnagraficaPerson, subject_id)
    company = db.get(AnagraficaCompany, subject_id)
    contact_type = (contact.type or "").strip().upper()
    is_pec = contact_type == "PEC" or "pec" in email.lower()
    if company is not None:
        if is_pec or not company.email_pec:
            company.email_pec = email
        if contact.phone and not company.telefono:
            company.telefono = contact.phone
        return
    if person is not None:
        if is_pec or not person.email:
            person.email = email
        if contact.phone and not person.telefono:
            person.telefono = contact.phone


def _merge_mailing_data_into_payment_notices(
    db: Session,
    *,
    subject_id: UUID,
    mailing_data: CapacitasInCassMailingData,
) -> None:
    contacts_payload = [contact.model_dump(mode="json") for contact in mailing_data.contacts]
    shipments_by_avviso: dict[str, list[CapacitasInCassMailingShipmentRow]] = {}
    for shipment in mailing_data.shipments:
        if not shipment.avviso:
            continue
        shipments_by_avviso.setdefault(shipment.avviso, []).append(shipment)

    for avviso, shipments in shipments_by_avviso.items():
        notice = db.scalar(
            select(AnagraficaPaymentNotice).where(
                AnagraficaPaymentNotice.source_system == "incass",
                AnagraficaPaymentNotice.source_notice_id == avviso,
            )
        )
        if notice is None:
            continue
        raw_detail = notice.raw_detail_json if isinstance(notice.raw_detail_json, dict) else {}
        receipt_parents_by_shipment_id = {
            shipment_id: [parent.model_dump(mode="json") for parent in parents]
            for shipment_id, parents in mailing_data.receipt_parents_by_shipment_id.items()
            if any(shipment.external_id == shipment_id for shipment in shipments)
        }
        receipt_parent_ids = {
            parent["parent_id"]
            for parents in receipt_parents_by_shipment_id.values()
            for parent in parents
            if parent.get("parent_id")
        }
        mailing_payload = {
            "contacts": contacts_payload,
            "shipments": [shipment.model_dump(mode="json") for shipment in shipments],
            "receipt_parents_by_shipment_id": receipt_parents_by_shipment_id,
            "receipt_documents_by_parent_id": {
                parent_id: [document.model_dump(mode="json") for document in documents]
                for parent_id, documents in mailing_data.receipt_documents_by_parent_id.items()
                if parent_id in receipt_parent_ids
            },
        }
        notice.raw_detail_json = {**raw_detail, "mailing_list": mailing_payload}
        flag_modified(notice, "raw_detail_json")
        notice.synced_at = datetime.now(UTC)


def _store_mailing_receipt_document(
    db: Session,
    *,
    subject_id: UUID,
    shipment: CapacitasInCassMailingShipmentRow,
    receipt_parent: CapacitasInCassMailingReceiptParent,
    document: CapacitasObjManDocument,
    file_bytes: bytes,
) -> bool:
    if not file_bytes:
        return False
    subject = db.get(AnagraficaSubject, subject_id)
    if subject is None:
        return False
    filename = _build_receipt_filename(shipment, receipt_parent, document)
    local_path = _receipt_local_path(subject_id, filename)
    existing = db.scalar(select(AnagraficaDocument).where(AnagraficaDocument.local_path == str(local_path)))
    if existing is not None:
        return False

    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(file_bytes)
    nas_path = _upload_receipt_to_nas(subject, filename, file_bytes)
    db.add(
        AnagraficaDocument(
            subject_id=subject_id,
            doc_type=AnagraficaDocType.CORRISPONDENZA.value,
            filename=filename,
            nas_path=nas_path,
            file_size_bytes=len(file_bytes),
            file_modified_at=document.created_at,
            classification_source=AnagraficaClassificationSource.AUTO.value,
            storage_type=AnagraficaStorageType.LOCAL_UPLOAD.value,
            local_path=str(local_path),
            mime_type=mimetypes.guess_type(filename)[0] or "message/rfc822",
            uploaded_at=datetime.now(UTC),
            notes=(
                "Ricevuta Capacitas inCASS "
                f"avviso={shipment.avviso or ''} gruppo={receipt_parent.group or document.group or ''} "
                f"objman_id={document.object_id}"
            ).strip(),
        )
    )
    return True


def _store_notice_pdf_document(
    db: Session,
    *,
    subject_id: UUID,
    row: CapacitasInCassNoticeRow,
    pdf: CapacitasInCassNoticePdf,
    file_bytes: bytes,
) -> dict[str, str | None] | None:
    if not file_bytes:
        return None
    subject = db.get(AnagraficaSubject, subject_id)
    if subject is None:
        return None
    filename = _build_notice_pdf_filename(row, pdf)
    local_path = _notice_pdf_local_path(subject_id, filename)
    existing = _find_notice_pdf_document(db, subject_id=subject_id, row=row, pdf=pdf)
    if existing is not None:
        existing = _ensure_notice_pdf_document_on_nas(db, existing)
        return _notice_pdf_document_link(existing)

    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(file_bytes)
    nas_path = _upload_notice_pdf_to_nas(subject, filename, file_bytes)
    document = AnagraficaDocument(
        subject_id=subject_id,
        doc_type=AnagraficaDocType.ESTRATTO_DEBITO.value,
        filename=filename,
        nas_path=nas_path,
        file_size_bytes=len(file_bytes),
        classification_source=AnagraficaClassificationSource.AUTO.value,
        storage_type=AnagraficaStorageType.LOCAL_UPLOAD.value,
        local_path=str(local_path),
        mime_type=mimetypes.guess_type(filename)[0] or "application/pdf",
        uploaded_at=datetime.now(UTC),
        notes=f"PDF avviso Capacitas inCASS avviso={row.avviso or ''} url={pdf.url}".strip(),
    )
    db.add(document)
    db.flush()
    return _notice_pdf_document_link(document)


def _find_notice_pdf_document(
    db: Session,
    *,
    subject_id: UUID,
    row: CapacitasInCassNoticeRow,
    pdf: CapacitasInCassNoticePdf,
) -> AnagraficaDocument | None:
    local_path = _notice_pdf_local_path(subject_id, _build_notice_pdf_filename(row, pdf))
    return db.scalar(select(AnagraficaDocument).where(AnagraficaDocument.local_path == str(local_path)))


def _notice_pdf_document_link(document: AnagraficaDocument) -> dict[str, str | None]:
    return {
        "document_id": str(document.id),
        "download_url": f"/utenze/documents/{document.id}/download",
        "nas_path": document.nas_path,
        "local_path": document.local_path,
    }


def _ensure_notice_pdf_document_on_nas(db: Session, document: AnagraficaDocument) -> AnagraficaDocument:
    if document.nas_path:
        return document
    subject = db.get(AnagraficaSubject, document.subject_id)
    if subject is None or not subject.nas_folder_path or not document.local_path:
        return document
    local_path = Path(document.local_path)
    if not local_path.exists() or not local_path.is_file():
        return document
    document.nas_path = _upload_notice_pdf_to_nas(subject, document.filename, local_path.read_bytes())
    db.flush()
    return document


def _upload_notice_pdf_to_nas(subject: AnagraficaSubject, filename: str, file_bytes: bytes) -> str | None:
    if not subject.nas_folder_path:
        return None
    connector = get_nas_client()
    try:
        target_dir = PurePosixPath(subject.nas_folder_path) / "capacitas" / "avvisi"
        connector.ensure_directory(str(target_dir))
        target_path = target_dir / filename
        if not connector.path_exists(str(target_path)):
            connector.upload_file(str(target_path), file_bytes)
        return str(target_path)
    finally:
        close = getattr(connector, "close", None)
        if callable(close):
            close()


def _upload_receipt_to_nas(subject: AnagraficaSubject, filename: str, file_bytes: bytes) -> str | None:
    if not subject.nas_folder_path:
        return None
    connector = get_nas_client()
    try:
        target_dir = PurePosixPath(subject.nas_folder_path) / "capacitas" / "ricevute"
        connector.ensure_directory(str(target_dir))
        target_path = target_dir / filename
        if not connector.path_exists(str(target_path)):
            connector.upload_file(str(target_path), file_bytes)
        return str(target_path)
    finally:
        close = getattr(connector, "close", None)
        if callable(close):
            close()


def _build_receipt_filename(
    shipment: CapacitasInCassMailingShipmentRow,
    receipt_parent: CapacitasInCassMailingReceiptParent,
    document: CapacitasObjManDocument,
) -> str:
    original = Path(document.filename or f"{document.object_id}.eml").name
    parts = [
        "capacitas",
        shipment.avviso or "senza-avviso",
        receipt_parent.group or document.group or "ricevuta",
        document.object_id,
        original,
    ]
    return _safe_filename("_".join(part for part in parts if part))


def _build_notice_pdf_filename(row: CapacitasInCassNoticeRow, pdf: CapacitasInCassNoticePdf) -> str:
    original = Path(pdf.filename or "").name
    if not original:
        original = f"{row.avviso or 'senza-avviso'}.pdf"
    parts = [
        "capacitas",
        row.avviso or "senza-avviso",
        pdf.label or "avviso",
        original,
    ]
    filename = _safe_filename("_".join(part for part in parts if part), fallback="capacitas_avviso.pdf")
    return filename if filename.lower().endswith(".pdf") else f"{filename}.pdf"


def _receipt_local_path(subject_id: UUID, filename: str) -> Path:
    storage_root = Path(settings.utenze_document_storage_path or settings.anagrafica_document_storage_path)
    return storage_root / str(subject_id) / "capacitas" / "ricevute" / filename


def _notice_pdf_local_path(subject_id: UUID, filename: str) -> Path:
    storage_root = Path(settings.utenze_document_storage_path or settings.anagrafica_document_storage_path)
    return storage_root / str(subject_id) / "capacitas" / "avvisi" / filename


def _safe_filename(value: str, *, fallback: str = "capacitas_ricevuta.eml") -> str:
    normalized = _SAFE_FILENAME_RE.sub("_", value).strip(" ._")
    return normalized[:240] or fallback


def _normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


async def _run_incass_retryable(client: InCassClient, operation, *, label: str):
    last_exc: Exception | None = None
    for attempt in range(1, len(INCASS_RETRY_DELAYS_SEC) + 2):
        try:
            return await operation()
        except Exception as exc:
            last_exc = exc
            if not _is_retryable_incass_exception(exc) or attempt > len(INCASS_RETRY_DELAYS_SEC):
                raise
            await client.refresh_session()
            await asyncio.sleep(INCASS_RETRY_DELAYS_SEC[attempt - 1])
    raise last_exc or RuntimeError(f"Retry loop exhausted for {label}")  # pragma: no cover - defensive fallback.


def _is_retryable_incass_exception(exc: Exception) -> bool:
    if isinstance(exc, (CapacitasInCassSessionExpiredError, httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    if isinstance(exc, RuntimeError):
        message = str(exc).lower()
        transient_markers = (
            "sessione",
            "login sso",
            "errore.aspx",
            "tempor",
            "timeout",
            "connection reset",
            "remoteprotocolerror",
        )
        return any(marker in message for marker in transient_markers)
    return False


def _resolve_subjects(
    db: Session,
    payload: CapacitasInCassSyncJobCreateRequest,
) -> list[tuple[AnagraficaSubject, str, str]]:
    subject_ids = [UUID(str(value)) for value in payload.subject_ids]
    rows: list[tuple[AnagraficaSubject, AnagraficaPerson | None, AnagraficaCompany | None]] = []
    if subject_ids:
        rows = list(
            db.execute(
                select(AnagraficaSubject, AnagraficaPerson, AnagraficaCompany)
                .outerjoin(AnagraficaPerson, AnagraficaPerson.subject_id == AnagraficaSubject.id)
                .outerjoin(AnagraficaCompany, AnagraficaCompany.subject_id == AnagraficaSubject.id)
                .where(AnagraficaSubject.id.in_(subject_ids))
                .order_by(AnagraficaSubject.updated_at.desc())
            ).all()
        )
    else:
        stmt = (
            select(AnagraficaSubject, AnagraficaPerson, AnagraficaCompany)
            .outerjoin(AnagraficaPerson, AnagraficaPerson.subject_id == AnagraficaSubject.id)
            .outerjoin(AnagraficaCompany, AnagraficaCompany.subject_id == AnagraficaSubject.id)
            .where(
                or_(
                    AnagraficaPerson.codice_fiscale.is_not(None),
                    AnagraficaCompany.partita_iva.is_not(None),
                    AnagraficaCompany.codice_fiscale.is_not(None),
                )
            )
            .order_by(AnagraficaSubject.updated_at.desc())
        )
        if payload.limit is not None:
            stmt = stmt.limit(payload.limit)
        rows = list(db.execute(stmt).all())

    resolved: list[tuple[AnagraficaSubject, str, str]] = []
    for subject, person, company in rows:
        identifier = None
        display_name = subject.source_name_raw
        if company is not None:
            identifier = (company.partita_iva or company.codice_fiscale or "").strip().upper()
            display_name = company.ragione_sociale or display_name
        elif person is not None:
            identifier = (person.codice_fiscale or "").strip().upper()
            display_name = f"{person.cognome} {person.nome}".strip() or display_name
        if identifier:
            resolved.append((subject, identifier, display_name))
    return resolved


def _upsert_payment_notice(
    db: Session,
    *,
    subject_id: UUID,
    identifier: str,
    display_name: str,
    row: CapacitasInCassNoticeRow,
    detail_info_html: str | None,
    detail_info_text: str | None,
    pdf_links_json: list[dict[str, str | None]],
    detail_payload: dict[str, object] | None,
) -> PaymentNoticeSyncStatus | None:
    if not row.avviso:
        return None
    existing = _find_pending_payment_notice(
        db,
        source_system="incass",
        source_notice_id=row.avviso,
    )
    if existing is None:
        existing = db.scalar(
            select(AnagraficaPaymentNotice).where(
                AnagraficaPaymentNotice.source_system == "incass",
                AnagraficaPaymentNotice.source_notice_id == row.avviso,
            )
        )
    previous_status = classify_payment_notice(existing) if existing is not None else None
    if existing is None:
        existing = AnagraficaPaymentNotice(source_system="incass", source_notice_id=row.avviso)
        db.add(existing)

    existing.subject_id = subject_id
    existing.source_internal_id = row.external_row_id
    existing.codice_fiscale = row.codice_fiscale or identifier
    existing.partita_iva = identifier if identifier.isdigit() and len(identifier) == 11 else None
    existing.display_name = row.denominazione or display_name
    existing.anno = row.anno
    existing.stato_code = row.stato_pagamento_code
    existing.stato_label = row.stato_pagamento_label
    existing.data_scadenza = _parse_date(row.data_scadenza)
    existing.data_pagamento = _parse_date(row.data_pagamento)
    existing.tipo_anagrafica = row.tipo_anagrafica
    existing.ultimo_invio = row.ultimo_invio
    existing.lista_id = row.lista_id
    existing.lista_descrizione = row.lista_descrizione
    existing.indirizzo = _join_address(row)
    existing.cap = row.cap
    existing.citta = row.citta
    existing.provincia = row.provincia
    existing.importo_carico = row.carico
    existing.importo_sgravio = row.sgravio
    existing.importo_riscosso = row.riscosso
    existing.importo_residuo = row.differenza
    existing.importo_riporto = row.riporto
    existing.importo_rateizzato = row.rateizzato
    existing.importo_annullato = row.annullato
    existing.detail_url = row.detail_url
    existing.detail_info_html = detail_info_html
    existing.detail_info_text = detail_info_text
    existing.pdf_links_json = pdf_links_json or None
    existing.raw_row_json = row.model_dump(mode="json", by_alias=True)
    existing.raw_detail_json = detail_payload
    existing.synced_at = datetime.now(UTC)
    current_status = classify_payment_notice(existing)
    return PaymentNoticeSyncStatus(
        status=current_status,
        previous_status=previous_status,
        changed=previous_status is not None and previous_status != current_status,
        newly_paid=previous_status in {"partial", "unpaid"} and current_status == "paid",
    )


def classify_payment_notice(notice: AnagraficaPaymentNotice) -> str:
    return classify_payment_notice_fields(
        importo_residuo=notice.importo_residuo,
        importo_riscosso=notice.importo_riscosso,
        importo_carico=notice.importo_carico,
        stato_label=notice.stato_label,
        data_pagamento=notice.data_pagamento,
    )


def classify_payment_notice_fields(
    *,
    importo_residuo: str | None,
    importo_riscosso: str | None,
    importo_carico: str | None,
    stato_label: str | None,
    data_pagamento: date | None,
) -> str:
    residuo = _parse_notice_amount(importo_residuo)
    riscosso = _parse_notice_amount(importo_riscosso) or 0
    carico = _parse_notice_amount(importo_carico)
    if (residuo is not None and residuo <= 0.005) or data_pagamento is not None or _is_paid_like_status(stato_label):
        return "paid"
    if riscosso > 0.005 or (carico is not None and residuo is not None and residuo > 0.005 and residuo < carico):
        return "partial"
    return "unpaid"


def _parse_notice_amount(value: str | None) -> float | None:
    if not value:
        return None
    raw = re.sub(r"[^\d,.-]", "", str(value).strip())
    if not raw:
        return None
    normalized = raw
    if "," in raw:
        normalized = raw.replace(".", "").replace(",", ".")
    elif "." in raw:
        parts = raw.split(".")
        if len(parts) > 2:
            decimal_like = len(parts[-1]) != 3
            normalized = f"{''.join(parts[:-1])}.{parts[-1]}" if decimal_like else "".join(parts)
    try:
        parsed = float(normalized)
    except ValueError:
        return None
    return parsed if parsed == parsed else None


def _is_paid_like_status(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.strip().lower()
    if normalized.startswith("non pagato") or "parzialmente" in normalized or "in parte" in normalized or "senza pagamenti" in normalized:
        return False
    return "pagato" in normalized and not normalized.startswith("non pagato")


def _find_pending_payment_notice(
    db: Session,
    *,
    source_system: str,
    source_notice_id: str,
) -> AnagraficaPaymentNotice | None:
    for instance in db.new:
        if not isinstance(instance, AnagraficaPaymentNotice):
            continue
        if instance.source_system == source_system and instance.source_notice_id == source_notice_id:
            return instance
    return None


def _join_address(row: CapacitasInCassNoticeRow) -> str | None:
    parts = [row.indirizzo, row.civico]
    if row.sub_civico:
        parts.append(f"/{row.sub_civico}")
    return " ".join(part for part in parts if part).strip() or None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    normalized = value.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized, fmt).date()
        except ValueError:
            continue
    return None
