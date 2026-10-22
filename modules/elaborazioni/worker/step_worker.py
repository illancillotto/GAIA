"""Dedicated worker process for STEP jobs (``elaborazioni-worker-step``).

Kept separate from ``worker.py``: STEP runs one job at a time, may hold a
browser for hours during a full sync and must not delay the other families.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.modules.elaborazioni.step.jobs import claim_next_job, recover_interrupted_jobs
from app.modules.elaborazioni.step.scheduler import queue_due_autosync
from app.worker_health import WorkerHeartbeat, run_with_heartbeat
from sister_worker_watchdog import run_supervised
from step_sync import run_step_job_by_id

logger = logging.getLogger(__name__)

HEALTH_SERVICE = os.getenv("GAIA_WORKER_HEALTH_SERVICE", "elaborazioni-worker-step")


class StepWorker:
    def __init__(
        self, session_factory: sessionmaker, *, headless: bool, poll_interval_sec: float
    ) -> None:
        self.session_factory = session_factory
        self.headless = headless
        self.poll_interval_sec = poll_interval_sec
        self.stop_requested = False

    def request_stop(self) -> None:
        self.stop_requested = True

    def recover(self) -> None:
        with self.session_factory() as db:
            recovered = recover_interrupted_jobs(db)
        if recovered:
            logger.info("Recuperati %d job STEP interrotti: %s", len(recovered), recovered)

    def claim(self) -> int | None:
        with self.session_factory() as db:
            job = claim_next_job(db)
            if job is None and queue_due_autosync(db) is not None:
                job = claim_next_job(db)
            return job.id if job is not None else None

    async def run_once(self) -> bool:
        job_id = self.claim()
        if job_id is None:
            return False
        logger.info("Job STEP %s prelevato dalla coda", job_id)
        await run_step_job_by_id(
            job_id=job_id, session_factory=self.session_factory, headless=self.headless
        )
        return True

    async def run(self) -> None:
        self.recover()
        logger.info("Worker STEP avviato")
        while not self.stop_requested:
            if not await self.run_once():
                await asyncio.sleep(self.poll_interval_sec)


def build_worker() -> StepWorker:
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    return StepWorker(
        sessionmaker(bind=engine, autoflush=False, autocommit=False),
        headless=os.getenv("ELABORAZIONI_HEADLESS", "true").lower() != "false",
        poll_interval_sec=float(os.getenv("ELABORAZIONI_POLL_INTERVAL_SEC", "5")),
    )


async def main() -> None:
    worker = build_worker()
    loop = asyncio.get_running_loop()
    for signame in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signame, worker.request_stop)
    await run_with_heartbeat(
        worker.run(), WorkerHeartbeat(HEALTH_SERVICE, details={"families": ["step"]})
    )


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("ELABORAZIONI_LOG_LEVEL", "INFO").upper())
    run_supervised(main, WorkerHeartbeat(HEALTH_SERVICE).path)
