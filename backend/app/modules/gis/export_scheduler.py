from __future__ import annotations

import inspect
import logging
from collections.abc import Generator
from contextlib import suppress
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.modules.gis.services import run_scheduled_shapefile_exports

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
        summary = run_scheduled_shapefile_exports(
            db,
            retention_count=settings.gis_export_retention_count,
            max_layers=settings.gis_export_max_layers_per_run,
        )
        logger.info(
            "GIS scheduled shapefile export completed: attempted=%s completed=%s failed=%s pruned=%s",
            summary.attempted_layers,
            summary.completed_exports,
            summary.failed_exports,
            summary.pruned_exports,
        )
    except Exception:
        logger.exception("GIS scheduled shapefile export failed")
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result
        if generator is not None:
            with suppress(StopIteration):
                next(generator)


async def register_gis_export_scheduler(
    scheduler: AsyncIOScheduler,
    get_db: Callable[[], Any],
) -> None:
    if not settings.gis_export_scheduler_enabled:
        logger.info("GIS export scheduler disabled; skip registration")
        return

    scheduler.add_job(
        _run_job_wrapper,
        trigger=CronTrigger.from_crontab(
            settings.gis_export_scheduler_cron,
            timezone=settings.gis_export_scheduler_timezone,
        ),
        id="gis_shapefile_export_schedule",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=4 * 3600,
        kwargs={"get_db": get_db},
    )
    logger.info(
        "GIS export scheduler registered; cron=%s timezone=%s retention=%s max_layers=%s",
        settings.gis_export_scheduler_cron,
        settings.gis_export_scheduler_timezone,
        settings.gis_export_retention_count,
        settings.gis_export_max_layers_per_run,
    )
