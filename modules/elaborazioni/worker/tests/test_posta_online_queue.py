from datetime import UTC, datetime

import pytest
import test_worker as worker_test_support  # noqa: F401 - installs isolated worker dependencies
from poste_pool_support import LeaseRegistry, finish, queue, seed, sqlite_sessions
from sqlalchemy import select

import posta_online_queue as module
from app.models.posta_online import PostaOnlineRegisteredMailSyncJob as Job


@pytest.fixture
def store(tmp_path, monkeypatch):
    sessions = sqlite_sessions(tmp_path / "poste.db")
    leases = LeaseRegistry()
    monkeypatch.setattr(module, "acquire_portal_lease", leases.acquire)
    monkeypatch.setattr(module, "has_available_credential", lambda *_args: True)
    yield sessions, leases
    for lease in leases.leases:
        lease.close()
    sessions.kw["bind"].dispose()


def test_other_accounts_can_be_claimed_while_the_same_account_waits(store):
    sessions, _ = store
    first, duplicate, other = seed(sessions), seed(sessions), seed(sessions, 2)
    a, b = queue(sessions).claim(), queue(sessions).claim()
    assert (a.id, b.id) == (first, other)
    assert queue(sessions).claim() is None
    with sessions() as db:
        assert db.get(Job, duplicate).status == "pending"
    finish(sessions, first)
    a.lease.close()
    assert queue(sessions).claim().id == duplicate


def test_credentials_with_the_same_poste_username_are_serialized(store):
    sessions, _ = store
    seed(sessions, 1, username="SameUser")
    seed(sessions, 2, username="  sameuser ")
    assert queue(sessions).claim() is not None
    assert queue(sessions).claim() is None


def test_recovery_cannot_reset_a_live_job_but_resumes_after_its_owner_disappears(store):
    sessions, _ = store
    identity = seed(sessions)
    first = queue(sessions).claim()
    assert queue(sessions).claim() is None
    with sessions() as db:
        assert db.get(Job, identity).status == "processing"
    first.lease.close()
    recovered = queue(sessions).claim()
    assert recovered.id == identity


def test_legacy_jobs_have_exclusive_access_even_without_a_pinned_account(store):
    sessions, _ = store
    dispatch, legacy = seed(sessions), seed(sessions, None, mode="registered_mails")
    first = queue(sessions).claim()
    assert queue(sessions).claim() is None
    finish(sessions, dispatch)
    first.lease.close()
    exclusive = queue(sessions).claim()
    assert exclusive.id == legacy
    seed(sessions, 2)
    assert queue(sessions).claim() is None


@pytest.mark.parametrize("mode", ["poste_dispatch_drafts", "registered_mails"])
def test_unavailable_credentials_do_not_block_other_available_accounts(store, monkeypatch, mode):
    sessions, _ = store
    blocked, ready = seed(sessions, mode=mode), seed(sessions, 2)
    monkeypatch.setattr(module, "has_available_credential", lambda _db, identity: identity == 2)
    assert queue(sessions).claim().id == ready
    with sessions() as db:
        assert db.get(Job, blocked).error_detail == module._WAITING


def test_tests_bypass_availability_and_stale_completed_jobs_are_expired(store, monkeypatch):
    sessions, _ = store
    stale = seed(sessions, status="processing")
    with sessions() as db:
        db.get(Job, stale).completed_at = datetime.now(UTC)
        db.commit()
    identity = seed(sessions, mode="credential_test")
    monkeypatch.setattr(module, "has_available_credential", lambda *_args: False)
    assert queue(sessions).claim().id == identity
    with sessions() as db:
        assert db.get(Job, stale).status == "failed"


@pytest.mark.parametrize("username", [None, "   "])
def test_dispatch_never_uses_a_fallback_account(store, username):
    sessions, _ = store
    identity = seed(sessions, None if username is None else 1, username=username)
    assert queue(sessions).claim() is None
    with sessions() as db:
        assert db.get(Job, identity).status == "pending"


def test_retry_cooldown_is_checked_again_under_the_job_row_lock(store):
    sessions, leases = store
    seed(sessions)
    pending = queue(sessions)
    decisions = iter([True, False])
    pending.retry_ready = lambda _job: next(decisions)
    assert pending.claim() is None
    assert leases.leases[0].closed


def test_a_deleted_dispatch_credential_is_not_replaced(store):
    sessions, _ = store
    identity = seed(sessions, None)
    with sessions() as db:
        db.get(Job, identity).credential_id = 999
        db.commit()
    assert queue(sessions).claim() is None


@pytest.mark.parametrize("change", ["finish", "account", "delete"])
def test_a_job_changed_since_the_scan_is_not_claimed(store, monkeypatch, change):
    sessions, leases = store
    identity = seed(sessions)
    pending = queue(sessions)
    original = pending._claim

    def changed(db, job_id, expected):
        db.rollback()
        with sessions() as other:
            job = other.get(Job, identity)
            if change == "finish":
                job.status = "succeeded"
            elif change == "account":
                job.credential_id = None
            else:
                other.delete(job)
            other.commit()
        return original(db, job_id, expected)

    monkeypatch.setattr(pending, "_claim", changed)
    assert pending.claim() is None
    assert leases.leases[0].closed


def test_commit_errors_release_the_lease(store, monkeypatch):
    sessions, leases = store
    seed(sessions)
    pending = queue(sessions)

    def failure(*_args):
        raise RuntimeError("database disconnected")

    monkeypatch.setattr(pending, "_claim", failure)
    with pytest.raises(RuntimeError, match="disconnected"):
        pending.claim()
    assert leases.leases[0].closed


def test_missing_finished_and_processing_jobs_fail_independently(store):
    sessions, _ = store
    pending = queue(sessions)
    pending.fail(999, "missing")
    done = seed(sessions, status="succeeded")
    pending.fail(done, "already done")
    identity = seed(sessions, status="processing")
    pending.fail(identity, "unexpected portal error")
    with sessions() as db:
        jobs = {job.id: job for job in db.scalars(select(Job))}
        assert jobs[done].status == "succeeded"
        assert jobs[identity].status == "failed"
        assert jobs[identity].completed_at
        assert jobs[identity].error_detail == "unexpected portal error"
