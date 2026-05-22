from __future__ import annotations

import inspect
import logging
from collections.abc import Generator
from contextlib import suppress
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.services.elaborazioni_bonifica_sync import run_daily_bonifica_sync_job

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
        await run_daily_bonifica_sync_job(db)
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result
        if generator is not None:
            with suppress(StopIteration):
                next(generator)


async def register_bonifica_scheduler(scheduler: AsyncIOScheduler, get_db: Callable[[], Any]) -> None:
    if not settings.wc_sync_daily_enabled:
        logger.info("WhiteCompany daily job disabled; skip scheduler registration")
        return

    scheduler.add_job(
        _run_job_wrapper,
        trigger=CronTrigger.from_crontab(
            settings.wc_sync_daily_cron,
            timezone=settings.wc_sync_daily_timezone,
        ),
        id="whitecompany_daily_sync",
        replace_existing=True,
        misfire_grace_time=3600,
        kwargs={"get_db": get_db},
    )
    logger.info(
        "WhiteCompany daily job registered; cron=%s timezone=%s",
        settings.wc_sync_daily_cron,
        settings.wc_sync_daily_timezone,
    )
