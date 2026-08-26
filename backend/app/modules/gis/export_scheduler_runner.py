from __future__ import annotations

import asyncio
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.database import get_db
from app.modules.gis.export_scheduler import register_gis_export_scheduler


async def run_scheduler() -> None:
    if not settings.gis_export_scheduler_enabled:
        raise RuntimeError("GIS export scheduler runner is disabled")
    scheduler = AsyncIOScheduler(timezone=settings.gis_export_scheduler_timezone)
    await register_gis_export_scheduler(scheduler, get_db)
    scheduler.start()
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, stop_event.set)
    loop.add_signal_handler(signal.SIGTERM, stop_event.set)
    try:
        await stop_event.wait()
    finally:
        scheduler.shutdown(wait=True)


def main() -> None:
    asyncio.run(run_scheduler())


if __name__ == "__main__":  # pragma: no cover - container entrypoint
    main()
