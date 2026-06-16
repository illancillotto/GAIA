from __future__ import annotations

import inspect
import logging
from collections.abc import Generator
from contextlib import suppress
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.services.elaborazioni_ruolo_autosync import run_ruolo_autosync_maintenance_for_all_users

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
        started = run_ruolo_autosync_maintenance_for_all_users(db)
        if started:
            logger.info("Ruolo autosync maintenance avviata per %s utenti", started)
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result
        if generator is not None:
            with suppress(StopIteration):
                next(generator)


async def register_ruolo_autosync_scheduler(scheduler: AsyncIOScheduler, get_db: Callable[[], Any]) -> None:
    scheduler.add_job(
        _run_job_wrapper,
        trigger=IntervalTrigger(minutes=1, timezone="UTC"),
        id="elaborazioni_ruolo_autosync",
        replace_existing=True,
        max_instances=1,
        kwargs={"get_db": get_db},
    )
    logger.info("Ruolo autosync scheduler registrato con intervallo di 1 minuto")
