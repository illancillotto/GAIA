from __future__ import annotations

from math import ceil
import logging
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import PresenzeAutoSyncConfig, PresenzeCollaborator, PresenzeCredential, PresenzeSyncJob
from app.modules.presenze.schemas import PresenzeAutoSyncConfigResponse, PresenzeAutoSyncConfigUpdate
from app.modules.presenze.services.inaz_sync_status import build_auto_retry_history_entry
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
logger = logging.getLogger(__name__)


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


def _normalize_employee_code(value: object) -> str:
    return str(value or "").strip()


def _active_employee_codes(db: Session, *, limit: int | None = None) -> list[str]:
    stmt = (
        select(PresenzeCollaborator.employee_code)
        .where(PresenzeCollaborator.is_active.is_(True), PresenzeCollaborator.employee_code.is_not(None))
        .order_by(PresenzeCollaborator.employee_code.asc())
    )
    rows = db.execute(stmt).scalars().all()
    codes: list[str] = []
    seen: set[str] = set()
    for row in rows:
        code = _normalize_employee_code(row)
        if not code or code in seen:
            continue
        seen.add(code)
        codes.append(code)
        if limit is not None and len(codes) >= limit:
            break
    return codes


def _employee_codes_for_job(job: PresenzeSyncJob) -> list[str]:
    params = job.params_json or {}
    values = params.get("employee_codes")
    if not isinstance(values, list):
        return []
    return [code for code in (_normalize_employee_code(value) for value in values) if code]


def _open_employee_codes_for_period(
    db: Session,
    *,
    credential_id: int,
    period_start,
    period_end,
) -> set[str] | None:
    jobs = db.execute(
        select(PresenzeSyncJob).where(
            PresenzeSyncJob.credential_id == credential_id,
            PresenzeSyncJob.period_start == period_start,
            PresenzeSyncJob.period_end == period_end,
            PresenzeSyncJob.status.in_(("pending", "running")),
        )
    ).scalars()
    open_codes: set[str] = set()
    for job in jobs:
        params = job.params_json or {}
        if params.get("trigger") != "auto":
            return None
        codes = _employee_codes_for_job(job)
        if not codes:
            return None
        open_codes.update(codes)
    return open_codes


def _chunk_employee_codes(codes: list[str]) -> list[list[str]]:
    if not codes:
        return []
    chunk_size = max(1, settings.presenze_auto_sync_parallel_chunk_size)
    max_jobs = max(1, settings.presenze_auto_sync_parallel_max_jobs)
    shard_count = min(max_jobs, ceil(len(codes) / chunk_size))
    balanced_size = ceil(len(codes) / shard_count)
    return [codes[index : index + balanced_size] for index in range(0, len(codes), balanced_size)]


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


def _auto_sync_failure_superseded_by_completed_job(db: Session, job: PresenzeSyncJob) -> bool:
    created_at = _as_utc(job.created_at)
    if created_at is None:
        return False
    candidates = db.execute(
        select(PresenzeSyncJob)
        .where(
            PresenzeSyncJob.id != job.id,
            PresenzeSyncJob.credential_id == job.credential_id,
            PresenzeSyncJob.status == "completed",
            PresenzeSyncJob.period_start == job.period_start,
            PresenzeSyncJob.period_end == job.period_end,
            PresenzeSyncJob.finished_at.is_not(None),
        )
        .order_by(PresenzeSyncJob.finished_at.desc(), PresenzeSyncJob.id.desc())
    ).scalars()
    return any(
        _is_auto_sync_job(candidate) and (_as_utc(candidate.finished_at) or created_at) >= created_at
        for candidate in candidates
    )


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
        build_auto_retry_history_entry(job, queued_at=now),
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


def _create_auto_sync_job(
    db: Session,
    *,
    requested_by_user_id: int,
    credential_id: int,
    period_start,
    period_end,
    local_now: datetime,
    target_months: list[str],
    target_scope: str,
    collaborator_limit: int | None,
    sync_group_id: str | None = None,
    shard_index: int | None = None,
    shard_count: int | None = None,
    employee_codes: list[str] | None = None,
) -> PresenzeSyncJob:
    params_json: dict[str, object] = {
        "auth_mode": "credential",
        "year": local_now.year,
        "month": local_now.month,
        "trigger": "auto",
        "trigger_timezone": settings.presenze_auto_sync_timezone,
        "target_scope": target_scope,
        "target_months": target_months,
    }
    if sync_group_id is not None:
        params_json["sync_group_id"] = sync_group_id
    if shard_index is not None and shard_count is not None:
        params_json["shard_index"] = shard_index
        params_json["shard_count"] = shard_count
        params_json["target_scope"] = f"{target_scope}_shard"
    if employee_codes is not None:
        params_json["employee_codes"] = employee_codes

    job = PresenzeSyncJob(
        status="pending",
        requested_by_user_id=requested_by_user_id,
        credential_id=credential_id,
        period_start=period_start,
        period_end=period_end,
        collaborator_limit=collaborator_limit,
        max_attempts=settings.presenze_sync_max_attempts,
        params_json=params_json,
    )
    db.add(job)
    db.flush()
    prepare_sync_job_artifacts(job)
    db.add(job)
    return job


def trigger_auto_sync_job(db: Session) -> PresenzeSyncJob | None:
    if not _try_acquire_auto_sync_lock(db):
        return None

    config = get_auto_sync_config(db)
    if not config.job_enabled or config.credential_id is None:
        return None

    stale_changed = reconcile_stale_sync_jobs(db, commit=False)

    credential = db.get(PresenzeCredential, config.credential_id)
    if credential is None or not credential.active:
        _commit_stale_changes_if_needed(db, stale_changed)
        return None

    now = datetime.now(UTC)
    latest_auto_sync_job = _latest_auto_sync_job(db, credential_id=credential.id)
    if (
        not settings.presenze_auto_sync_parallel_enabled
        and latest_auto_sync_job is not None
        and latest_auto_sync_job.status == "failed"
        and not _auto_sync_failure_superseded_by_completed_job(db, latest_auto_sync_job)
    ):
        if not _is_auto_sync_retry_due(latest_auto_sync_job, now=now):
            _commit_stale_changes_if_needed(db, stale_changed)
            return None
        if latest_auto_sync_job.attempt_count < latest_auto_sync_job.max_attempts:
            return _requeue_auto_sync_job(db, latest_auto_sync_job, now=now)

    local_now = datetime.now(ZoneInfo(settings.presenze_auto_sync_timezone))
    period_start, period_end, target_months, target_scope = _resolve_auto_sync_period(local_now)
    requested_by_user_id = _resolve_trigger_user_id(db, config, credential)

    if settings.presenze_auto_sync_parallel_enabled:
        open_codes = _open_employee_codes_for_period(
            db,
            credential_id=credential.id,
            period_start=period_start,
            period_end=period_end,
        )
        if open_codes is not None:
            active_codes = _active_employee_codes(db, limit=config.collaborator_limit)
            pending_codes = [code for code in active_codes if code not in open_codes]
            chunks = _chunk_employee_codes(pending_codes)
            if chunks:
                sync_group_id = uuid.uuid4().hex
                jobs: list[PresenzeSyncJob] = []
                for index, chunk in enumerate(chunks, start=1):
                    jobs.append(
                        _create_auto_sync_job(
                            db,
                            requested_by_user_id=requested_by_user_id,
                            credential_id=credential.id,
                            period_start=period_start,
                            period_end=period_end,
                            local_now=local_now,
                            target_months=target_months,
                            target_scope=target_scope,
                            collaborator_limit=len(chunk),
                            sync_group_id=sync_group_id,
                            shard_index=index,
                            shard_count=len(chunks),
                            employee_codes=chunk,
                        )
                    )
                db.commit()
                first_job = jobs[0]
                db.refresh(first_job)
                apply_sync_job_retention(db)
                logger.info(
                    "Presenze auto sync queued %d shard job(s); group=%s period=%s..%s employees=%d",
                    len(jobs),
                    sync_group_id,
                    period_start,
                    period_end,
                    len(pending_codes),
                )
                return first_job
            if active_codes:
                _commit_stale_changes_if_needed(db, stale_changed)
                return None

    has_open_job, _ = _reconcile_and_has_open_sync_job(db)
    if has_open_job:
        _commit_stale_changes_if_needed(db, stale_changed)
        return None

    job = _create_auto_sync_job(
        db,
        requested_by_user_id=requested_by_user_id,
        credential_id=credential.id,
        period_start=period_start,
        period_end=period_end,
        local_now=local_now,
        target_months=target_months,
        target_scope=target_scope,
        collaborator_limit=config.collaborator_limit,
    )
    db.commit()
    db.refresh(job)
    apply_sync_job_retention(db)
    logger.info("Presenze auto sync queued single job; period=%s..%s", period_start, period_end)
    return job
