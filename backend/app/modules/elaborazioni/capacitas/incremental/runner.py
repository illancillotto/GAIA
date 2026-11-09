"""Run with python -m app.modules.elaborazioni.capacitas.incremental.runner.

This entry point is intentionally not installed in the existing autosync process.
"""

import argparse
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.models.capacitas import CapacitasInCassSyncJob
from app.modules.elaborazioni.capacitas.apps.incass.client import InCassClient
from app.modules.elaborazioni.capacitas.apps.incass.exports import InCassExportClient
from app.modules.elaborazioni.capacitas.incremental.config import IncrementalSettings
from app.modules.elaborazioni.capacitas.incremental.cycle import execute_cycle
from app.modules.elaborazioni.capacitas.incremental.dispatch import drain
from app.modules.elaborazioni.capacitas.incremental.journal import begin_cycle, pending_changes
from app.modules.elaborazioni.capacitas.incremental.models import IncrementalCycle
from app.modules.elaborazioni.capacitas.incremental.normalize import SnapshotInvalid
from app.modules.elaborazioni.capacitas.incremental.observability import outbox_counts
from app.modules.elaborazioni.capacitas.incremental.storage import pipeline_lease
from app.services.capacitas_ruoli_export import CapacitasPortal, default_policy
from app.services.elaborazioni_capacitas_incass import (
    ACTIVE_JOB_STATUSES,
    is_incass_autosync_within_operation_window,
)
from app.services.google_drive import GoogleDriveClient, drive_credentials_from_settings
from app.worker_health import WorkerHeartbeat, run_with_heartbeat

logger = logging.getLogger(__name__)


class LazyPortal:
    """Summary-only application and already collected retries need no portal login."""

    def __init__(self, config):
        self.portal = CapacitasPortal("incass", config.credential_id)
        self.manager = None
        self.requests = 0

    async def count_request(self, request):
        self.requests += 1

    async def open(self):
        if self.manager is None:
            self.manager = await self.portal.open()
            self.manager.get_http_client().event_hooks["request"].append(self.count_request)
        return self.manager

    async def list_ricerca_years(self):
        client = InCassExportClient(await self.open(), progress_timeout_seconds=1800)
        return await client.list_ricerca_years()

    async def export_ricerca_avvisi(self, year):
        client = InCassExportClient(await self.open(), progress_timeout_seconds=1800)
        return await client.export_ricerca_avvisi(year)

    async def fetch_notice_detail(self, avviso):
        return await InCassClient(await self.open()).fetch_notice_detail(avviso)

    async def fetch_notice_partitario(self, avviso):
        return await InCassClient(await self.open()).fetch_notice_partitario(avviso)

    async def refresh_session(self):
        await self.portal.relogin()


@asynccontextmanager
async def dependencies(config):
    portal = LazyPortal(config)
    policy = default_policy()
    # Retry labels contain no subject/notice identifiers. Existing polite transport
    # provides cross-process rate limits and exponential circuit-breaker pauses.
    async with httpx.AsyncClient(timeout=300) as http:
        drive = GoogleDriveClient(drive_credentials_from_settings(), http)
        try:
            yield SimpleNamespace(
                exports=portal,
                client=portal,
                portal=portal,
                drive=drive,
                parent=settings.capacitas_ruoli_export_drive_folder_id,
                policy=policy,
            )
        finally:
            await portal.portal.close()


def should_attempt(cycle, config, now) -> bool:
    if cycle.status == "invalid" or cycle.attempts >= config.max_attempts:
        return False
    attempted = cycle.report.get("attempted_at")
    return (
        not attempted
        or now.timestamp() - datetime.fromisoformat(attempted).timestamp() >= config.retry_seconds
    )


async def tick(config, now=None, revision=0) -> dict:
    if config.mode == "off":
        return {"status": "off"}
    now = now or datetime.now(UTC)
    if not is_incass_autosync_within_operation_window(now):
        return {"status": "outside_window"}
    with pipeline_lease(engine) as acquired:
        if not acquired:
            return {"status": "busy"}
        with SessionLocal() as db:
            busy = db.scalar(
                select(CapacitasInCassSyncJob.id)
                .where(CapacitasInCassSyncJob.status.in_(tuple(ACTIVE_JOB_STATUSES)))
                .limit(1)
            )
            if busy is not None:
                return {"status": "legacy_job_busy"}
            return await process(db, config, now, revision)


async def process(db, config, now, revision) -> dict:
    require_shadow_history(db, config)
    cycle = begin_cycle(db, config, now, revision)
    attempt = cycle.status != "validated" and should_attempt(cycle, config, now)
    queued = config.mode == "active" and bool(pending_changes(db, 1))
    if not attempt and not (cycle.status == "validated" and queued):
        return {"cycle": cycle.id, "status": cycle.status}
    async with dependencies(config) as deps:
        if attempt:
            await execute_cycle(db, cycle, deps, config, now)
        completed = await drain(db, deps.client, config)
        cycle.report = {
            **cycle.report,
            "requests_since_login_this_attempt": deps.portal.requests,
            "completed_this_attempt": completed,
            "outbox": outbox_counts(db, cycle.id),
            "rows_by_year": {year: len(item["rows"]) for year, item in cycle.artifacts.items()},
            "latency_seconds": max(0, datetime.now(UTC).timestamp() - now.timestamp()),
        }
        db.commit()
    return {"cycle": cycle.id, "status": cycle.status, "report": cycle.report}


def require_shadow_history(db, config) -> None:
    if config.mode != "active":
        return
    cycles = db.scalars(
        select(IncrementalCycle)
        .where(IncrementalCycle.mode == "shadow", IncrementalCycle.status == "validated")
        .order_by(IncrementalCycle.id.desc())
        .limit(config.min_shadow_cycles)
    ).all()
    days = {cycle.id[:10] for cycle in cycles}
    if len(days) < config.min_shadow_cycles:
        raise SnapshotInvalid("insufficient_shadow_days")


async def run(config, once=False, revision=0):
    while True:
        try:
            result = await tick(config, revision=revision)
            logger.info("inCASS incremental status=%s", result["status"])
        except Exception as exc:
            # No URLs, raw rows, names or fiscal identifiers in this log.
            logger.error("inCASS incremental failure=%s fallback=legacy", type(exc).__name__)
            if once:
                raise
        if once:
            return
        await asyncio.sleep(30)


async def main(argv=None):
    parser = argparse.ArgumentParser(description="Daily incremental inCASS (default off)")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--revision", type=int, default=0)
    args = parser.parse_args(argv)
    if not 0 <= args.revision <= 9999:
        parser.error("revision must be 0..9999")
    config = IncrementalSettings()
    await run_with_heartbeat(
        run(config, args.once, args.revision), WorkerHeartbeat("incass-incremental")
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
