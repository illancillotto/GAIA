from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.capacitas import CapacitasParticelleSyncJob
from app.models.catasto_phase1 import CatComune, CatParticella
from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
from app.modules.elaborazioni.capacitas.models import (
    CapacitasParticelleSyncJobCreateRequest,
    CapacitasParticelleSyncJobOut,
    CapacitasTerreniBatchItem,
    CapacitasTerreniBatchRequest,
)
from app.services.elaborazioni_capacitas_terreni import sync_terreni_batch

ROME_TZ = ZoneInfo("Europe/Rome")
DAY_THROTTLE_MS = 1500
EVENING_THROTTLE_MS = 350
DAY_RECHECK_HOURS = 24
EVENING_RECHECK_HOURS = 6
RECENT_ITEM_LIMIT = 200


@dataclass(slots=True)
class ParticelleSyncPolicy:
    aggressive_window: bool
    throttle_ms: int
    due_before: datetime
    recheck_hours: int


def serialize_particelle_sync_job(job: CapacitasParticelleSyncJob) -> CapacitasParticelleSyncJobOut:
    return CapacitasParticelleSyncJobOut.model_validate(job)


def create_particelle_sync_job(
    db: Session,
    *,
    requested_by_user_id: int | None,
    credential_id: int | None,
    payload: CapacitasParticelleSyncJobCreateRequest,
) -> CapacitasParticelleSyncJob:
    job = CapacitasParticelleSyncJob(
        requested_by_user_id=requested_by_user_id,
        credential_id=credential_id,
        status="pending",
        mode="progressive_catalog",
        payload_json=payload.model_dump(exclude_none=True, mode="json"),
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


def compute_sync_policy(now: datetime | None = None) -> ParticelleSyncPolicy:
    current = now or datetime.now(UTC)
    local = current.astimezone(ROME_TZ)
    aggressive_window = local.hour >= 19
    recheck_hours = EVENING_RECHECK_HOURS if aggressive_window else DAY_RECHECK_HOURS
    throttle_ms = EVENING_THROTTLE_MS if aggressive_window else DAY_THROTTLE_MS
    return ParticelleSyncPolicy(
        aggressive_window=aggressive_window,
        throttle_ms=throttle_ms,
        due_before=current - timedelta(hours=recheck_hours),
        recheck_hours=recheck_hours,
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
        "recent_items": [],
    }


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


async def run_particelle_sync_job(
    db: Session,
    client: InVoltureClient,
    job: CapacitasParticelleSyncJob,
) -> CapacitasParticelleSyncJob:
    payload = CapacitasParticelleSyncJobCreateRequest.model_validate(job.payload_json or {})
    job.status = "processing"
    job.started_at = datetime.now(UTC)
    job.error_detail = None

    policy = compute_sync_policy(job.started_at)
    particelle = _select_particelle_for_job(db, payload=payload, policy=policy)
    result_json = _build_initial_result(len(particelle), policy)
    job.result_json = result_json
    db.commit()
    db.refresh(job)

    try:
        for index, particella in enumerate(particelle, start=1):
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
                sync_result = await sync_terreni_batch(
                    db,
                    client,
                    CapacitasTerreniBatchRequest(
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
                    ),
                )
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

            if index < len(particelle) and policy.throttle_ms > 0:
                await asyncio.sleep(policy.throttle_ms / 1000)

        job = db.get(CapacitasParticelleSyncJob, job.id)
        assert job is not None
        final_result = dict(job.result_json or result_json)
        final_result["current_label"] = None
        final_result["progress_percent"] = 100
        final_result["completed_at"] = datetime.now(UTC).isoformat()
        job.result_json = final_result
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
