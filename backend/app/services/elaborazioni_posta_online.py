from __future__ import annotations

from datetime import datetime, timezone
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.posta_online import PostaOnlineCredential, PostaOnlineRegisteredMailSyncJob
from app.modules.elaborazioni.posta_online.schemas import (
    PostaOnlineCredentialCreate,
    PostaOnlineCredentialOut,
    PostaOnlineCredentialTestJobCreateRequest,
    PostaOnlineCredentialUpdate,
    PostaOnlineRegisteredMailSyncJobCreateRequest,
    PostaOnlineRegisteredMailSyncJobOut,
)
from app.services.catasto_credentials import get_credential_fernet

logger = logging.getLogger(__name__)

TERMINAL_JOB_STATUSES = {"succeeded", "completed_with_errors", "failed", "cancelled"}
ACTIVE_JOB_STATUSES = {"pending", "queued_resume", "processing"}
_MAX_CONSECUTIVE_FAILURES = 5


def _encrypt(plaintext: str) -> str:
    return get_credential_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_posta_online_password(ciphertext: str) -> str:
    return get_credential_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def create_credential(db: Session, data: PostaOnlineCredentialCreate) -> PostaOnlineCredentialOut:
    credential = PostaOnlineCredential(
        label=data.label.strip(),
        username=data.username.strip(),
        password_encrypted=_encrypt(data.password),
        active=data.active,
        allowed_hours_start=data.allowed_hours_start,
        allowed_hours_end=data.allowed_hours_end,
        min_delay_ms=data.min_delay_ms,
        max_delay_ms=data.max_delay_ms,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return PostaOnlineCredentialOut.model_validate(credential)


def list_credentials(db: Session) -> list[PostaOnlineCredentialOut]:
    rows = db.scalars(select(PostaOnlineCredential).order_by(PostaOnlineCredential.id.asc())).all()
    return [PostaOnlineCredentialOut.model_validate(row) for row in rows]


def get_credential(db: Session, credential_id: int) -> PostaOnlineCredential | None:
    return db.get(PostaOnlineCredential, credential_id)


def update_credential(db: Session, credential_id: int, data: PostaOnlineCredentialUpdate) -> PostaOnlineCredentialOut | None:
    credential = db.get(PostaOnlineCredential, credential_id)
    if credential is None:
        return None
    if data.label is not None:
        credential.label = data.label.strip()
    if data.username is not None:
        credential.username = data.username.strip()
    if data.password is not None:
        credential.password_encrypted = _encrypt(data.password)
    if data.active is not None:
        credential.active = data.active
        if data.active:
            credential.consecutive_failures = 0
    if data.allowed_hours_start is not None:
        credential.allowed_hours_start = data.allowed_hours_start
    if data.allowed_hours_end is not None:
        credential.allowed_hours_end = data.allowed_hours_end
    if data.min_delay_ms is not None:
        credential.min_delay_ms = data.min_delay_ms
    if data.max_delay_ms is not None:
        credential.max_delay_ms = data.max_delay_ms
    if credential.max_delay_ms < credential.min_delay_ms:
        raise ValueError("max_delay_ms non puo essere minore di min_delay_ms")
    db.commit()
    db.refresh(credential)
    return PostaOnlineCredentialOut.model_validate(credential)


def delete_credential(db: Session, credential_id: int) -> bool:
    credential = db.get(PostaOnlineCredential, credential_id)
    if credential is None:
        return False
    db.delete(credential)
    db.commit()
    return True


def create_credential_test_job(
    db: Session,
    *,
    credential_id: int,
    requested_by_user_id: int | None,
    payload: PostaOnlineCredentialTestJobCreateRequest,
) -> PostaOnlineRegisteredMailSyncJob | None:
    credential = db.get(PostaOnlineCredential, credential_id)
    if credential is None:
        return None
    job = PostaOnlineRegisteredMailSyncJob(
        credential_id=credential_id,
        requested_by_user_id=requested_by_user_id,
        status="pending",
        mode="credential_test",
        payload_json={
            "credential_id": credential_id,
            "min_delay_ms": payload.min_delay_ms,
            "max_delay_ms": payload.max_delay_ms,
        },
        result_json=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _is_in_allowed_hours(credential: PostaOnlineCredential) -> bool:
    current_hour = datetime.now().hour
    start = credential.allowed_hours_start
    end = credential.allowed_hours_end
    if start <= end:
        return start <= current_hour <= end
    return current_hour >= start or current_hour <= end


def pick_credential(db: Session, credential_id: int | None = None) -> tuple[PostaOnlineCredential, str]:
    if credential_id is not None:
        credential = db.get(PostaOnlineCredential, credential_id)
        if credential is None:
            raise RuntimeError(f"Credenziale Poste Online {credential_id} non trovata")
        if not credential.active:
            raise RuntimeError(f"Credenziale Poste Online {credential_id} non attiva")
        if not _is_in_allowed_hours(credential):
            raise RuntimeError(
                f"Credenziale Poste Online {credential_id} fuori fascia oraria "
                f"({credential.allowed_hours_start}-{credential.allowed_hours_end})",
            )
    else:
        candidates = db.scalars(
            select(PostaOnlineCredential)
            .where(PostaOnlineCredential.active.is_(True))
            .order_by(PostaOnlineCredential.last_used_at.asc().nullsfirst(), PostaOnlineCredential.id.asc()),
        ).all()
        candidates = [candidate for candidate in candidates if _is_in_allowed_hours(candidate)]
        if not candidates:
            raise RuntimeError("Nessuna credenziale Poste Online disponibile nella fascia oraria corrente")
        credential = candidates[0]

    return credential, decrypt_posta_online_password(credential.password_encrypted)


def has_available_credential(db: Session, credential_id: int | None = None) -> bool:
    try:
        pick_credential(db, credential_id)
    except RuntimeError:
        return False
    return True


def mark_credential_used(db: Session, credential_id: int) -> None:
    credential = db.get(PostaOnlineCredential, credential_id)
    if credential is None:
        return
    credential.last_used_at = datetime.now(timezone.utc)
    credential.last_error = None
    credential.consecutive_failures = 0
    db.commit()


def mark_credential_error(db: Session, credential_id: int | None, error: str) -> None:
    if credential_id is None:
        return
    credential = db.get(PostaOnlineCredential, credential_id)
    if credential is None:
        return
    credential.last_error = error[:1000]
    credential.consecutive_failures += 1
    if credential.consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
        credential.active = False
        logger.warning(
            "Poste Online: credenziale id=%d disabilitata dopo %d fallimenti consecutivi",
            credential.id,
            credential.consecutive_failures,
        )
    db.commit()


def create_registered_mail_sync_job(
    db: Session,
    *,
    requested_by_user_id: int | None,
    payload: PostaOnlineRegisteredMailSyncJobCreateRequest,
) -> PostaOnlineRegisteredMailSyncJob:
    job = PostaOnlineRegisteredMailSyncJob(
        credential_id=payload.credential_id,
        requested_by_user_id=requested_by_user_id,
        status="pending",
        mode="registered_mails",
        payload_json=payload.model_dump(mode="json"),
        result_json=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def serialize_registered_mail_sync_job(job: PostaOnlineRegisteredMailSyncJob) -> PostaOnlineRegisteredMailSyncJobOut:
    return PostaOnlineRegisteredMailSyncJobOut.model_validate(job)


def list_registered_mail_sync_jobs(db: Session) -> list[PostaOnlineRegisteredMailSyncJob]:
    return list(db.scalars(select(PostaOnlineRegisteredMailSyncJob).order_by(PostaOnlineRegisteredMailSyncJob.id.desc())).all())


def get_registered_mail_sync_job(db: Session, job_id: int) -> PostaOnlineRegisteredMailSyncJob | None:
    return db.get(PostaOnlineRegisteredMailSyncJob, job_id)


def delete_registered_mail_sync_job(db: Session, job: PostaOnlineRegisteredMailSyncJob) -> None:
    db.delete(job)
    db.commit()


def expire_stale_registered_mail_sync_jobs(db: Session) -> None:
    jobs = db.scalars(
        select(PostaOnlineRegisteredMailSyncJob).where(
            PostaOnlineRegisteredMailSyncJob.status == "processing",
            PostaOnlineRegisteredMailSyncJob.completed_at.isnot(None),
        )
    ).all()
    for job in jobs:
        if job.status not in TERMINAL_JOB_STATUSES:
            job.status = "failed"
            job.error_detail = job.error_detail or "Job in stato incoerente"
    if jobs:
        db.commit()


def prepare_registered_mail_sync_jobs_for_recovery(db: Session) -> list[int]:
    jobs = db.scalars(
        select(PostaOnlineRegisteredMailSyncJob).where(
            PostaOnlineRegisteredMailSyncJob.status == "processing",
            PostaOnlineRegisteredMailSyncJob.completed_at.is_(None),
        )
    ).all()
    recovered: list[int] = []
    for job in jobs:
        job.status = "queued_resume"
        job.started_at = None
        job.error_detail = "Recuperato dopo riavvio worker"
        recovered.append(job.id)
    return recovered
