from __future__ import annotations

import inspect
import logging
from collections.abc import Callable, Generator
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.capacitas import (
    CapacitasCredential,
    CapacitasDomandeIrrigueAutoSyncState,
    CapacitasDomandeIrrigueSyncJob,
)
from app.models.catasto_phase1 import CatUtenzaIrrigua
from app.modules.catasto.services.domande_irrigue import scan_domande_irrigue_anomalies
from app.modules.elaborazioni.capacitas.models import (
    CapacitasDomandeIrrigueAnagraficaSearch,
    CapacitasDomandeIrrigueSyncJobCreateRequest,
)
from app.services.elaborazioni_capacitas import has_available_credential
from app.services.elaborazioni_capacitas_domande_irrigue import create_domande_irrigue_sync_job

logger = logging.getLogger(__name__)

ACTIVE_JOB_STATUSES = {"pending", "queued_resume", "processing"}
SUCCESS_JOB_STATUSES = {"succeeded", "completed_with_errors"}


class _AutoSyncJobRequest(CapacitasDomandeIrrigueSyncJobCreateRequest):
    trigger: Literal["autosync"] = "autosync"


def _window_zone() -> ZoneInfo:
    try:
        return ZoneInfo(settings.capacitas_domande_irrigue_autosync_timezone)
    except ZoneInfoNotFoundError:
        logger.warning(
            "Domande irrigue autosync timezone %r non valida; uso UTC",
            settings.capacitas_domande_irrigue_autosync_timezone,
        )
        return ZoneInfo("UTC")


def _window_context(now_utc: datetime | None = None) -> tuple[bool, str]:
    local_now = (now_utc or datetime.now(UTC)).astimezone(_window_zone())
    start = settings.capacitas_domande_irrigue_autosync_start_hour
    end = settings.capacitas_domande_irrigue_autosync_end_hour
    if not settings.capacitas_domande_irrigue_autosync_window_enabled or start == end:
        return True, local_now.date().isoformat()
    if start < end:
        return start <= local_now.hour < end, local_now.date().isoformat()
    within_window = local_now.hour >= start or local_now.hour < end
    cycle_date = local_now.date() - timedelta(days=1) if local_now.hour < end else local_now.date()
    return within_window, cycle_date.isoformat()


def _load_state(db: Session) -> CapacitasDomandeIrrigueAutoSyncState:
    state = db.get(CapacitasDomandeIrrigueAutoSyncState, 1)
    if state is None:
        state = CapacitasDomandeIrrigueAutoSyncState(id=1)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def _reconcile_pending_job(db: Session, state: CapacitasDomandeIrrigueAutoSyncState) -> bool:
    if state.pending_job_id is None:
        return False
    job = db.get(CapacitasDomandeIrrigueSyncJob, state.pending_job_id)
    if job is not None and job.status in ACTIVE_JOB_STATUSES:
        return True
    if job is not None and job.status in SUCCESS_JOB_STATUSES:
        state.cursor = state.pending_cursor
        payload = job.payload_json if isinstance(job.payload_json, dict) else {}
        state.processed_identifiers += len(payload.get("searches") or [])
        state.last_error = job.error_detail if job.status == "completed_with_errors" else None
    else:
        state.last_error = job.error_detail if job is not None else "Job autosync non trovato"
    state.pending_job_id = None
    state.pending_cursor = None
    db.commit()
    return False


def _next_identifiers(db: Session, cursor: str | None) -> list[str]:
    identifier = func.upper(func.trim(CatUtenzaIrrigua.codice_fiscale))
    query = (
        select(identifier)
        .where(
            CatUtenzaIrrigua.codice_fiscale.is_not(None),
            identifier != "",
            identifier != "NAN",
            func.length(identifier).in_((11, 16)),
        )
        .group_by(identifier)
        .order_by(identifier)
        .limit(settings.capacitas_domande_irrigue_autosync_chunk_size)
    )
    if cursor is not None:
        query = query.where(identifier > cursor)
    return [str(value) for value in db.execute(query).scalars().all()]


def _has_configured_credential(db: Session, credential_id: int) -> bool:
    return (
        db.scalar(
            select(CapacitasCredential.id).where(
                CapacitasCredential.id == credential_id,
                CapacitasCredential.active.is_(True),
            )
        )
        is not None
    )


def run_domande_irrigue_autosync(db: Session, *, now_utc: datetime | None = None) -> int:
    context = _autosync_context(db, now_utc)
    if context is None:
        return 0
    cycle_key, credential_id = context

    state = _load_state(db)
    if state.completed_cycle_key == cycle_key or _reconcile_pending_job(db, state):
        return 0
    active_job_id = db.scalar(
        select(CapacitasDomandeIrrigueSyncJob.id)
        .where(CapacitasDomandeIrrigueSyncJob.status.in_(tuple(ACTIVE_JOB_STATUSES)))
        .limit(1)
    )
    if active_job_id is not None:
        return 0

    identifiers = _next_identifiers(db, state.cursor)
    now = now_utc or datetime.now(UTC)
    if not identifiers:
        _complete_cycle(db, state, cycle_key=cycle_key, now=now)
        return 0
    return _enqueue_chunk(
        db, state, identifiers, cycle_key=cycle_key, credential_id=credential_id, now=now
    )


def _autosync_context(db: Session, now_utc: datetime | None) -> tuple[str, int] | None:
    if not settings.capacitas_domande_irrigue_autosync_enabled:
        return None
    within_window, cycle_key = _window_context(now_utc)
    if not within_window:
        return None
    credential_id = settings.capacitas_domande_irrigue_autosync_credential_id
    if credential_id is None:
        logger.warning("Domande irrigue autosync sospeso: credenziale fissa non configurata")
        return None
    if not _has_configured_credential(db, credential_id) or not has_available_credential(
        db, credential_id
    ):
        logger.warning(
            "Domande irrigue autosync sospeso: credenziale id=%s non disponibile", credential_id
        )
        return None
    return cycle_key, credential_id


def _complete_cycle(
    db: Session, state: CapacitasDomandeIrrigueAutoSyncState, *, cycle_key: str, now: datetime
) -> None:
    anomaly_summary = scan_domande_irrigue_anomalies(db)
    state.cursor, state.cycle_key = None, None
    state.completed_cycle_key, state.cycle_completed_at = cycle_key, now
    state.last_error = None
    db.commit()
    logger.info(
        "Domande irrigue autosync ciclo %s completato: identifiers=%s anomalies=%s/%s/%s",
        cycle_key,
        state.processed_identifiers,
        anomaly_summary.opened,
        anomaly_summary.updated,
        anomaly_summary.closed,
    )


def _enqueue_chunk(
    db: Session,
    state: CapacitasDomandeIrrigueAutoSyncState,
    identifiers: list[str],
    *,
    cycle_key: str,
    credential_id: int,
    now: datetime,
) -> int:
    if state.cycle_key != cycle_key:
        state.cycle_key, state.cycle_started_at = cycle_key, now
        state.cycle_completed_at, state.processed_identifiers = None, 0
    job = create_domande_irrigue_sync_job(
        db,
        requested_by_user_id=None,
        credential_id=credential_id,
        payload=_AutoSyncJobRequest(
            credential_id=credential_id,
            searches=[
                CapacitasDomandeIrrigueAnagraficaSearch(
                    q=value, tipo_ricerca=1, solo_con_beni=False
                )
                for value in identifiers
            ],
            include_details=settings.capacitas_domande_irrigue_autosync_include_details,
            continue_on_error=True,
            run_anomaly_checks=False,
            deduplicate_contexts=True,
            throttle_ms=settings.capacitas_domande_irrigue_autosync_throttle_ms,
            auto_resume=True,
        ),
    )
    state.pending_job_id = job.id
    state.pending_cursor = identifiers[-1]
    state.last_error = None
    db.commit()
    logger.info(
        "Domande irrigue autosync accodato job id=%s chunk=%s cursor=%s",
        job.id,
        len(identifiers),
        state.pending_cursor,
    )
    return job.id


async def _consume_db_factory(get_db: Callable[[], Any]) -> tuple[Any, Generator | None]:
    resource = get_db()
    if inspect.isgenerator(resource):
        return next(resource), resource
    return resource, None


async def _run_job_wrapper(get_db: Callable[[], Any]) -> None:
    db, generator = await _consume_db_factory(get_db)
    try:
        run_domande_irrigue_autosync(db)
    except Exception:
        logger.exception("Domande irrigue autosync scheduler job fallito")
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result
        if generator is not None:
            with suppress(StopIteration):
                next(generator)


async def register_domande_irrigue_autosync_scheduler(
    scheduler: AsyncIOScheduler,
    get_db: Callable[[], Any],
) -> None:
    if not settings.capacitas_domande_irrigue_autosync_enabled:
        logger.info("Domande irrigue autosync scheduler disabilitato")
        return
    scheduler.add_job(
        _run_job_wrapper,
        trigger=IntervalTrigger(
            minutes=settings.capacitas_domande_irrigue_autosync_interval_minutes,
            timezone="UTC",
        ),
        id="capacitas_domande_irrigue_autosync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        kwargs={"get_db": get_db},
    )
