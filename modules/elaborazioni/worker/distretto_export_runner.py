from __future__ import annotations

import asyncio
import logging
import os
import signal
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.catasto import CatastoDistrettoExportJob, CatastoElaborazioniMassiveJobStatus
from app.modules.catasto.routes.anagrafica import (
    prepare_distretto_export_jobs_for_recovery,
    run_distretto_export_job_by_id,
)
from app.worker_health import WorkerHeartbeat, run_with_heartbeat

logger = logging.getLogger(__name__)
POLL_INTERVAL_SEC = int(os.getenv("ELABORAZIONI_POLL_INTERVAL_SEC", "3"))
HEALTH_SERVICE = "elaborazioni-worker-exports"


def recover_exports() -> None:
    with SessionLocal() as db:
        recovered = prepare_distretto_export_jobs_for_recovery(db)
        db.commit()
    if recovered:
        logger.info("Recuperati %d job export distretto catasto", recovered)


def claim_next_export() -> UUID | None:
    with SessionLocal() as db:
        job = db.scalar(
            select(CatastoDistrettoExportJob)
            .where(
                CatastoDistrettoExportJob.status
                == CatastoElaborazioniMassiveJobStatus.PENDING.value
            )
            .order_by(CatastoDistrettoExportJob.created_at.asc())
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return None
        job.status = CatastoElaborazioniMassiveJobStatus.PROCESSING.value
        job.started_at = datetime.now(UTC)
        job.error_message = None
        db.commit()
        return job.id


def mark_failed_export(job_id: UUID, error: Exception) -> None:
    with SessionLocal() as db:
        job = db.get(CatastoDistrettoExportJob, job_id)
        if job is None or job.status != CatastoElaborazioniMassiveJobStatus.PROCESSING.value:
            return
        job.status = CatastoElaborazioniMassiveJobStatus.FAILED.value
        job.error_message = str(error)
        job.current_label = "Export fallito."
        job.completed_at = datetime.now(UTC)
        db.commit()


def install_signal_handlers(stop_requested: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for signame in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signame, stop_requested.set)


async def run() -> None:
    stop_requested = asyncio.Event()
    install_signal_handlers(stop_requested)
    recover_exports()
    logger.info("Worker export distretto catasto avviato")

    while not stop_requested.is_set():
        job_id = claim_next_export()
        if job_id is not None:
            try:
                await asyncio.to_thread(run_distretto_export_job_by_id, job_id)
            except Exception as exc:
                logger.exception("Job export distretto catasto %s fallito", job_id)
                mark_failed_export(job_id, exc)
            continue
        await asyncio.sleep(POLL_INTERVAL_SEC)


async def main() -> None:
    await run_with_heartbeat(run(), WorkerHeartbeat(HEALTH_SERVICE))


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("ELABORAZIONI_LOG_LEVEL", "INFO"))
    asyncio.run(main())
