from collections import Counter
from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy import Column, Integer, MetaData, Table, create_engine
from sqlalchemy.orm import sessionmaker

from app.models.posta_online import PostaOnlineCredential, PostaOnlineRegisteredMailSyncJob
from posta_online_queue import PosteQueue


def metadata():
    result = MetaData()
    Table("application_users", result, Column("id", Integer, primary_key=True))
    PostaOnlineCredential.__table__.to_metadata(result)
    PostaOnlineRegisteredMailSyncJob.__table__.to_metadata(result)
    return result


def sqlite_sessions(path):
    engine = create_engine("sqlite:///" + str(path))
    metadata().create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def seed(sessions, account=1, *, username=None, mode="poste_dispatch_drafts", status="pending"):
    with sessions() as db:
        if account is not None and db.get(PostaOnlineCredential, account) is None:
            db.add(
                PostaOnlineCredential(
                    id=account,
                    username=username or f"account-{account}",
                    label=f"Account {account}",
                    password_encrypted="test-only",
                )
            )
            db.flush()
        job = PostaOnlineRegisteredMailSyncJob(
            credential_id=account, mode=mode, status=status, payload_json={}
        )
        db.add(job)
        db.commit()
        return job.id


def finish(sessions, identity, status="succeeded"):
    with sessions() as db:
        job = db.get(PostaOnlineRegisteredMailSyncJob, identity)
        job.status = status
        job.completed_at = datetime.now(UTC)
        db.commit()


def queue(sessions):
    return PosteQueue(sessions, lambda _job: True, lambda job: job.credential_id)


class LeaseRegistry:
    """Deterministic substitute; separate PostgreSQL tests exercise real session locks."""

    def __init__(self):
        self.accounts = Counter()
        self.exclusive = False
        self.leases = []

    def acquire(self, _engine, username):
        key = username.strip().casefold() if username is not None else None
        if self.exclusive or self.accounts[key] or (key is None and self.accounts):
            return None
        if key is None:
            self.exclusive = True
        else:
            self.accounts[key] += 1
        lease = SimpleNamespace(closed=False)

        def close():
            if lease.closed:
                return
            lease.closed = True
            if key is None:
                self.exclusive = False
            else:
                del self.accounts[key]

        lease.close = close
        self.leases.append(lease)
        return lease
