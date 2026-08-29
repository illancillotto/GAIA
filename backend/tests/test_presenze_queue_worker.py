from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import datetime

import pytest
from app.core.datetime_compat import UTC
from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.presenze.models import PresenzeCredential, PresenzeSyncJob
from app.modules.presenze.services import queue_worker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setattr(
        queue_worker,
        "PRESENZE_HEARTBEAT",
        type("FakeHeartbeat", (), {"touch": lambda self, **_kwargs: None})(),
    )
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


def test_heartbeat_active_processes_renews_owned_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = _create_pending_job()
    monkeypatch.setattr(queue_worker, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(queue_worker.os, "getpid", lambda: 7777)

    class DummyProcess:
        pid = 8888

        def poll(self):
            return None

    monkeypatch.setattr(queue_worker, "launch_sync_worker_process", lambda _job: DummyProcess())

    assert queue_worker._heartbeat_active_processes() == 0
    assert queue_worker._claim_and_launch_one() is True
    assert queue_worker._heartbeat_active_processes() == 1

    db = TestingSessionLocal()
    try:
        job = db.get(PresenzeSyncJob, uuid.UUID(job_id))
        assert job is not None
        assert job.worker_id == queue_worker.WORKER_INSTANCE_ID
        assert job.heartbeat_at is not None
        assert job.lease_expires_at is not None
    finally:
        db.close()


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


def test_handle_termination_stops_children_before_forwarding_signal(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(queue_worker, "_terminate_active_processes", lambda: calls.append(("terminate",)))
    monkeypatch.setattr(
        queue_worker.sync_worker,
        "_handle_termination",
        lambda signum, frame: calls.append(("worker", signum, frame)),
    )

    queue_worker._handle_termination(queue_worker.signal.SIGTERM, None)

    assert calls == [("terminate",), ("worker", queue_worker.signal.SIGTERM, None)]


def test_heartbeat_supervisor_renews_leases_and_publishes_active_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []
    queue_worker._ACTIVE_PROCESSES["job"] = object()
    monkeypatch.setattr(queue_worker, "_heartbeat_active_processes", lambda: calls.append("leases"))
    monkeypatch.setattr(
        queue_worker,
        "PRESENZE_HEARTBEAT",
        type(
            "RecordingHeartbeat",
            (),
            {"touch": lambda self, **kwargs: calls.append(kwargs)},
        )(),
    )

    queue_worker._heartbeat_supervisor()

    assert calls == ["leases", {"details": {"active_jobs": 1}}]


def test_main_parallel_installs_handlers_and_sleeps_when_idle(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, object]] = []
    heartbeat_calls: list[dict[str, object]] = []
    monkeypatch.setattr(queue_worker.signal, "signal", lambda signum, handler: calls.append((signum, handler)))
    monkeypatch.setattr(queue_worker.settings, "presenze_worker_concurrency", 2)
    monkeypatch.setattr(queue_worker.settings, "presenze_worker_poll_seconds", 0.0)
    monkeypatch.setattr(queue_worker, "_reap_finished_processes", lambda: None)
    monkeypatch.setattr(queue_worker, "_claim_and_launch_one", lambda: False)
    monkeypatch.setattr(
        queue_worker,
        "_heartbeat_supervisor",
        lambda: heartbeat_calls.append({"details": {"active_jobs": 0}}),
    )

    def _stop(_seconds: float) -> None:
        raise KeyboardInterrupt()

    monkeypatch.setattr(queue_worker.time, "sleep", _stop)

    with pytest.raises(KeyboardInterrupt):
        queue_worker.main()

    assert calls[0][0] == queue_worker.signal.SIGTERM
    assert calls[1][0] == queue_worker.signal.SIGINT
    assert heartbeat_calls == [{"details": {"active_jobs": 0}}]


def test_main_parallel_records_successful_launch_before_idle_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(queue_worker.signal, "signal", lambda *_args: None)
    monkeypatch.setattr(queue_worker.settings, "presenze_worker_concurrency", 2)
    monkeypatch.setattr(queue_worker.settings, "presenze_worker_poll_seconds", 0.0)
    monkeypatch.setattr(queue_worker, "_reap_finished_processes", lambda: None)
    monkeypatch.setattr(queue_worker, "_heartbeat_active_processes", lambda: 0)
    claim_results = iter([True, False, False])
    monkeypatch.setattr(queue_worker, "_claim_and_launch_one", lambda: next(claim_results))

    def _stop(_seconds: float) -> None:
        raise KeyboardInterrupt()

    monkeypatch.setattr(queue_worker.time, "sleep", _stop)

    with pytest.raises(KeyboardInterrupt):
        queue_worker.main()


def test_main_parallel_sleeps_when_capacity_is_already_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyProcess:
        pid = 8888

    queue_worker._ACTIVE_PROCESSES["active"] = DummyProcess()
    monkeypatch.setattr(queue_worker.signal, "signal", lambda *_args: None)
    monkeypatch.setattr(queue_worker.settings, "presenze_worker_concurrency", 1)
    monkeypatch.setattr(queue_worker.settings, "presenze_worker_poll_seconds", 0.0)
    monkeypatch.setattr(queue_worker, "_reap_finished_processes", lambda: None)
    monkeypatch.setattr(queue_worker, "_heartbeat_active_processes", lambda: 1)
    monkeypatch.setattr(
        queue_worker,
        "_claim_and_launch_one",
        lambda: pytest.fail("claim must not run while capacity is full"),
    )

    def _stop(_seconds: float) -> None:
        raise KeyboardInterrupt()

    monkeypatch.setattr(queue_worker.time, "sleep", _stop)

    with pytest.raises(KeyboardInterrupt):
        queue_worker.main()


def test_main_uses_parallel_supervisor_with_concurrency_one(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, object]] = []
    monkeypatch.setattr(queue_worker.signal, "signal", lambda signum, handler: calls.append((signum, handler)))
    monkeypatch.setattr(queue_worker.settings, "presenze_worker_concurrency", 1)
    monkeypatch.setattr(queue_worker.settings, "presenze_worker_poll_seconds", 0.0)
    monkeypatch.setattr(queue_worker, "_reap_finished_processes", lambda: None)
    monkeypatch.setattr(queue_worker, "_heartbeat_active_processes", lambda: 0)
    monkeypatch.setattr(queue_worker, "_claim_and_launch_one", lambda: False)

    def _stop(_seconds: float) -> None:
        raise KeyboardInterrupt()

    monkeypatch.setattr(queue_worker.time, "sleep", _stop)

    with pytest.raises(KeyboardInterrupt):
        queue_worker.main()

    assert [signum for signum, _handler in calls] == [
        queue_worker.signal.SIGTERM,
        queue_worker.signal.SIGINT,
    ]


def test_entrypoint_exits_with_main_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(queue_worker, "main", lambda: 17)

    with pytest.raises(SystemExit) as exc_info:
        queue_worker._entrypoint()

    assert exc_info.value.code == 17
