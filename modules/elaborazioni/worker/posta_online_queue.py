"""Claim or recover a Poste job only while owning its portal/account lease."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select

from app.models.posta_online import PostaOnlineCredential, PostaOnlineRegisteredMailSyncJob
from app.services.elaborazioni_posta_online import (
    expire_stale_registered_mail_sync_jobs,
    has_available_credential,
)
from posta_online_dispatch_runner import HANDLERS
from posta_online_leases import PortalLease, acquire_portal_lease

_CLAIMABLE = ("pending", "queued_resume", "processing")
_WAITING = "In attesa di una credenziale Poste Online disponibile"


@dataclass
class ClaimedJob:
    id: int
    lease: PortalLease


class PosteQueue:
    def __init__(self, session_factory, retry_ready, credential_id) -> None:
        self.session_factory = session_factory
        self.retry_ready = retry_ready
        self.credential_id = credential_id

    def _account(self, db, job) -> tuple[bool, str | None]:
        if job.mode in HANDLERS and job.credential_id is None:
            return False, None
        if job.mode != "credential_test" and not has_available_credential(
            db, self.credential_id(job)
        ):
            return False, None
        if job.mode not in HANDLERS:
            return True, None
        credential = db.get(PostaOnlineCredential, job.credential_id)
        if credential is None or not credential.username.strip():
            return False, None
        return True, credential.username

    def _claim(self, db, identity: int, expected: tuple) -> int | None:
        job = db.scalar(
            select(PostaOnlineRegisteredMailSyncJob)
            .where(
                PostaOnlineRegisteredMailSyncJob.id == identity,
                PostaOnlineRegisteredMailSyncJob.status.in_(_CLAIMABLE),
                PostaOnlineRegisteredMailSyncJob.completed_at.is_(None),
            )
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        if job is None or (job.mode, job.credential_id) != expected or not self.retry_ready(job):
            return None
        job.status = "processing"
        job.started_at = datetime.now(UTC)
        job.error_detail = None
        db.commit()
        return job.id

    def _lease_and_claim(self, db, job, username) -> ClaimedJob | None:
        expected = (job.mode, job.credential_id)
        lease = acquire_portal_lease(db.get_bind(), username)
        if lease is None:
            return None
        try:
            identity = self._claim(db, job.id, expected)
            if identity is not None:
                return ClaimedJob(identity, lease)
        except BaseException:
            lease.close()
            raise
        lease.close()
        return None

    def claim(self) -> ClaimedJob | None:
        with self.session_factory() as db:
            expire_stale_registered_mail_sync_jobs(db)
            jobs = db.scalars(
                select(PostaOnlineRegisteredMailSyncJob)
                .where(
                    PostaOnlineRegisteredMailSyncJob.status.in_(_CLAIMABLE),
                    PostaOnlineRegisteredMailSyncJob.completed_at.is_(None),
                )
                .order_by(
                    PostaOnlineRegisteredMailSyncJob.created_at.asc(),
                    PostaOnlineRegisteredMailSyncJob.id.asc(),
                )
            ).all()
            for job in filter(self.retry_ready, jobs):
                ready, username = self._account(db, job)
                if not ready:
                    job.error_detail = _WAITING
                    db.commit()
                    continue
                claimed = self._lease_and_claim(db, job, username)
                if claimed is not None:
                    return claimed
        return None

    def fail(self, identity: int, error: str) -> None:
        with self.session_factory() as db:
            job = db.get(PostaOnlineRegisteredMailSyncJob, identity)
            if job is not None and job.status == "processing":
                job.status = "failed"
                job.error_detail = error
                job.completed_at = datetime.now(UTC)
                db.commit()
