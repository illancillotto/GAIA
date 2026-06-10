from __future__ import annotations

import argparse
from datetime import datetime
import sys

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.datetime_compat import UTC
from app.jobs.sync import run_live_sync_job
from app.models.sync_job import SyncJob
from app.services.sync_runtime import get_sync_job_artifact_dir


def _log_worker(job_id: int, message: str) -> None:
    timestamp = datetime.now(UTC).isoformat()
    print(f"[{timestamp}] [sync-job:{job_id}] {message}", flush=True)


def _run_job(db: Session, job: SyncJob) -> int:
    _log_worker(job.id, f"Worker picked up job profile={job.profile} trigger={job.trigger_type}")
    job.status = "running"
    job.started_at = datetime.now(UTC)
    db.add(job)
    db.commit()
    db.refresh(job)
    _log_worker(job.id, "Job marked as running")

    try:
        result = run_live_sync_job(
            db,
            trigger_type=job.trigger_type,
            initiated_by=f"sync-job:{job.requested_by_user_id}",
            source_label=job.source_label or f"worker:ssh:{job.profile}",
            profile=job.profile,
            progress_callback=lambda message: _log_worker(job.id, message),
        )
    except Exception as exc:
        _log_worker(job.id, f"Job failed: {exc}")
        db.refresh(job)
        job.status = "failed"
        job.finished_at = datetime.now(UTC)
        job.attempt_count = max(job.attempt_count, job.max_attempts)
        job.error_detail = str(exc)
        job.worker_pid = None
        db.add(job)
        db.commit()
        return 1

    sync_result = result.sync_result
    _log_worker(
        job.id,
        "Persisting completion "
        f"snapshot_id={sync_result.snapshot_id} users={sync_result.persisted_users} "
        f"groups={sync_result.persisted_groups} shares={sync_result.persisted_shares}",
    )
    db.refresh(job)
    job.status = "succeeded"
    job.snapshot_id = sync_result.snapshot_id
    job.persisted_users = sync_result.persisted_users
    job.persisted_groups = sync_result.persisted_groups
    job.persisted_shares = sync_result.persisted_shares
    job.persisted_permission_entries = sync_result.persisted_permission_entries
    job.persisted_effective_permissions = sync_result.persisted_effective_permissions
    job.share_acl_pairs_used = sync_result.share_acl_pairs_used
    job.attempt_count = result.attempts_used
    job.finished_at = datetime.now(UTC)
    job.error_detail = None
    job.worker_pid = None
    db.add(job)
    db.commit()
    _log_worker(job.id, "Job marked as succeeded")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GAIA NAS live sync worker")
    parser.add_argument("--job-id", type=int, required=True)
    args = parser.parse_args(argv)

    artifact_dir = get_sync_job_artifact_dir(args.job_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        job = db.get(SyncJob, args.job_id)
        if job is None:
            _log_worker(args.job_id, "Job not found")
            return 2
        return _run_job(db, job)
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
