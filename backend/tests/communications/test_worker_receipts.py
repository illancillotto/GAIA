from datetime import timedelta
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.modules.communications import models, queue, receipts
from app.modules.communications.policy import Conflict, now, sha256
from app.modules.communications.receipt_parser import parse
from app.modules.communications.transports import SafeFailure, Uncertain
from app.modules.communications.worker import Worker
from app.modules.ruolo.notice_register_models import NoticeEvidence, NoticeNotification

from .conftest import approved


def queued(api, channel="pec"):
    value = approved(api, channel)
    response = api.client.post(
        f"/communications/messages/{value['id']}/dispatch", json={"expected_version": 1}
    )
    assert response.status_code == 202
    return value, UUID(response.json()["id"])


class FakeSMTP:
    def __init__(self, error=None):
        self.error, self.sent, self.tests = error, [], []

    def send(self, account, recipient, content):
        self.sent.append((account.id, recipient, content))
        if self.error:
            raise self.error

    def test(self, account):
        self.tests.append(account.id)


class FakeIMAP:
    def __init__(self, raw=None):
        self.raw, self.tests = raw, []

    def fetch(self, account, validity, last_uid):
        if self.raw:
            yield "42", 1, self.raw

    def test(self, account):
        self.tests.append(account.id)


def run_job(api, identity, monkeypatch, smtp=None, imap=None):
    monkeypatch.setenv("COMMUNICATIONS_TRANSPORT_ENABLED", "true")
    with api.session() as db:
        job = db.get(models.CommunicationJob, identity)
        job.state, job.lease_token, job.attempts = "processing", uuid4(), job.attempts + 1
        job.lease_until = now() + timedelta(minutes=3)
        token = job.lease_token
        db.commit()
    worker = Worker(api.session, smtp=smtp or FakeSMTP(), imap=imap or FakeIMAP(), test_mode=True)
    worker.run(identity, token)
    return worker


@pytest.mark.parametrize("channel", ["pec", "email"])
def test_worker_transports_exact_snapshot_and_no_legal_notification(api, monkeypatch, channel):
    value, identity = queued(api, channel)
    smtp = FakeSMTP()
    run_job(api, identity, monkeypatch, smtp=smtp)
    raw = smtp.sent[0][2]
    mime = BytesParser(policy=policy.default).parsebytes(raw)
    payload = next(iter(mime.iter_attachments())).get_payload(decode=True)
    assert sha256(payload) == value["attachments"][0]["sha256"]
    with api.session() as db:
        message = db.get(models.CommunicationMessage, UUID(value["id"]))
        assert message.state == "submitted"
        attempt = db.scalar(select(models.CommunicationAttempt))
        assert attempt.mime_content == raw and attempt.mime_sha256 == sha256(raw)
        assert mime["Message-ID"] == message.technical_id
        assert set(db.scalars(select(NoticeNotification.state))) == {"nessuna_evidenza"}
        assert db.get(models.CommunicationJob, identity).state == "submitted"


@pytest.mark.parametrize(
    "error,state,retry",
    [
        (Uncertain(), "uncertain", False),
        (SafeFailure("temporary", retryable=True), "queued", True),
        (SafeFailure("rejected"), "failed", False),
    ],
)
def test_outcomes_have_safe_retry_semantics(api, monkeypatch, error, state, retry):
    value, identity = queued(api)
    run_job(api, identity, monkeypatch, smtp=FakeSMTP(error))
    with api.session() as db:
        assert db.get(models.CommunicationMessage, UUID(value["id"])).state == state
        job = db.get(models.CommunicationJob, identity)
        assert (job.state == "pending") is retry
        assert job.lease_token is None


def test_repeated_explicit_rejection_becomes_terminal(api, monkeypatch):
    _value, identity = queued(api)
    for _ in range(3):
        run_job(
            api, identity, monkeypatch, smtp=FakeSMTP(SafeFailure("negative_451", retryable=True))
        )
    with api.session() as db:
        assert db.get(models.CommunicationJob, identity).state == "failed"
        assert db.scalar(select(func.count()).select_from(models.CommunicationAttempt)) == 3


def test_crash_after_boundary_is_uncertain_without_resending(api, monkeypatch):
    value, identity = queued(api)
    monkeypatch.setenv("COMMUNICATIONS_TRANSPORT_ENABLED", "true")
    worker = Worker(api.session, smtp=FakeSMTP(), imap=FakeIMAP(), test_mode=True)
    with api.session() as db:
        job_id, token = queue.claim(db, api.account_ids[0])
        assert job_id == identity
        worker._prepare(db, queue.fenced_job(db, identity, token))
        job = db.get(models.CommunicationJob, identity)
        job.lease_until = now() - timedelta(seconds=1)
        db.commit()
    with api.session() as db:
        queue.recover(db, api.account_ids[0])
        db.commit()
        assert db.get(models.CommunicationJob, identity).state == "uncertain"
        assert db.get(models.CommunicationMessage, UUID(value["id"])).state == "uncertain"
        with pytest.raises(Conflict):
            queue.fenced_job(db, identity, token)
    assert worker.smtp.sent == []


def test_tick_disabled_pauses_account_and_heartbeat_independent(api, monkeypatch):
    _value, _identity = queued(api)
    smtp, imap = FakeSMTP(), FakeIMAP()
    worker = Worker(api.session, smtp=smtp, imap=imap, test_mode=True)
    monkeypatch.setenv("COMMUNICATIONS_TRANSPORT_ENABLED", "false")
    assert not worker.tick()
    with api.session() as db:
        assert queue.control(db).worker_seen_at is not None
        # Remove automatic IMAP jobs to examine dispatch pause in isolation.
        for job in db.scalars(
            select(models.CommunicationJob).where(models.CommunicationJob.kind.like("reconcile_%"))
        ):
            job.state = "done"
        for account in db.scalars(select(models.CommunicationAccount)):
            account.last_sync_at = now()
        queue.control(db).paused = True
        db.commit()
    monkeypatch.setenv("COMMUNICATIONS_TRANSPORT_ENABLED", "true")
    assert not worker.tick()
    assert not smtp.sent
    with queue.account_mutex(api.engine, api.account_ids[0], test_mode=True) as ok:
        assert ok
    with pytest.raises(Conflict):
        with queue.account_mutex(api.engine, api.account_ids[0]):
            pass


def test_connection_test_and_reconciliation_are_queued_and_archived(api, monkeypatch):
    test = api.client.post(f"/communications/accounts/{api.account_ids[0]}/test").json()
    worker = run_job(api, UUID(test["id"]), monkeypatch)
    assert len(worker.smtp.tests) == len(worker.imap.tests) == 1
    task = api.client.post(f"/communications/accounts/{api.account_ids[0]}/reconcile").json()
    run_job(
        api,
        UUID(task["id"]),
        monkeypatch,
        imap=FakeIMAP(b"Message-ID: <unknown@synthetic>\r\n\r\nUnmatched"),
    )
    with api.session() as db:
        account = db.get(models.CommunicationAccount, api.account_ids[0])
        assert account.imap_last_uid == 1 and account.imap_uidvalidity == "42"
        assert account.last_sync_at and account.last_test_at
        assert db.get(models.CommunicationJob, UUID(task["id"])).state == "done"
    assert len(api.client.get("/communications/admin/unmatched-receipts").json()) == 1


def pec_raw(
    kind="avvenuta-consegna", identifier="<original@synthetic>", recipient="recipient@example.org"
):
    message = EmailMessage()
    message.set_content("Ricevuta sintetica")
    message.add_attachment(
        f'''<postacert tipo="{kind}"><intestazione><destinatari tipo="certificato">{recipient}</destinatari></intestazione>
        <dati><msgid>{identifier.replace("<", "&lt;").replace(">", "&gt;")}</msgid><data zona="+0100"><giorno>03/11/2026</giorno><ora>12:00:00</ora></data></dati></postacert>'''.encode(),
        maintype="application",
        subtype="xml",
        filename="daticert.xml",
    )
    return message.as_bytes()


def verified(raw, channel):
    return parse(raw, channel, verifier=lambda content: content)


def test_signed_receipts_correlate_out_of_order_deduplicate_and_preserve_legal_state(
    api, monkeypatch
):
    value, identity = queued(api)
    run_job(api, identity, monkeypatch)
    with api.session() as db:
        account = db.get(models.CommunicationAccount, api.account_ids[0])
        message = db.get(models.CommunicationMessage, UUID(value["id"]))
        raw = pec_raw(identifier=message.technical_id)
        delivered = receipts.ingest(db, account, raw, parser=verified)
        assert receipts.ingest(db, account, raw, parser=verified).id == delivered.id
        for kind in ("accettazione", "errore-consegna"):
            receipts.ingest(
                db, account, pec_raw(kind, identifier=message.technical_id), parser=verified
            )
        assert message.state == "delivered"
        assert db.scalar(select(func.count()).select_from(models.CommunicationReceipt)) == 3
        db.flush()
        assert db.scalar(select(func.count()).select_from(NoticeEvidence)) == 3
        assert set(db.scalars(select(NoticeNotification.state))) == {"nessuna_evidenza"}
        db.commit()
        receipt_id = delivered.id
    originals = api.client.get(
        f"/communications/messages/{value['id']}/receipts/{receipt_id}/original"
    )
    assert originals.status_code == 200 and originals.content == raw


def test_receipt_unverified_wrong_recipient_and_unknown_id_do_not_deliver(api, monkeypatch):
    value, identity = queued(api)
    run_job(api, identity, monkeypatch)
    with api.session() as db:
        account = db.get(models.CommunicationAccount, api.account_ids[0])
        message = db.get(models.CommunicationMessage, UUID(value["id"]))
        for raw, parser in (
            (pec_raw(identifier=message.technical_id), parse),
            (pec_raw(identifier=message.technical_id, recipient="wrong@example.org"), verified),
            (pec_raw(identifier="<unknown@synthetic>"), verified),
        ):
            assert receipts.ingest(db, account, raw, parser=parser).message_id is None
        assert message.state == "submitted"


def test_dsn_bounce_and_delivery_are_not_pec(api, monkeypatch):
    value, identity = queued(api, "email")
    run_job(api, identity, monkeypatch)
    with api.session() as db:
        account = db.get(models.CommunicationAccount, api.account_ids[1])
        message = db.get(models.CommunicationMessage, UUID(value["id"]))
        for action in ("delivered", "failed"):
            raw = (
                f"Content-Type: multipart/report; boundary=dsn; report-type=delivery-status\r\n"
                f"\r\n--dsn\r\nContent-Type: message/delivery-status\r\n\r\n"
                f"Original-Message-ID: {message.technical_id}\r\n\r\n"
                f"Final-Recipient: rfc822; recipient@example.org\r\nAction: {action}\r\nStatus: 5.1.1\r\n\r\n--dsn--\r\n"
            ).encode()
            receipt = receipts.ingest(db, account, raw)
            assert receipt.message_id == message.id
            assert message.state == ("submitted" if action == "delivered" else "not_delivered")
