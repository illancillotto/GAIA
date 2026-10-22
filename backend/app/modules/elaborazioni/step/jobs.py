"""STEP sync job queue (consumed by ``modules/elaborazioni/worker/step_worker.py``).

Status lifecycle: ``pending`` -> ``processing`` -> ``succeeded`` /
``completed_with_errors`` / ``failed``; ``cancelled`` for jobs stopped before
start. A worker restart moves ``processing`` jobs back to ``pending``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.elaborazioni.step.models import StepCredential, StepSyncJob
from app.modules.elaborazioni.step.schemas import StepSyncJobCreate

TERMINAL_JOB_STATUSES = frozenset({"succeeded", "completed_with_errors", "failed", "cancelled"})
ACTIVE_JOB_STATUSES = frozenset({"pending", "processing"})
BROWSER_MODES = frozenset({"sync", "list_only", "credential_test"})


class StepJobConflict(RuntimeError):
    """Raised when a job cannot be queued or changed in its current state."""


def active_job(db: Session) -> StepSyncJob | None:
    return db.scalar(
        select(StepSyncJob)
        .where(StepSyncJob.status.in_(ACTIVE_JOB_STATUSES))
        .order_by(StepSyncJob.id)
    )


def create_job(
    db: Session, payload: StepSyncJobCreate, *, requested_by_user_id: int | None
) -> StepSyncJob:
    if payload.mode == "archive_import" and payload.archive_name is None:
        raise ValueError("archive_name obbligatorio per l'import di un archivio STEP")
    running = active_job(db)
    if running is not None:
        raise StepJobConflict(f"Job STEP {running.id} gia in coda o in esecuzione")
    job = StepSyncJob(
        credential_id=payload.credential_id if payload.mode in BROWSER_MODES else None,
        requested_by_user_id=requested_by_user_id,
        status="pending",
        mode=payload.mode,
        payload_json=payload.model_dump(mode="json"),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def create_credential_test_job(
    db: Session, credential_id: int, *, requested_by_user_id: int | None
) -> StepSyncJob | None:
    if db.get(StepCredential, credential_id) is None:
        return None
    running = active_job(db)
    if running is not None:
        raise StepJobConflict(f"Job STEP {running.id} gia in coda o in esecuzione")
    job = StepSyncJob(
        credential_id=credential_id,
        requested_by_user_id=requested_by_user_id,
        status="pending",
        mode="credential_test",
        payload_json={"credential_id": credential_id},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_jobs(db: Session, *, limit: int = 50) -> list[StepSyncJob]:
    return list(db.scalars(select(StepSyncJob).order_by(StepSyncJob.id.desc()).limit(limit)).all())


def cancel_job(db: Session, job: StepSyncJob) -> StepSyncJob:
    if job.status != "pending":
        raise StepJobConflict("Solo un job STEP in coda puo essere annullato")
    job.status = "cancelled"
    job.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(job)
    return job


def delete_job(db: Session, job: StepSyncJob) -> None:
    if job.status not in TERMINAL_JOB_STATUSES:
        raise StepJobConflict("Il job STEP puo essere eliminato solo quando e terminato")
    db.delete(job)
    db.commit()


def claim_next_job(db: Session) -> StepSyncJob | None:
    job = db.scalar(
        select(StepSyncJob)
        .where(StepSyncJob.status == "pending")
        .order_by(StepSyncJob.created_at.asc(), StepSyncJob.id.asc())
        .with_for_update(skip_locked=True)
    )
    if job is None:
        return None
    job.status = "processing"
    job.started_at = datetime.now(UTC)
    job.completed_at = None
    job.error_detail = None
    db.commit()
    return job


def recover_interrupted_jobs(db: Session) -> list[int]:
    jobs = db.scalars(select(StepSyncJob).where(StepSyncJob.status == "processing")).all()
    for job in jobs:
        job.status = "pending"
        job.started_at = None
        job.error_detail = "Recuperato dopo riavvio worker"
    db.commit()
    return [job.id for job in jobs]


def update_progress(db: Session, job_id: int, progress: dict) -> None:
    job = db.get(StepSyncJob, job_id)
    if job is None:
        return
    job.result_json = {
        **(job.result_json or {}),
        "progress": progress,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    db.commit()


def finish_job(
    db: Session, job_id: int, *, status: str, result: dict | None, error: str | None = None
) -> None:
    job = db.get(StepSyncJob, job_id)
    if job is None:
        return
    job.status = status
    job.result_json = {**(job.result_json or {}), **(result or {})}
    job.error_detail = error[:4000] if error else None
    job.completed_at = datetime.now(UTC)
    db.commit()
