from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import PresenzeAutoSyncConfig, PresenzeCredential, PresenzeSyncJob
from app.modules.presenze.schemas import PresenzeAutoSyncConfigResponse, PresenzeAutoSyncConfigUpdate
from app.modules.presenze.services.sync_runtime import build_period, has_running_sync_job, prepare_sync_job_artifacts

PRESENZE_AUTO_SYNC_TIMES = ("06:00", "12:00", "18:00")
PRESENZE_PREVIOUS_MONTH_SYNC_CUTOFF_DAY = 10


def get_auto_sync_config(db: Session) -> PresenzeAutoSyncConfig:
    config = db.get(PresenzeAutoSyncConfig, 1)
    if config is not None:
        return config

    config = PresenzeAutoSyncConfig(id=1)
    db.add(config)
    db.flush()
    return config


def serialize_auto_sync_config(config: PresenzeAutoSyncConfig) -> PresenzeAutoSyncConfigResponse:
    return PresenzeAutoSyncConfigResponse(
        job_enabled=config.job_enabled,
        credential_id=config.credential_id,
        collaborator_limit=config.collaborator_limit,
        updated_at=config.updated_at,
        updated_by_user_id=config.updated_by_user_id,
        schedule_cron=settings.presenze_auto_sync_cron,
        schedule_timezone=settings.presenze_auto_sync_timezone,
        schedule_times=list(PRESENZE_AUTO_SYNC_TIMES),
    )


def _month_value(*, year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _should_include_previous_month(local_now: datetime) -> bool:
    if local_now.day > PRESENZE_PREVIOUS_MONTH_SYNC_CUTOFF_DAY:
        return False
    return local_now.strftime("%H:%M") == PRESENZE_AUTO_SYNC_TIMES[0]


def _resolve_auto_sync_period(local_now: datetime) -> tuple[date, date, list[str], str]:
    current_start, current_end = build_period(local_now.year, local_now.month)
    current_month_value = _month_value(year=local_now.year, month=local_now.month)
    if not _should_include_previous_month(local_now):
        return current_start, current_end, [current_month_value], "current_month_only"

    if local_now.month == 1:
        previous_year = local_now.year - 1
        previous_month = 12
    else:
        previous_year = local_now.year
        previous_month = local_now.month - 1
    previous_start, _ = build_period(previous_year, previous_month)
    previous_month_value = _month_value(year=previous_year, month=previous_month)
    return previous_start, current_end, [previous_month_value, current_month_value], "previous_and_current_month"


def update_auto_sync_config(
    db: Session,
    payload: PresenzeAutoSyncConfigUpdate,
    *,
    user_id: int,
) -> PresenzeAutoSyncConfig:
    config = get_auto_sync_config(db)
    fields = payload.model_fields_set

    if "credential_id" in fields:
        if payload.credential_id is None:
            config.credential_id = None
        else:
            credential = db.get(PresenzeCredential, payload.credential_id)
            if credential is None:
                raise HTTPException(status_code=404, detail="Credenziale Presenze non trovata")
            if not credential.active:
                raise HTTPException(status_code=409, detail="La credenziale Presenze selezionata non e attiva")
            config.credential_id = payload.credential_id

    if "collaborator_limit" in fields:
        config.collaborator_limit = payload.collaborator_limit

    if "job_enabled" in fields:
        config.job_enabled = bool(payload.job_enabled)

    if config.job_enabled:
        if config.credential_id is None:
            raise HTTPException(
                status_code=409,
                detail="Per attivare la sync automatica devi selezionare una credenziale Presenze attiva",
            )
        credential = db.get(PresenzeCredential, config.credential_id)
        if credential is None:
            raise HTTPException(status_code=404, detail="Credenziale Presenze non trovata")
        if not credential.active:
            raise HTTPException(status_code=409, detail="La credenziale Presenze selezionata non e attiva")

    config.updated_at = datetime.now(UTC)
    config.updated_by_user_id = user_id
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def _resolve_trigger_user_id(
    db: Session,
    config: PresenzeAutoSyncConfig,
    credential: PresenzeCredential,
) -> int:
    for candidate_id in (config.updated_by_user_id, credential.application_user_id):
        if candidate_id is None:
            continue
        user = db.get(ApplicationUser, candidate_id)
        if user is not None and user.is_active and user.module_presenze:
            return user.id

    fallback_user_id = db.execute(
        select(ApplicationUser.id)
        .where(ApplicationUser.is_active.is_(True), ApplicationUser.module_presenze.is_(True))
        .order_by(ApplicationUser.id.asc())
        .limit(1)
    ).scalar_one_or_none()
    if fallback_user_id is None:
        raise RuntimeError("No active Presenze-enabled user available to own automatic sync jobs")
    return int(fallback_user_id)


def trigger_auto_sync_job(db: Session) -> PresenzeSyncJob | None:
    config = get_auto_sync_config(db)
    if not config.job_enabled or config.credential_id is None:
        return None
    if has_running_sync_job(db):
        return None

    credential = db.get(PresenzeCredential, config.credential_id)
    if credential is None or not credential.active:
        return None

    local_now = datetime.now(ZoneInfo(settings.presenze_auto_sync_timezone))
    period_start, period_end, target_months, target_scope = _resolve_auto_sync_period(local_now)
    requested_by_user_id = _resolve_trigger_user_id(db, config, credential)
    job = PresenzeSyncJob(
        status="pending",
        requested_by_user_id=requested_by_user_id,
        credential_id=credential.id,
        period_start=period_start,
        period_end=period_end,
        collaborator_limit=config.collaborator_limit,
        max_attempts=settings.presenze_sync_max_attempts,
        params_json={
            "auth_mode": "credential",
            "year": local_now.year,
            "month": local_now.month,
            "trigger": "auto",
            "trigger_timezone": settings.presenze_auto_sync_timezone,
            "target_scope": target_scope,
            "target_months": target_months,
        },
    )
    db.add(job)
    db.flush()
    prepare_sync_job_artifacts(job)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
