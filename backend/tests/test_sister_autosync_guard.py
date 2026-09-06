"""Campaigns cannot erase remote evidence through a replacement request."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.catasto import (
    CatastoBatch,
    CatastoPerpetualSyncItem,
    CatastoRuoloAutoSyncConfig,
    CatastoRuoloAutoSyncItem,
    CatastoVisuraRequest,
)
from app.modules.elaborazioni.sister_autosync_guard import (
    guard_campaign_items,
    replacement_is_unsafe,
    requires_original_request,
    unsubmitted_stale_batches,
)
from app.modules.elaborazioni.sister_manual_retry import BatchConflictError
from app.services.elaborazioni_batches import RELEASE_REQUESTED_MESSAGE, RELEASE_REQUESTED_OPERATION
from app.services.elaborazioni_perpetual_sync import _reconcile_item
from app.services.elaborazioni_ruolo_autosync import _classify_request_failure


@pytest.mark.parametrize(
    "evidence",
    [
        {"sister_remote_state": "pending"},
        {"sister_remote_request_id": "REMOTE"},
        {"sister_remote_request_url": "https://sister/requests"},
        {"sister_first_submitted_at": datetime.now(UTC)},
        {"attempts": 1},
        {"execution_token": uuid4()},
        {"document_id": uuid4()},
        {"last_error_code": "sister_recovery_review_required"},
    ],
)
def test_each_evidence_prevents_replacement(evidence):
    request = CatastoVisuraRequest(status="failed", **evidence)
    assert requires_original_request(request)
    now = datetime.now(UTC)
    item = CatastoPerpetualSyncItem(status="pending", attempt_count=1, retry_after=now)
    _reconcile_item(item, request, CatastoRuoloAutoSyncConfig(), now)
    assert item.status == "failed"
    assert item.retry_after is None


@pytest.mark.parametrize("status", ["failed", "skipped"])
@pytest.mark.parametrize("hours", [1, 24, 25])
def test_original_identity_and_deadline_survive_reconciliation(status, hours):
    now = datetime.now(UTC)
    request = CatastoVisuraRequest(
        id=uuid4(),
        status=status,
        attempts=1,
        sister_remote_state="pending",
        sister_remote_request_id="REMOTE",
        sister_remote_request_url="https://sister/requests",
        sister_first_submitted_at=now - timedelta(hours=hours),
        last_error_code="sister_recovery_review_required",
        current_operation=RELEASE_REQUESTED_OPERATION,
        error_message=RELEASE_REQUESTED_MESSAGE,
    )
    item = CatastoPerpetualSyncItem(
        status="processing",
        attempt_count=1,
        linked_request_id=request.id,
        linked_batch_id=uuid4(),
    )
    original = (item.linked_request_id, item.linked_batch_id, request.sister_first_submitted_at)
    _reconcile_item(item, request, CatastoRuoloAutoSyncConfig(), now)
    assert item.status == "failed"
    assert item.attempt_count == 1
    assert original == (
        item.linked_request_id,
        item.linked_batch_id,
        request.sister_first_submitted_at,
    )


@pytest.mark.parametrize("attempts", [0, 1])
def test_unlinked_items_retain_attempt_history(attempts):
    db = MagicMock()
    item = CatastoPerpetualSyncItem(attempt_count=attempts)
    assert replacement_is_unsafe(db, item) is bool(attempts)
    db.scalar.assert_not_called()


@pytest.mark.parametrize(
    "status,attempts,unsafe",
    [
        (None, 0, True),
        ("pending", 0, True),
        ("processing", 0, True),
        ("awaiting_captcha", 0, True),
        ("completed", 1, False),
        ("not_found", 1, False),
        ("failed", 0, False),
        ("skipped", 1, True),
    ],
)
def test_queue_boundary_locks_and_reloads_linked_request(status, attempts, unsafe):
    db = MagicMock()
    db.scalar.return_value = (
        CatastoVisuraRequest(status=status, attempts=attempts) if status else None
    )
    item = CatastoPerpetualSyncItem(linked_request_id=uuid4(), attempt_count=0)
    assert replacement_is_unsafe(db, item) is unsafe
    statement = db.scalar.call_args.args[0]
    assert statement._for_update_arg is not None
    assert statement.get_execution_options()["populate_existing"] is True


@pytest.mark.parametrize(
    "kind,status",
    [(CatastoPerpetualSyncItem, "failed"), (CatastoRuoloAutoSyncItem, "blocked_runtime")],
)
def test_automatic_guard_preserves_links_and_filters_only_unsafe(kind, status):
    db = MagicMock()
    safe = kind(status="pending", attempt_count=0)
    blocked = kind(status="pending", attempt_count=1, last_error_message="original")
    assert guard_campaign_items(db, [safe, blocked]) == [safe]
    assert blocked.status == status
    assert blocked.last_error_message == "original"
    assert blocked.attempt_count == 1
    db.flush.assert_called_once()


def test_manual_preflight_is_all_or_nothing():
    db = MagicMock()
    safe = CatastoPerpetualSyncItem(status="failed", attempt_count=0)
    blocked = CatastoPerpetualSyncItem(status="failed", attempt_count=1)
    with pytest.raises(BatchConflictError, match="Nessun elemento"):
        guard_campaign_items(db, [safe, blocked], manual=True)
    assert safe.status == blocked.status == "failed"
    assert blocked.last_error_message is None
    db.flush.assert_not_called()
    assert guard_campaign_items(db, [safe], manual=True) == [safe]
    assert guard_campaign_items(db, []) == []
    guard_campaign_items(db, [blocked])
    assert "precedente richiesta" in blocked.last_error_message


@pytest.mark.parametrize("status", ["processing", "awaiting_captcha", "pending"])
def test_stale_batch_cleanup_never_detaches_remote_or_active_requests(status):
    db = MagicMock()
    unsafe = CatastoBatch(id=uuid4())
    safe = CatastoBatch(id=uuid4())
    request = CatastoVisuraRequest(status=status, attempts=0)
    if status == "pending":
        request.sister_remote_request_id = "REMOTE"
    db.scalars.return_value.all.side_effect = [[request], []]
    assert unsubmitted_stale_batches(db, [unsafe, safe]) == [(safe, [])]


def test_unattempted_release_still_requeues():
    now = datetime.now(UTC)
    request = CatastoVisuraRequest(
        status="skipped",
        attempts=0,
        current_operation=RELEASE_REQUESTED_OPERATION,
        error_message=RELEASE_REQUESTED_MESSAGE,
    )
    item = CatastoPerpetualSyncItem(status="queued", attempt_count=0, linked_request_id=uuid4())
    assert _reconcile_item(item, request, CatastoRuoloAutoSyncConfig(), now)
    assert item.status == "pending"
    assert item.linked_request_id is None
    assert item.next_due_at == now


@pytest.mark.parametrize("error,hours", [(None, 0.25), ("local_error", 6)])
def test_unattempted_failure_retains_backoff(error, hours):
    now = datetime.now(UTC)
    request = CatastoVisuraRequest(status="failed", attempts=0, last_error_code=error)
    item = CatastoPerpetualSyncItem(status="pending", attempt_count=0)
    _reconcile_item(item, request, CatastoRuoloAutoSyncConfig(), now)
    assert item.status == "pending"
    assert item.retry_after == now + timedelta(hours=hours)
    _reconcile_item(item, request, CatastoRuoloAutoSyncConfig(), now + timedelta(seconds=10))
    assert item.retry_after == now + timedelta(hours=hours)
    assert _classify_request_failure(request) == "pending"


def test_historical_attempt_limit_still_stops_local_failure():
    now = datetime.now(UTC)
    request = CatastoVisuraRequest(status="failed", attempts=0)
    item = CatastoPerpetualSyncItem(status="processing", attempt_count=3)
    _reconcile_item(item, request, CatastoRuoloAutoSyncConfig(), now)
    assert item.status == "failed"
    assert item.retry_after is None
