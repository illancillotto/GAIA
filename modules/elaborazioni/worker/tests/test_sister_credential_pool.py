from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.models.catasto import CatastoBatchStatus
from sister_credential_pool import (
    ActiveSisterCredentialPool,
    CredentialRejectionContext,
    RejectedCredentialQuarantined,
    credential_is_active,
    finalize_credential_pool,
    is_rejected_credential_error,
    isolate_rejected_credential_runner,
    load_active_credential_pool,
    quarantine_rejected_credential,
    run_dynamic_credential_pool,
    should_stop_credential_runner,
)


class Rows:
    def __init__(self, values) -> None:
        self.values = values

    def all(self):
        return self.values


class FakeDb:
    def __init__(self, *, get_value=None, scalars_values=()) -> None:
        self.get_value = get_value
        self.scalars_values = list(scalars_values)
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def get(self, _model, _identity):
        return self.get_value

    def scalars(self, _query):
        return Rows(self.scalars_values)

    def commit(self):
        self.commits += 1


def credential(*, user_id=1, active=True, username="user", schedule_enabled=False, availability_schedule=None):
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        active=active,
        sister_username=username,
        schedule_enabled=schedule_enabled,
        availability_schedule=availability_schedule,
    )


def test_load_active_credential_pool_honors_batch_scope() -> None:
    selected = credential()
    pinned_batch = SimpleNamespace(credential_id=selected.id, user_id=1)
    assert load_active_credential_pool(FakeDb(get_value=selected), pinned_batch).credentials == (selected,)

    wrong_user = credential(user_id=2)
    assert not load_active_credential_pool(FakeDb(get_value=wrong_user), pinned_batch).credentials
    assert not load_active_credential_pool(FakeDb(get_value=None), pinned_batch).credentials
    assert not load_active_credential_pool(
        FakeDb(get_value=credential(active=False)),
        pinned_batch,
    ).credentials

    first = credential(username="first")
    second = credential(username="second")
    unpinned_batch = SimpleNamespace(credential_id=None, user_id=1)
    assert load_active_credential_pool(
        FakeDb(scalars_values=[first, second]),
        unpinned_batch,
    ).credentials == (first, second)


def test_load_active_credential_pool_defers_credentials_outside_their_schedule() -> None:
    schedule = {
        "timezone": "Europe/Rome",
        "weekly": {"0": [{"start": "18:00", "end": "08:00"}]},
    }
    reference = datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc)
    scheduled = credential(schedule_enabled=True, availability_schedule=schedule)
    batch = SimpleNamespace(credential_id=scheduled.id, user_id=1)

    pool = load_active_credential_pool(FakeDb(get_value=scheduled), batch, reference)

    assert pool.credentials == ()
    assert pool.active_credential_count == 1
    assert pool.next_availability == datetime(2026, 8, 24, 16, 0, tzinfo=timezone.utc)

    unpinned = SimpleNamespace(credential_id=None, user_id=1)
    always_available = credential()
    pool = load_active_credential_pool(
        FakeDb(scalars_values=[scheduled, always_available]),
        unpinned,
        reference,
    )
    assert pool.credentials == (always_available,)
    assert pool.next_availability == datetime(2026, 8, 24, 16, 0, tzinfo=timezone.utc)


def test_pool_rejection_state_and_error_classification() -> None:
    first = credential(username="first")
    second = credential(username="second")
    pool = ActiveSisterCredentialPool((first, second))

    assert pool.available_ids == {first.id, second.id}
    assert pool.reject(first.id) == 1
    assert pool.available_ids == {second.id}
    assert "pool sincronizzato con 1" in pool.rejection_operation(first)

    assert is_rejected_credential_error(RuntimeError("Credenziali SISTER rifiutate"))
    assert is_rejected_credential_error(RuntimeError("Credenziali errate"))
    assert is_rejected_credential_error(RuntimeError("Autenticazione fallita"))
    assert not is_rejected_credential_error(RuntimeError("SISTER_SESSION_LOCKED"))


def test_pool_merge_adds_only_new_available_credentials() -> None:
    first = credential(username="first")
    second = credential(username="second")
    rejected = credential(username="rejected")
    pool = ActiveSisterCredentialPool((first, rejected))
    pool.reject(rejected.id)

    added = pool.merge(ActiveSisterCredentialPool((first, second, rejected), 3))

    assert added == (second,)
    assert pool.credentials == (first, rejected, second)
    assert pool.active_credential_count == 3
    assert pool.available_ids == {first.id, second.id}


def test_quarantine_rejected_credential_requeues_for_remaining_pool() -> None:
    class Repository:
        def __init__(self) -> None:
            self.failed_unavailable = []
            self.resets = []

        def fail_unavailable_pinned_requests(self, *args):
            self.failed_unavailable.append(args)

        def reset_for_retry(self, *args, **kwargs):
            self.resets.append((args, kwargs))

    rejected = credential(username="rejected")
    available = credential(username="available")
    pool = ActiveSisterCredentialPool((rejected, available))
    repository = Repository()
    operations = []
    batch_id = uuid4()
    request_id = uuid4()
    token = uuid4()

    context = CredentialRejectionContext(
        pool,
        rejected,
        batch_id,
        request_id,
        token,
        repository,
        lambda _batch_id, operation: operations.append(operation),
    )

    assert quarantine_rejected_credential(RuntimeError("timeout"), context) is None
    with pytest.raises(RejectedCredentialQuarantined):
        quarantine_rejected_credential(RuntimeError("Credenziali errate"), context)
    assert repository.failed_unavailable == [(batch_id, {available.id})]
    assert repository.resets[0][1] == {
        "error_code": "sister_credential_rejected",
        "execution_token": token,
    }
    assert "pool sincronizzato con 1" in operations[0]


def test_isolate_rejected_credential_runner_only_suppresses_quarantine() -> None:
    async def quarantined():
        raise RejectedCredentialQuarantined

    async def failed():
        raise RuntimeError("unexpected")

    assert asyncio.run(isolate_rejected_credential_runner(quarantined())) is None
    with pytest.raises(RuntimeError, match="unexpected"):
        asyncio.run(isolate_rejected_credential_runner(failed()))


def test_dynamic_pool_accepts_an_empty_initial_pool() -> None:
    async def run_credential(_credential):
        return None

    asyncio.run(
        run_dynamic_credential_pool(
            (),
            run_credential,
            lambda _started_ids: (),
            lambda: False,
            lambda: None,
            1,
        )
    )


def test_should_stop_credential_runner_preserves_release_semantics() -> None:
    calls = []

    assert should_stop_credential_runner(True, uuid4(), "user", lambda: calls.append("release") or True)
    assert not calls
    assert not should_stop_credential_runner(False, uuid4(), "user", lambda: False)
    assert should_stop_credential_runner(False, uuid4(), "user", lambda: True)
    assert should_stop_credential_runner(False, uuid4(), "user", lambda: False, lambda: True)
    assert not should_stop_credential_runner(False, uuid4(), "user", lambda: False, lambda: False)


def test_credential_is_active_reads_current_persisted_state() -> None:
    assert credential_is_active(lambda: FakeDb(get_value=credential()), uuid4())
    assert not credential_is_active(lambda: FakeDb(get_value=credential(active=False)), uuid4())
    assert not credential_is_active(lambda: FakeDb(get_value=None), uuid4())


def test_finalize_pool_pauses_only_when_all_credentials_are_rejected() -> None:
    selected = credential()
    pool = ActiveSisterCredentialPool((selected,))
    pool.reject(selected.id)
    batch = SimpleNamespace(status=CatastoBatchStatus.PROCESSING.value, completed_at=None, current_operation=None)
    db = FakeDb(get_value=batch)
    finalized: list[object] = []

    finalize_credential_pool(pool, uuid4(), True, lambda: db, finalized.append)

    assert batch.status == CatastoBatchStatus.FAILED.value
    assert batch.completed_at is not None
    assert "riattivare o aggiornare il pool" in batch.current_operation
    assert db.commits == 1
    assert not finalized

    finalize_credential_pool(pool, uuid4(), False, lambda: db, finalized.append)
    assert len(finalized) == 1


def test_finalize_pool_preserves_missing_or_cancelled_batch() -> None:
    selected = credential()
    pool = ActiveSisterCredentialPool((selected,))
    pool.reject(selected.id)

    missing = FakeDb(get_value=None)
    finalize_credential_pool(pool, uuid4(), True, lambda: missing, lambda _batch_id: None)
    assert missing.commits == 0

    cancelled_batch = SimpleNamespace(status=CatastoBatchStatus.CANCELLED.value)
    cancelled = FakeDb(get_value=cancelled_batch)
    finalize_credential_pool(pool, uuid4(), True, lambda: cancelled, lambda _batch_id: None)
    assert cancelled.commits == 0
