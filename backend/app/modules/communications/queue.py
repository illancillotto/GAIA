"""PostgreSQL account mutex plus recoverable, fenced job leases."""

import contextlib
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select, text

from . import receipts, store
from .models import (
    CommunicationAccount,
    CommunicationAttempt,
    CommunicationControl,
    CommunicationJob,
)
from .policy import Conflict, now


@contextlib.contextmanager
def account_mutex(engine, identity, *, test_mode=False):
    if engine.dialect.name != "postgresql":
        if not test_mode:
            raise Conflict("Il worker richiede lock PostgreSQL")
        yield True
        return
    key = int.from_bytes(identity.bytes[:8], "big", signed=True)
    with engine.connect() as connection:
        acquired = connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": key})
        connection.commit()
        try:
            yield acquired
        finally:
            if acquired:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                connection.commit()


def control(db):
    result = db.get(CommunicationControl, 1)
    if result is None:
        raise Conflict("Migrazione Communications non inizializzata")
    return result


def recover(db, account_id):
    """Only the owner of the account mutex can recover an expired lease."""
    jobs = db.scalars(
        select(CommunicationJob)
        .where(
            CommunicationJob.account_id == account_id,
            CommunicationJob.state == "processing",
            CommunicationJob.lease_until < now(),
        )
        .with_for_update()
    )
    for job in jobs:
        message = store.message(db, job.message_id) if job.message_id else None
        if message and message.state == "sending":
            uncertain(db, job, message, "worker_interrupted")
            job.state, job.error_code = "uncertain", "worker_interrupted"
        elif message and message.state != "queued":
            job.state = "cancelled"
        else:
            job.state = "pending"
        job.lease_token, job.lease_until = None, None
        store.event(db, job.account_id, "lease_recovered", job_id=str(job.id), state=job.state)


def uncertain(db, job, message, code):
    """A persisted DATA boundary is never eligible for automatic retransmission."""
    store.transition(db, message, "uncertain", error_code=code)
    for attempt in db.scalars(
        select(CommunicationAttempt).where(
            CommunicationAttempt.job_id == job.id, CommunicationAttempt.state == "sending"
        )
    ):
        attempt.state, attempt.error_code = "uncertain", code
    receipts.register_attempt(db, message)


def claim(db, account_id):
    recover(db, account_id)
    account = db.get(CommunicationAccount, account_id)
    globally_paused = control(db).paused
    query = select(CommunicationJob).where(
        CommunicationJob.account_id == account_id,
        CommunicationJob.state == "pending",
        CommunicationJob.available_at <= now(),
    )
    if globally_paused or account.paused or not account.active:
        query = query.where(~CommunicationJob.kind.in_(("dispatch_pec", "dispatch_email")))
    job = db.scalar(
        query.order_by(CommunicationJob.created_at, CommunicationJob.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if job:
        job.state, job.lease_token = "processing", uuid4()
        job.lease_until = now() + timedelta(seconds=180)
        job.attempts += 1
    db.commit()
    return (job.id, job.lease_token) if job else None


def fenced_job(db, identity, token):
    value = db.scalar(
        select(CommunicationJob)
        .where(CommunicationJob.id == identity)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if value is None or value.state != "processing" or value.lease_token != token:
        raise Conflict("Lease job non più valida")
    return value


def heartbeat_and_schedule(db):
    settings = db.scalar(
        select(CommunicationControl).where(CommunicationControl.id == 1).with_for_update()
    )
    if settings is None:
        raise Conflict("Migrazione Communications non inizializzata")
    settings.worker_seen_at = now()
    for account in db.scalars(
        select(CommunicationAccount).where(CommunicationAccount.active.is_(True))
    ):
        active = db.scalar(
            select(CommunicationJob.id)
            .where(
                CommunicationJob.account_id == account.id,
                CommunicationJob.kind == f"reconcile_{account.channel}",
                CommunicationJob.state.in_(("pending", "processing")),
            )
            .limit(1)
        )
        recent = account.last_sync_at
        if recent and recent.tzinfo is None:
            recent = recent.replace(tzinfo=now().tzinfo)
        if not active and (not recent or now() - recent > timedelta(seconds=60)):
            db.add(
                CommunicationJob(
                    account_id=account.id,
                    kind=f"reconcile_{account.channel}",
                    idempotency_key=str(uuid4()),
                )
            )
    db.commit()
