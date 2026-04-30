from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.models.capacitas import CapacitasParticelleSyncJob
from app.models.catasto_phase1 import CatComune, CatParticella
from app.modules.elaborazioni.capacitas.apps.involture.client import CapacitasSessionExpiredError, InVoltureClient
from app.modules.elaborazioni.capacitas.models import (
    CapacitasParticelleSyncJobCreateRequest,
    CapacitasParticelleSyncJobOut,
    CapacitasTerreniBatchItem,
    CapacitasTerreniBatchRequest,
)
from app.services.elaborazioni_capacitas_terreni import sync_terreni_batch

ROME_TZ = ZoneInfo("Europe/Rome")
DAY_THROTTLE_MS = 900
EVENING_THROTTLE_MS = 350
DOUBLE_SPEED_MULTIPLIER = 2
MIN_THROTTLE_MS = 100
MAX_PARALLEL_WORKERS = 2
DAY_RECHECK_HOURS = 72
EVENING_RECHECK_HOURS = 12
RECENT_ITEM_LIMIT = 200
PARTICELLE_STALE_JOB_MINUTES = 30
AUTO_RESUME_COMPATIBLE_MODES = {"progressive_catalog"}
UTC = timezone.utc


@dataclass(slots=True)
class ParticelleSyncPolicy:
    aggressive_window: bool
    throttle_ms: int
    due_before: datetime
    recheck_hours: int
    speed_multiplier: int
    parallel_workers: int


@dataclass(slots=True)
class ParticellaSyncItem:
    index: int
    particella_id: UUID
    label: str
    comune_label: str | None
    sezione: str
    foglio: str
    particella: str
    sub: str


def serialize_particelle_sync_job(job: CapacitasParticelleSyncJob) -> CapacitasParticelleSyncJobOut:
    return CapacitasParticelleSyncJobOut.model_validate(job)


def create_particelle_sync_job(
    db: Session,
    *,
    requested_by_user_id: int | None,
    credential_id: int | None,
    payload: CapacitasParticelleSyncJobCreateRequest,
) -> CapacitasParticelleSyncJob:
    payload_json = payload.model_dump(exclude_none=True, mode="json")
    payload_json.setdefault("auto_resume", True)
    job = CapacitasParticelleSyncJob(
        requested_by_user_id=requested_by_user_id,
        credential_id=credential_id,
        status="pending",
        mode="progressive_catalog",
        payload_json=payload_json,
        result_json=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_particelle_sync_jobs(db: Session) -> list[CapacitasParticelleSyncJob]:
    return list(db.scalars(select(CapacitasParticelleSyncJob).order_by(CapacitasParticelleSyncJob.id.desc())).all())


def get_particelle_sync_job(db: Session, job_id: int) -> CapacitasParticelleSyncJob | None:
    return db.get(CapacitasParticelleSyncJob, job_id)


def delete_particelle_sync_job(db: Session, job: CapacitasParticelleSyncJob) -> None:
    db.delete(job)
    db.commit()


def cancel_particelle_sync_job(db: Session, job: CapacitasParticelleSyncJob) -> CapacitasParticelleSyncJob:
    if job.status in {"pending", "queued_resume"}:
        # No worker is running — cancel immediately
        result_json = dict(job.result_json or {})
        result_json["current_label"] = None
        result_json["completed_at"] = datetime.now(UTC).isoformat()
        job.result_json = result_json
        job.status = "cancelled"
        job.completed_at = datetime.now(UTC)
    elif job.status == "processing":
        # Signal the worker to stop at the next iteration
        result_json = dict(job.result_json or {})
        result_json["stop_requested"] = True
        job.result_json = result_json
        job.status = "cancelling"
    # If already "cancelling" or terminal: no-op (idempotent)
    db.commit()
    db.refresh(job)
    return job


def _normalize_job_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _mark_stale_particelle_job(
    job: CapacitasParticelleSyncJob,
    *,
    completed_at: datetime,
    detail: str,
) -> None:
    job.status = "failed"
    job.completed_at = completed_at
    job.error_detail = f"{job.error_detail}\n{detail}".strip() if job.error_detail else detail
    if isinstance(job.result_json, dict):
        result_json = dict(job.result_json)
        result_json["current_label"] = None
        result_json["completed_at"] = completed_at.isoformat()
        job.result_json = result_json


def expire_stale_particelle_sync_jobs(db: Session) -> None:
    now = datetime.now(UTC)
    stale_cutoff = now - timedelta(minutes=PARTICELLE_STALE_JOB_MINUTES)
    jobs = db.scalars(
        select(CapacitasParticelleSyncJob).where(
            CapacitasParticelleSyncJob.status == "processing",
            CapacitasParticelleSyncJob.completed_at.is_(None),
        )
    ).all()
    if not jobs:
        return

    changed = False
    for job in jobs:
        started_at = _normalize_job_datetime(job.started_at)
        updated_at = _normalize_job_datetime(job.updated_at)
        reference_at = updated_at or started_at

        if reference_at is not None and reference_at < stale_cutoff:
            _mark_stale_particelle_job(
                job,
                completed_at=now,
                detail=(
                    "Job marcato come failed: worker Capacitas senza avanzamento oltre la soglia di "
                    f"{PARTICELLE_STALE_JOB_MINUTES} minuti."
                ),
            )
            changed = True

    if changed:
        db.commit()


def prepare_particelle_sync_jobs_for_recovery(db: Session) -> list[int]:
    now = datetime.now(UTC)
    jobs = db.scalars(
        select(CapacitasParticelleSyncJob).where(
            CapacitasParticelleSyncJob.status.in_(("pending", "processing", "queued_resume")),
            CapacitasParticelleSyncJob.completed_at.is_(None),
        )
    ).all()
    if not jobs:
        return []

    recovered_ids: list[int] = []
    changed = False
    for job in jobs:
        payload_json = dict(job.payload_json or {})
        auto_resume = bool(payload_json.get("auto_resume", True))
        if not auto_resume or job.mode not in AUTO_RESUME_COMPATIBLE_MODES:
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


def compute_sync_policy(
    now: datetime | None = None,
    *,
    double_speed: bool = False,
    parallel_workers: int = 1,
) -> ParticelleSyncPolicy:
    current = now or datetime.now(UTC)
    local = current.astimezone(ROME_TZ)
    aggressive_window = local.hour >= 19
    recheck_hours = EVENING_RECHECK_HOURS if aggressive_window else DAY_RECHECK_HOURS
    speed_multiplier = DOUBLE_SPEED_MULTIPLIER if double_speed else 1
    base_throttle_ms = EVENING_THROTTLE_MS if aggressive_window else DAY_THROTTLE_MS
    throttle_ms = max(MIN_THROTTLE_MS, round(base_throttle_ms / speed_multiplier))
    worker_count = max(1, min(MAX_PARALLEL_WORKERS, parallel_workers))
    return ParticelleSyncPolicy(
        aggressive_window=aggressive_window,
        throttle_ms=throttle_ms,
        due_before=current - timedelta(hours=recheck_hours),
        recheck_hours=recheck_hours,
        speed_multiplier=speed_multiplier,
        parallel_workers=worker_count,
    )


def _build_initial_result(total_items: int, policy: ParticelleSyncPolicy) -> dict[str, object]:
    return {
        "mode": "progressive_catalog",
        "total_items": total_items,
        "processed_items": 0,
        "success_items": 0,
        "failed_items": 0,
        "skipped_items": 0,
        "progress_percent": 0,
        "current_label": None,
        "throttle_ms": policy.throttle_ms,
        "aggressive_window": policy.aggressive_window,
        "recheck_hours": policy.recheck_hours,
        "speed_multiplier": policy.speed_multiplier,
        "parallel_workers": policy.parallel_workers,
        "recent_items": [],
    }


def _finalize_single_item_result(
    *,
    mode: str,
    policy: ParticelleSyncPolicy,
    item_result: dict[str, object],
) -> tuple[str, dict[str, object]]:
    status = str(item_result.get("status") or "failed")
    result_json = {
        "mode": mode,
        "total_items": 1,
        "processed_items": 1,
        "success_items": 1 if status == "synced" else 0,
        "failed_items": 1 if status == "failed" else 0,
        "skipped_items": 1 if status == "skipped" else 0,
        "progress_percent": 100,
        "current_label": None,
        "throttle_ms": policy.throttle_ms,
        "aggressive_window": policy.aggressive_window,
        "recheck_hours": policy.recheck_hours,
        "speed_multiplier": policy.speed_multiplier,
        "parallel_workers": 1,
        "recent_items": [item_result],
        "completed_at": datetime.now(UTC).isoformat(),
    }
    job_status = "succeeded" if status == "synced" else "completed_with_errors"
    return job_status, result_json


def _append_recent_item(result_json: dict[str, object], item: dict[str, object]) -> None:
    recent_items = result_json.get("recent_items")
    if not isinstance(recent_items, list):
        recent_items = []
        result_json["recent_items"] = recent_items
    recent_items.append(item)
    if len(recent_items) > RECENT_ITEM_LIMIT:
        del recent_items[0 : len(recent_items) - RECENT_ITEM_LIMIT]


def _compute_progress_percent(processed: int, total: int) -> int:
    if total <= 0:
        return 100
    return max(0, min(100, round((processed / total) * 100)))


def _resolve_comune_label(db: Session, particella: CatParticella) -> str | None:
    if particella.nome_comune:
        return particella.nome_comune
    if particella.comune_id:
        comune = db.get(CatComune, particella.comune_id)
        if comune is not None:
            return comune.nome_comune
    return None


def _select_particelle_for_job(
    db: Session,
    *,
    payload: CapacitasParticelleSyncJobCreateRequest,
    policy: ParticelleSyncPolicy,
) -> list[CatParticella]:
    query = (
        select(CatParticella)
        .where(CatParticella.is_current.is_(True), CatParticella.suppressed.is_(False))
        .order_by(CatParticella.capacitas_last_sync_at.asc().nullsfirst(), CatParticella.updated_at.asc())
    )
    if payload.only_due:
        query = query.where(
            or_(
                CatParticella.capacitas_last_sync_at.is_(None),
                CatParticella.capacitas_last_sync_at < policy.due_before,
            )
        )
    if payload.limit is not None:
        query = query.limit(payload.limit)
    return list(db.scalars(query).all())


def _build_sync_items(db: Session, particelle: list[CatParticella]) -> list[ParticellaSyncItem]:
    items: list[ParticellaSyncItem] = []
    for index, particella in enumerate(particelle, start=1):
        comune_label = _resolve_comune_label(db, particella)
        label = (
            f"{comune_label or 'Comune sconosciuto'} "
            f"{particella.foglio}/{particella.particella}"
            f"{f'/{particella.subalterno}' if particella.subalterno else ''}"
        )
        items.append(
            ParticellaSyncItem(
                index=index,
                particella_id=particella.id,
                label=label,
                comune_label=comune_label,
                sezione=particella.sezione_catastale or "",
                foglio=particella.foglio,
                particella=particella.particella,
                sub=particella.subalterno or "",
            ),
        )
    return items


async def _sync_particella_item(
    db: Session,
    client: InVoltureClient,
    *,
    job_id: int,
    credential_id: int | None,
    payload: CapacitasParticelleSyncJobCreateRequest,
    item: ParticellaSyncItem,
) -> dict[str, object]:
    current_time = datetime.now(UTC)
    particella = db.get(CatParticella, item.particella_id)
    if particella is None:
        return {
            "particella_id": str(item.particella_id),
            "label": item.label,
            "status": "failed",
            "message": "Particella non trovata durante la sync.",
        }

    if not item.comune_label:
        particella.capacitas_last_sync_at = current_time
        particella.capacitas_last_sync_status = "skipped"
        particella.capacitas_last_sync_error = "Comune non disponibile sulla particella."
        particella.capacitas_last_sync_job_id = job_id
        db.commit()
        return {
            "particella_id": str(item.particella_id),
            "label": item.label,
            "status": "skipped",
            "message": "Comune non disponibile sulla particella.",
        }

    batch_request = CapacitasTerreniBatchRequest(
        items=[
            CapacitasTerreniBatchItem(
                label=item.label,
                comune=item.comune_label,
                sezione=item.sezione,
                foglio=item.foglio,
                particella=item.particella,
                sub=item.sub,
            ),
        ],
        continue_on_error=False,
        credential_id=credential_id,
        fetch_certificati=payload.fetch_certificati,
        fetch_details=payload.fetch_details,
    )

    try:
        try:
            sync_result = await sync_terreni_batch(db, client, batch_request)
        except CapacitasSessionExpiredError:
            logger.warning("Sessione Capacitas scaduta per %s, re-login e retry", item.label)
            await client.relogin()
            sync_result = await sync_terreni_batch(db, client, batch_request)

        item_result = sync_result.items[0] if sync_result.items else None
        particella.capacitas_last_sync_at = current_time
        particella.capacitas_last_sync_job_id = job_id
        if item_result is None:
            particella.capacitas_last_sync_status = "failed"
            particella.capacitas_last_sync_error = "Nessun item result restituito dal sync."
            item_status = "failed"
            item_message = "Nessun item result restituito dal sync."
        elif not item_result.ok:
            particella.capacitas_last_sync_status = "failed"
            particella.capacitas_last_sync_error = item_result.error
            item_status = "failed"
            item_message = item_result.error or "Errore sync particella."
        elif item_result.total_rows <= 0:
            particella.capacitas_last_sync_status = "skipped"
            particella.capacitas_last_sync_error = None
            item_status = "skipped"
            item_message = "Nessun risultato Capacitas per la particella."
        else:
            particella.capacitas_last_sync_status = "synced"
            particella.capacitas_last_sync_error = None
            item_status = "synced"
            item_message = (
                f"{item_result.total_rows} righe, "
                f"{item_result.imported_certificati} certificati, "
                f"{item_result.imported_details} dettagli"
            )
        db.commit()
        return {
            "particella_id": str(item.particella_id),
            "label": item.label,
            "status": item_status,
            "message": item_message,
        }
    except Exception as exc:
        db.rollback()
        particella = db.get(CatParticella, item.particella_id)
        if particella is not None:
            particella.capacitas_last_sync_at = current_time
            particella.capacitas_last_sync_status = "failed"
            particella.capacitas_last_sync_error = str(exc)
            particella.capacitas_last_sync_job_id = job_id
            db.commit()
        return {
            "particella_id": str(item.particella_id),
            "label": item.label,
            "status": "failed",
            "message": str(exc),
        }


async def sync_single_particella(
    db: Session,
    client: InVoltureClient,
    *,
    particella_id: UUID,
    requested_by_user_id: int | None,
    credential_id: int | None,
    fetch_certificati: bool = True,
    fetch_details: bool = True,
) -> tuple[CapacitasParticelleSyncJob, dict[str, object], CatParticella]:
    particella = db.get(CatParticella, particella_id)
    if particella is None:
        raise RuntimeError("Particella non trovata.")

    items = _build_sync_items(db, [particella])
    if not items:
        raise RuntimeError("Particella non sincronizzabile.")

    payload = CapacitasParticelleSyncJobCreateRequest(
        credential_id=credential_id,
        only_due=False,
        limit=1,
        fetch_certificati=fetch_certificati,
        fetch_details=fetch_details,
        double_speed=False,
        parallel_workers=1,
    )
    policy = compute_sync_policy(double_speed=payload.double_speed, parallel_workers=payload.parallel_workers)
    job = CapacitasParticelleSyncJob(
        requested_by_user_id=requested_by_user_id,
        credential_id=credential_id,
        status="processing",
        mode="single_particella",
        payload_json=payload.model_dump(exclude_none=True, mode="json"),
        result_json=_build_initial_result(1, policy),
        started_at=datetime.now(UTC),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        item_result = await _sync_particella_item(
            db,
            client,
            job_id=job.id,
            credential_id=credential_id,
            payload=payload,
            item=items[0],
        )
        job = db.get(CapacitasParticelleSyncJob, job.id)
        assert job is not None
        final_status, final_result = _finalize_single_item_result(mode="single_particella", policy=policy, item_result=item_result)
        job.status = final_status
        job.result_json = final_result
        job.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(job)
        particella = db.get(CatParticella, particella_id)
        assert particella is not None
        return job, item_result, particella
    except Exception as exc:
        db.rollback()
        job = db.get(CapacitasParticelleSyncJob, job.id)
        assert job is not None
        job.status = "failed"
        job.error_detail = str(exc)
        job.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(job)
        raise


def _apply_item_progress(
    db: Session,
    *,
    job_id: int,
    total_items: int,
    item_result: dict[str, object],
    fallback_result: dict[str, object],
) -> CapacitasParticelleSyncJob:
    job = db.get(CapacitasParticelleSyncJob, job_id)
    assert job is not None
    current_result = dict(job.result_json or fallback_result)
    current_result["processed_items"] = int(current_result.get("processed_items", 0)) + 1
    item_status = item_result.get("status")
    if item_status == "synced":
        current_result["success_items"] = int(current_result.get("success_items", 0)) + 1
    elif item_status == "skipped":
        current_result["skipped_items"] = int(current_result.get("skipped_items", 0)) + 1
    else:
        current_result["failed_items"] = int(current_result.get("failed_items", 0)) + 1
    current_result["progress_percent"] = _compute_progress_percent(int(current_result["processed_items"]), total_items)
    current_result["current_label"] = item_result.get("label") if int(current_result["processed_items"]) < total_items else None
    _append_recent_item(current_result, item_result)
    job.result_json = current_result
    db.commit()
    return job


async def _run_particelle_sync_parallel(
    db: Session,
    *,
    session_factory: Callable[[], Session],
    clients: Sequence[InVoltureClient],
    job: CapacitasParticelleSyncJob,
    payload: CapacitasParticelleSyncJobCreateRequest,
    policy: ParticelleSyncPolicy,
    items: list[ParticellaSyncItem],
    result_json: dict[str, object],
) -> CapacitasParticelleSyncJob:
    queue: asyncio.Queue[ParticellaSyncItem] = asyncio.Queue()
    for item in items:
        queue.put_nowait(item)
    progress_lock = asyncio.Lock()

    async def worker(client: InVoltureClient) -> None:
        while True:
            try:
                item = queue.get_nowait()
            except asyncio.QueueEmpty:
                return

            job_check = db.get(CapacitasParticelleSyncJob, job.id)
            if job_check is not None and job_check.status == "cancelling":
                queue.task_done()
                return

            worker_db = session_factory()
            try:
                item_result = await _sync_particella_item(
                    worker_db,
                    client,
                    job_id=job.id,
                    credential_id=job.credential_id,
                    payload=payload,
                    item=item,
                )
            finally:
                worker_db.close()

            async with progress_lock:
                _apply_item_progress(
                    db,
                    job_id=job.id,
                    total_items=len(items),
                    item_result=item_result,
                    fallback_result=result_json,
                )
            queue.task_done()
            if not queue.empty() and policy.throttle_ms > 0:
                await asyncio.sleep(policy.throttle_ms / 1000)

    await asyncio.gather(*(worker(client) for client in clients))
    job = db.get(CapacitasParticelleSyncJob, job.id)
    assert job is not None
    return job


async def run_particelle_sync_job(
    db: Session,
    client: InVoltureClient,
    job: CapacitasParticelleSyncJob,
    *,
    session_factory: Callable[[], Session] | None = None,
    clients: Sequence[InVoltureClient] | None = None,
) -> CapacitasParticelleSyncJob:
    payload = CapacitasParticelleSyncJobCreateRequest.model_validate(job.payload_json or {})
    job.status = "processing"
    job.started_at = datetime.now(UTC)
    job.error_detail = None

    policy = compute_sync_policy(
        job.started_at,
        double_speed=payload.double_speed,
        parallel_workers=payload.parallel_workers,
    )
    particelle = _select_particelle_for_job(db, payload=payload, policy=policy)
    result_json = _build_initial_result(len(particelle), policy)
    client_pool = list(clients or [client])
    parallel_workers = min(policy.parallel_workers, len(client_pool), max(1, len(particelle)))
    result_json["parallel_workers"] = parallel_workers
    job.result_json = result_json
    db.commit()
    db.refresh(job)

    try:
        if parallel_workers > 1 and session_factory is not None:
            items = _build_sync_items(db, particelle)
            await _run_particelle_sync_parallel(
                db,
                session_factory=session_factory,
                clients=client_pool[:parallel_workers],
                job=job,
                payload=payload,
                policy=policy,
                items=items,
                result_json=result_json,
            )
            job = db.get(CapacitasParticelleSyncJob, job.id)
            assert job is not None
            final_result = dict(job.result_json or result_json)
            final_result["current_label"] = None
            final_result["completed_at"] = datetime.now(UTC).isoformat()
            job.result_json = final_result
            if job.status == "cancelling":
                job.status = "cancelled"
            else:
                final_result["progress_percent"] = 100
                job.status = "succeeded" if int(final_result.get("failed_items", 0)) == 0 else "completed_with_errors"
            job.completed_at = datetime.now(UTC)
            db.commit()
            db.refresh(job)
            return job

        for index, particella in enumerate(particelle, start=1):
            # job attributes are expired by SQLAlchemy after each commit, so status re-loads from DB
            if job.status == "cancelling":
                break
            current_time = datetime.now(UTC)
            current_result = dict(job.result_json or result_json)
            label = (
                f"{_resolve_comune_label(db, particella) or 'Comune sconosciuto'} "
                f"{particella.foglio}/{particella.particella}"
                f"{f'/{particella.subalterno}' if particella.subalterno else ''}"
            )
            current_result["current_label"] = label

            comune_label = _resolve_comune_label(db, particella)
            if not comune_label:
                particella.capacitas_last_sync_at = current_time
                particella.capacitas_last_sync_status = "skipped"
                particella.capacitas_last_sync_error = "Comune non disponibile sulla particella."
                particella.capacitas_last_sync_job_id = job.id
                current_result["processed_items"] = int(current_result.get("processed_items", 0)) + 1
                current_result["skipped_items"] = int(current_result.get("skipped_items", 0)) + 1
                current_result["progress_percent"] = _compute_progress_percent(int(current_result["processed_items"]), len(particelle))
                _append_recent_item(
                    current_result,
                    {
                        "particella_id": str(particella.id),
                        "label": label,
                        "status": "skipped",
                        "message": "Comune non disponibile sulla particella.",
                    },
                )
                job.result_json = current_result
                db.commit()
                continue

            try:
                _batch_req = CapacitasTerreniBatchRequest(
                    items=[
                        CapacitasTerreniBatchItem(
                            label=label,
                            comune=comune_label,
                            sezione=particella.sezione_catastale or "",
                            foglio=particella.foglio,
                            particella=particella.particella,
                            sub=particella.subalterno or "",
                        )
                    ],
                    continue_on_error=False,
                    credential_id=job.credential_id,
                    fetch_certificati=payload.fetch_certificati,
                    fetch_details=payload.fetch_details,
                )
                try:
                    sync_result = await sync_terreni_batch(db, client, _batch_req)
                except CapacitasSessionExpiredError:
                    logger.warning("Sessione Capacitas scaduta per %s, re-login e retry", label)
                    await client.relogin()
                    sync_result = await sync_terreni_batch(db, client, _batch_req)
                item_result = sync_result.items[0] if sync_result.items else None
                particella.capacitas_last_sync_at = current_time
                particella.capacitas_last_sync_job_id = job.id
                if item_result is None:
                    particella.capacitas_last_sync_status = "failed"
                    particella.capacitas_last_sync_error = "Nessun item result restituito dal sync."
                    current_result["failed_items"] = int(current_result.get("failed_items", 0)) + 1
                    item_status = "failed"
                    item_message = "Nessun item result restituito dal sync."
                elif not item_result.ok:
                    particella.capacitas_last_sync_status = "failed"
                    particella.capacitas_last_sync_error = item_result.error
                    current_result["failed_items"] = int(current_result.get("failed_items", 0)) + 1
                    item_status = "failed"
                    item_message = item_result.error or "Errore sync particella."
                elif item_result.total_rows <= 0:
                    particella.capacitas_last_sync_status = "skipped"
                    particella.capacitas_last_sync_error = None
                    current_result["skipped_items"] = int(current_result.get("skipped_items", 0)) + 1
                    item_status = "skipped"
                    item_message = "Nessun risultato Capacitas per la particella."
                else:
                    particella.capacitas_last_sync_status = "synced"
                    particella.capacitas_last_sync_error = None
                    current_result["success_items"] = int(current_result.get("success_items", 0)) + 1
                    item_status = "synced"
                    item_message = (
                        f"{item_result.total_rows} righe, "
                        f"{item_result.imported_certificati} certificati, "
                        f"{item_result.imported_details} dettagli"
                    )

                current_result["processed_items"] = int(current_result.get("processed_items", 0)) + 1
                current_result["progress_percent"] = _compute_progress_percent(int(current_result["processed_items"]), len(particelle))
                _append_recent_item(
                    current_result,
                    {
                        "particella_id": str(particella.id),
                        "label": label,
                        "status": item_status,
                        "message": item_message,
                    },
                )
                job.result_json = current_result
                db.commit()
            except Exception as exc:
                db.rollback()
                job = db.get(CapacitasParticelleSyncJob, job.id)
                particella = db.get(CatParticella, particella.id)
                assert job is not None
                assert particella is not None
                current_result = dict(job.result_json or result_json)
                particella.capacitas_last_sync_at = current_time
                particella.capacitas_last_sync_status = "failed"
                particella.capacitas_last_sync_error = str(exc)
                particella.capacitas_last_sync_job_id = job.id
                current_result["processed_items"] = int(current_result.get("processed_items", 0)) + 1
                current_result["failed_items"] = int(current_result.get("failed_items", 0)) + 1
                current_result["progress_percent"] = _compute_progress_percent(int(current_result["processed_items"]), len(particelle))
                _append_recent_item(
                    current_result,
                    {
                        "particella_id": str(particella.id),
                        "label": label,
                        "status": "failed",
                        "message": str(exc),
                    },
                )
                job.result_json = current_result
                db.commit()

            if index < len(particelle):
                # Re-read throttle_ms from result_json to pick up live speed overrides
                job_now = db.get(CapacitasParticelleSyncJob, job.id)
                effective_throttle = policy.throttle_ms
                if job_now is not None and isinstance(job_now.result_json, dict):
                    effective_throttle = int(job_now.result_json.get("throttle_ms", policy.throttle_ms))
                effective_throttle = max(MIN_THROTTLE_MS, effective_throttle)
                if effective_throttle > 0:
                    await asyncio.sleep(effective_throttle / 1000)

        job = db.get(CapacitasParticelleSyncJob, job.id)
        assert job is not None
        final_result = dict(job.result_json or result_json)
        final_result["current_label"] = None
        final_result["completed_at"] = datetime.now(UTC).isoformat()
        job.result_json = final_result
        if job.status == "cancelling":
            job.status = "cancelled"
        else:
            final_result["progress_percent"] = 100
            job.status = "succeeded" if int(final_result.get("failed_items", 0)) == 0 else "completed_with_errors"
        job.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(job)
        return job
    except Exception as exc:
        db.rollback()
        job = db.get(CapacitasParticelleSyncJob, job.id)
        assert job is not None
        job.status = "failed"
        job.error_detail = str(exc)
        job.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(job)
        raise
