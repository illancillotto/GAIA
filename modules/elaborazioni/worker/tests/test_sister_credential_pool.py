from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoBatch, CatastoBatchStatus, CatastoCredential
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
    refresh_shared_credential_pool,
    run_dynamic_credential_pool,
    should_stop_credential_runner,
)


class Rows:
    def __init__(self, values) -> None:
        self.values = values

    def all(self):
        return self.values


class FakeDb:
    def __init__(self, *, get_value=None, get_values=None, scalars_values=()) -> None:
        self.get_value = get_value
        self.get_values = get_values
        self.scalars_values = list(scalars_values)
        self.scalar_queries = []
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def get(self, model, _identity):
        if self.get_values is not None:
            return self.get_values.get(model)
        return self.get_value

    def scalars(self, query):
        self.scalar_queries.append(query)
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
    db = FakeDb(scalars_values=[first, second])
    assert load_active_credential_pool(
        db,
        unpinned_batch,
    ).credentials == (first, second)
    assert "catasto_credentials.user_id" in str(db.scalar_queries[0]).split("WHERE", 1)[1]


def test_super_admin_shared_pool_uses_all_available_credentials() -> None:
    owner = SimpleNamespace(is_super_admin=True)
    own = credential(user_id=1, username="own")
    shared = credential(user_id=2, username="shared")
    unavailable = credential(
        user_id=3,
        username="scheduled",
        schedule_enabled=True,
        availability_schedule={
            "timezone": "Europe/Rome",
            "weekly": {"0": [{"start": "18:00", "end": "08:00"}]},
        },
    )
    db = FakeDb(
        get_values={ApplicationUser: owner},
        scalars_values=[own, shared, unavailable],
    )
    batch = SimpleNamespace(credential_id=None, user_id=1)

    pool = load_active_credential_pool(
        db,
        batch,
        datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc),
    )

    assert pool.credentials == (own, shared)
    assert pool.active_credential_count == 3
    assert pool.next_availability == datetime(2026, 8, 24, 16, 0, tzinfo=timezone.utc)
    assert "catasto_credentials.user_id" not in str(db.scalar_queries[0]).split("WHERE", 1)[1]


def test_super_admin_pinned_pool_remains_bound_to_owned_credential() -> None:
    other_users_credential = credential(user_id=2)
    batch = SimpleNamespace(credential_id=other_users_credential.id, user_id=1)

    pool = load_active_credential_pool(FakeDb(get_value=other_users_credential), batch)

    assert pool.credentials == ()


def test_super_admin_global_pool_executes_real_queries_and_refreshes_cross_user_credentials() -> None:
    engine = create_engine("sqlite://")
    ApplicationUser.__table__.create(bind=engine)
    CatastoCredential.__table__.create(bind=engine)
    CatastoBatch.__table__.create(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    reference = datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc)

    with session_factory() as db:
        super_admin = ApplicationUser(
            username="super-admin",
            email="super-admin@example.local",
            password_hash="hash",
            role="super_admin",
        )
        operator = ApplicationUser(
            username="operator",
            email="operator@example.local",
            password_hash="hash",
            role="operator",
        )
        db.add_all([super_admin, operator])
        db.flush()
        own = CatastoCredential(
            user_id=super_admin.id,
            label="Own",
            sister_username="own-real",
            sister_password_encrypted=b"secret",
            active=True,
        )
        shared = CatastoCredential(
            user_id=operator.id,
            label="Shared",
            sister_username="shared-real",
            sister_password_encrypted=b"secret",
            active=True,
        )
        inactive = CatastoCredential(
            user_id=operator.id,
            label="Inactive",
            sister_username="inactive-real",
            sister_password_encrypted=b"secret",
            active=False,
        )
        scheduled = CatastoCredential(
            user_id=operator.id,
            label="Scheduled",
            sister_username="scheduled-real",
            sister_password_encrypted=b"secret",
            active=True,
            schedule_enabled=True,
            availability_schedule={
                "timezone": "Europe/Rome",
                "weekly": {},
            },
        )
        db.add_all([own, shared, inactive, scheduled])
        db.flush()
        batch = CatastoBatch(
            user_id=super_admin.id,
            name="Global pool",
            status=CatastoBatchStatus.PROCESSING.value,
            total_items=1,
        )
        db.add(batch)
        db.commit()

        global_pool = load_active_credential_pool(db, batch, reference)
        operator_pool = load_active_credential_pool(
            db,
            SimpleNamespace(credential_id=None, user_id=operator.id),
            reference,
        )

        assert {item.id for item in global_pool.credentials} == {own.id, shared.id}
        assert global_pool.active_credential_count == 3
        assert operator_pool.credentials == (shared,)

        late_user = ApplicationUser(
            username="late-operator",
            email="late-operator@example.local",
            password_hash="hash",
            role="operator",
        )
        db.add(late_user)
        db.flush()
        late = CatastoCredential(
            user_id=late_user.id,
            label="Late",
            sister_username="late-real",
            sister_password_encrypted=b"secret",
            active=True,
        )
        db.add(late)
        db.commit()

    added = refresh_shared_credential_pool(
        session_factory,
        batch.id,
        global_pool,
        {item.id for item in global_pool.credentials},
    )

    assert {item.id for item in added} == {late.id}
    engine.dispose()


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


def test_dynamic_pool_starts_all_initial_credentials_concurrently() -> None:
    credentials = tuple(credential(username=f"user-{index}") for index in range(3))
    started: set[object] = set()
    all_started = asyncio.Event()

    async def run_credential(selected):
        started.add(selected.id)
        if len(started) == len(credentials):
            all_started.set()
        await asyncio.wait_for(all_started.wait(), timeout=1)

    asyncio.run(
        run_dynamic_credential_pool(
            credentials,
            run_credential,
            lambda _started_ids: (),
            lambda: False,
            lambda: None,
            1,
        )
    )

    assert started == {selected.id for selected in credentials}


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
