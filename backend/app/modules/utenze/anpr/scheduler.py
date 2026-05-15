from __future__ import annotations

import inspect
import logging
from collections.abc import Generator
from contextlib import suppress
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.modules.utenze.anpr.service import get_config, run_daily_job

logger = logging.getLogger(__name__)


async def _consume_db_factory(get_db: Callable[[], Any]) -> tuple[Any, Generator | None]:
    resource = get_db()
    if inspect.isgenerator(resource):
        db = next(resource)
        return db, resource
    return resource, None


async def _run_job_wrapper(get_db: Callable[[], Any]) -> None:
    async def db_factory():
        db, generator = await _consume_db_factory(get_db)
        if generator is not None:
            setattr(db, "_anpr_generator", generator)
        return db

    await run_daily_job(db_factory)


async def register_anpr_scheduler(scheduler: AsyncIOScheduler, get_db: Callable[[], Any]) -> None:
    """
    Legge config da DB e registra il job.
    Chiamare durante l'avvio del backend (lifespan o startup event).
    """
    db, generator = await _consume_db_factory(get_db)
    try:
        config = await get_config(db)
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result
        if generator is not None:
            with suppress(StopIteration):
                next(generator)

    if not config.job_enabled:
        logger.info("ANPR daily job disabled; skip scheduler registration")
        return

    scheduler.add_job(
        _run_job_wrapper,
        trigger=CronTrigger.from_crontab(config.job_cron, timezone=settings.anpr_job_timezone),
        id="anpr_daily_check",
        replace_existing=True,
        misfire_grace_time=3600,
        kwargs={"get_db": get_db},
    )
    logger.info("ANPR daily job registered; cron=%s", config.job_cron)
