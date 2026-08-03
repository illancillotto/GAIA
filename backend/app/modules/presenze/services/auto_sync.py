from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import PresenzeAutoSyncConfig, PresenzeCredential, PresenzeSyncJob
from app.modules.presenze.schemas import PresenzeAutoSyncConfigResponse, PresenzeAutoSyncConfigUpdate
from app.modules.presenze.services.sync_runtime import (
    _as_utc,
    apply_sync_job_retention,
    build_period,
    prepare_sync_job_artifacts,
    reconcile_stale_sync_jobs,
)

PRESENZE_AUTO_SYNC_TIMES = ("06:00", "12:00", "18:00")
PRESENZE_PREVIOUS_MONTH_SYNC_CUTOFF_DAY = 10
AUTO_SYNC_RETRY_HISTORY_LIMIT = 10
PRESENZE_AUTO_SYNC_ADVISORY_LOCK_KEY = 760031001


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


def _session_dialect_name(db: Session) -> str:
    bind = db.get_bind()
    return str(getattr(getattr(bind, "dialect", None), "name", ""))


def _try_acquire_auto_sync_lock(db: Session) -> bool:
    if _session_dialect_name(db) != "postgresql":
        return True
    acquired = db.execute(
        text("SELECT pg_try_advisory_xact_lock(:lock_key)"),
        {"lock_key": PRESENZE_AUTO_SYNC_ADVISORY_LOCK_KEY},
    ).scalar()
    return bool(acquired)


def _reconcile_and_has_open_sync_job(db: Session) -> tuple[bool, bool]:
    stale_changed = reconcile_stale_sync_jobs(db, commit=False)
    existing = db.execute(
        select(PresenzeSyncJob.id).where(PresenzeSyncJob.status.in_(("pending", "running"))).limit(1)
    ).first()
    return existing is not None, stale_changed


def _commit_stale_changes_if_needed(db: Session, stale_changed: bool) -> None:
    if stale_changed:
        db.commit()


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


def _is_auto_sync_job(job: PresenzeSyncJob) -> bool:
    return (job.params_json or {}).get("trigger") == "auto"


def _latest_auto_sync_job(db: Session, *, credential_id: int) -> PresenzeSyncJob | None:
    jobs = db.execute(
        select(PresenzeSyncJob)
        .where(PresenzeSyncJob.credential_id == credential_id)
        .order_by(PresenzeSyncJob.created_at.desc(), PresenzeSyncJob.id.desc())
    ).scalars()
    return next((job for job in jobs if _is_auto_sync_job(job)), None)


def _is_auto_sync_retry_due(job: PresenzeSyncJob, *, now: datetime) -> bool:
    last_terminal_at = _as_utc(job.finished_at) or _as_utc(job.started_at) or _as_utc(job.created_at)
    if last_terminal_at is None:
        return False
    retry_delay = timedelta(hours=settings.presenze_auto_sync_retry_delay_hours)
    return _as_utc(now) - last_terminal_at >= retry_delay


def _requeue_auto_sync_job(db: Session, job: PresenzeSyncJob, *, now: datetime) -> PresenzeSyncJob:
    params = dict(job.params_json or {})
    retry_history = params.get("auto_retry_history")
    if not isinstance(retry_history, list):
        retry_history = []
    retry_history = [
        *retry_history,
        {
            "queued_at": _as_utc(now).isoformat(),
            "attempt_count": job.attempt_count,
            "previous_status": job.status,
            "previous_error": job.error_detail,
        },
    ][-AUTO_SYNC_RETRY_HISTORY_LIMIT:]
    progress = dict(params.get("progress") or {})
    progress.update(
        {
            "state": "pending",
            "last_event": "auto_retry_queued",
            "last_event_at": _as_utc(now).isoformat(),
        }
    )
    progress.pop("error", None)
    params["auto_retry_history"] = retry_history
    params["progress"] = progress

    job.status = "pending"
    job.error_detail = None
    job.started_at = None
    job.finished_at = None
    job.worker_pid = None
    job.params_json = params
    prepare_sync_job_artifacts(job)
    db.add(job)
    db.commit()
    db.refresh(job)
    apply_sync_job_retention(db)
    return job


def trigger_auto_sync_job(db: Session) -> PresenzeSyncJob | None:
    if not _try_acquire_auto_sync_lock(db):
        return None

    config = get_auto_sync_config(db)
    if not config.job_enabled or config.credential_id is None:
        return None

    has_open_job, stale_changed = _reconcile_and_has_open_sync_job(db)
    if has_open_job:
        _commit_stale_changes_if_needed(db, stale_changed)
        return None

    credential = db.get(PresenzeCredential, config.credential_id)
    if credential is None or not credential.active:
        _commit_stale_changes_if_needed(db, stale_changed)
        return None

    now = datetime.now(UTC)
    latest_auto_sync_job = _latest_auto_sync_job(db, credential_id=credential.id)
    if latest_auto_sync_job is not None and latest_auto_sync_job.status == "failed":
        if not _is_auto_sync_retry_due(latest_auto_sync_job, now=now):
            _commit_stale_changes_if_needed(db, stale_changed)
            return None
        if latest_auto_sync_job.attempt_count < latest_auto_sync_job.max_attempts:
            return _requeue_auto_sync_job(db, latest_auto_sync_job, now=now)

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
    apply_sync_job_retention(db)
    return job
