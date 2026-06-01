from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import exists, delete, or_, select
from sqlalchemy.orm import Session

from app.models.capacitas import CapacitasInCassSyncJob
from app.modules.elaborazioni.capacitas.apps.incass.client import (
    CapacitasInCassSessionExpiredError,
    InCassClient,
)
from app.modules.elaborazioni.capacitas.models import (
    CapacitasInCassNoticeRow,
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
    AnagraficaPaymentNotice,
    AnagraficaPerson,
    AnagraficaSubject,
)

UTC = timezone.utc
TERMINAL_JOB_STATUSES = {"succeeded", "completed_with_errors", "failed", "cancelled"}
ACTIVE_JOB_STATUSES = {"pending", "processing", "queued_resume"}
INCASS_RETRY_DELAYS_SEC = (1, 3)


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
    )
    already_queued_subject_ids = _load_active_incass_subject_ids(db)
    subject_ids = [subject_id for subject_id in subject_ids if subject_id not in already_queued_subject_ids]
    job_ids: list[int] = []
    for index in range(0, len(subject_ids), payload.chunk_size):
        chunk = subject_ids[index:index + payload.chunk_size]
        if not chunk:
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
    throttle_ms: int,
) -> CapacitasInCassSyncItemResult:
    result = await _run_incass_retryable(
        client,
        lambda: client.search_notices(identifier),
        label=f"search_notices:{identifier}",
    )
    synced_for_subject = 0
    for row in result.rows:
        detail_info_text: str | None = None
        detail_info_html: str | None = None
        detail_payload: dict[str, object] | None = None
        pdf_links_json: list[dict[str, str | None]] = []
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

        _upsert_payment_notice(
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
        synced_for_subject += 1
        if throttle_ms > 0:
            await asyncio.sleep(throttle_ms / 1000)

    return CapacitasInCassSyncItemResult(
        subject_id=str(subject_id),
        identifier=identifier,
        display_name=display_name,
        status="succeeded",
        notices_found=result.total,
        notices_synced=synced_for_subject,
    )


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
    raise last_exc or RuntimeError(f"Retry loop exhausted for {label}")


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
) -> None:
    if not row.avviso:
        return
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
