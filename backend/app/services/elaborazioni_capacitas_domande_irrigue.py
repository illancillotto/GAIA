from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.capacitas import CapacitasDomandeIrrigueSyncJob
from app.modules.catasto.services.domande_irrigue import persist_capacitas_domande_irrigue_batch, scan_domande_irrigue_anomalies
from app.modules.elaborazioni.capacitas.apps.involture.client import CapacitasSessionExpiredError, InVoltureClient
from app.modules.elaborazioni.capacitas.apps.involture.domande_irrigue import DomandeIrrigueScraper
from app.modules.elaborazioni.capacitas.models import (
    CapacitasAnagrafica,
    CapacitasDomandeIrrigueSyncJobCreateRequest,
    CapacitasDomandeIrrigueSyncJobOut,
)

UTC = timezone.utc
DOMANDE_IRRIGUE_STALE_JOB_MINUTES = 30
RECENT_DOMANDE_IRRIGUE_ITEM_LIMIT = 100


def serialize_domande_irrigue_sync_job(job: CapacitasDomandeIrrigueSyncJob) -> CapacitasDomandeIrrigueSyncJobOut:
    return CapacitasDomandeIrrigueSyncJobOut.model_validate(job)


def create_domande_irrigue_sync_job(
    db: Session,
    *,
    requested_by_user_id: int | None,
    credential_id: int | None,
    payload: CapacitasDomandeIrrigueSyncJobCreateRequest,
) -> CapacitasDomandeIrrigueSyncJob:
    payload_json = payload.model_dump(exclude_none=True, mode="json")
    payload_json.setdefault("auto_resume", True)
    job = CapacitasDomandeIrrigueSyncJob(
        requested_by_user_id=requested_by_user_id,
        credential_id=credential_id,
        status="pending",
        mode="anagrafica_search",
        payload_json=payload_json,
        result_json=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_domande_irrigue_sync_jobs(db: Session) -> list[CapacitasDomandeIrrigueSyncJob]:
    return list(db.scalars(select(CapacitasDomandeIrrigueSyncJob).order_by(CapacitasDomandeIrrigueSyncJob.id.desc())).all())


def get_domande_irrigue_sync_job(db: Session, job_id: int) -> CapacitasDomandeIrrigueSyncJob | None:
    return db.get(CapacitasDomandeIrrigueSyncJob, job_id)


def delete_domande_irrigue_sync_job(db: Session, job: CapacitasDomandeIrrigueSyncJob) -> None:
    db.delete(job)
    db.commit()


def _normalize_job_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def expire_stale_domande_irrigue_sync_jobs(db: Session) -> None:
    now = datetime.now(UTC)
    stale_cutoff = now - timedelta(minutes=DOMANDE_IRRIGUE_STALE_JOB_MINUTES)
    jobs = db.scalars(
        select(CapacitasDomandeIrrigueSyncJob).where(
            CapacitasDomandeIrrigueSyncJob.status == "processing",
            CapacitasDomandeIrrigueSyncJob.completed_at.is_(None),
        )
    ).all()
    changed = False
    for job in jobs:
        reference_at = _normalize_job_datetime(job.updated_at) or _normalize_job_datetime(job.started_at)
        if reference_at is not None and reference_at < stale_cutoff:
            result_json = dict(job.result_json or {})
            result_json["current_label"] = None
            result_json["completed_at"] = now.isoformat()
            job.result_json = result_json
            job.status = "failed"
            job.completed_at = now
            detail = (
                "Job marcato come failed: worker Capacitas domande irrigue senza avanzamento "
                f"oltre la soglia di {DOMANDE_IRRIGUE_STALE_JOB_MINUTES} minuti."
            )
            job.error_detail = f"{job.error_detail}\n{detail}".strip() if job.error_detail else detail
            changed = True
    if changed:
        db.commit()


def prepare_domande_irrigue_sync_jobs_for_recovery(db: Session) -> list[int]:
    now = datetime.now(UTC)
    jobs = db.scalars(
        select(CapacitasDomandeIrrigueSyncJob).where(
            CapacitasDomandeIrrigueSyncJob.status.in_(("pending", "processing", "queued_resume")),
            CapacitasDomandeIrrigueSyncJob.completed_at.is_(None),
        )
    ).all()
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


async def run_domande_irrigue_sync_job(
    db: Session,
    client: InVoltureClient,
    scraper: DomandeIrrigueScraper,
    job: CapacitasDomandeIrrigueSyncJob,
) -> CapacitasDomandeIrrigueSyncJob:
    payload = CapacitasDomandeIrrigueSyncJobCreateRequest.model_validate(job.payload_json or {})
    job.status = "processing"
    job.started_at = datetime.now(UTC)
    job.completed_at = None
    job.error_detail = None
    job.result_json = _build_initial_result(total_searches=len(payload.searches))
    db.commit()
    db.refresh(job)

    try:
        rows = await _load_anagrafica_rows(db, client, job, payload)
        if payload.deduplicate_contexts:
            rows = _deduplicate_rows(rows)
            _update_result(db, job, skipped_duplicate_contexts=int((job.result_json or {}).get("source_rows", 0)) - len(rows))
        _update_result(db, job, total_rows=len(rows))
        await _process_rows(db, scraper, job, payload, rows)
        _finalize_anomaly_scan(db, job, payload)
        _finish_job(db, job)
        return job
    except Exception as exc:
        db.rollback()
        job = db.get(CapacitasDomandeIrrigueSyncJob, job.id)
        assert job is not None
        job.status = "failed"
        job.error_detail = str(exc)
        job.completed_at = datetime.now(UTC)
        result_json = dict(job.result_json or {})
        result_json["current_label"] = None
        result_json["completed_at"] = job.completed_at.isoformat()
        job.result_json = result_json
        db.commit()
        db.refresh(job)
        raise


async def _load_anagrafica_rows(
    db: Session,
    client: InVoltureClient,
    job: CapacitasDomandeIrrigueSyncJob,
    payload: CapacitasDomandeIrrigueSyncJobCreateRequest,
) -> list[CapacitasAnagrafica]:
    rows: list[CapacitasAnagrafica] = []
    for search in payload.searches:
        try:
            result = await client.search_anagrafica(
                q=search.q,
                tipo=search.tipo_ricerca,
                solo_con_beni=search.solo_con_beni,
            )
            rows.extend(result.rows)
            _update_result(
                db,
                job,
                searches_completed=1,
                source_rows=len(result.rows),
                current_label=f"Ricerca anagrafica: {search.q}",
            )
        except CapacitasSessionExpiredError:
            await client.relogin()
            result = await client.search_anagrafica(
                q=search.q,
                tipo=search.tipo_ricerca,
                solo_con_beni=search.solo_con_beni,
            )
            rows.extend(result.rows)
            _update_result(db, job, searches_completed=1, source_rows=len(result.rows), current_label=f"Ricerca anagrafica: {search.q}")
        except Exception as exc:
            _append_recent_item(
                job.result_json or {},
                {"status": "failed", "label": f"Ricerca anagrafica: {search.q}", "error": str(exc)},
            )
            _update_result(db, job, searches_completed=1, failed_items=1)
            if not payload.continue_on_error:
                raise
    return rows


async def _process_rows(
    db: Session,
    scraper: DomandeIrrigueScraper,
    job: CapacitasDomandeIrrigueSyncJob,
    payload: CapacitasDomandeIrrigueSyncJobCreateRequest,
    rows: Sequence[CapacitasAnagrafica],
) -> None:
    for index, row in enumerate(rows, start=1):
        label = _row_label(row)
        _update_result(db, job, current_label=label)
        try:
            batch = await scraper.fetch_for_anagrafica_rows(
                [row],
                include_details=payload.include_details,
                continue_on_error=payload.continue_on_error,
            )
            summary = persist_capacitas_domande_irrigue_batch(db, batch, run_anomaly_checks=False)
            db.commit()
            item = batch.items[0] if batch.items else None
            item_status = "failed" if item is not None and item.error else "checked"
            item_payload = {
                "status": item_status,
                "label": label,
                "source_row_id": row.id,
                "cco": row.cco,
                "com": row.com,
                "pvc": row.pvc,
                "fra": row.fraz,
                "ccs": row.sche or "00000",
                "total_domande": item.total_domande if item is not None else 0,
                "error": item.error if item is not None else None,
            }
            _append_recent_item(job.result_json or {}, item_payload)
            _update_result(
                db,
                job,
                processed_rows=1,
                records_with_domande=1 if item is not None and item.total_domande > 0 else 0,
                failed_items=1 if item_status == "failed" else 0,
                **_summary_delta(summary),
            )
        except Exception as exc:
            db.rollback()
            _append_recent_item(job.result_json or {}, {"status": "failed", "label": label, "source_row_id": row.id, "error": str(exc)})
            _update_result(db, job, processed_rows=1, failed_items=1)
            if not payload.continue_on_error:
                raise
        if index < len(rows) and payload.throttle_ms > 0:
            await asyncio.sleep(payload.throttle_ms / 1000)


def _finalize_anomaly_scan(
    db: Session,
    job: CapacitasDomandeIrrigueSyncJob,
    payload: CapacitasDomandeIrrigueSyncJobCreateRequest,
) -> None:
    if not payload.run_anomaly_checks:
        return
    summary = scan_domande_irrigue_anomalies(db)
    _update_result(db, job, anomalies_opened=summary.opened, anomalies_updated=summary.updated)


def _finish_job(db: Session, job: CapacitasDomandeIrrigueSyncJob) -> None:
    result_json = dict(job.result_json or {})
    result_json["current_label"] = None
    result_json["progress_percent"] = 100
    result_json["completed_at"] = datetime.now(UTC).isoformat()
    job.result_json = result_json
    job.status = "succeeded" if int(result_json.get("failed_items", 0)) == 0 else "completed_with_errors"
    job.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(job)


def _build_initial_result(*, total_searches: int) -> dict[str, Any]:
    return {
        "mode": "anagrafica_search",
        "total_searches": total_searches,
        "searches_completed": 0,
        "source_rows": 0,
        "skipped_duplicate_contexts": 0,
        "total_rows": 0,
        "processed_rows": 0,
        "records_with_domande": 0,
        "domande_seen": 0,
        "domande_inserted": 0,
        "domande_updated": 0,
        "particelle_inserted": 0,
        "linked_utenze": 0,
        "linked_occupancies": 0,
        "linked_particelle": 0,
        "anomalies_opened": 0,
        "anomalies_updated": 0,
        "failed_items": 0,
        "progress_percent": 0,
        "current_label": None,
        "recent_items": [],
    }


def _update_result(db: Session, job: CapacitasDomandeIrrigueSyncJob, **deltas: Any) -> None:
    result_json = dict(job.result_json or _build_initial_result(total_searches=0))
    for key, value in deltas.items():
        if key == "current_label":
            result_json[key] = value
        else:
            result_json[key] = int(result_json.get(key, 0) or 0) + int(value or 0)
    total_rows = int(result_json.get("total_rows", 0) or 0)
    processed = int(result_json.get("processed_rows", 0) or 0)
    result_json["progress_percent"] = 100 if total_rows <= 0 else max(0, min(100, round((processed / total_rows) * 100)))
    job.result_json = result_json
    db.commit()
    db.refresh(job)


def _append_recent_item(result_json: dict[str, Any], item: dict[str, Any]) -> None:
    recent_items = result_json.get("recent_items")
    if not isinstance(recent_items, list):
        recent_items = []
        result_json["recent_items"] = recent_items
    recent_items.append({key: value for key, value in item.items() if value is not None})
    if len(recent_items) > RECENT_DOMANDE_IRRIGUE_ITEM_LIMIT:
        del recent_items[0 : len(recent_items) - RECENT_DOMANDE_IRRIGUE_ITEM_LIMIT]


def _summary_delta(summary: Any) -> dict[str, int]:
    return {
        "domande_seen": int(summary.domande_seen),
        "domande_inserted": int(summary.domande_inserted),
        "domande_updated": int(summary.domande_updated),
        "particelle_inserted": int(summary.particelle_inserted),
        "linked_utenze": int(summary.linked_utenze),
        "linked_occupancies": int(summary.linked_occupancies),
        "linked_particelle": int(summary.linked_particelle),
    }


def _deduplicate_rows(rows: Sequence[CapacitasAnagrafica]) -> list[CapacitasAnagrafica]:
    seen: set[tuple[str, str, str, str, str]] = set()
    result: list[CapacitasAnagrafica] = []
    for row in rows:
        key = (row.cco or "", row.com or "", row.pvc or "", row.fraz or "", row.sche or "00000")
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def _row_label(row: CapacitasAnagrafica) -> str:
    context = " / ".join(part for part in [row.cco, row.com, row.pvc, row.fraz, row.sche or "00000"] if part)
    return f"{row.denominazione or row.codice_fiscale or row.id_ana or 'Anagrafica'} [{context or 'contesto incompleto'}]"
