from __future__ import annotations

import inspect
import logging
from collections.abc import Generator
from contextlib import suppress
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.modules.utenze.services.visure_routing_service import route_public_visure_files
from app.services.nas_connector import get_nas_client

logger = logging.getLogger(__name__)


async def _consume_db_factory(get_db: Callable[[], Any]) -> tuple[Any, Generator | None]:
    resource = get_db()
    if inspect.isgenerator(resource):
        db = next(resource)
        return db, resource
    return resource, None


async def _run_visure_router_job(get_db: Callable[[], Any]) -> None:
    db, generator = await _consume_db_factory(get_db)
    connector = get_nas_client()
    try:
        result = route_public_visure_files(db, connector, source_path=settings.visure_nas_inbox_path)
        logger.info(
            "Visure NAS router completed: scanned=%s ignored=%s moved=%s created_documents=%s updated_documents=%s anomalies_created=%s anomalies_updated=%s",
            result.scanned_files,
            result.ignored_files,
            result.moved_files,
            result.created_documents,
            result.updated_documents,
            result.created_anomalies,
            result.updated_anomalies,
        )
    finally:
        close_connector = getattr(connector, "close", None)
        if callable(close_connector):
            close_connector()
        close_db = getattr(db, "close", None)
        if callable(close_db):
            result = close_db()
            if inspect.isawaitable(result):
                await result
        if generator is not None:
            with suppress(StopIteration):
                next(generator)


async def register_visure_router_scheduler(scheduler: AsyncIOScheduler, get_db: Callable[[], Any]) -> None:
    if not settings.visure_nas_router_enabled:
        logger.info("Visure NAS router scheduler disabled; skip registration")
        return

    scheduler.add_job(
        _run_visure_router_job,
        trigger=CronTrigger.from_crontab(
            settings.visure_nas_router_cron,
            timezone=settings.visure_nas_router_timezone,
        ),
        id="utenze_visure_nas_router",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        kwargs={"get_db": get_db},
    )
    logger.info(
        "Visure NAS router scheduler registered; cron=%s timezone=%s inbox=%s",
        settings.visure_nas_router_cron,
        settings.visure_nas_router_timezone,
        settings.visure_nas_inbox_path,
    )
