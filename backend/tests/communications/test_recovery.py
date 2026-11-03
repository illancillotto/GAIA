"""Crash, revocation and lease fences never turn uncertain delivery into a retry."""

import runpy
from datetime import timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import select

from app.modules.communications import models, outbox, policy, queue, ruolo_source, worker
from app.modules.communications.receipt_parser import _recipient_report
from app.modules.ruolo.notice_register_models import NoticeDocument

from .conftest import create, pdf
from .test_worker_receipts import FakeIMAP, FakeSMTP, queued


def claim(api):
    with api.session() as db:
        return queue.claim(db, api.account_ids[0])


@pytest.mark.parametrize("fault", ["queued", "sending", "cancelled", "reconcile"])
def test_unexpected_error_recovers_the_correct_boundary(api, monkeypatch, fault):
    monkeypatch.setenv("COMMUNICATIONS_TRANSPORT_ENABLED", "true")
    if fault == "reconcile":
        identity = UUID(
            api.client.post(f"/communications/accounts/{api.account_ids[0]}/reconcile").json()["id"]
        )
    else:
        value, identity = queued(api)
    identity, token = claim(api)
    runner = worker.Worker(api.session, smtp=FakeSMTP(), imap=FakeIMAP(), test_mode=True)
    if fault == "sending":
        with api.session() as db:
            runner._prepare(db, queue.fenced_job(db, identity, token))
    elif fault == "cancelled":
        with api.session() as db:
            db.get(models.CommunicationMessage, UUID(value["id"])).state = "cancelled"
            db.commit()
    runner._unexpected(identity, token)
    with api.session() as db:
        job = db.get(models.CommunicationJob, identity)
        assert (
            job.state
            == {
                "queued": "failed",
                "sending": "uncertain",
                "cancelled": "cancelled",
                "reconcile": "pending",
            }[fault]
        )
        assert job.lease_token is None
        if fault == "sending":
            attempt = db.scalar(select(models.CommunicationAttempt))
            assert attempt.state == "uncertain" and attempt.error_code == "worker_error"
        if fault == "reconcile":
            job.state, job.lease_token, job.attempts = "processing", token, 3
            db.commit()
    if fault == "reconcile":
        runner._unexpected(identity, token)
        with api.session() as db:
            assert db.get(models.CommunicationJob, identity).state == "failed"


@pytest.mark.parametrize(
    "fault", ["not_queued", "global", "disabled", "actor", "paused", "wrong_account", "rate"]
)
def test_prepare_rechecks_authority_pause_and_rate(api, monkeypatch, fault):
    monkeypatch.setenv("COMMUNICATIONS_TRANSPORT_ENABLED", "true")
    value, identity = queued(api)
    _, token = claim(api)
    runner = worker.Worker(api.session, test_mode=True)
    with api.session() as db:
        job = queue.fenced_job(db, identity, token)
        message = db.get(models.CommunicationMessage, UUID(value["id"]))
        account = db.get(models.CommunicationAccount, job.account_id)
        if fault == "not_queued":
            message.state = "cancelled"
        elif fault == "global":
            queue.control(db).paused = True
        elif fault == "disabled":
            monkeypatch.setenv("COMMUNICATIONS_TRANSPORT_ENABLED", "false")
        elif fault == "actor":
            from app.models.application_user import ApplicationUser

            db.get(ApplicationUser, 1).is_active = False
        elif fault == "paused":
            account.paused = True
        elif fault == "wrong_account":
            job.account_id = api.account_ids[1]
        else:
            account.hourly_limit = 0  # Synthetic saturated account; API enforces a positive limit.
        db.commit()
        if fault == "rate":
            assert runner._dispatch(identity, token) is None
            db.refresh(job)
            assert job.state == "pending" and message.state == "queued"
        else:
            with pytest.raises(policy.Conflict):
                runner._prepare(db, job)


def test_tick_runs_job_and_quarantines_unexpected_transport_error(api, monkeypatch):
    monkeypatch.setenv("COMMUNICATIONS_TRANSPORT_ENABLED", "true")
    value, _ = queued(api)
    runner = worker.Worker(
        api.session, smtp=FakeSMTP(RuntimeError("private error")), imap=FakeIMAP(), test_mode=True
    )
    for _ in range(3):
        assert runner.tick()
    with api.session() as db:
        assert db.get(models.CommunicationMessage, UUID(value["id"])).state == "uncertain"
    # No dispatch retry is eligible: remaining ticks only poll receipts.
    assert not runner.tick()
    assert len(runner.smtp.sent) == 1


def test_recover_pending_cancelled_non_message_and_missing_control(api):
    _, identity = queued(api)
    _, _token = claim(api)
    with api.session() as db:
        job = db.get(models.CommunicationJob, identity)
        job.lease_until = policy.now() - timedelta(seconds=1)
        db.flush()
        queue.recover(db, job.account_id)
        assert job.state == "pending"
        job.state, job.lease_until = "processing", policy.now() - timedelta(seconds=1)
        db.get(models.CommunicationMessage, job.message_id).state = "cancelled"
        db.commit()
        queue.recover(db, job.account_id)
        assert job.state == "cancelled"
        db.delete(queue.control(db))
        db.commit()
        with pytest.raises(policy.Conflict):
            queue.control(db)
        with pytest.raises(policy.Conflict):
            queue.heartbeat_and_schedule(db)


def test_loop_handles_both_stop_signals_without_network(monkeypatch, tmp_path):
    monkeypatch.setenv("COMMUNICATIONS_HEARTBEAT_FILE", str(tmp_path / "heartbeat"))
    handlers = {}
    calls = []

    class Stop:
        stopped = False

        def is_set(self):
            return self.stopped

        def set(self):
            self.stopped = True

        def wait(self, seconds):
            calls.append(seconds)
            for handler in handlers.values():
                handler(None, None)

    monkeypatch.setattr(worker.threading, "Event", Stop)
    monkeypatch.setattr(
        worker.signal, "signal", lambda number, handler: handlers.update({number: handler})
    )
    monkeypatch.setattr(worker.Worker, "tick", lambda self: calls.append("tick"))
    worker.main()
    assert calls == ["tick", 2.0]
    calls.clear()
    # Exercise the executable module path too; no sockets and no DB operations.
    monkeypatch.setattr(worker.Worker, "tick", lambda self: None)
    monkeypatch.setattr(worker.queue, "heartbeat_and_schedule", lambda db: None)
    import app.core.database as database

    class NoDB:
        def __enter__(self):
            return SimpleNamespace(scalars=lambda query: [], get_bind=lambda: None)

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(database, "SessionLocal", NoDB)
    runpy.run_module("app.modules.communications.worker", run_name="__main__")
    assert calls == [2.0]


def test_source_render_and_draft_edges(api, monkeypatch):
    value = create(api)
    base = f"/communications/messages/{value['id']}"
    payload = {
        "expected_version": 1,
        "account_id": value["account_id"],
        "recipient": value["recipient"],
        "subject": "Updated",
        "body": "Text",
    }
    assert api.client.patch(base, json=payload).status_code == 200
    assert (
        api.client.post(
            f"{base}/attachments",
            data={"expected_version": "2"},
            files={"upload": ("appendix.pdf", pdf(), "application/pdf")},
        ).status_code
        == 201
    )
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        api.summary["reminder_enabled"] = False
        with pytest.raises(policy.Conflict):
            ruolo_source._positions(db, item)
        assert (
            ruolo_source.list_candidates(
                db, channel="email", filters={"state": "draft"}, page=1, page_size=25
            )["total"]
            == 1
        )
        message = db.get(models.CommunicationMessage, UUID(value["id"]))
        document = db.get(NoticeDocument, message.document_id)
        monkeypatch.setattr(
            ruolo_source, "inspect", lambda *args, **kwargs: (item, document, pdf(), "changed")
        )
        with pytest.raises(policy.Conflict):
            outbox.verify(db, message, 1)
    assert _recipient_report([], "") is None


def test_process_health_marker_missing_current_stale_and_cli(tmp_path, monkeypatch):
    import os
    import time

    from app.modules.communications import health

    path = tmp_path / "marker"
    monkeypatch.setenv("COMMUNICATIONS_HEARTBEAT_FILE", str(path))
    assert not health.healthy()
    health.mark()
    assert health.healthy()
    with pytest.raises(SystemExit) as result:
        runpy.run_module("app.modules.communications.health", run_name="__main__")
    assert result.value.code == 0
    os.utime(path, (time.time() - 1000, time.time() - 1000))
    assert not health.healthy()
    with pytest.raises(SystemExit) as result:
        runpy.run_module("app.modules.communications.health", run_name="__main__")
    assert result.value.code == 1


def test_preflight_failure_can_be_cancelled_and_revised_without_smtp(api, monkeypatch):
    monkeypatch.setenv("COMMUNICATIONS_TRANSPORT_ENABLED", "true")
    value, _identity = queued(api)
    with api.session() as db:
        ruolo_source.source_item(db, api.source_id).display_name = "Changed before SMTP"
        db.commit()
    runner = worker.Worker(api.session, smtp=FakeSMTP(), imap=FakeIMAP(), test_mode=True)
    assert runner._claim_and_run(api.account_ids[0])
    with api.session() as db:
        assert db.get(models.CommunicationMessage, UUID(value["id"])).state == "failed"
    response = api.client.post(
        f"/communications/messages/{value['id']}/cancel", json={"expected_version": 1}
    )
    assert response.status_code == 200 and response.json()["active_key"] is None
    assert create(api)["state"] == "draft"
    assert runner.smtp.sent == []


def test_cancel_never_releases_a_message_with_uncertain_transport_evidence(api, monkeypatch):
    from app.modules.communications.transports import Uncertain

    from .test_worker_receipts import run_job

    value, identity = queued(api)
    run_job(api, identity, monkeypatch, smtp=FakeSMTP(Uncertain()))
    assert (
        api.client.post(
            f"/communications/messages/{value['id']}/cancel", json={"expected_version": 1}
        ).status_code
        == 409
    )
    with api.session() as db:
        assert db.get(models.CommunicationMessage, UUID(value["id"])).active_key is not None
