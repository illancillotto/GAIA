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
PENDING_WITHOUT_WORKER_STALE_AFTER = timedelta(minutes=5)


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


def prepare_sync_job_artifacts(job: PresenzeSyncJob, *, artifact_filename: str = "presenze_collaboratori.json") -> Path:
    artifact_dir = get_sync_artifact_dir(str(job.id))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    job.worker_log_path = str(artifact_dir / "worker.log")
    job.json_artifact_path = str(artifact_dir / artifact_filename)
    return artifact_dir


def resolve_sync_artifact_path(job_id: str, artifact_name: str) -> Path:
    artifact_dir = get_sync_artifact_dir(job_id).resolve()
    allowed = {
        "json": "presenze_collaboratori.json",
        "log": "worker.log",
        "summary": "summary.json",
        "progress": "progress.json",
        "events": "events.ndjson",
        "xlsm": "giornaliere_export.xlsm",
        "xlsx": "straordinari.xlsx",
    }
    filename = allowed.get(artifact_name)
    if filename is None:
        raise ValueError(f"Unsupported artifact: {artifact_name}")
    return (artifact_dir / filename).resolve()


def delete_sync_artifact_dir(job_id: str) -> None:
    shutil.rmtree(get_sync_artifact_dir(job_id), ignore_errors=True)


def _is_sync_job(job: PresenzeSyncJob) -> bool:
    mode = (job.params_json or {}).get("mode")
    return mode in (None, "sync")


def apply_sync_job_retention(db: Session, *, keep_count: int | None = None) -> int:
    retention_count = settings.presenze_sync_retention_count if keep_count is None else keep_count
    if retention_count <= 0:
        return 0

    terminal_jobs = db.execute(
        select(PresenzeSyncJob)
        .where(PresenzeSyncJob.status.in_(("completed", "failed", "cancelled")))
        .order_by(PresenzeSyncJob.created_at.desc(), PresenzeSyncJob.id.desc())
    ).scalars().all()
    sync_terminal_jobs = [job for job in terminal_jobs if _is_sync_job(job)]
    jobs_to_delete = sync_terminal_jobs[retention_count:]

    for job in jobs_to_delete:
        delete_sync_artifact_dir(str(job.id))
        db.delete(job)

    if jobs_to_delete:
        db.commit()
    return len(jobs_to_delete)


def claim_next_pending_sync_job(db: Session, *, worker_pid: int) -> PresenzeSyncJob | None:
    job = db.execute(
        select(PresenzeSyncJob)
        .where(PresenzeSyncJob.status == "pending", PresenzeSyncJob.credential_id.is_not(None))
        .order_by(PresenzeSyncJob.created_at.asc())
        .limit(1)
    ).scalar_one_or_none()
    if job is None:
        return None

    prepare_sync_job_artifacts(job)
    job.status = "running"
    job.started_at = datetime.now(UTC)
    job.finished_at = None
    job.error_detail = None
    job.worker_pid = worker_pid
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def launch_sync_worker(job: PresenzeSyncJob) -> int:
    artifact_dir = prepare_sync_job_artifacts(job)
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


def launch_xlsm_export_worker(job: PresenzeSyncJob) -> int:
    artifact_dir = prepare_sync_job_artifacts(job, artifact_filename="giornaliere_export.xlsm")
    log_path = artifact_dir / "worker.log"

    command = [sys.executable, "-m", "app.modules.presenze.services.xlsm_export_worker", "--job-id", str(job.id)]
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


def launch_straordinari_export_worker(job: PresenzeSyncJob) -> int:
    artifact_dir = prepare_sync_job_artifacts(job, artifact_filename="straordinari.xlsx")
    log_path = artifact_dir / "worker.log"

    command = [sys.executable, "-m", "app.modules.presenze.services.straordinari_export_worker", "--job-id", str(job.id)]
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
        created_at = _as_utc(job.created_at)
        if (
            job.status == "pending"
            and job.worker_pid is None
            and created_at is not None
            and now - created_at > PENDING_WITHOUT_WORKER_STALE_AFTER
        ):
            job.status = "failed"
            job.finished_at = now
            job.error_detail = "Pending sync job had no worker assigned; marked stale after queue timeout"
            db.add(job)
            changed = True
            continue
        if job.status == "running" and job.worker_pid and not _pid_exists(job.worker_pid):
            job.status = "failed"
            job.finished_at = now
            job.error_detail = "Worker process not found; sync job marked stale after restart or crash"
            db.add(job)
            changed = True
            continue
        if job.status == "pending" and job.worker_pid and not _pid_exists(job.worker_pid):
            job.status = "failed"
            job.finished_at = now
            job.error_detail = "Worker process not found; pending sync job marked stale after failed start or crash"
            db.add(job)
            changed = True
            continue
    if changed:
        db.commit()


def has_running_sync_job(db: Session) -> bool:
    reconcile_stale_sync_jobs(db)
    existing = db.execute(select(PresenzeSyncJob.id).where(PresenzeSyncJob.status.in_(("pending", "running"))).limit(1)).first()
    return existing is not None
