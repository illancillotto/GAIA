from __future__ import annotations

import inspect
import logging
from collections.abc import Generator
from contextlib import suppress
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.modules.catasto.services.ade_wfs import run_ade_autosync_job

logger = logging.getLogger(__name__)


async def _consume_db_factory(get_db: Callable[[], Any]) -> tuple[Any, Generator | None]:
    resource = get_db()
    if inspect.isgenerator(resource):
        db = next(resource)
        return db, resource
    return resource, None


async def _run_catasto_ade_autosync_job(get_db: Callable[[], Any]) -> None:
    db, generator = await _consume_db_factory(get_db)
    try:
        if not settings.catasto_ade_autosync_enabled:
            logger.info("Catasto AdE autosync skipped: toggle disabled")
            return
        result = run_ade_autosync_job(db)
        logger.info("Catasto AdE autosync completed: %s", result)
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result
        if generator is not None:
            with suppress(StopIteration):
                next(generator)


async def register_catasto_ade_autosync_scheduler(
    scheduler: AsyncIOScheduler,
    get_db: Callable[[], Any],
) -> None:
    scheduler.add_job(
        _run_catasto_ade_autosync_job,
        trigger=CronTrigger.from_crontab(
            settings.catasto_ade_autosync_cron,
            timezone=settings.catasto_ade_autosync_timezone,
        ),
        id="catasto_ade_autosync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=4 * 3600,
        kwargs={"get_db": get_db},
    )
    logger.info(
        "Catasto AdE autosync scheduler registered; cron=%s timezone=%s default_enabled=%s",
        settings.catasto_ade_autosync_cron,
        settings.catasto_ade_autosync_timezone,
        settings.catasto_ade_autosync_enabled,
    )
