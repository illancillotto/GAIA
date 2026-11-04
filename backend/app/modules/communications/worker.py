"""Worker orchestration. No HTTP handler imports or invokes these transports."""

import os
import signal
import threading
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import load_only

from app.models.application_user import ApplicationUser
from app.services.permission_resolver import can_access_section

from . import health, outbox, queue, receipts, registry, store
from .models import CommunicationAccount, CommunicationAttempt, CommunicationJob
from .policy import Conflict, now, sha256, transport_enabled
from .transports import IMAPAdapter, SafeFailure, SMTPAdapter, Uncertain, mime_message


def _authorize_operator(db, actor_id):
    actor = db.get(
        ApplicationUser,
        actor_id,
        options=[
            load_only(
                ApplicationUser.id,
                ApplicationUser.role,
                ApplicationUser.is_active,
                ApplicationUser.module_ruolo,
                raiseload=True,
            )
        ],
    )
    if (
        actor is None
        or not actor.is_active
        or not (actor.is_super_admin or actor.module_ruolo)
        or not can_access_section(db, actor, "ruolo.tributi.manage_status")
    ):
        raise Conflict("Operatore approvatore non più autorizzato")


class Worker:
    def __init__(self, session_factory, *, smtp=None, imap=None, test_mode=False):
        self.sessions = session_factory
        self.smtp = smtp or SMTPAdapter()
        self.imap = imap or IMAPAdapter()
        self.test_mode = test_mode

    def tick(self):
        with self.sessions() as db:
            queue.heartbeat_and_schedule(db)
            ids = list(
                db.scalars(select(CommunicationAccount.id).order_by(CommunicationAccount.id))
            )
            engine = db.get_bind()
        if not transport_enabled():
            return False
        for identity in ids:
            with queue.account_mutex(engine, identity, test_mode=self.test_mode) as acquired:
                if acquired and self._claim_and_run(identity):
                    return True
        return False

    def _claim_and_run(self, account_id):
        with self.sessions() as db:
            claimed = queue.claim(db, account_id)
        if not claimed:
            return False
        identity, token = claimed
        try:
            self.run(identity, token)
        except Exception:
            # Never persist exception text: SMTP/IMAP exceptions can include addresses or credentials.
            self._unexpected(identity, token)
        return True

    def run(self, identity, token):
        with self.sessions() as db:
            job = queue.fenced_job(db, identity, token)
            kind = job.kind
        if kind.startswith("dispatch_"):
            return self._dispatch(identity, token)
        if kind.startswith("reconcile_"):
            return self._reconcile(identity, token)
        return self._test_account(identity, token)

    def _prepare(self, db, job):
        value = store.message(db, job.message_id)
        if value.state != "queued":
            raise Conflict("Messaggio non più in coda")
        if queue.control(db).paused or not transport_enabled():
            raise Conflict("Invio sospeso globalmente")
        auth = outbox.authorization(db, value, store.attachments(db, value.id))
        _authorize_operator(db, auth.actor_id)
        account = registry.route_account(db, value.channel, auth.actor_id, value.account_id)
        if account.paused or job.account_id != value.account_id:
            raise Conflict("Account sospeso o job incoerente")
        recent = db.scalar(
            select(func.count())
            .select_from(CommunicationAttempt)
            .join(CommunicationJob, CommunicationJob.id == CommunicationAttempt.job_id)
            .where(
                CommunicationJob.account_id == account.id,
                CommunicationAttempt.created_at > now() - timedelta(hours=1),
            )
        )
        if recent >= account.hourly_limit:
            job.state, job.available_at = "pending", now() + timedelta(minutes=5)
            db.commit()
            return None
        parts = outbox.verify(db, value, auth.actor_id)
        technical_id = f"<{value.id}.{uuid4()}@{account.sender.rsplit('@', 1)[1]}>"
        content = mime_message(value, account, parts, technical_id)
        attempt = CommunicationAttempt(
            message_id=value.id,
            job_id=job.id,
            number=job.attempts,
            technical_id=technical_id,
            state="sending",
            mime_sha256=sha256(content),
            mime_content=content,
        )
        db.add(attempt)
        value.technical_id = technical_id
        store.transition(db, value, "sending")
        db.flush()
        result = (attempt.id, value.recipient, content)
        db.commit()  # Irreversible boundary persisted before any SMTP DATA.
        return result

    def _dispatch(self, identity, token):
        with self.sessions() as db:
            job = queue.fenced_job(db, identity, token)
            prepared = self._prepare(db, job)
            if prepared is None:
                return
            attempt_id, recipient, content = prepared
            account = db.get(CommunicationAccount, job.account_id)
            try:
                self.smtp.send(account, recipient, content)
            except Uncertain:
                state, code, retry = "uncertain", "smtp_outcome_unknown", False
            except SafeFailure as exc:
                state, code, retry = "failed", exc.code, exc.retryable and job.attempts < 3
            else:
                state, code, retry = "submitted", None, False
            self._finish_dispatch(db, identity, token, (attempt_id, state, code, retry))

    def _finish_dispatch(self, db, identity, token, result):
        attempt_id, state, code, retry = result
        job = queue.fenced_job(db, identity, token)
        attempt = db.get(CommunicationAttempt, attempt_id)
        value = store.message(db, job.message_id)
        attempt.state, attempt.error_code = state, code
        job.state, job.error_code = ("pending" if retry else state), code
        job.lease_until, job.lease_token = None, None
        if retry:
            job.available_at = now() + timedelta(seconds=30 * 2**job.attempts)
        store.transition(db, value, "queued" if retry else state, error_code=code)
        if state in {"submitted", "uncertain"}:
            receipts.register_attempt(db, value)
        db.commit()

    def _reconcile(self, identity, token):
        with self.sessions() as db:
            job = queue.fenced_job(db, identity, token)
            account = db.get(CommunicationAccount, job.account_id)
            for validity, uid, raw in self.imap.fetch(
                account, account.imap_uidvalidity, account.imap_last_uid
            ):
                queue.fenced_job(db, identity, token)
                receipts.ingest(db, account, raw)
                account.imap_uidvalidity, account.imap_last_uid = validity, uid
                db.commit()  # Archive/cursor move atomically. Never DELETE or mark SEEN.
                health.mark()
            job = queue.fenced_job(db, identity, token)
            account.last_sync_at, job.state = now(), "done"
            account.health = "imap_available"
            db.commit()

    def _test_account(self, identity, token):
        with self.sessions() as db:
            job = queue.fenced_job(db, identity, token)
            account = db.get(CommunicationAccount, job.account_id)
            self.smtp.test(account)
            self.imap.test(account)
            account.health, account.last_test_at, job.state = "smtp_imap_available", now(), "done"
            store.event(db, account.id, "connection_test_succeeded", job_id=str(job.id))
            db.commit()

    def _unexpected(self, identity, token):
        with self.sessions() as db:
            job = queue.fenced_job(db, identity, token)
            value = store.message(db, job.message_id) if job.message_id else None
            if value and value.state in {"queued", "sending"}:
                state = "uncertain" if value.state == "sending" else "failed"
                if state == "uncertain":
                    queue.uncertain(db, job, value, "worker_error")
                else:
                    store.transition(db, value, state, error_code="worker_error")
                job.state = state
            elif value:
                job.state = "cancelled"
            else:
                job.state = "pending" if job.attempts < 3 else "failed"
                job.available_at = now() + timedelta(seconds=30 * 2**job.attempts)
                account = db.get(CommunicationAccount, job.account_id)
                account.health = "connection_error"
            job.error_code = "worker_error"
            job.lease_token, job.lease_until = None, None
            store.event(db, job.account_id, "worker_error", job_id=str(job.id), state=job.state)
            db.commit()


def main():
    from app.core.database import SessionLocal

    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    worker = Worker(SessionLocal)
    while not stop.is_set():
        worker.tick()
        health.mark()
        stop.wait(float(os.environ.get("COMMUNICATIONS_POLL_SECONDS", "2")))


if __name__ == "__main__":
    main()
