import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
import test_worker
from sqlalchemy import select
from test_worker import _seed_batch

from app.models.catasto import CatastoCredential, CatastoVisuraRequest
from app.modules.elaborazioni.telemetry_models import SisterPortalEvent
from sister_auth_gate import SisterAuthenticationGate, authentication_reason, suspension_seconds
from sister_recovery_policy import remote_poll_delay

worker_db = test_worker.worker_db


@pytest.mark.parametrize(
    "failures,seconds", [(1, 180), (2, 180), (3, 900), (4, 1800), (5, 3600), (50, 3600)]
)
def test_bounded_suspension(failures, seconds):
    assert suspension_seconds(failures) == seconds


@pytest.mark.parametrize(
    "message,reason",
    [
        ("Utente non abilitato", "account_not_enabled"),
        ("Password cambiata", "password_changed"),
        ("Password modificata", "password_changed"),
        ("Password scaduta", "password_expired"),
        ("Credenziali SISTER rifiutate", "credentials_rejected"),
        ("Sessione occupata", "session_unavailable"),
        ("Login timeout", "authentication_failed"),
    ],
)
def test_diagnosis_does_not_infer_password_change(message, reason):
    assert authentication_reason(message) == reason


@pytest.mark.parametrize(
    "age,seconds",
    [
        (None, 300),
        (-1, 300),
        (0, 300),
        (3600, 600),
        (7200, 1200),
        (82800, 300),
        (86390, 10),
        (86400, 0),
    ],
)
def test_progressive_polling_preserves_deadline(age, seconds):
    now = datetime.now(UTC)
    request = SimpleNamespace(
        sister_first_submitted_at=None if age is None else now - timedelta(seconds=age)
    )
    assert remote_poll_delay(request, now).total_seconds() == seconds


def test_authentication_circuit_survives_restart_without_claiming(worker_db, monkeypatch):
    worker, sessions, _ = worker_db
    engine = sessions.kw["bind"]
    CatastoCredential.__table__.create(engine)
    SisterPortalEvent.__table__.create(engine)
    user_id, batch_id, request_ids = _seed_batch(sessions, request_statuses=["pending"])
    account = SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        label="Account",
        sister_username="test",
        sister_password_encrypted=b"encrypted",
    )
    with sessions() as db:
        db.add(CatastoCredential(**vars(account)))
        db.commit()
    worker.vault = SimpleNamespace(decrypt=lambda value: "secret")
    worker._set_batch_operation = Mock()
    runtime = SimpleNamespace(
        worker=worker, batch_id=batch_id, batch=SimpleNamespace(batch_kind="perpetual_sync")
    )
    browser = SimpleNamespace(
        ensure_authenticated=AsyncMock(side_effect=RuntimeError("Utente non abilitato"))
    )
    gate = SisterAuthenticationGate(runtime, sessions)
    assert not asyncio.run(gate.ready(account, browser))
    restarted = SisterAuthenticationGate(runtime, sessions)
    assert restarted.suspended(account)
    assert not asyncio.run(restarted.ready(account, browser))
    assert browser.ensure_authenticated.await_count == 1
    with sessions() as db:
        event = db.scalar(select(SisterPortalEvent))
        assert event.context_json == {"error_code": "account_not_enabled"}
        event.occurred_at = datetime.now(UTC) - timedelta(hours=2)
        event.attempt = 2
        db.commit()
    assert not asyncio.run(restarted.ready(account, browser))
    assert restarted.previous(account).cooldown_seconds == 900
    with sessions() as db:
        event = db.scalar(select(SisterPortalEvent).order_by(SisterPortalEvent.occurred_at.desc()))
        event.occurred_at = datetime.now(UTC) - timedelta(minutes=16)
        db.commit()
    browser.ensure_authenticated.side_effect = None
    worker._sister_observability = SimpleNamespace(_binding=Mock())
    assert asyncio.run(restarted.ready(account, browser))
    assert restarted.previous(account).attempt == 0
    assert not restarted.suspended(account)
    assert asyncio.run(restarted.ready(account, browser))
    with sessions() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request.status == "pending"
        assert request.attempts == 0
    runtime.batch.batch_kind = "manual_single"
    assert not restarted.suspended(account)
    assert asyncio.run(restarted.ready(account, browser))


def test_closed_gate_never_claims_request():
    import worker as module

    runtime = module._SisterBatchRuntime.__new__(module._SisterBatchRuntime)
    runtime.authentication_gate = SimpleNamespace(ready=AsyncMock(return_value=False))
    runtime.claim_coordinator = SimpleNamespace(claim_next=AsyncMock())
    assert (
        asyncio.run(runtime._process_next_request(object(), SimpleNamespace(browser=object())))
        == "stop"
    )
    runtime.claim_coordinator.claim_next.assert_not_called()


def test_suspended_runner_does_not_open_browser():
    import worker as module

    runtime = module._SisterBatchRuntime.__new__(module._SisterBatchRuntime)
    runtime.authentication_gate = SimpleNamespace(suspended=lambda _: True)
    assert (
        asyncio.run(runtime._prepare_session(object(), module._CredentialRuntimeSession()))
        == "stop"
    )


def test_probe_lock_contention_does_not_authenticate(worker_db, monkeypatch):
    from sister_auth_gate import acquire_probe_lock

    _, sessions, _ = worker_db
    runtime = SimpleNamespace(batch=SimpleNamespace(batch_kind="perpetual_sync"))
    gate = SisterAuthenticationGate(runtime, sessions)
    monkeypatch.setattr("sister_auth_gate.acquire_probe_lock", lambda *_args: False)
    assert not asyncio.run(gate.ready(SimpleNamespace(sister_username="test"), object()))
    db = Mock()
    db.get_bind.return_value.dialect.name = "postgresql"
    db.scalar.return_value = False
    assert not acquire_probe_lock(db, "test")
    assert db.scalar.call_args.args[1] == {"key": "sister-auth:test"}


def test_remote_queue_preserves_identity_and_prioritizes_deadline(worker_db):
    from sister_recovery_policy import queue_remote_poll

    worker, sessions, _ = worker_db
    _, batch_id, ids = _seed_batch(sessions, request_statuses=["pending", "pending"])
    with sessions() as db:
        request = db.get(CatastoVisuraRequest, ids[1])
        request.sister_remote_state = "pending"
        request.sister_remote_request_id = "original"
        request.sister_remote_request_url = "https://sister/requests"
        request.sister_first_submitted_at = datetime.now(UTC) - timedelta(hours=2)
        queue_remote_poll(request)
        assert request.sister_remote_request_id == "original"
        assert request.retry_not_before > datetime.now(UTC) + timedelta(minutes=19)
        request.retry_not_before = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert worker._request_repository().claim_next(batch_id).request_id == ids[1]
