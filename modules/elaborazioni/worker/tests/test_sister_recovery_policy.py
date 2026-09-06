"""Clock boundaries and durable recovery with a real repository/database."""

from datetime import datetime, timedelta, timezone
import uuid

import pytest

from test_worker import CatastoVisuraRequest, _seed_batch, worker_db  # noqa: F401 - pytest fixture.

from sister_recovery_policy import record_first_submission, recovery_stop_reason
from sister_worker_types import SisterRemoteStateUpdate


@pytest.mark.parametrize("age", [None, 86400, 86401])
def test_remote_recovery_requires_known_unexpired_submission(worker_db, age):
    worker, sessions, _ = worker_db
    _, batch_id, ids = _seed_batch(sessions, request_statuses=["pending"])
    now = datetime.now(timezone.utc)
    with sessions() as db:
        request = db.get(CatastoVisuraRequest, ids[0])
        request.sister_remote_state = "pending"
        request.sister_remote_request_id = "REMOTE"
        request.sister_remote_request_url = "https://sister/requests"
        request.sister_first_submitted_at = None if age is None else now - timedelta(seconds=age)
        db.commit()
    assert worker._request_repository().claim_next(batch_id).request_id is None
    with sessions() as db:
        request = db.get(CatastoVisuraRequest, ids[0])
        assert request.last_error_code == "sister_recovery_review_required"
        assert request.status == "failed"
        assert request.sister_remote_request_id == "REMOTE"
        assert request.execution_token is None


def test_remote_polls_do_not_spend_submit_budget_and_delay_survives_restart(worker_db, tmp_path):
    worker, sessions, _ = worker_db
    _, batch_id, ids = _seed_batch(sessions, request_statuses=["pending"])
    now = datetime.now(timezone.utc)
    with sessions() as db:
        request = db.get(CatastoVisuraRequest, ids[0])
        request.attempts = 3
        request.sister_remote_state = "pending"
        request.sister_remote_request_url = "https://sister/requests"
        request.sister_first_submitted_at = now - timedelta(hours=23)
        db.commit()
    repository = worker._request_repository()
    repository.artifact_root = tmp_path
    claim = repository.claim_next(batch_id)
    assert claim.request_id == ids[0]
    prepared = repository.prepare_execution(batch_id, ids[0])
    assert prepared.request.attempts == 3
    repository.reset_for_retry(
        ids[0], "waiting", now + timedelta(minutes=5), execution_token=claim.execution_token
    )
    assert worker._request_repository().claim_next(batch_id).wait_reason == "RETRY_LATER"


def test_first_submission_is_not_renewed_by_poll_or_stale_callback(worker_db):
    worker, sessions, _ = worker_db
    _, batch_id, ids = _seed_batch(sessions, request_statuses=["pending"])
    repository = worker._request_repository()
    claim = repository.claim_next(batch_id)
    update = SisterRemoteStateUpdate(
        remote_id="REMOTE", remote_url="https://sister/requests", state="submitted"
    )
    repository.set_remote_state(ids[0], claim.execution_token, update)
    with sessions() as db:
        first = db.get(CatastoVisuraRequest, ids[0]).sister_first_submitted_at
    repository.set_remote_state(ids[0], uuid.uuid4(), update)
    repository.set_remote_state(ids[0], claim.execution_token, update)
    with sessions() as db:
        assert db.get(CatastoVisuraRequest, ids[0]).sister_first_submitted_at == first


def test_recovery_clock_boundary_missing_url_and_historical_updates():
    now = datetime.now(timezone.utc)
    request = CatastoVisuraRequest(sister_remote_state="pending", sister_first_submitted_at=now)
    assert "URL" in recovery_stop_reason(request, now)
    request.sister_remote_request_url = "https://sister/requests"
    assert (
        recovery_stop_reason(request, now + timedelta(hours=24) - timedelta(microseconds=1)) is None
    )
    assert "24 ore" in recovery_stop_reason(request, now + timedelta(hours=24))
    request.sister_first_submitted_at = None
    record_first_submission(request, "pending")
    assert request.sister_first_submitted_at is None
    request.sister_remote_state = "deleted"
    record_first_submission(request, "deleted")
    assert request.sister_first_submitted_at is None
    record_first_submission(request, "submitted")
    first = request.sister_first_submitted_at
    record_first_submission(request, "submitted")
    assert request.sister_first_submitted_at == first


def test_prepare_execution_cannot_bypass_submit_budget(worker_db):
    worker, sessions, _ = worker_db
    _, batch_id, ids = _seed_batch(sessions, request_statuses=["pending"])
    with sessions() as db:
        request = db.get(CatastoVisuraRequest, ids[0])
        request.attempts = 100
        db.commit()
    assert worker._request_repository().prepare_execution(batch_id, ids[0]) is None


def test_prepare_execution_does_not_resurrect_terminal_request(worker_db):
    worker, sessions, _ = worker_db
    _, batch_id, ids = _seed_batch(sessions, request_statuses=["completed"])
    assert worker._request_repository().prepare_execution(batch_id, ids[0]) is None


def test_exhaustion_preserves_the_underlying_failure():
    from sister_recovery_policy import allow_execution

    request = CatastoVisuraRequest(
        status="pending",
        attempts=3,
        error_message="network failed",
        last_error_code="session_recovery",
    )
    assert not allow_execution(request, datetime.now(timezone.utc), 3)
    assert "session_recovery" in request.error_message
    assert "network failed" in request.error_message
