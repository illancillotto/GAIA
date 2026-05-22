from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.models.wc_sync_job import WCSyncJob
from app.modules.operazioni.models.vehicles import Vehicle
from app.modules.operazioni.schemas.vehicles import VehicleAutodocSyncJobResponse

AUTODOC_SYNC_ENTITY = "autodoc_vehicle_details"
AUTODOC_RUNNING_STATUSES = {"queued", "running"}
AUTODOC_STALE_MINUTES = 90


def serialize_autodoc_sync_job(job: WCSyncJob) -> VehicleAutodocSyncJobResponse:
    return VehicleAutodocSyncJobResponse(
        job_id=str(job.id),
        entity=job.entity,
        status=job.status,
        started_at=job.started_at,
        finished_at=job.finished_at,
        records_synced=job.records_synced,
        records_skipped=job.records_skipped,
        records_errors=job.records_errors,
        error_detail=job.error_detail,
        params_json=job.params_json,
    )


def _base_vehicle_query(
    *,
    vehicle_ids: list[UUID] | None = None,
    only_with_autodoc_url: bool = False,
) -> Select[tuple[Vehicle]]:
    query = select(Vehicle).where(Vehicle.is_active == True)
    if vehicle_ids:
        query = query.where(Vehicle.id.in_(vehicle_ids))
    if only_with_autodoc_url:
        query = query.where(Vehicle.autodoc_url.is_not(None))
    return query.order_by(Vehicle.name.asc())


def _normalize_started_at(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def expire_stale_autodoc_jobs(db: Session) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=AUTODOC_STALE_MINUTES)
    jobs = db.scalars(
        select(WCSyncJob).where(
            WCSyncJob.entity == AUTODOC_SYNC_ENTITY,
            WCSyncJob.status == "running",
            WCSyncJob.finished_at.is_(None),
        )
    ).all()
    changed = False
    for job in jobs:
        if _normalize_started_at(job.started_at) >= cutoff:
            continue
        job.status = "failed"
        job.finished_at = datetime.now(timezone.utc)
        job.records_synced = job.records_synced or 0
        job.records_skipped = job.records_skipped or 0
        job.records_errors = max(job.records_errors or 0, 1)
        job.error_detail = (
            f"{job.error_detail}\nJob AUTODOC marcato come failed: timeout oltre {AUTODOC_STALE_MINUTES} minuti."
            if job.error_detail
            else f"Job AUTODOC marcato come failed: timeout oltre {AUTODOC_STALE_MINUTES} minuti."
        )
        changed = True
    if changed:
        db.commit()


def get_latest_autodoc_sync_job(db: Session) -> WCSyncJob | None:
    expire_stale_autodoc_jobs(db)
    return db.scalar(
        select(WCSyncJob)
        .where(WCSyncJob.entity == AUTODOC_SYNC_ENTITY)
        .order_by(WCSyncJob.started_at.desc())
        .limit(1)
    )


def queue_autodoc_sync_job(
    db: Session,
    *,
    current_user: ApplicationUser,
    vehicle_ids: list[UUID] | None = None,
    only_with_autodoc_url: bool = False,
    force_refresh: bool = False,
) -> WCSyncJob:
    expire_stale_autodoc_jobs(db)

    existing = db.scalar(
        select(WCSyncJob)
        .where(
            WCSyncJob.entity == AUTODOC_SYNC_ENTITY,
            WCSyncJob.status.in_(tuple(AUTODOC_RUNNING_STATUSES)),
            WCSyncJob.finished_at.is_(None),
        )
        .order_by(WCSyncJob.started_at.desc())
        .limit(1)
    )
    if existing is not None:
        return existing

    vehicles = db.scalars(
        _base_vehicle_query(
            vehicle_ids=vehicle_ids,
            only_with_autodoc_url=only_with_autodoc_url,
        )
    ).all()
    selected_ids = [str(item.id) for item in vehicles]
    params_json: dict[str, Any] = {
        "vehicle_ids": selected_ids,
        "only_with_autodoc_url": only_with_autodoc_url,
        "force_refresh": force_refresh,
        "scope": "single" if len(selected_ids) == 1 else "batch",
        "selected_total": len(selected_ids),
    }
    job = WCSyncJob(
        id=uuid.uuid4(),
        entity=AUTODOC_SYNC_ENTITY,
        status="queued",
        triggered_by=current_user.id,
        params_json=params_json,
        records_synced=0,
        records_skipped=0,
        records_errors=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
