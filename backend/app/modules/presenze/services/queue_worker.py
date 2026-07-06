from __future__ import annotations

import logging
import os
import signal
import time

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.presenze.services import sync_worker
from app.modules.presenze.services.sync_runtime import claim_next_pending_sync_job


logger = logging.getLogger(__name__)


def run_once() -> bool:
    db = SessionLocal()
    try:
        job = claim_next_pending_sync_job(db, worker_pid=os.getpid())
    finally:
        db.close()

    if job is None:
        return False

    job_id = str(job.id)
    logger.info("Presenze queue worker picked job %s", job_id)
    sync_worker.CURRENT_JOB_ID = job_id
    try:
        exit_code = sync_worker.run_job_by_id(job_id)
    finally:
        sync_worker.CURRENT_JOB_ID = None

    if exit_code != 0:
        logger.warning("Presenze queue worker finished job %s with exit code %s", job_id, exit_code)
    return True


def main() -> int:
    signal.signal(signal.SIGTERM, sync_worker._handle_termination)
    signal.signal(signal.SIGINT, sync_worker._handle_termination)

    while True:
        processed = run_once()
        if not processed:
            time.sleep(settings.presenze_worker_poll_seconds)


def _entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":  # pragma: no cover
    _entrypoint()
