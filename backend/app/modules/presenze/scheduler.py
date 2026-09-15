from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.modules.presenze.services.auto_sync import trigger_auto_sync_job
from app.modules.presenze.services.punch_reminder_dispatch import ROME
from app.modules.presenze.services.punch_reminder_job import (
    build_dispatch_options_from_settings,
    run_punch_reminder_job,
)
from app.modules.presenze.services.whatsapp_config import (
    WhatsAppRuntimeConfig,
    load_whatsapp_config,
)
from app.modules.presenze.services.whatsapp_waha import build_whatsapp_sender

logger = logging.getLogger(__name__)


def _run_job_wrapper(get_db: Callable[[], Any]) -> None:
    _run_with_db(get_db, trigger_auto_sync_job, "Presenze automatic sync scheduler job failed")


def _run_punch_reminder_wrapper(get_db: Callable[[], Any]) -> None:
    _run_with_db(get_db, _run_punch_reminder_job, "Presenze WhatsApp punch reminder job failed")


def _run_punch_reminder_job(db: Any) -> None:
    config = load_whatsapp_config(db)
    if not config.provider or not _reminder_is_due(config):
        return
    sender = build_whatsapp_sender(config)
    if sender is not None:
        run_punch_reminder_job(db, sender, build_dispatch_options_from_settings(config), config)


def _reminder_is_due(config: WhatsAppRuntimeConfig, now: datetime | None = None) -> bool:
    current = (now or datetime.now(UTC)).astimezone(ROME).replace(second=0, microsecond=0)
    trigger = CronTrigger.from_crontab(config.reminder_cron, timezone=ROME)
    return trigger.get_next_fire_time(None, current - timedelta(microseconds=1)) == current


def _run_with_db(
    get_db: Callable[[], Any], job: Callable[[Any], Any], failure_message: str
) -> None:
    db, generator = get_db(), None
    if hasattr(db, "__next__"):
        generator = db
        db = next(generator)

    try:
        job(db)
    except Exception:
        logger.exception(failure_message)
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
        trigger=CronTrigger.from_crontab(settings.presenze_auto_sync_cron, timezone=settings.presenze_auto_sync_timezone),
        id="presenze_auto_sync",
        replace_existing=True,
        misfire_grace_time=3600,
        kwargs={"get_db": get_db},
    )
    logger.info(
        "Presenze automatic sync registered; cron=%s timezone=%s",
        settings.presenze_auto_sync_cron,
        settings.presenze_auto_sync_timezone,
    )


def register_punch_reminder_scheduler(
    scheduler: AsyncIOScheduler, get_db: Callable[[], Any]
) -> None:
    scheduler.add_job(
        _run_punch_reminder_wrapper,
        trigger=CronTrigger.from_crontab("* * * * *", timezone=ROME),
        id="presenze_whatsapp_punch_reminders",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
        kwargs={"get_db": get_db},
    )
    logger.info(
        "Presenze WhatsApp dynamic schedule watcher registered",
    )


async def register_presenze_scheduler(
    scheduler: AsyncIOScheduler, get_db: Callable[[], Any]
) -> None:
    await register_inaz_scheduler(scheduler, get_db)
    register_punch_reminder_scheduler(scheduler, get_db)
