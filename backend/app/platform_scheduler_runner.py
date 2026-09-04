from __future__ import annotations

import asyncio
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.database import get_db
from app.modules.catasto.ade_autosync_scheduler import (
    register_catasto_ade_autosync_scheduler,
)
from app.modules.elaborazioni.autosync_scheduler import (
    register_ruolo_autosync_scheduler,
)
from app.modules.elaborazioni.bonifica_oristanese_scheduler import (
    register_bonifica_scheduler,
)
from app.modules.elaborazioni.capacitas_particelle_autosync_scheduler import (
    register_particelle_autosync_scheduler,
)
from app.modules.elaborazioni.db_backup_scheduler import (
    register_elaborazioni_db_backup_scheduler,
)
from app.modules.elaborazioni.domande_irrigue_autosync_scheduler import (
    register_domande_irrigue_autosync_scheduler,
)
from app.modules.elaborazioni.incass_autosync_scheduler import (
    register_incass_autosync_scheduler,
)
from app.modules.gis.export_scheduler import register_gis_export_scheduler
from app.modules.network.telemetry_scheduler import (
    register_network_telemetry_scheduler,
)
from app.modules.presenze.scheduler import register_presenze_scheduler
from app.modules.utenze.anpr.scheduler import register_anpr_scheduler
from app.modules.utenze.visure_scheduler import register_visure_router_scheduler
from app.modules.wiki.telemetry_scheduler import register_wiki_telemetry_scheduler
from app.worker_health import WorkerHeartbeat, run_with_heartbeat

SCHEDULER_HEARTBEAT = WorkerHeartbeat(
    "platform-scheduler",
    details={"role": "apscheduler"},
)


async def register_platform_schedulers(scheduler: AsyncIOScheduler) -> None:
    await register_catasto_ade_autosync_scheduler(scheduler, get_db)
    await register_bonifica_scheduler(scheduler, get_db)
    await register_elaborazioni_db_backup_scheduler(scheduler, get_db)
    await register_incass_autosync_scheduler(scheduler, get_db)
    await register_domande_irrigue_autosync_scheduler(scheduler, get_db)
    await register_particelle_autosync_scheduler(scheduler, get_db)
    await register_ruolo_autosync_scheduler(scheduler, get_db)
    await register_gis_export_scheduler(scheduler, get_db)
    await register_presenze_scheduler(scheduler, get_db)
    await register_network_telemetry_scheduler(scheduler, get_db)
    await register_anpr_scheduler(scheduler, get_db)
    await register_visure_router_scheduler(scheduler, get_db)
    await register_wiki_telemetry_scheduler(scheduler, get_db)


async def run_scheduler() -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    await register_platform_schedulers(scheduler)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, stop_event.set)
    loop.add_signal_handler(signal.SIGTERM, stop_event.set)

    scheduler.start()
    try:
        await run_with_heartbeat(stop_event.wait(), SCHEDULER_HEARTBEAT)
    finally:
        scheduler.shutdown(wait=True)


def main() -> None:
    asyncio.run(run_scheduler())


if __name__ == "__main__":  # pragma: no cover - container entrypoint
    main()
