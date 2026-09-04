from __future__ import annotations

import inspect
import logging
from collections.abc import Callable, Generator
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.capacitas import CapacitasParticelleSyncJob
from app.models.catasto_phase1 import CatParticella
from app.modules.elaborazioni.capacitas_particelle_autosync_policy import (
    CapacitasParticelleAutoSyncJobRequest,
    build_autosync_due_predicate,
)
from app.services.elaborazioni_capacitas import has_available_credential
from app.services.elaborazioni_capacitas_particelle_sync import create_particelle_sync_job

logger = logging.getLogger(__name__)

UTC = timezone.utc  # noqa: UP017 - the runtime worker image still uses Python 3.10.
ACTIVE_JOB_STATUSES = {"pending", "queued_resume", "processing", "cancelling"}


def run_particelle_autosync(db: Session) -> int:
    if not settings.capacitas_particelle_autosync_enabled:
        return 0

    credential_id = settings.capacitas_particelle_autosync_credential_id
    if credential_id is None:
        logger.warning("Particelle autosync skipped: fixed credential id is not configured")
        return 0
    if not has_available_credential(db, credential_id):
        logger.warning(
            "Particelle autosync skipped: credential id=%s is unavailable", credential_id
        )
        return 0

    active_job_id = db.scalar(
        select(CapacitasParticelleSyncJob.id)
        .where(CapacitasParticelleSyncJob.status.in_(tuple(ACTIVE_JOB_STATUSES)))
        .order_by(CapacitasParticelleSyncJob.created_at.asc())
        .limit(1)
    )
    if active_job_id is not None:
        logger.info("Particelle autosync skipped: active job id=%s", active_job_id)
        return 0

    now = datetime.now(UTC)
    due_id = db.scalar(
        select(CatParticella.id)
        .where(
            build_autosync_due_predicate(
                now=now,
                refresh_days=settings.capacitas_particelle_autosync_refresh_days,
                transient_retry_hours=settings.capacitas_particelle_autosync_transient_retry_hours,
                failed_retry_hours=settings.capacitas_particelle_autosync_failed_retry_hours,
            )
        )
        .limit(1)
    )
    if due_id is None:
        logger.info("Particelle autosync skipped: no parcel is due")
        return 0

    job = create_particelle_sync_job(
        db,
        requested_by_user_id=None,
        credential_id=credential_id,
        payload=CapacitasParticelleAutoSyncJobRequest(
            credential_id=credential_id,
            only_due=True,
            limit=settings.capacitas_particelle_autosync_batch_size,
            fetch_certificati=True,
            fetch_details=True,
            double_speed=False,
            parallel_workers=1,
            auto_resume=True,
            refresh_days=settings.capacitas_particelle_autosync_refresh_days,
            transient_retry_hours=settings.capacitas_particelle_autosync_transient_retry_hours,
            failed_retry_hours=settings.capacitas_particelle_autosync_failed_retry_hours,
        ),
    )
    logger.info(
        "Particelle autosync queued job id=%s batch_size=%s",
        job.id,
        settings.capacitas_particelle_autosync_batch_size,
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
        run_particelle_autosync(db)
    except Exception:
        logger.exception("Particelle autosync scheduler job failed")
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result
        if generator is not None:
            with suppress(StopIteration):
                next(generator)


async def register_particelle_autosync_scheduler(
    scheduler: AsyncIOScheduler,
    get_db: Callable[[], Any],
) -> None:
    if not settings.capacitas_particelle_autosync_enabled:
        logger.info("Particelle autosync scheduler disabled; skip registration")
        return

    scheduler.add_job(
        _run_job_wrapper,
        trigger=IntervalTrigger(
            minutes=settings.capacitas_particelle_autosync_interval_minutes,
            timezone="UTC",
        ),
        id="capacitas_particelle_autosync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        kwargs={"get_db": get_db},
    )
    logger.info(
        "Particelle autosync scheduler registered; interval_minutes=%s refresh_days=%s batch_size=%s credential_id=%s",
        settings.capacitas_particelle_autosync_interval_minutes,
        settings.capacitas_particelle_autosync_refresh_days,
        settings.capacitas_particelle_autosync_batch_size,
        settings.capacitas_particelle_autosync_credential_id,
    )
