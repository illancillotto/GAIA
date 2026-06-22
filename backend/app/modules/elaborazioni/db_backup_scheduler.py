from __future__ import annotations

import inspect
import logging
from collections.abc import Generator
from contextlib import suppress
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.services.elaborazioni_auto_jobs import is_elaborazioni_db_backup_enabled
from app.services.elaborazioni_db_backup import run_elaborazioni_db_backup_job

logger = logging.getLogger(__name__)


async def _consume_db_factory(get_db: Callable[[], Any]) -> tuple[Any, Generator | None]:
    resource = get_db()
    if inspect.isgenerator(resource):
        db = next(resource)
        return db, resource
    return resource, None


async def _run_job_wrapper(get_db: Callable[[], Any]) -> None:
    db, generator = await _consume_db_factory(get_db)
    try:
        if not is_elaborazioni_db_backup_enabled(db):
            logger.info("Elaborazioni DB backup skipped: toggle disabled")
            return
        run_elaborazioni_db_backup_job()
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result
        if generator is not None:
            with suppress(StopIteration):
                next(generator)


async def register_elaborazioni_db_backup_scheduler(
    scheduler: AsyncIOScheduler,
    get_db: Callable[[], Any],
) -> None:
    scheduler.add_job(
        _run_job_wrapper,
        trigger=CronTrigger.from_crontab(
            settings.elaborazioni_db_backup_cron,
            timezone=settings.elaborazioni_db_backup_timezone,
        ),
        id="elaborazioni_db_backup",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=4 * 3600,
        kwargs={"get_db": get_db},
    )
    logger.info(
        "Elaborazioni DB backup scheduler registered; cron=%s timezone=%s retention=%s default_enabled=%s",
        settings.elaborazioni_db_backup_cron,
        settings.elaborazioni_db_backup_timezone,
        settings.elaborazioni_db_backup_retention_count,
        settings.elaborazioni_db_backup_enabled,
    )
