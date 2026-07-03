from __future__ import annotations

import inspect
import logging
from collections.abc import Generator
from contextlib import suppress
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.services.elaborazioni_bonifica_sync import (
    run_daily_bonifica_sync_job,
    run_operazioni_live_bonifica_sync_job,
)
from app.services.elaborazioni_auto_jobs import (
    is_whitecompany_daily_sync_enabled,
    is_whitecompany_operazioni_live_sync_enabled,
)

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
        if not is_whitecompany_daily_sync_enabled(db):
            logger.info("WhiteCompany daily job skipped: toggle disabled")
            return
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


async def _run_operazioni_live_job_wrapper(get_db: Callable[[], Any]) -> None:
    db, generator = await _consume_db_factory(get_db)
    try:
        if not is_whitecompany_operazioni_live_sync_enabled(db):
            logger.info("WhiteCompany Operazioni live job skipped: toggle disabled")
            return
        await run_operazioni_live_bonifica_sync_job(db)
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
        "WhiteCompany daily job registered; cron=%s timezone=%s default_enabled=%s",
        settings.wc_sync_daily_cron,
        settings.wc_sync_daily_timezone,
        settings.wc_sync_daily_enabled,
    )
    scheduler.add_job(
        _run_operazioni_live_job_wrapper,
        trigger=IntervalTrigger(
            seconds=max(settings.wc_sync_operazioni_live_interval_seconds, 60),
            timezone="UTC",
        ),
        id="whitecompany_operazioni_live_sync",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=max(settings.wc_sync_operazioni_live_interval_seconds, 60),
        kwargs={"get_db": get_db},
    )
    logger.info(
        "WhiteCompany Operazioni live job registered; interval_seconds=%s default_enabled=%s",
        max(settings.wc_sync_operazioni_live_interval_seconds, 60),
        settings.wc_sync_operazioni_live_enabled,
    )
