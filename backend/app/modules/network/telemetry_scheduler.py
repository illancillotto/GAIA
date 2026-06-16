from __future__ import annotations

import inspect
import logging
from collections.abc import Generator
from contextlib import suppress
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.database import engine
from app.modules.network.telemetry_rollups import prune_network_firewall_events, refresh_network_firewall_hourly_rollups

logger = logging.getLogger(__name__)
NETWORK_TELEMETRY_ROLLUP_LOCK_KEY = 2200615


async def _consume_db_factory(get_db: Callable[[], Any]) -> tuple[Any, Generator | None]:
    resource = get_db()
    if inspect.isgenerator(resource):
        db = next(resource)
        return db, resource
    return resource, None


async def _run_job_wrapper(get_db: Callable[[], Any]) -> None:
    db, generator = await _consume_db_factory(get_db)
    lock_connection = None
    try:
        lock_acquired = True
        if engine.dialect.name == "postgresql":
            lock_connection = engine.raw_connection()
            cursor = lock_connection.cursor()
            try:
                cursor.execute("SELECT pg_try_advisory_lock(%s)", (NETWORK_TELEMETRY_ROLLUP_LOCK_KEY,))
                lock_acquired = bool(cursor.fetchone()[0])
            finally:
                cursor.close()
        if not lock_acquired:
            logger.info("Network telemetry rollup job skipped because another worker already holds the execution lock")
            return

        refresh_network_firewall_hourly_rollups(
            db,
            lookback_hours=settings.network_telemetry_rollup_lookback_hours,
        )
        prune_network_firewall_events(
            db,
            retention_days=settings.network_firewall_raw_retention_days,
        )
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result
        if lock_connection is not None:
            with suppress(Exception):
                cursor = lock_connection.cursor()
                try:
                    cursor.execute("SELECT pg_advisory_unlock(%s)", (NETWORK_TELEMETRY_ROLLUP_LOCK_KEY,))
                finally:
                    cursor.close()
            with suppress(Exception):
                lock_connection.close()
        if generator is not None:
            with suppress(StopIteration):
                next(generator)


async def register_network_telemetry_scheduler(scheduler: AsyncIOScheduler, get_db: Callable[[], Any]) -> None:
    if not settings.network_telemetry_rollup_enabled:
        logger.info("Network telemetry rollup scheduler disabled; skip registration")
        return

    scheduler.add_job(
        _run_job_wrapper,
        trigger=CronTrigger.from_crontab(
            settings.network_telemetry_rollup_cron,
            timezone=settings.network_telemetry_rollup_timezone,
        ),
        id="network_telemetry_rollup_refresh",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
        kwargs={"get_db": get_db},
    )
    logger.info(
        "Network telemetry rollup scheduler registered; cron=%s timezone=%s lookback_hours=%s retention_days=%s",
        settings.network_telemetry_rollup_cron,
        settings.network_telemetry_rollup_timezone,
        settings.network_telemetry_rollup_lookback_hours,
        settings.network_firewall_raw_retention_days,
    )
