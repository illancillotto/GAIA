from __future__ import annotations

import inspect
import logging
from collections.abc import Generator
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.capacitas import CapacitasCredential, CapacitasInCassSyncJob
from app.modules.elaborazioni.capacitas.models import CapacitasInCassRuoloHarvestRequest
from app.services.elaborazioni_capacitas_incass import ACTIVE_JOB_STATUSES, create_incass_ruolo_harvest_jobs

logger = logging.getLogger(__name__)


async def _consume_db_factory(get_db: Callable[[], Any]) -> tuple[Any, Generator | None]:
    resource = get_db()
    if inspect.isgenerator(resource):
        db = next(resource)
        return db, resource
    return resource, None


def run_incass_autosync_harvest(db: Session) -> int:
    if not settings.capacitas_incass_autosync_enabled:
        return 0

    active_job = db.scalar(
        select(CapacitasInCassSyncJob.id)
        .where(CapacitasInCassSyncJob.status.in_(tuple(ACTIVE_JOB_STATUSES)))
        .order_by(CapacitasInCassSyncJob.created_at.asc())
    )
    if active_job is not None:
        logger.info("inCASS autosync skipped: active job already queued or processing id=%s", active_job)
        return 0
    if not _has_active_capacitas_credential(db):
        logger.warning("inCASS autosync skipped: no active Capacitas credential available")
        return 0

    stale_before = datetime.now(timezone.utc) - timedelta(hours=settings.capacitas_incass_autosync_stale_after_hours)
    result = create_incass_ruolo_harvest_jobs(
        db,
        requested_by_user_id=None,
        payload=CapacitasInCassRuoloHarvestRequest(
            credential_id=settings.capacitas_incass_autosync_credential_id,
            anno=settings.capacitas_incass_autosync_anno,
            chunk_size=settings.capacitas_incass_autosync_chunk_size,
            limit_subjects=settings.capacitas_incass_autosync_limit_subjects,
            exclude_synced_subjects=False,
            stale_synced_before=stale_before,
            include_details=settings.capacitas_incass_autosync_include_details,
            include_partitario=settings.capacitas_incass_autosync_include_partitario,
            include_details_for_new_notices=settings.capacitas_incass_autosync_include_details_for_new_notices,
            include_partitario_for_new_notices=settings.capacitas_incass_autosync_include_partitario_for_new_notices,
            include_mailing_list=False,
            download_mailing_receipts=False,
            continue_on_error=True,
            throttle_ms=settings.capacitas_incass_autosync_throttle_ms,
        ),
    )
    if result.total_jobs:
        logger.info(
            "inCASS autosync queued %s jobs for %s stale subjects",
            result.total_jobs,
            result.total_subjects,
        )
    return result.total_jobs


def _has_active_capacitas_credential(db: Session) -> bool:
    stmt = select(CapacitasCredential.id).where(CapacitasCredential.active.is_(True))
    if settings.capacitas_incass_autosync_credential_id is not None:
        stmt = stmt.where(CapacitasCredential.id == settings.capacitas_incass_autosync_credential_id)
    return db.scalar(stmt.limit(1)) is not None


async def _run_job_wrapper(get_db: Callable[[], Any]) -> None:
    db, generator = await _consume_db_factory(get_db)
    try:
        run_incass_autosync_harvest(db)
    except Exception:
        logger.exception("inCASS autosync scheduler job failed")
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result
        if generator is not None:
            with suppress(StopIteration):
                next(generator)


async def register_incass_autosync_scheduler(scheduler: AsyncIOScheduler, get_db: Callable[[], Any]) -> None:
    if not settings.capacitas_incass_autosync_enabled:
        logger.info("inCASS autosync scheduler disabled; skip registration")
        return

    scheduler.add_job(
        _run_job_wrapper,
        trigger=IntervalTrigger(minutes=settings.capacitas_incass_autosync_interval_minutes, timezone="UTC"),
        id="capacitas_incass_autosync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        kwargs={"get_db": get_db},
    )
    logger.info(
        "inCASS autosync scheduler registered; interval_minutes=%s stale_after_hours=%s",
        settings.capacitas_incass_autosync_interval_minutes,
        settings.capacitas_incass_autosync_stale_after_hours,
    )
