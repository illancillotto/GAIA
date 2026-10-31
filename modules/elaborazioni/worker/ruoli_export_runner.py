from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
from contextlib import suppress

from app.core.config import settings
from app.services.capacitas_ruoli_export import (
    GROUP_FOLDERS,
    export_is_due,
    run_group_export,
    utc_now,
)
from app.worker_health import WorkerHeartbeat, run_with_heartbeat

logger = logging.getLogger(__name__)
POLL_INTERVAL_SEC = int(os.getenv("RUOLI_EXPORT_POLL_INTERVAL_SEC", "300"))
HEALTH_SERVICE_PREFIX = "elaborazioni-worker-ruoli"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export settimanale ruoli Capacitas su Google Drive"
    )
    parser.add_argument("group", choices=sorted(GROUP_FOLDERS))
    parser.add_argument(
        "--once", action="store_true", help="esegue subito lo snapshot corrente ed esce"
    )
    return parser.parse_args(argv)


def install_signal_handlers(stop_requested: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for signame in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signame, stop_requested.set)


async def run_if_due(group: str) -> None:
    if not settings.capacitas_ruoli_export_enabled:
        return
    if not export_is_due(group, utc_now()):
        return
    try:
        await run_group_export(group)
    except Exception:
        logger.exception(
            "Export ruoli %s interrotto: nuovo tentativo al prossimo ciclo utile", group
        )


async def run(group: str) -> None:
    stop_requested = asyncio.Event()
    install_signal_handlers(stop_requested)
    logger.info(
        "Worker export ruoli %s avviato (abilitato=%s)",
        group,
        settings.capacitas_ruoli_export_enabled,
    )
    while not stop_requested.is_set():
        await run_if_due(group)
        with suppress(TimeoutError):
            await asyncio.wait_for(stop_requested.wait(), timeout=POLL_INTERVAL_SEC)


async def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.once:
        await run_group_export(args.group)
        return
    await run_with_heartbeat(
        run(args.group), WorkerHeartbeat(f"{HEALTH_SERVICE_PREFIX}-{args.group}")
    )


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("ELABORAZIONI_LOG_LEVEL", "INFO"))
    asyncio.run(main())
