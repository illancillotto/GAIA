from __future__ import annotations

import os
import signal
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.sync_job import SyncJob


# /.../backend/app/services/sync_runtime.py -> backend root is parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


def get_sync_job_artifact_dir(job_id: int) -> Path:
    return Path(settings.sync_live_worker_artifacts_path).expanduser() / str(job_id)


def launch_sync_worker(job: SyncJob) -> int:
    artifact_dir = get_sync_job_artifact_dir(job.id)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    log_path = artifact_dir / "worker.log"

    command = [sys.executable, "-m", "app.services.sync_worker", "--job-id", str(job.id)]
    env = os.environ.copy()
    current_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(BACKEND_ROOT) if not current_pythonpath else f"{BACKEND_ROOT}:{current_pythonpath}"

    with log_path.open("ab") as stream:
        process = subprocess.Popen(
            command,
            cwd=BACKEND_ROOT,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return process.pid


def stop_sync_worker(job: SyncJob) -> None:
    if job.worker_pid is None:
        raise RuntimeError("Sync job has no worker PID")
    try:
        os.killpg(job.worker_pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except OSError as exc:
        raise RuntimeError(f"Unable to stop worker process group {job.worker_pid}: {exc}") from exc


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def reconcile_stale_sync_jobs(db: Session) -> None:
    stale_jobs = db.execute(select(SyncJob).where(SyncJob.status.in_(("pending", "running")))).scalars().all()
    changed = False
    now = datetime.now(UTC)
    for job in stale_jobs:
        if job.status == "running" and job.worker_pid and not _pid_exists(job.worker_pid):
            job.status = "failed"
            job.finished_at = now
            job.error_detail = "Worker process not found; sync job marked stale after restart or crash"
            db.add(job)
            changed = True
            continue
        started_at = job.started_at
        if started_at and started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        if job.status == "running" and job.worker_pid is None and started_at and now - started_at > timedelta(
            minutes=settings.sync_live_pending_timeout_minutes
        ):
            job.status = "failed"
            job.finished_at = now
            job.error_detail = "Running sync job lost worker PID and exceeded stale timeout"
            db.add(job)
            changed = True
            continue
        created_at = job.created_at
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if job.status == "pending" and created_at and now - created_at > timedelta(minutes=settings.sync_live_pending_timeout_minutes):
            job.status = "failed"
            job.finished_at = now
            job.error_detail = "Pending sync job expired without worker start"
            db.add(job)
            changed = True
    if changed:
        db.commit()


def has_running_sync_job(db: Session) -> bool:
    reconcile_stale_sync_jobs(db)
    existing = db.execute(select(SyncJob.id).where(SyncJob.status.in_(("pending", "running"))).limit(1)).first()
    return existing is not None
