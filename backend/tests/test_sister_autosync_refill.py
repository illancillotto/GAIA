from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.models.catasto import (
    CatastoBatch,
    CatastoPerpetualSyncItem,
    CatastoRuoloAutoSyncConfig,
    CatastoVisuraRequest,
)
from app.modules.elaborazioni.sister_autosync_refill import (
    _is_deferred_recovery,
    append_validated_requests,
    lock_refill_capacity,
)
from app.services import elaborazioni_perpetual_sync as sync


def remote(now, **changes):
    values = dict(
        status="pending",
        execution_token=None,
        sister_remote_state="pending",
        sister_remote_request_id="REMOTE",
        sister_remote_request_url="https://sister/requests",
        sister_credential_id=uuid4(),
        sister_first_submitted_at=now - timedelta(minutes=5),
        retry_not_before=now + timedelta(minutes=5),
    )
    values.update(changes)
    return CatastoVisuraRequest(**values)


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "processing"},
        {"execution_token": uuid4()},
        {"sister_remote_state": "unknown"},
        {"sister_remote_request_id": None},
        {"sister_remote_request_url": None},
        {"sister_credential_id": None},
        {"sister_first_submitted_at": None},
        {"retry_not_before": None},
    ],
)
def test_missing_remote_evidence_or_claim_is_not_spare_capacity(changes):
    now = datetime.now(UTC)
    assert not _is_deferred_recovery(remote(now, **changes), now)


def test_recovery_deadline_and_due_polls_take_precedence():
    now = datetime.now(UTC)
    assert _is_deferred_recovery(remote(now), now)
    assert _is_deferred_recovery(remote(now.replace(tzinfo=None)), now)
    assert _is_deferred_recovery(remote(now.astimezone(timezone(timedelta(hours=2)))), now)
    for changes in [
        {"sister_first_submitted_at": now - timedelta(hours=24)},
        {"sister_first_submitted_at": now + timedelta(seconds=1)},
        {"retry_not_before": now},
    ]:
        assert not _is_deferred_recovery(remote(now, **changes), now)


@pytest.mark.parametrize(
    "status,completed", [("pending", None), ("completed", None), ("processing", datetime.now(UTC))]
)
def test_batch_must_be_live_processing(status, completed):
    assert (
        lock_refill_capacity(
            MagicMock(),
            SimpleNamespace(status=status, completed_at=completed),
            20,
            datetime.now(UTC),
        )
        == 0
    )


def test_capacity_is_fail_closed_for_locked_rows_and_bounded():
    now = datetime.now(UTC)
    batch = SimpleNamespace(id=uuid4(), status="processing", completed_at=None)
    db = MagicMock()
    db.scalar.return_value = 2
    db.scalars.return_value = [remote(now)]
    assert lock_refill_capacity(db, batch, 20, now) == 0
    db.scalars.return_value = []
    assert lock_refill_capacity(db, batch, 20, now) == 0
    db.scalar.return_value = 1
    db.scalars.return_value = [remote(now, status="processing")]
    assert lock_refill_capacity(db, batch, 20, now) == 0
    db.scalars.return_value = [remote(now)]
    assert lock_refill_capacity(db, batch, 1000, now) == 99
    assert lock_refill_capacity(db, batch, 0, now) == 0


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for model in (
            CatastoBatch,
            CatastoVisuraRequest,
            CatastoPerpetualSyncItem,
            CatastoRuoloAutoSyncConfig,
        ):
            connection.execute(CreateTable(model.__table__, include_foreign_key_constraints=[]))
    with Session(engine) as session:
        yield session
    engine.dispose()


def item(now, index):
    return CatastoPerpetualSyncItem(
        user_id=1,
        scope="ruolo_particella",
        target_key=str(index),
        priority=10,
        search_mode="immobile",
        comune="Comune",
        comune_codice="C",
        foglio="1",
        particella=str(index),
        catasto="Terreni",
        status="pending",
        next_due_at=now,
    )


def test_refill_keeps_one_batch_original_identity_and_finite_capacity(db):
    now = datetime.now(UTC)
    config = CatastoRuoloAutoSyncConfig(user_id=1, enabled=True, batch_size=3)
    batch = CatastoBatch(
        user_id=1, name="Campaign", batch_kind="perpetual_sync", status="processing", total_items=2
    )
    db.add_all([config, batch])
    db.flush()
    original = remote(now)
    original.batch_id, original.user_id, original.row_index = batch.id, 1, 2
    completed = CatastoVisuraRequest(batch_id=batch.id, user_id=1, row_index=1, status="completed")
    pending = [item(now, i) for i in range(3)]
    db.add_all([original, completed, *pending])
    db.commit()
    identity = (
        original.id,
        original.sister_remote_request_id,
        original.sister_credential_id,
        original.sister_first_submitted_at,
    )
    assert sync.ensure_perpetual_sync_batch(db, config).id == batch.id
    rows = list(db.scalars(select(CatastoVisuraRequest).order_by(CatastoVisuraRequest.row_index)))
    assert len(rows) == 4
    assert [r.row_index for r in rows] == [1, 2, 3, 4]
    assert batch.total_items == 4
    assert (
        original.id,
        original.sister_remote_request_id,
        original.sister_credential_id,
        original.sister_first_submitted_at,
    ) == identity
    assert len(list(db.scalars(select(CatastoBatch)))) == 1
    assert [r.status for r in rows[2:]] == ["pending", "pending"]
    assert sum(p.status == "queued" for p in pending) == 2
    assert sync.ensure_perpetual_sync_batch(db, config) is None
    assert len(list(db.scalars(select(CatastoVisuraRequest)))) == 4


def test_refill_empty_scope_and_missing_batch_are_noops(db):
    config = CatastoRuoloAutoSyncConfig(user_id=1, enabled=True, batch_size=3)
    assert sync._refill_deferred_batch(db, config) is None
    batch = CatastoBatch(
        user_id=1, name="Campaign", batch_kind="perpetual_sync", status="processing", total_items=1
    )
    db.add(batch)
    db.flush()
    request = remote(datetime.now(UTC))
    request.batch_id, request.user_id, request.row_index = batch.id, 1, 1
    db.add(request)
    db.commit()
    assert sync._refill_deferred_batch(db, config) is None


def test_append_starts_indices_at_one_for_empty_batch(db):
    batch = CatastoBatch(user_id=1, name="Campaign", status="processing", total_items=0)
    db.add(batch)
    db.flush()
    rows = append_validated_requests(
        db, batch, [sync._validated_row(99, item(datetime.now(UTC), 1))]
    )
    assert rows[0].row_index == 1
    assert batch.total_items == 1


def test_refill_does_not_append_unavailable_or_disabled_work(db):
    now = datetime.now(UTC)
    config = CatastoRuoloAutoSyncConfig(user_id=1, enabled=False, batch_size=3)
    batch = CatastoBatch(
        user_id=1, name="Campaign", batch_kind="perpetual_sync", status="processing", total_items=1
    )
    db.add_all([config, batch])
    db.flush()
    request = remote(now)
    request.batch_id, request.user_id, request.row_index = batch.id, 1, 1
    candidate = item(now + timedelta(days=1), 1)
    db.add_all([request, candidate])
    db.commit()
    assert sync.ensure_perpetual_sync_batch(db, config) is None
    config.enabled = True
    db.commit()
    assert sync.ensure_perpetual_sync_batch(db, config) is None
    assert len(list(db.scalars(select(CatastoVisuraRequest)))) == 1


def test_legacy_retry_backoff_and_release_without_remote_evidence():
    now = datetime.now(UTC)
    config = CatastoRuoloAutoSyncConfig()
    for attempts, code, hours in [(0, None, 0.25), (2, None, 0.5), (1, "local", 6)]:
        candidate = CatastoPerpetualSyncItem(status="queued", attempt_count=attempts)
        request = CatastoVisuraRequest(status="failed", attempts=0, last_error_code=code)
        sync._retry_item(candidate, request, now)
        assert candidate.status == "pending"
        assert candidate.retry_after == now + timedelta(hours=hours)
        retry_at = candidate.retry_after
        sync._retry_item(candidate, request, now + timedelta(seconds=10))
        assert candidate.retry_after == retry_at
    candidate = CatastoPerpetualSyncItem(status="queued", attempt_count=3)
    sync._retry_item(candidate, CatastoVisuraRequest(status="failed", attempts=0), now)
    assert candidate.status == "failed"
    from app.services.elaborazioni_batches import (
        RELEASE_REQUESTED_MESSAGE,
        RELEASE_REQUESTED_OPERATION,
    )

    candidate = CatastoPerpetualSyncItem(
        status="queued", attempt_count=0, linked_request_id=uuid4(), linked_batch_id=uuid4()
    )
    request = CatastoVisuraRequest(
        status="skipped",
        attempts=0,
        error_message=RELEASE_REQUESTED_MESSAGE,
        current_operation=RELEASE_REQUESTED_OPERATION,
    )
    assert sync._reconcile_item(candidate, request, config, now)
    assert candidate.status == "pending"
    assert candidate.linked_request_id is None


def test_credential_profiles_and_schedule_fallbacks():
    credential = SimpleNamespace(id=uuid4(), schedule_enabled=False, availability_schedule=None)
    config = CatastoRuoloAutoSyncConfig(credential_profiles={str(credential.id): {"enabled": True}})
    assert sync._configured_credential_ids(config) == {credential.id}
    assert sync._autosync_schedule(config, credential) == (False, None)
    config.credential_profiles = {}
    assert sync._autosync_schedule(config, credential) == (True, None)


def test_manual_retry_empty_and_safe_manifest(db):
    now = datetime.now(UTC)
    assert sync.retry_perpetual_sync_failures(db, 1, "ruolo_particella") == 0
    candidate = item(now, 1)
    candidate.status = "failed"
    candidate.attempt_count = 0
    db.add(candidate)
    db.commit()
    assert sync.retry_perpetual_sync_failures(db, 1, "ruolo_particella") == 1
    assert candidate.status == "pending"
    assert candidate.retry_after is None


def test_leased_credential_is_not_available_for_new_batch():
    db = MagicMock()
    credential = SimpleNamespace(
        id=uuid4(), sister_username="leased", schedule_enabled=False, availability_schedule=None
    )
    db.scalars.side_effect = [
        SimpleNamespace(all=lambda: [credential]),
        SimpleNamespace(all=lambda: [SimpleNamespace(sister_username="leased")]),
    ]
    config = CatastoRuoloAutoSyncConfig(user_id=1)
    assert sync.available_perpetual_credentials(db, config) == []
