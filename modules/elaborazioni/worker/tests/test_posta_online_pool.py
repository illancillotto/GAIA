import asyncio
from types import SimpleNamespace

import pytest
import test_worker as worker_test_support  # noqa: F401 - installs isolated worker dependencies
from poste_pool_support import LeaseRegistry, finish, queue, seed, sqlite_sessions

import posta_online_pool as module
import posta_online_queue as queue_module
from posta_online_queue import ClaimedJob


def run(coroutine):
    return asyncio.run(coroutine)


@pytest.mark.parametrize("configured,expected", [(None, 3), ("1", 1), ("32", 32)])
def test_configurable_account_limit(monkeypatch, configured, expected):
    monkeypatch.delenv("POSTA_ONLINE_MAX_CONCURRENT_ACCOUNTS", raising=False)
    if configured is not None:
        monkeypatch.setenv("POSTA_ONLINE_MAX_CONCURRENT_ACCOUNTS", configured)
    assert module.concurrent_account_limit() == expected


@pytest.mark.parametrize("configured", ["0", "33", "invalid"])
def test_invalid_limits_fail_before_starting_work(monkeypatch, configured):
    monkeypatch.setenv("POSTA_ONLINE_MAX_CONCURRENT_ACCOUNTS", configured)
    with pytest.raises(ValueError):
        module.concurrent_account_limit()


@pytest.fixture
def store(tmp_path, monkeypatch):
    sessions = sqlite_sessions(tmp_path / "pool.db")
    leases = LeaseRegistry()
    monkeypatch.setattr(queue_module, "acquire_portal_lease", leases.acquire)
    monkeypatch.setattr(queue_module, "has_available_credential", lambda *_args: True)
    yield sessions, leases
    sessions.kw["bind"].dispose()


def test_three_accounts_overlap_and_a_fourth_waits_without_reusing_an_account(store):
    sessions, leases = store
    jobs = {seed(sessions, account): account for account in [1, 1, 2, 3, 4]}

    async def scenario():
        state = SimpleNamespace(stop_requested=False)
        barrier, release = asyncio.Event(), asyncio.Event()
        running, completed, peaks = set(), [], []

        async def process(identity):
            account = jobs[identity]
            assert account not in running
            running.add(account)
            peaks.append(len(running))
            if len(running) == 3:
                barrier.set()
            await release.wait()
            running.remove(account)
            finish(sessions, identity)
            completed.append(identity)
            if len(completed) == len(jobs):
                state.stop_requested = True

        pool = module.PostePool(queue(sessions), process, state, limit=3, poll_interval=0.001)
        task = asyncio.create_task(pool.run())
        await asyncio.wait_for(barrier.wait(), 3)
        assert running == {1, 2, 3}
        assert not completed
        release.set()
        await asyncio.wait_for(task, 3)
        assert max(peaks) == 3 and len(completed) == 5
        assert all(lease.closed for lease in leases.leases)

    run(scenario())


def test_one_account_failure_does_not_cancel_the_other_accounts(store):
    sessions, _ = store
    first, second = seed(sessions), seed(sessions, 2)

    async def scenario():
        state = SimpleNamespace(stop_requested=False)
        completed = []

        async def process(identity):
            if identity == first:
                raise RuntimeError("account one unavailable")
            await asyncio.sleep(0)
            finish(sessions, identity)
            completed.append(identity)
            state.stop_requested = True

        pool = module.PostePool(queue(sessions), process, state, limit=3, poll_interval=0.001)
        await pool.run()
        assert completed == [second]
        with sessions() as db:
            assert db.get(queue_module.PostaOnlineRegisteredMailSyncJob, first).status == "failed"

    run(scenario())


def test_stop_drains_the_running_browser_and_leaves_queued_work_untouched(store):
    sessions, _ = store
    first, waiting = seed(sessions), seed(sessions)

    async def scenario():
        state = SimpleNamespace(stop_requested=False)
        started, release = asyncio.Event(), asyncio.Event()

        async def process(identity):
            assert identity == first
            started.set()
            await release.wait()
            finish(sessions, identity)

        pool = module.PostePool(queue(sessions), process, state, limit=3, poll_interval=0.001)
        task = asyncio.create_task(pool.run())
        await asyncio.wait_for(started.wait(), 3)
        state.stop_requested = True
        await asyncio.sleep(0.01)
        assert not task.done()
        release.set()
        await task
        with sessions() as db:
            assert (
                db.get(queue_module.PostaOnlineRegisteredMailSyncJob, waiting).status == "pending"
            )

    run(scenario())


def test_cancellation_closes_browsers_and_releases_ownership_for_recovery(store):
    sessions, leases = store
    seed(sessions)

    async def scenario():
        state = SimpleNamespace(stop_requested=False)
        started, closed = asyncio.Event(), asyncio.Event()

        async def process(_identity):
            try:
                started.set()
                await asyncio.Event().wait()
            finally:
                closed.set()

        pool = module.PostePool(queue(sessions), process, state, limit=3, poll_interval=0.001)
        task = asyncio.create_task(pool.run())
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert closed.is_set() and all(lease.closed for lease in leases.leases)
        recovered = queue(sessions).claim()
        assert recovered is not None
        recovered.lease.close()

    run(scenario())


def test_cancel_before_a_browser_task_starts_still_releases_its_lease():
    leases = LeaseRegistry()
    claimed = ClaimedJob(1, leases.acquire(None, "account"))
    pending = SimpleNamespace(claim=lambda: claimed)

    async def scenario():
        state = SimpleNamespace(stop_requested=True)
        pool = module.PostePool(pending, None, state, limit=1, poll_interval=0.001)
        state.stop_requested = False
        pool._fill()
        state.stop_requested = True
        for task in pool.tasks:
            task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pool.run()
        assert claimed.lease.closed

    run(scenario())


def test_idle_pool_waits_and_exits_on_stop():
    async def scenario():
        state = SimpleNamespace(stop_requested=False)
        pool = module.PostePool(
            SimpleNamespace(claim=lambda: None), None, state, limit=1, poll_interval=0.001
        )
        task = asyncio.create_task(pool.run())
        await asyncio.sleep(0.01)
        state.stop_requested = True
        await task

    run(scenario())


@pytest.mark.parametrize("families", [{"posta_online"}, {"posta_online", "registry"}, {"registry"}])
def test_entrypoint_integrates_the_pool_without_resetting_peers_or_other_job_families(
    monkeypatch, families
):
    calls = []

    class Worker:
        job_families = families
        state = SimpleNamespace(stop_requested=False)
        _posta_online_retry_ready = "retry"
        _posta_online_job_credential_id = "credential"
        _process_posta_online_job = "process"

        def _install_signal_handlers(self):
            calls.append("signals")

        async def run(self):
            calls.append(set(self.job_families))

    class Pool:
        def __init__(self, pending, process, state, **options):
            assert pending == ("factory", "retry", "credential")
            assert process == "process" and options == {"limit": 3, "poll_interval": 2}

        async def run(self):
            calls.append("pool")

    monkeypatch.setattr(module, "PosteQueue", lambda *args: args)
    monkeypatch.setattr(module, "PostePool", Pool)
    monkeypatch.delenv("POSTA_ONLINE_MAX_CONCURRENT_ACCOUNTS", raising=False)
    worker = Worker()
    runtime = SimpleNamespace(SessionLocal="factory", POLL_INTERVAL_SEC=2)
    run(module.run_with_poste_pool(worker, runtime))
    assert worker.job_families is families
    if families == {"registry"}:
        assert calls == [{"registry"}]
    elif families == {"posta_online"}:
        assert calls == ["signals", "pool"]
    else:
        assert calls == [{"registry"}, "pool"]


def test_entrypoint_restores_families_when_the_pool_fails(monkeypatch):
    families = {"posta_online"}
    worker = SimpleNamespace(
        job_families=families,
        state=None,
        _posta_online_retry_ready=None,
        _posta_online_job_credential_id=None,
        _process_posta_online_job=None,
        _install_signal_handlers=lambda: None,
    )

    async def failure(_self):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(module.PostePool, "run", failure)
    with pytest.raises(RuntimeError, match="unavailable"):
        run(
            module.run_with_poste_pool(
                worker, SimpleNamespace(SessionLocal=None, POLL_INTERVAL_SEC=2)
            )
        )
    assert worker.job_families is families
