"""Use an explicitly configured disposable PostgreSQL database, never production."""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
import test_worker as worker_test_support  # noqa: F401 - installs isolated worker dependencies
from poste_pool_support import finish, metadata, queue, seed
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import posta_online_queue as queue_module
from app.models.posta_online import PostaOnlineRegisteredMailSyncJob as Job
from posta_online_leases import acquire_portal_lease
from posta_online_pool import PostePool


@pytest.fixture
def store(monkeypatch):
    url = os.getenv("POSTE_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set POSTE_TEST_DATABASE_URL to a disposable PostgreSQL database")
    base = create_engine(url, pool_pre_ping=True)
    schema = "poste_test_" + uuid4().hex
    with base.begin() as connection:
        connection.execute(text('CREATE SCHEMA "' + schema + '"'))
    engine = base.execution_options(schema_translate_map={None: schema})
    metadata().create_all(engine)
    monkeypatch.setattr(queue_module, "has_available_credential", lambda *_args: True)
    try:
        yield engine, sessionmaker(engine, expire_on_commit=False)
    finally:
        with base.begin() as connection:
            connection.execute(text('DROP SCHEMA "' + schema + '" CASCADE'))
        base.dispose()


def test_real_session_locks_separate_accounts_and_block_duplicate_usernames(store):
    engine, _ = store
    first = acquire_portal_lease(engine, "Account-One")
    second = acquire_portal_lease(engine, "Account-Two")
    try:
        assert first is not None and second is not None
        assert acquire_portal_lease(engine, " account-ONE ") is None
        assert acquire_portal_lease(engine, None) is None
        first.connection.commit()
        assert acquire_portal_lease(engine, "account-one") is None
    finally:
        first.close()
        second.close()
    exclusive = acquire_portal_lease(engine, None)
    try:
        assert exclusive is not None
        assert acquire_portal_lease(engine, "another-account") is None
        assert acquire_portal_lease(engine, None) is None
    finally:
        exclusive.close()


def test_another_worker_cannot_recover_a_live_job_but_can_after_connection_loss(store):
    _, sessions = store
    identity = seed(sessions)
    first = queue(sessions).claim()
    try:
        assert first.id == identity
        assert queue(sessions).claim() is None
        with sessions() as db:
            assert db.get(Job, identity).status == "processing"
        first.lease.connection.invalidate()
        first.lease.connection.close()
        recovered = queue(sessions).claim()
        try:
            assert recovered.id == identity
        finally:
            recovered.lease.close()
    finally:
        first.lease.close()


def test_two_pools_overlap_three_accounts_without_overlapping_the_same_account(store):
    _, sessions = store
    identities = {seed(sessions, account): account for account in [1, 1, 2, 2, 3, 3]}

    async def scenario():
        state = SimpleNamespace(stop_requested=False)
        barrier, release = asyncio.Event(), asyncio.Event()
        active, completed, peaks = set(), [], []

        async def process(identity):
            account = identities[identity]
            assert account not in active
            active.add(account)
            peaks.append(len(active))
            if len(active) == 3:
                barrier.set()
            await release.wait()
            active.remove(account)
            finish(sessions, identity)
            completed.append(identity)
            if len(completed) == 6:
                state.stop_requested = True

        pools = [
            PostePool(queue(sessions), process, state, limit=3, poll_interval=0.001)
            for _ in range(2)
        ]
        tasks = [asyncio.create_task(pool.run()) for pool in pools]
        try:
            await asyncio.wait_for(barrier.wait(), 10)
            assert active == {1, 2, 3} and not completed
            release.set()
            await asyncio.wait_for(asyncio.gather(*tasks), 10)
            assert max(peaks) == 3 and len(completed) == 6
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(scenario())


def test_a_job_row_locked_by_another_transaction_is_skipped_without_leaking_a_lease(store):
    engine, sessions = store
    identity = seed(sessions)
    with sessions() as blocker:
        blocker.execute(
            text(
                'SELECT id FROM "'
                + engine.get_execution_options()["schema_translate_map"][None]
                + '".posta_online_registered_mail_sync_jobs WHERE id=:id FOR UPDATE'
            ),
            {"id": identity},
        )
        assert queue(sessions).claim() is None
    lease = acquire_portal_lease(engine, "account-1")
    assert lease is not None
    lease.close()


@pytest.mark.parametrize("same_username", [True, False])
def test_simultaneous_workers_claim_distinct_accounts_without_duplicate_ownership(
    store, same_username
):
    _, sessions = store
    first = seed(sessions, 1, username="Account-One")
    second = seed(sessions, 2, username=" account-ONE " if same_username else "Account-Two")
    start = Barrier(2)

    def claim():
        start.wait(timeout=10)
        return queue(sessions).claim()

    claimed = []
    try:
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = [workers.submit(claim) for _ in range(2)]
            claimed = [result.result(timeout=15) for result in results]
        owned = [job for job in claimed if job is not None]
        assert len(owned) == (1 if same_username else 2)
        assert len({job.id for job in owned}) == len(owned)
        with sessions() as db:
            statuses = [db.get(Job, identity).status for identity in [first, second]]
        assert statuses.count("processing") == len(owned)
        assert statuses.count("pending") == (1 if same_username else 0)
    finally:
        for job in claimed:
            if job is not None:
                job.lease.close()
