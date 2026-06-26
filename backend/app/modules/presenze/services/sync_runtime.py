from __future__ import annotations

import os
import signal
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datetime_compat import UTC
from app.modules.presenze.models import PresenzeSyncJob


# sync_runtime.py may run in a detached worker process, while `python -m app...`
# needs the repository root `/app` on PYTHONPATH.
BACKEND_ROOT = Path(__file__).resolve().parents[4]


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def build_period(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date.fromordinal(date(year, month + 1, 1).toordinal() - 1)
    return start, end


def get_sync_artifact_dir(job_id: str) -> Path:
    return Path(settings.presenze_sync_artifacts_path).expanduser() / job_id


def resolve_sync_artifact_path(job_id: str, artifact_name: str) -> Path:
    artifact_dir = get_sync_artifact_dir(job_id).resolve()
    allowed = {
        "json": "presenze_collaboratori.json",
        "log": "worker.log",
        "summary": "summary.json",
        "progress": "progress.json",
        "events": "events.ndjson",
    }
    filename = allowed.get(artifact_name)
    if filename is None:
        raise ValueError(f"Unsupported artifact: {artifact_name}")
    return (artifact_dir / filename).resolve()


def delete_sync_artifact_dir(job_id: str) -> None:
    shutil.rmtree(get_sync_artifact_dir(job_id), ignore_errors=True)


def launch_sync_worker(job: PresenzeSyncJob) -> int:
    artifact_dir = get_sync_artifact_dir(str(job.id))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    log_path = artifact_dir / "worker.log"

    command = [sys.executable, "-m", "app.modules.presenze.services.sync_worker", "--job-id", str(job.id)]
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


def stop_sync_worker(job: PresenzeSyncJob) -> None:
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
    stale_jobs = db.execute(select(PresenzeSyncJob).where(PresenzeSyncJob.status.in_(("pending", "running")))).scalars().all()
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
        created_at = _as_utc(job.created_at)
        if job.status == "pending" and created_at and now - created_at > timedelta(minutes=10):
            job.status = "failed"
            job.finished_at = now
            job.error_detail = "Pending sync job expired without worker start"
            db.add(job)
            changed = True
    if changed:
        db.commit()


def has_running_sync_job(db: Session) -> bool:
    reconcile_stale_sync_jobs(db)
    existing = db.execute(select(PresenzeSyncJob.id).where(PresenzeSyncJob.status.in_(("pending", "running"))).limit(1)).first()
    return existing is not None
