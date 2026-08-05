from __future__ import annotations

import logging
import os
import signal
import subprocess
import time
import uuid
from datetime import datetime

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.datetime_compat import UTC
from app.modules.presenze.services import sync_worker
from app.modules.presenze.services.sync_runtime import claim_next_pending_sync_job, launch_sync_worker_process, mark_orphaned_queue_worker_jobs


logger = logging.getLogger(__name__)
WORKER_INSTANCE_ID = uuid.uuid4().hex
_ACTIVE_PROCESSES: dict[str, subprocess.Popen] = {}


def run_once() -> bool:
    db = SessionLocal()
    try:
        mark_orphaned_queue_worker_jobs(db, worker_instance_id=WORKER_INSTANCE_ID)
        job = claim_next_pending_sync_job(db, worker_pid=os.getpid(), worker_instance_id=WORKER_INSTANCE_ID)
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


def _reap_finished_processes() -> None:
    for job_id, process in list(_ACTIVE_PROCESSES.items()):
        exit_code = process.poll()
        if exit_code is None:
            continue
        _ACTIVE_PROCESSES.pop(job_id, None)
        if exit_code == 0:
            logger.info("Presenze queue worker child finished job %s", job_id)
        else:
            logger.warning("Presenze queue worker child finished job %s with exit code %s", job_id, exit_code)


def _claim_and_launch_one() -> bool:
    db = SessionLocal()
    try:
        mark_orphaned_queue_worker_jobs(
            db,
            worker_instance_id=WORKER_INSTANCE_ID,
            active_job_ids=set(_ACTIVE_PROCESSES),
        )
        job = claim_next_pending_sync_job(db, worker_pid=os.getpid(), worker_instance_id=WORKER_INSTANCE_ID)
        if job is None:
            return False
        job_id = str(job.id)
        try:
            process = launch_sync_worker_process(job)
        except Exception as exc:
            job.status = "failed"
            job.finished_at = datetime.now(UTC)
            job.error_detail = f"Queue worker could not launch child process: {exc}"
            db.add(job)
            db.commit()
            logger.exception("Presenze queue worker could not launch child process for job %s", job_id)
            return True
        _ACTIVE_PROCESSES[job_id] = process
        logger.info(
            "Presenze queue worker launched child pid=%s for job %s; active=%d/%d",
            process.pid,
            job_id,
            len(_ACTIVE_PROCESSES),
            settings.presenze_worker_concurrency,
        )
        return True
    finally:
        db.close()


def _terminate_active_processes() -> None:
    for job_id, process in list(_ACTIVE_PROCESSES.items()):
        try:
            os.killpg(process.pid, signal.SIGTERM)
            logger.info("Presenze queue worker sent SIGTERM to child job %s pid=%s", job_id, process.pid)
        except ProcessLookupError:
            pass
        except OSError:
            logger.exception("Presenze queue worker could not terminate child job %s pid=%s", job_id, process.pid)


def _main_parallel() -> int:
    signal.signal(signal.SIGTERM, lambda signum, frame: (_terminate_active_processes(), sync_worker._handle_termination(signum, frame)))
    signal.signal(signal.SIGINT, lambda signum, frame: (_terminate_active_processes(), sync_worker._handle_termination(signum, frame)))
    logger.info(
        "Presenze queue worker supervisor started; instance=%s concurrency=%d",
        WORKER_INSTANCE_ID,
        settings.presenze_worker_concurrency,
    )

    while True:
        _reap_finished_processes()
        launched = False
        while len(_ACTIVE_PROCESSES) < settings.presenze_worker_concurrency:
            if not _claim_and_launch_one():
                break
            launched = True
        if not launched:
            time.sleep(settings.presenze_worker_poll_seconds)


def main() -> int:
    if settings.presenze_worker_concurrency > 1:
        return _main_parallel()

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
