from __future__ import annotations

import inspect
import logging
from collections.abc import Generator
from contextlib import suppress
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.modules.wiki.services.conversation_backfill_jobs import (
    process_next_wiki_conversation_metrics_backfill_job,
    prune_wiki_conversation_metrics_backfill_jobs,
)
from app.modules.wiki.services.conversation_metrics import refresh_recent_wiki_conversation_daily_metrics
from app.modules.wiki.services.telemetry import prune_wiki_telemetry_data, refresh_recent_wiki_daily_metrics

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
        refresh_recent_wiki_daily_metrics(db, days=settings.wiki_telemetry_schedule_lookback_days)
        refresh_recent_wiki_conversation_daily_metrics(db, days=settings.wiki_telemetry_schedule_lookback_days)
        prune_wiki_telemetry_data(
            db,
            audit_retention_days=settings.wiki_audit_retention_days,
            daily_retention_days=settings.wiki_telemetry_daily_retention_days,
            period_retention_days=settings.wiki_telemetry_period_retention_days,
        )
        prune_wiki_conversation_metrics_backfill_jobs(
            db,
            retention_days=settings.wiki_conversation_backfill_retention_days,
        )
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result
        if generator is not None:
            with suppress(StopIteration):
                next(generator)


async def _run_backfill_worker_wrapper(get_db: Callable[[], Any]) -> None:
    db, generator = await _consume_db_factory(get_db)
    try:
        process_next_wiki_conversation_metrics_backfill_job(db)
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result
        if generator is not None:
            with suppress(StopIteration):
                next(generator)


async def register_wiki_telemetry_scheduler(scheduler: AsyncIOScheduler, get_db: Callable[[], Any]) -> None:
    if not settings.wiki_telemetry_schedule_enabled:
        logger.info("Wiki telemetry scheduler disabled; skip registration")
        return

    scheduler.add_job(
        _run_job_wrapper,
        trigger=CronTrigger.from_crontab(
            settings.wiki_telemetry_schedule_cron,
            timezone=settings.wiki_telemetry_schedule_timezone,
        ),
        id="wiki_telemetry_refresh",
        replace_existing=True,
        misfire_grace_time=3600,
        kwargs={"get_db": get_db},
    )
    logger.info(
        "Wiki telemetry scheduler registered; cron=%s timezone=%s lookback_days=%s",
        settings.wiki_telemetry_schedule_cron,
        settings.wiki_telemetry_schedule_timezone,
        settings.wiki_telemetry_schedule_lookback_days,
    )
    if settings.wiki_conversation_backfill_worker_enabled:
        scheduler.add_job(
            _run_backfill_worker_wrapper,
            trigger=IntervalTrigger(seconds=max(settings.wiki_conversation_backfill_poll_seconds, 5)),
            id="wiki_conversation_backfill_worker",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            kwargs={"get_db": get_db},
        )
        logger.info(
            "Wiki conversation backfill worker registered; poll_seconds=%s",
            settings.wiki_conversation_backfill_poll_seconds,
        )
    else:
        logger.info("Wiki conversation backfill worker disabled; skip registration")
