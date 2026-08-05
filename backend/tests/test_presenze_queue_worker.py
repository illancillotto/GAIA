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
    queue_worker._ACTIVE_PROCESSES.clear()
    yield
    queue_worker._ACTIVE_PROCESSES.clear()
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


def test_run_once_logs_warning_when_sync_worker_fails(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    job_id = _create_pending_job()
    monkeypatch.setattr(queue_worker, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(queue_worker.os, "getpid", lambda: 7777)
    monkeypatch.setattr(queue_worker.sync_worker, "run_job_by_id", lambda current_job_id: 17 if current_job_id == job_id else 0)

    assert queue_worker.run_once() is True
    assert "exit code 17" in caplog.text


def test_claim_and_launch_one_starts_child_process(monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = _create_pending_job()
    monkeypatch.setattr(queue_worker, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(queue_worker.os, "getpid", lambda: 7777)

    class DummyProcess:
        pid = 8888

        def poll(self):
            return None

    launched: list[str] = []

    def fake_launch(job):
        launched.append(str(job.id))
        return DummyProcess()

    monkeypatch.setattr(queue_worker, "launch_sync_worker_process", fake_launch)

    assert queue_worker._claim_and_launch_one() is True
    assert launched == [job_id]
    assert list(queue_worker._ACTIVE_PROCESSES) == [job_id]


def test_claim_and_launch_one_returns_false_when_queue_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(queue_worker, "SessionLocal", TestingSessionLocal)

    assert queue_worker._claim_and_launch_one() is False


def test_claim_and_launch_one_marks_job_failed_when_child_launch_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = _create_pending_job()
    monkeypatch.setattr(queue_worker, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(queue_worker.os, "getpid", lambda: 7777)
    monkeypatch.setattr(queue_worker, "launch_sync_worker_process", lambda job: (_ for _ in ()).throw(RuntimeError("spawn boom")))

    assert queue_worker._claim_and_launch_one() is True

    db = TestingSessionLocal()
    try:
        job = db.get(PresenzeSyncJob, uuid.UUID(job_id))
        assert job is not None
        assert job.status == "failed"
        assert "spawn boom" in (job.error_detail or "")
    finally:
        db.close()


def test_reap_finished_processes_handles_running_success_and_failed_children(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO")

    class DummyProcess:
        def __init__(self, exit_code):
            self.pid = 8888
            self.exit_code = exit_code

        def poll(self):
            return self.exit_code

    queue_worker._ACTIVE_PROCESSES["running"] = DummyProcess(None)
    queue_worker._ACTIVE_PROCESSES["success"] = DummyProcess(0)
    queue_worker._ACTIVE_PROCESSES["failed"] = DummyProcess(17)

    queue_worker._reap_finished_processes()

    assert list(queue_worker._ACTIVE_PROCESSES) == ["running"]
    assert "child finished job success" in caplog.text
    assert "exit code 17" in caplog.text


def test_terminate_active_processes_covers_signal_branches(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    class DummyProcess:
        def __init__(self, pid: int):
            self.pid = pid

    calls: list[int] = []

    def fake_killpg(pid: int, signum: int) -> None:
        calls.append(pid)
        if pid == 2:
            raise ProcessLookupError()
        if pid == 3:
            raise OSError("boom")

    queue_worker._ACTIVE_PROCESSES["ok"] = DummyProcess(1)
    queue_worker._ACTIVE_PROCESSES["missing"] = DummyProcess(2)
    queue_worker._ACTIVE_PROCESSES["oserror"] = DummyProcess(3)
    monkeypatch.setattr(queue_worker.os, "killpg", fake_killpg)

    queue_worker._terminate_active_processes()

    assert calls == [1, 2, 3]
    assert "could not terminate child job oserror" in caplog.text


def test_main_parallel_installs_handlers_and_sleeps_when_idle(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, object]] = []
    monkeypatch.setattr(queue_worker.signal, "signal", lambda signum, handler: calls.append((signum, handler)))
    monkeypatch.setattr(queue_worker.settings, "presenze_worker_concurrency", 2)
    monkeypatch.setattr(queue_worker.settings, "presenze_worker_poll_seconds", 0.0)
    monkeypatch.setattr(queue_worker, "_reap_finished_processes", lambda: None)
    monkeypatch.setattr(queue_worker, "_claim_and_launch_one", lambda: False)

    def _stop(_seconds: float) -> None:
        raise KeyboardInterrupt()

    monkeypatch.setattr(queue_worker.time, "sleep", _stop)

    with pytest.raises(KeyboardInterrupt):
        queue_worker.main()

    assert calls[0][0] == queue_worker.signal.SIGTERM
    assert calls[1][0] == queue_worker.signal.SIGINT


def test_main_parallel_records_successful_launch_before_idle_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(queue_worker.signal, "signal", lambda *_args: None)
    monkeypatch.setattr(queue_worker.settings, "presenze_worker_concurrency", 2)
    monkeypatch.setattr(queue_worker.settings, "presenze_worker_poll_seconds", 0.0)
    monkeypatch.setattr(queue_worker, "_reap_finished_processes", lambda: None)
    claim_results = iter([True, False, False])
    monkeypatch.setattr(queue_worker, "_claim_and_launch_one", lambda: next(claim_results))

    def _stop(_seconds: float) -> None:
        raise KeyboardInterrupt()

    monkeypatch.setattr(queue_worker.time, "sleep", _stop)

    with pytest.raises(KeyboardInterrupt):
        queue_worker.main()


def test_main_installs_signal_handlers_and_sleeps_when_idle(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, object]] = []
    monkeypatch.setattr(queue_worker.signal, "signal", lambda signum, handler: calls.append((signum, handler)))
    monkeypatch.setattr(queue_worker.settings, "presenze_worker_concurrency", 1)
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


def test_entrypoint_exits_with_main_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(queue_worker, "main", lambda: 17)

    with pytest.raises(SystemExit) as exc_info:
        queue_worker._entrypoint()

    assert exc_info.value.code == 17
