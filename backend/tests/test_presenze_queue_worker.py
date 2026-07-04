from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.datetime_compat import UTC
from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.presenze.models import PresenzeCredential, PresenzeSyncJob
from app.modules.presenze.services import queue_worker


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _create_pending_job() -> str:
    db = TestingSessionLocal()
    try:
        user = ApplicationUser(
            username="queue_worker_admin",
            email="queue_worker_admin@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
            module_accessi=True,
            module_presenze=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        credential = PresenzeCredential(
            application_user_id=user.id,
            label="Queue",
            username="queue.inaz",
            password_encrypted="encrypted",
            active=True,
        )
        db.add(credential)
        db.commit()
        db.refresh(credential)
        job = PresenzeSyncJob(
            id=uuid.uuid4(),
            status="pending",
            requested_by_user_id=user.id,
            credential_id=credential.id,
            period_start=datetime(2026, 6, 1, tzinfo=UTC).date(),
            period_end=datetime(2026, 6, 30, tzinfo=UTC).date(),
            max_attempts=3,
        )
        db.add(job)
        db.commit()
        return str(job.id)
    finally:
        db.close()


def test_run_once_returns_false_when_queue_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(queue_worker, "SessionLocal", TestingSessionLocal)
    assert queue_worker.run_once() is False


def test_run_once_claims_job_and_executes_sync_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = _create_pending_job()
    monkeypatch.setattr(queue_worker, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(queue_worker.os, "getpid", lambda: 7777)
    monkeypatch.setattr(queue_worker.sync_worker, "run_job_by_id", lambda current_job_id: 0 if current_job_id == job_id else 1)

    assert queue_worker.run_once() is True
    assert queue_worker.sync_worker.CURRENT_JOB_ID is None


def test_main_installs_signal_handlers_and_sleeps_when_idle(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, object]] = []
    monkeypatch.setattr(queue_worker.signal, "signal", lambda signum, handler: calls.append((signum, handler)))
    monkeypatch.setattr(queue_worker.settings, "presenze_worker_poll_seconds", 0.0)
    monkeypatch.setattr(queue_worker, "run_once", lambda: False)

    def _stop(_seconds: float) -> None:
        raise KeyboardInterrupt()

    monkeypatch.setattr(queue_worker.time, "sleep", _stop)

    with pytest.raises(KeyboardInterrupt):
        queue_worker.main()

    assert calls == [
        (queue_worker.signal.SIGTERM, queue_worker.sync_worker._handle_termination),
        (queue_worker.signal.SIGINT, queue_worker.sync_worker._handle_termination),
    ]
