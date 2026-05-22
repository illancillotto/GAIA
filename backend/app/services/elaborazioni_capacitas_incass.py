from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.models.capacitas import CapacitasInCassSyncJob
from app.modules.elaborazioni.capacitas.apps.incass.client import InCassClient
from app.modules.elaborazioni.capacitas.models import (
    CapacitasInCassNoticeRow,
    CapacitasInCassSyncItemResult,
    CapacitasInCassSyncJobCreateRequest,
    CapacitasInCassSyncJobOut,
    CapacitasInCassSyncJobResult,
)
from app.modules.utenze.models import (
    AnagraficaCompany,
    AnagraficaPaymentNotice,
    AnagraficaPerson,
    AnagraficaSubject,
)

UTC = timezone.utc
TERMINAL_JOB_STATUSES = {"succeeded", "completed_with_errors", "failed", "cancelled"}


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


def prepare_incass_sync_jobs_for_recovery(db: Session) -> list[int]:
    jobs = db.scalars(
        select(CapacitasInCassSyncJob).where(
            CapacitasInCassSyncJob.status == "processing",
            CapacitasInCassSyncJob.completed_at.is_(None),
        )
    ).all()
    recovered: list[int] = []
    for job in jobs:
        job.status = "pending"
        job.started_at = None
        job.error_detail = "Recuperato dopo riavvio worker"
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

    item_results: list[CapacitasInCassSyncItemResult] = []
    notices_found = 0
    notices_synced = 0
    failed_subjects = 0

    for subject, identifier, display_name in subjects:
        try:
            result = await client.search_notices(identifier)
            synced_for_subject = 0
            for row in result.rows:
                detail_info_text: str | None = None
                detail_payload: dict[str, object] | None = None
                pdf_links_json: list[dict[str, str | None]] = []
                if payload.include_details and row.avviso:
                    detail = await client.fetch_notice_detail(row.avviso)
                    detail_info_text = detail.info_text
                    detail_payload = detail.model_dump(mode="json")
                    pdf_links_json = [pdf.model_dump(mode="json") for pdf in detail.pdf_links]
                if payload.include_partitario and row.avviso:
                    partitario_text = await client.fetch_notice_partitario(row.avviso)
                    if partitario_text:
                        detail_info_text = f"{detail_info_text}\n\n{partitario_text}".strip() if detail_info_text else partitario_text

                _upsert_payment_notice(
                    db,
                    subject_id=subject.id,
                    identifier=identifier,
                    display_name=display_name,
                    row=row,
                    detail_info_text=detail_info_text,
                    pdf_links_json=pdf_links_json,
                    detail_payload=detail_payload,
                )
                synced_for_subject += 1
                notices_synced += 1
                if payload.throttle_ms > 0:
                    await asyncio.sleep(payload.throttle_ms / 1000)

            notices_found += result.total
            item_results.append(
                CapacitasInCassSyncItemResult(
                    subject_id=str(subject.id),
                    identifier=identifier,
                    display_name=display_name,
                    status="succeeded",
                    notices_found=result.total,
                    notices_synced=synced_for_subject,
                )
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            failed_subjects += 1
            item_results.append(
                CapacitasInCassSyncItemResult(
                    subject_id=str(subject.id),
                    identifier=identifier,
                    display_name=display_name,
                    status="failed",
                    error=str(exc),
                )
            )
            if not payload.continue_on_error:
                job.status = "failed"
                job.error_detail = str(exc)
                job.result_json = CapacitasInCassSyncJobResult(
                    items=item_results,
                    processed_subjects=len(item_results),
                    failed_subjects=failed_subjects,
                    notices_found=notices_found,
                    notices_synced=notices_synced,
                ).model_dump(mode="json")
                job.completed_at = datetime.now(UTC)
                db.commit()
                db.refresh(job)
                return job

    result_payload = CapacitasInCassSyncJobResult(
        items=item_results,
        processed_subjects=len(item_results),
        failed_subjects=failed_subjects,
        notices_found=notices_found,
        notices_synced=notices_synced,
    )
    job.result_json = result_payload.model_dump(mode="json")
    job.status = "completed_with_errors" if failed_subjects > 0 else "succeeded"
    job.completed_at = datetime.now(UTC)
    job.error_detail = None if failed_subjects == 0 else f"{failed_subjects} soggetti falliti durante il sync inCASS"
    db.commit()
    db.refresh(job)
    return job


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
    detail_info_text: str | None,
    pdf_links_json: list[dict[str, str | None]],
    detail_payload: dict[str, object] | None,
) -> None:
    if not row.avviso:
        return
    existing = db.scalar(
        select(AnagraficaPaymentNotice).where(
            AnagraficaPaymentNotice.source_system == "incass",
            AnagraficaPaymentNotice.source_notice_id == row.avviso,
        )
    )
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
    existing.detail_info_text = detail_info_text
    existing.pdf_links_json = pdf_links_json or None
    existing.raw_row_json = row.model_dump(mode="json", by_alias=True)
    existing.raw_detail_json = detail_payload
    existing.synced_at = datetime.now(UTC)


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
