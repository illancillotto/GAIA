from __future__ import annotations

import logging
from contextlib import suppress
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.modules.inaz.services.auto_sync import trigger_auto_sync_job

logger = logging.getLogger(__name__)


def _run_job_wrapper(get_db: Callable[[], Any]) -> None:
    db, generator = get_db(), None
    if hasattr(db, "__next__"):
        generator = db
        db = next(generator)

    try:
        trigger_auto_sync_job(db)
    except Exception:
        logger.exception("INAZ automatic sync scheduler job failed")
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            close()
        if generator is not None:
            with suppress(StopIteration):
                next(generator)


async def register_inaz_scheduler(scheduler: AsyncIOScheduler, get_db: Callable[[], Any]) -> None:
    scheduler.add_job(
        _run_job_wrapper,
        trigger=CronTrigger.from_crontab(settings.inaz_auto_sync_cron, timezone=settings.inaz_auto_sync_timezone),
        id="inaz_auto_sync",
        replace_existing=True,
        misfire_grace_time=3600,
        kwargs={"get_db": get_db},
    )
    logger.info(
        "INAZ automatic sync registered; cron=%s timezone=%s",
        settings.inaz_auto_sync_cron,
        settings.inaz_auto_sync_timezone,
    )
