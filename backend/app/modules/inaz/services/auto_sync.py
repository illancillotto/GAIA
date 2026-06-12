from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.inaz.models import InazAutoSyncConfig, InazCredential, InazSyncJob
from app.modules.inaz.schemas import InazAutoSyncConfigResponse, InazAutoSyncConfigUpdate
from app.modules.inaz.services.sync_runtime import build_period, get_sync_artifact_dir, has_running_sync_job, launch_sync_worker

INAZ_AUTO_SYNC_TIMES = ("06:00", "12:00", "18:00")


def get_auto_sync_config(db: Session) -> InazAutoSyncConfig:
    config = db.get(InazAutoSyncConfig, 1)
    if config is not None:
        return config

    config = InazAutoSyncConfig(id=1)
    db.add(config)
    db.flush()
    return config


def serialize_auto_sync_config(config: InazAutoSyncConfig) -> InazAutoSyncConfigResponse:
    return InazAutoSyncConfigResponse(
        job_enabled=config.job_enabled,
        credential_id=config.credential_id,
        collaborator_limit=config.collaborator_limit,
        updated_at=config.updated_at,
        updated_by_user_id=config.updated_by_user_id,
        schedule_cron=settings.inaz_auto_sync_cron,
        schedule_timezone=settings.inaz_auto_sync_timezone,
        schedule_times=list(INAZ_AUTO_SYNC_TIMES),
    )


def update_auto_sync_config(
    db: Session,
    payload: InazAutoSyncConfigUpdate,
    *,
    user_id: int,
) -> InazAutoSyncConfig:
    config = get_auto_sync_config(db)
    fields = payload.model_fields_set

    if "credential_id" in fields:
        if payload.credential_id is None:
            config.credential_id = None
        else:
            credential = db.get(InazCredential, payload.credential_id)
            if credential is None:
                raise HTTPException(status_code=404, detail="Credenziale Inaz non trovata")
            if not credential.active:
                raise HTTPException(status_code=409, detail="La credenziale Inaz selezionata non e attiva")
            config.credential_id = payload.credential_id

    if "collaborator_limit" in fields:
        config.collaborator_limit = payload.collaborator_limit

    if "job_enabled" in fields:
        config.job_enabled = bool(payload.job_enabled)

    if config.job_enabled:
        if config.credential_id is None:
            raise HTTPException(
                status_code=409,
                detail="Per attivare la sync automatica devi selezionare una credenziale Inaz attiva",
            )
        credential = db.get(InazCredential, config.credential_id)
        if credential is None:
            raise HTTPException(status_code=404, detail="Credenziale Inaz non trovata")
        if not credential.active:
            raise HTTPException(status_code=409, detail="La credenziale Inaz selezionata non e attiva")

    config.updated_at = datetime.now(UTC)
    config.updated_by_user_id = user_id
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def _resolve_trigger_user_id(db: Session, config: InazAutoSyncConfig, credential: InazCredential) -> int:
    for candidate_id in (config.updated_by_user_id, credential.application_user_id):
        if candidate_id is None:
            continue
        user = db.get(ApplicationUser, candidate_id)
        if user is not None and user.is_active and user.module_inaz:
            return user.id

    fallback_user_id = db.execute(
        select(ApplicationUser.id)
        .where(ApplicationUser.is_active.is_(True), ApplicationUser.module_inaz.is_(True))
        .order_by(ApplicationUser.id.asc())
        .limit(1)
    ).scalar_one_or_none()
    if fallback_user_id is None:
        raise RuntimeError("No active INAZ-enabled user available to own automatic sync jobs")
    return int(fallback_user_id)


def trigger_auto_sync_job(db: Session) -> InazSyncJob | None:
    config = get_auto_sync_config(db)
    if not config.job_enabled or config.credential_id is None:
        return None
    if has_running_sync_job(db):
        return None

    credential = db.get(InazCredential, config.credential_id)
    if credential is None or not credential.active:
        return None

    local_now = datetime.now(ZoneInfo(settings.inaz_auto_sync_timezone))
    period_start, period_end = build_period(local_now.year, local_now.month)
    requested_by_user_id = _resolve_trigger_user_id(db, config, credential)
    job = InazSyncJob(
        status="pending",
        requested_by_user_id=requested_by_user_id,
        credential_id=credential.id,
        period_start=period_start,
        period_end=period_end,
        collaborator_limit=config.collaborator_limit,
        max_attempts=settings.inaz_sync_max_attempts,
        params_json={
            "auth_mode": "credential",
            "year": local_now.year,
            "month": local_now.month,
            "trigger": "auto",
            "trigger_timezone": settings.inaz_auto_sync_timezone,
        },
    )
    db.add(job)
    db.flush()

    artifact_dir = get_sync_artifact_dir(str(job.id))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    job.worker_log_path = str(artifact_dir / "worker.log")
    job.json_artifact_path = str(artifact_dir / "inaz_collaboratori.json")

    try:
        job.worker_pid = launch_sync_worker(job)
    except Exception as exc:
        job.status = "failed"
        job.error_detail = str(exc)
        job.finished_at = datetime.now(UTC)
        db.add(job)
        db.commit()
        raise

    db.add(job)
    db.commit()
    db.refresh(job)
    return job
