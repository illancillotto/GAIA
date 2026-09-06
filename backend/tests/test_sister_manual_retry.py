"""Operator retries must not duplicate requests or reset their remote deadline."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.catasto import CatastoVisuraRequest
from app.modules.elaborazioni.sister_manual_retry import manual_retry_conflict
from app.modules.elaborazioni.sister_recovery_contract import recovery_stop_reason


def request(**overrides):
    values = dict(status="failed", row_index=2, attempts=0)
    values.update(overrides)
    return CatastoVisuraRequest(**values)


def remote_request(now, **overrides):
    values = dict(
        sister_remote_state="pending",
        sister_remote_request_id="REMOTE",
        sister_remote_request_url="https://sister/requests",
        sister_credential_id=uuid4(),
        sister_first_submitted_at=now - timedelta(hours=1),
        attempts=3,
    )
    values.update(overrides)
    return request(**values)


def test_retry_allows_unattempted_and_known_remote_without_mutating_them():
    now = datetime.now(UTC)
    remote = remote_request(now)
    first = remote.sister_first_submitted_at
    assert manual_retry_conflict([request(status="completed"), request(), remote], now) is None
    assert remote.attempts == 3
    assert remote.sister_first_submitted_at == first
    assert remote.status == "failed"


@pytest.mark.parametrize(
    "field,value",
    [
        ("execution_token", uuid4()),
        ("document_id", uuid4()),
        ("sister_remote_request_id", None),
        ("sister_credential_id", None),
        ("sister_first_submitted_at", None),
        ("sister_remote_request_url", None),
    ],
)
def test_unsafe_remote_retry_requires_review(field, value):
    now = datetime.now(UTC)
    message = manual_retry_conflict([request(), remote_request(now, **{field: value})], now)
    assert "riga 2" in message
    assert "Nessuna richiesta rimessa in coda" in message


@pytest.mark.parametrize(
    "field,value",
    [
        ("attempts", 3),
        ("sister_remote_request_id", "ORPHAN"),
        ("sister_remote_state", "deleted"),
        ("sister_remote_request_url", "https://sister"),
        ("sister_first_submitted_at", datetime(2026, 9, 5, tzinfo=UTC)),
    ],
)
def test_missing_remote_state_is_not_proof_of_no_submission(field, value):
    assert "precedente tentativo" in manual_retry_conflict(
        [request(**{field: value})], datetime.now(UTC)
    )


@pytest.mark.parametrize(
    "offset,expected",
    [
        (timedelta(hours=-24), "24 ore"),
        (timedelta(hours=-24, microseconds=1), None),
        (timedelta(seconds=1), "futura"),
    ],
)
def test_deadline_is_shared_and_never_renewed(offset, expected):
    now = datetime.now(UTC)
    item = remote_request(now, sister_first_submitted_at=(now + offset).replace(tzinfo=None))
    reason = recovery_stop_reason(item, now)
    if expected:
        assert expected in reason
        assert expected in manual_retry_conflict([item], now)
    else:
        assert reason is None
        assert manual_retry_conflict([item], now) is None
