from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pandas as pd
from pandas.errors import EmptyDataError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.capacitas import CapacitasAnagraficaHistoryImportJob
from app.modules.elaborazioni.capacitas.client import InVoltureClient
from app.modules.elaborazioni.capacitas.models import (
    CapacitasAnagrafica,
    CapacitasAnagraficaDetail,
    CapacitasAnagraficaHistoryImportItem,
    CapacitasAnagraficaHistoryImportJobCreateRequest,
    CapacitasAnagraficaHistoryImportJobOut,
    CapacitasAnagraficaHistoryImportItemResult,
    CapacitasAnagraficaHistoryImportRequest,
    CapacitasAnagraficaHistoryImportResponse,
    CapacitasStoricoAnagraficaRow,
)
from app.modules.utenze.models import (
    AnagraficaPerson,
    AnagraficaSubject,
    AnagraficaSubjectStatus,
    AnagraficaSubjectType,
)
from app.modules.utenze.services.person_history_service import persist_person_source_snapshot
from app.services.elaborazioni_capacitas_terreni import (
    _compose_address,
    _normalize_cf,
    _parse_datetime_value,
    _split_denominazione,
)

UTC = timezone.utc


class CapacitasAnagraficaHistoryImportError(Exception):
    pass


HistoryItemProgressCallback = Callable[[CapacitasAnagraficaHistoryImportItemResult, dict[str, int]], Awaitable[None]]
RECENT_HISTORY_ITEM_LIMIT = 100
HISTORY_STALE_JOB_MINUTES = 30


@dataclass(slots=True)
class _ResolvedTarget:
    subject: AnagraficaSubject | None
    person: AnagraficaPerson | None
    idxana: str | None


def load_anagrafica_history_import_request(
    *,
    filename: str,
    content: bytes,
    credential_id: int | None = None,
) -> CapacitasAnagraficaHistoryImportRequest:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".csv":
            dataframe = pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False)
        elif suffix == ".xlsx":
            dataframe = pd.read_excel(BytesIO(content), dtype=str, keep_default_na=False)
        else:
            raise CapacitasAnagraficaHistoryImportError("Formato file non supportato. Usare CSV o XLSX.")
    except EmptyDataError as exc:
        raise CapacitasAnagraficaHistoryImportError("Il file batch non contiene righe.") from exc
    except ValueError as exc:
        raise CapacitasAnagraficaHistoryImportError("Il file batch non puo essere letto.") from exc

    if dataframe.empty:
        raise CapacitasAnagraficaHistoryImportError("Il file batch non contiene righe.")

    normalized_columns = {str(column).strip().lower(): column for column in dataframe.columns}
    subject_col = normalized_columns.get("subject_id")
    idxana_col = normalized_columns.get("idxana")
    if subject_col is None and idxana_col is None:
        raise CapacitasAnagraficaHistoryImportError("Il file batch deve contenere almeno una colonna tra subject_id e idxana.")

    items: list[CapacitasAnagraficaHistoryImportItem] = []
    for _, row in dataframe.iterrows():
        subject_id_raw = str(row.get(subject_col, "")).strip() if subject_col is not None else ""
        idxana_raw = str(row.get(idxana_col, "")).strip() if idxana_col is not None else ""
        if not subject_id_raw and not idxana_raw:
            continue
        items.append(
            CapacitasAnagraficaHistoryImportItem(
                subject_id=UUID(subject_id_raw) if subject_id_raw else None,
                idxana=idxana_raw or None,
            )
        )

    if not items:
        raise CapacitasAnagraficaHistoryImportError("Il file batch non contiene righe valide.")

    return CapacitasAnagraficaHistoryImportRequest(items=items, credential_id=credential_id)


def serialize_anagrafica_history_job(job: CapacitasAnagraficaHistoryImportJob) -> CapacitasAnagraficaHistoryImportJobOut:
    return CapacitasAnagraficaHistoryImportJobOut.model_validate(job)


def create_anagrafica_history_job(
    db: Session,
    *,
    requested_by_user_id: int | None,
    credential_id: int | None,
    payload: CapacitasAnagraficaHistoryImportJobCreateRequest,
) -> CapacitasAnagraficaHistoryImportJob:
    payload_json = payload.model_dump(exclude_none=True, mode="json")
    payload_json.setdefault("auto_resume", True)
    job = CapacitasAnagraficaHistoryImportJob(
        requested_by_user_id=requested_by_user_id,
        credential_id=credential_id,
        status="pending",
        mode="history_import",
        payload_json=payload_json,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_anagrafica_history_jobs(db: Session) -> list[CapacitasAnagraficaHistoryImportJob]:
    return list(
        db.scalars(select(CapacitasAnagraficaHistoryImportJob).order_by(CapacitasAnagraficaHistoryImportJob.id.desc())).all()
    )


def get_anagrafica_history_job(db: Session, job_id: int) -> CapacitasAnagraficaHistoryImportJob | None:
    return db.get(CapacitasAnagraficaHistoryImportJob, job_id)


def delete_anagrafica_history_job(db: Session, job: CapacitasAnagraficaHistoryImportJob) -> None:
    db.delete(job)
    db.commit()


def _normalize_job_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _append_recent_history_item(result_json: dict[str, object], item: CapacitasAnagraficaHistoryImportItemResult) -> None:
    recent_items = result_json.get("recent_items")
    if not isinstance(recent_items, list):
        recent_items = []
        result_json["recent_items"] = recent_items
    recent_items.append(item.model_dump(exclude_none=True, mode="json"))
    if len(recent_items) > RECENT_HISTORY_ITEM_LIMIT:
        del recent_items[0 : len(recent_items) - RECENT_HISTORY_ITEM_LIMIT]


def _build_initial_history_job_result(total_items: int) -> dict[str, object]:
    return {
        "mode": "history_import",
        "total_items": total_items,
        "processed": 0,
        "imported": 0,
        "skipped": 0,
        "failed": 0,
        "snapshot_records_imported": 0,
        "progress_percent": 0,
        "current_label": None,
        "recent_items": [],
    }


def _compute_history_progress(processed: int, total: int) -> int:
    if total <= 0:
        return 100
    return max(0, min(100, round((processed / total) * 100)))


def _mark_stale_history_job(job: CapacitasAnagraficaHistoryImportJob, *, completed_at: datetime, detail: str) -> None:
    job.status = "failed"
    job.completed_at = completed_at
    job.error_detail = f"{job.error_detail}\n{detail}".strip() if job.error_detail else detail
    if isinstance(job.result_json, dict):
        result_json = dict(job.result_json)
        result_json["current_label"] = None
        result_json["completed_at"] = completed_at.isoformat()
        job.result_json = result_json


def expire_stale_anagrafica_history_jobs(db: Session) -> None:
    now = datetime.now(UTC)
    jobs = db.scalars(
        select(CapacitasAnagraficaHistoryImportJob).where(
            CapacitasAnagraficaHistoryImportJob.status == "processing",
            CapacitasAnagraficaHistoryImportJob.completed_at.is_(None),
        )
    ).all()
    if not jobs:
        return
    stale_cutoff = now.timestamp() - (HISTORY_STALE_JOB_MINUTES * 60)
    changed = False
    for job in jobs:
        started_at = _normalize_job_datetime(job.started_at)
        updated_at = _normalize_job_datetime(job.updated_at)
        reference_at = updated_at or started_at
        if reference_at is not None and reference_at.timestamp() < stale_cutoff:
            _mark_stale_history_job(
                job,
                completed_at=now,
                detail=f"Job marcato come failed: worker Capacitas senza avanzamento oltre la soglia di {HISTORY_STALE_JOB_MINUTES} minuti.",
            )
            changed = True
    if changed:
        db.commit()


def prepare_anagrafica_history_jobs_for_recovery(db: Session) -> list[int]:
    now = datetime.now(UTC)
    jobs = db.scalars(
        select(CapacitasAnagraficaHistoryImportJob).where(
            CapacitasAnagraficaHistoryImportJob.status.in_(("pending", "processing", "queued_resume")),
            CapacitasAnagraficaHistoryImportJob.completed_at.is_(None),
        )
    ).all()
    if not jobs:
        return []
    recovered_ids: list[int] = []
    changed = False
    for job in jobs:
        payload_json = dict(job.payload_json or {})
        if not bool(payload_json.get("auto_resume", True)):
            continue
        result_json = dict(job.result_json or {})
        result_json["resume_reason"] = "backend_restart"
        result_json["last_resume_at"] = now.isoformat()
        result_json["resume_count"] = int(result_json.get("resume_count", 0)) + 1
        result_json["current_label"] = None
        job.result_json = result_json
        job.error_detail = None
        job.completed_at = None
        job.status = "queued_resume"
        recovered_ids.append(job.id)
        changed = True
    if changed:
        db.commit()
    return recovered_ids


async def import_anagrafica_history_batch(
    db: Session,
    client: InVoltureClient,
    request: CapacitasAnagraficaHistoryImportRequest,
    *,
    progress_callback: HistoryItemProgressCallback | None = None,
) -> CapacitasAnagraficaHistoryImportResponse:
    totals = {
        "processed": 0,
        "imported": 0,
        "skipped": 0,
        "failed": 0,
        "snapshot_records_imported": 0,
    }
    items: list[CapacitasAnagraficaHistoryImportItemResult] = []
    storico_cache: dict[str, list[CapacitasStoricoAnagraficaRow]] = {}
    detail_cache: dict[str, CapacitasAnagraficaDetail] = {}

    for item in request.items:
        totals["processed"] += 1
        try:
            result = await _import_single_item(
                db,
                client,
                item,
                storico_cache=storico_cache,
                detail_cache=detail_cache,
            )
            items.append(result)
            if result.status == "imported":
                totals["imported"] += 1
                totals["snapshot_records_imported"] += result.imported_records
            elif result.status == "skipped":
                totals["skipped"] += 1
            elif result.status == "failed":
                totals["failed"] += 1
        except Exception as exc:
            db.rollback()
            result = CapacitasAnagraficaHistoryImportItemResult(
                subject_id=str(item.subject_id) if item.subject_id else None,
                idxana=item.idxana,
                status="failed",
                error=str(exc),
            )
            items.append(result)
            totals["failed"] += 1
            if not request.continue_on_error:
                if progress_callback is not None:
                    await progress_callback(result, dict(totals))
                break
        if progress_callback is not None:
            await progress_callback(items[-1], dict(totals))

    return CapacitasAnagraficaHistoryImportResponse(items=items, **totals)


def _record_history_job_progress(
    db: Session,
    *,
    job_id: int,
    total_items: int,
    item_result: CapacitasAnagraficaHistoryImportItemResult,
    totals: dict[str, int],
) -> None:
    job = db.get(CapacitasAnagraficaHistoryImportJob, job_id)
    assert job is not None
    current_result = dict(job.result_json or _build_initial_history_job_result(total_items))
    current_result["processed"] = totals["processed"]
    current_result["imported"] = totals["imported"]
    current_result["skipped"] = totals["skipped"]
    current_result["failed"] = totals["failed"]
    current_result["snapshot_records_imported"] = totals["snapshot_records_imported"]
    current_result["progress_percent"] = _compute_history_progress(totals["processed"], total_items)
    current_result["current_label"] = (item_result.idxana or item_result.subject_id) if totals["processed"] < total_items else None
    _append_recent_history_item(current_result, item_result)
    job.result_json = current_result
    db.commit()


async def run_anagrafica_history_job(
    db: Session,
    client: InVoltureClient,
    job: CapacitasAnagraficaHistoryImportJob,
) -> CapacitasAnagraficaHistoryImportJob:
    payload = CapacitasAnagraficaHistoryImportJobCreateRequest.model_validate(job.payload_json or {})
    job.status = "processing"
    job.started_at = datetime.now(UTC)
    job.error_detail = None
    job.result_json = _build_initial_history_job_result(len(payload.items))
    db.commit()
    db.refresh(job)

    async def record_progress(item_result: CapacitasAnagraficaHistoryImportItemResult, totals: dict[str, int]) -> None:
        _record_history_job_progress(db, job_id=job.id, total_items=len(payload.items), item_result=item_result, totals=totals)

    try:
        result = await import_anagrafica_history_batch(db, client, payload, progress_callback=record_progress)
        final_result = result.model_dump(exclude_none=True, mode="json")
        final_result["progress_percent"] = 100
        final_result["current_label"] = None
        final_result["completed_at"] = datetime.now(UTC).isoformat()
        final_result["resume_count"] = int((job.result_json or {}).get("resume_count", 0)) if isinstance(job.result_json, dict) else 0
        final_result["recent_items"] = (job.result_json or {}).get("recent_items", []) if isinstance(job.result_json, dict) else []
        job.result_json = final_result
        job.status = "succeeded" if result.failed == 0 else "completed_with_errors"
        job.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(job)
        return job
    except Exception as exc:
        db.rollback()
        job = db.get(CapacitasAnagraficaHistoryImportJob, job.id)
        assert job is not None
        job.status = "failed"
        job.error_detail = str(exc)
        job.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(job)
        raise


async def _import_single_item(
    db: Session,
    client: InVoltureClient,
    item: CapacitasAnagraficaHistoryImportItem,
    *,
    storico_cache: dict[str, list[CapacitasStoricoAnagraficaRow]],
    detail_cache: dict[str, CapacitasAnagraficaDetail],
) -> CapacitasAnagraficaHistoryImportItemResult:
    resolved = await _resolve_target(db, client, item)
    if resolved.subject is not None and resolved.subject.subject_type != AnagraficaSubjectType.PERSON.value:
        raise CapacitasAnagraficaHistoryImportError("Lo storico anagrafico e supportato solo per soggetti persona.")
    if not resolved.idxana:
        raise CapacitasAnagraficaHistoryImportError("Impossibile determinare IDXANA per il soggetto richiesto.")

    history_rows = storico_cache.get(resolved.idxana)
    if history_rows is None:
        history_rows = await client.fetch_anagrafica_history(idxana=resolved.idxana)
        history_rows = _sort_history_rows(history_rows)
        storico_cache[resolved.idxana] = history_rows

    if not history_rows:
        return CapacitasAnagraficaHistoryImportItemResult(
            subject_id=str(item.subject_id) if item.subject_id else None,
            resolved_subject_id=str(resolved.subject.id) if resolved.subject is not None else None,
            idxana=resolved.idxana,
            status="skipped",
            message="Nessuno storico presente.",
        )

    latest_row = history_rows[-1]
    latest_detail = await _load_detail(client, latest_row.history_id, detail_cache)
    subject, person = _ensure_subject_person(
        db,
        subject=resolved.subject,
        person=resolved.person,
        idxana=resolved.idxana,
        latest_row=latest_row,
        latest_detail=latest_detail,
    )

    imported_records = 0
    for history_row in history_rows:
        detail = await _load_detail(client, history_row.history_id, detail_cache)
        snapshot_payload = _build_person_payload(detail, history_row)
        imported = persist_person_source_snapshot(
            db,
            person,
            snapshot_payload,
            source_system="capacitas",
            source_ref=history_row.history_id,
            collected_at=_parse_datetime_value(history_row.data_agg) or datetime.now(UTC),
            valid_from=_parse_datetime_value(history_row.data_agg),
            is_capacitas_history=True,
        )
        if imported:
            imported_records += 1

    if subject.source_external_id != resolved.idxana:
        subject.source_external_id = resolved.idxana
    if subject.source_system != "capacitas":
        subject.source_system = "capacitas"

    db.commit()
    db.refresh(subject)

    if imported_records == 0:
        return CapacitasAnagraficaHistoryImportItemResult(
            subject_id=str(item.subject_id) if item.subject_id else None,
            resolved_subject_id=str(subject.id),
            idxana=resolved.idxana,
            status="skipped",
            history_records_total=len(history_rows),
            skipped_records=len(history_rows),
            message="Storico gia importato.",
        )

    return CapacitasAnagraficaHistoryImportItemResult(
        subject_id=str(item.subject_id) if item.subject_id else None,
        resolved_subject_id=str(subject.id),
        idxana=resolved.idxana,
        status="imported",
        history_records_total=len(history_rows),
        imported_records=imported_records,
        skipped_records=len(history_rows) - imported_records,
        message=f"Importati {imported_records} record storici.",
    )


async def _resolve_target(
    db: Session,
    client: InVoltureClient,
    item: CapacitasAnagraficaHistoryImportItem,
) -> _ResolvedTarget:
    subject: AnagraficaSubject | None = None
    person: AnagraficaPerson | None = None
    idxana = item.idxana.strip() if item.idxana else None

    if item.subject_id is not None:
        subject = db.get(AnagraficaSubject, item.subject_id)
        if subject is None:
            raise CapacitasAnagraficaHistoryImportError(f"Soggetto {item.subject_id} non trovato.")
        person = db.get(AnagraficaPerson, item.subject_id)
        if person is None:
            raise CapacitasAnagraficaHistoryImportError(f"Soggetto {item.subject_id} non associato a una persona.")

    if idxana is None and subject is not None and subject.source_system == "capacitas" and subject.source_external_id:
        idxana = subject.source_external_id

    if idxana is None and person is not None:
        idxana = await _resolve_idxana_from_cf(client, person.codice_fiscale)

    if subject is None and idxana is not None:
        subject = db.scalar(
            select(AnagraficaSubject).where(
                AnagraficaSubject.source_system == "capacitas",
                AnagraficaSubject.source_external_id == idxana,
            )
        )
        if subject is not None:
            person = db.get(AnagraficaPerson, subject.id)

    return _ResolvedTarget(subject=subject, person=person, idxana=idxana)


async def _resolve_idxana_from_cf(client: InVoltureClient, codice_fiscale: str | None) -> str | None:
    normalized_cf = _normalize_cf(codice_fiscale)
    if not normalized_cf:
        return None
    search_result = await client.search_by_cf(normalized_cf)
    for row in search_result.rows:
        if _normalize_cf(row.codice_fiscale) == normalized_cf and row.id_ana:
            return row.id_ana
    matching_row = _pick_best_search_row(search_result.rows)
    return matching_row.id_ana if matching_row is not None else None


def _pick_best_search_row(rows: list[CapacitasAnagrafica]) -> CapacitasAnagrafica | None:
    for row in rows:
        if row.id_ana:
            return row
    return None


def _ensure_subject_person(
    db: Session,
    *,
    subject: AnagraficaSubject | None,
    person: AnagraficaPerson | None,
    idxana: str,
    latest_row: CapacitasStoricoAnagraficaRow,
    latest_detail: CapacitasAnagraficaDetail,
) -> tuple[AnagraficaSubject, AnagraficaPerson]:
    if subject is not None and person is not None:
        return subject, person

    normalized_cf = _normalize_cf(latest_detail.codice_fiscale or latest_row.codice_fiscale)
    if person is None and normalized_cf:
        person = db.scalar(select(AnagraficaPerson).where(AnagraficaPerson.codice_fiscale == normalized_cf))
        if person is not None and subject is None:
            subject = db.get(AnagraficaSubject, person.subject_id)

    if subject is None:
        if not normalized_cf:
            raise CapacitasAnagraficaHistoryImportError("Storico privo di codice fiscale utilizzabile per creare il soggetto.")
        payload = _build_person_payload(latest_detail, latest_row)
        subject = AnagraficaSubject(
            subject_type=AnagraficaSubjectType.PERSON.value,
            status=AnagraficaSubjectStatus.ACTIVE.value,
            source_system="capacitas",
            source_external_id=idxana,
            source_name_raw=latest_detail.denominazione or latest_row.denominazione or normalized_cf,
            requires_review=False,
        )
        db.add(subject)
        db.flush()
        person = AnagraficaPerson(subject_id=subject.id, **payload)
        db.add(person)
        db.flush()
        return subject, person

    if person is None:
        person = db.get(AnagraficaPerson, subject.id)
    if person is None:
        raise CapacitasAnagraficaHistoryImportError("Soggetto risolto senza record persona associato.")
    return subject, person


def _build_person_payload(
    detail: CapacitasAnagraficaDetail,
    history_row: CapacitasStoricoAnagraficaRow,
) -> dict[str, object | None]:
    cognome, nome = _split_denominazione(
        detail.denominazione or history_row.denominazione,
        fallback_cognome=detail.cognome,
        fallback_nome=detail.nome,
    )
    indirizzo = _compose_address(
        detail.residenza_toponimo,
        detail.residenza_indirizzo,
        detail.residenza_civico,
        detail.residenza_sub,
    )
    note_parts = [value.strip() for value in detail.note if value and value.strip()]
    return {
        "cognome": detail.cognome or cognome,
        "nome": detail.nome or nome,
        "codice_fiscale": _normalize_cf(detail.codice_fiscale or history_row.codice_fiscale) or "",
        "data_nascita": detail.data_nascita,
        "comune_nascita": history_row.luogo_nascita or detail.luogo_nascita,
        "indirizzo": indirizzo,
        "comune_residenza": detail.residenza_belfiore,
        "cap": detail.residenza_cap,
        "email": detail.email,
        "telefono": detail.telefono or detail.cellulare,
        "note": " | ".join(note_parts) if note_parts else None,
    }


def _sort_history_rows(rows: list[CapacitasStoricoAnagraficaRow]) -> list[CapacitasStoricoAnagraficaRow]:
    return sorted(
        rows,
        key=lambda row: (
            _parse_datetime_value(row.data_agg) or datetime.min.replace(tzinfo=UTC),
            row.history_id,
        ),
    )


async def _load_detail(
    client: InVoltureClient,
    history_id: str,
    cache: dict[str, CapacitasAnagraficaDetail],
) -> CapacitasAnagraficaDetail:
    detail = cache.get(history_id)
    if detail is None:
        detail = await client.fetch_anagrafica_detail(history_id=history_id)
        cache[history_id] = detail
    return detail
