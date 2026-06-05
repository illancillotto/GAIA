from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.sync_job import SyncJob
from app.services import sync_runtime, sync_worker


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _create_user_and_job(
    *,
    status: str = "pending",
    profile: str = "quick",
    worker_pid: int | None = None,
    created_at: datetime | None = None,
    started_at: datetime | None = None,
) -> int:
    db = TestingSessionLocal()
    try:
        unique_suffix = db.query(ApplicationUser).count() + 1
        user = ApplicationUser(
            username=f"syncadmin{unique_suffix}",
            email=f"syncadmin{unique_suffix}@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        job = SyncJob(
            requested_by_user_id=user.id,
            profile=profile,
            trigger_type="api",
            status=status,
            worker_pid=worker_pid,
            created_at=created_at or datetime.now(UTC),
            started_at=started_at,
            max_attempts=3,
            source_label=f"api:ssh:{profile}",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job.id
    finally:
        db.close()


def test_launch_sync_worker_creates_artifact_dir_and_uses_backend_pythonpath(tmp_path, monkeypatch) -> None:
    job_id = _create_user_and_job()
    db = TestingSessionLocal()
    try:
        job = db.get(SyncJob, job_id)
        assert job is not None

        monkeypatch.setattr(sync_runtime.settings, "sync_live_worker_artifacts_path", str(tmp_path))

        captured: dict[str, object] = {}

        class DummyProcess:
            pid = 9876

        def fake_popen(command, cwd, env, stdout, stderr, start_new_session):
            captured["command"] = command
            captured["cwd"] = cwd
            captured["env"] = env
            captured["stdout_name"] = stdout.name
            captured["stderr"] = stderr
            captured["start_new_session"] = start_new_session
            return DummyProcess()

        monkeypatch.setattr(sync_runtime.subprocess, "Popen", fake_popen)

        pid = sync_runtime.launch_sync_worker(job)
    finally:
        db.close()

    assert pid == 9876
    assert captured["command"] == ["python", "-m", "app.services.sync_worker", "--job-id", str(job_id)] or captured["command"] == [sync_runtime.sys.executable, "-m", "app.services.sync_worker", "--job-id", str(job_id)]
    assert captured["cwd"] == sync_runtime.BACKEND_ROOT
    assert str(sync_runtime.BACKEND_ROOT) in captured["env"]["PYTHONPATH"]
    assert captured["stderr"] == sync_runtime.subprocess.STDOUT
    assert captured["start_new_session"] is True
    assert Path(captured["stdout_name"]).name == "worker.log"
    assert Path(tmp_path / str(job_id) / "worker.log").exists()


def test_stop_sync_worker_handles_missing_pid_and_os_errors(monkeypatch) -> None:
    job_without_pid = SyncJob(requested_by_user_id=1, status="running", worker_pid=None)
    with pytest.raises(RuntimeError, match="no worker PID"):
        sync_runtime.stop_sync_worker(job_without_pid)

    job = SyncJob(requested_by_user_id=1, status="running", worker_pid=4321)
    calls: list[tuple[int, int]] = []

    def fake_killpg(pid: int, sig: int) -> None:
        calls.append((pid, sig))

    monkeypatch.setattr(sync_runtime.os, "killpg", fake_killpg)
    sync_runtime.stop_sync_worker(job)
    assert calls == [(4321, sync_runtime.signal.SIGTERM)]

    def fake_killpg_missing(pid: int, sig: int) -> None:
        raise ProcessLookupError()

    monkeypatch.setattr(sync_runtime.os, "killpg", fake_killpg_missing)
    sync_runtime.stop_sync_worker(job)

    def fake_killpg_oserror(pid: int, sig: int) -> None:
        raise OSError("boom")

    monkeypatch.setattr(sync_runtime.os, "killpg", fake_killpg_oserror)
    with pytest.raises(RuntimeError, match="Unable to stop worker process group 4321"):
        sync_runtime.stop_sync_worker(job)


def test_pid_exists_maps_process_and_permission_errors(monkeypatch) -> None:
    monkeypatch.setattr(sync_runtime.os, "kill", lambda pid, sig: None)
    assert sync_runtime._pid_exists(111) is True

    def fake_missing(pid: int, sig: int) -> None:
        raise ProcessLookupError()

    monkeypatch.setattr(sync_runtime.os, "kill", fake_missing)
    assert sync_runtime._pid_exists(111) is False

    def fake_permission(pid: int, sig: int) -> None:
        raise PermissionError()

    monkeypatch.setattr(sync_runtime.os, "kill", fake_permission)
    assert sync_runtime._pid_exists(111) is True


def test_reconcile_stale_sync_jobs_marks_running_and_pending_jobs_failed(monkeypatch) -> None:
    running_job_id = _create_user_and_job(status="running", worker_pid=3333)
    running_without_pid_job_id = _create_user_and_job(
        status="running",
        worker_pid=None,
        started_at=(datetime.now(UTC) - timedelta(minutes=30)).replace(tzinfo=None),
    )
    pending_job_id = _create_user_and_job(
        status="pending",
        created_at=(datetime.now(UTC) - timedelta(minutes=30)).replace(tzinfo=None),
    )

    monkeypatch.setattr(sync_runtime.settings, "sync_live_pending_timeout_minutes", 10)
    monkeypatch.setattr(sync_runtime, "_pid_exists", lambda pid: False)

    db = TestingSessionLocal()
    try:
        sync_runtime.reconcile_stale_sync_jobs(db)

        running_job = db.get(SyncJob, running_job_id)
        running_without_pid_job = db.get(SyncJob, running_without_pid_job_id)
        pending_job = db.get(SyncJob, pending_job_id)
        assert running_job is not None
        assert running_without_pid_job is not None
        assert pending_job is not None
        assert running_job.status == "failed"
        assert "Worker process not found" in (running_job.error_detail or "")
        assert running_job.finished_at is not None
        assert running_without_pid_job.status == "failed"
        assert running_without_pid_job.error_detail == "Running sync job lost worker PID and exceeded stale timeout"
        assert running_without_pid_job.finished_at is not None
        assert pending_job.status == "failed"
        assert pending_job.error_detail == "Pending sync job expired without worker start"
        assert pending_job.finished_at is not None
    finally:
        db.close()


def test_has_running_sync_job_reconciles_before_answering(monkeypatch) -> None:
    pending_job_id = _create_user_and_job(status="pending")
    db = TestingSessionLocal()
    try:
        calls: list[str] = []

        def fake_reconcile(session) -> None:
            calls.append("called")

        monkeypatch.setattr(sync_runtime, "reconcile_stale_sync_jobs", fake_reconcile)
        assert sync_runtime.has_running_sync_job(db) is True
        assert calls == ["called"]

        job = db.get(SyncJob, pending_job_id)
        assert job is not None
        job.status = "failed"
        db.add(job)
        db.commit()

        assert sync_runtime.has_running_sync_job(db) is False
    finally:
        db.close()


@dataclass
class _FakeSyncResult:
    snapshot_id: int = 99
    persisted_users: int = 5
    persisted_groups: int = 4
    persisted_shares: int = 3
    persisted_permission_entries: int = 7
    persisted_effective_permissions: int = 8
    share_acl_pairs_used: int = 2


@dataclass
class _FakeJobResult:
    sync_result: _FakeSyncResult
    attempts_used: int = 2


def test_worker_run_job_marks_success_and_persists_counters(monkeypatch) -> None:
    job_id = _create_user_and_job(status="pending", profile="full")
    db = TestingSessionLocal()
    try:
        job = db.get(SyncJob, job_id)
        assert job is not None

        def fake_run_live_sync_job(session, **kwargs):
            assert kwargs["trigger_type"] == "api"
            assert kwargs["initiated_by"].startswith("sync-job:")
            assert kwargs["source_label"] == "api:ssh:full"
            assert kwargs["profile"] == "full"
            return _FakeJobResult(sync_result=_FakeSyncResult(), attempts_used=2)

        monkeypatch.setattr(sync_worker, "run_live_sync_job", fake_run_live_sync_job)

        exit_code = sync_worker._run_job(db, job)
        db.refresh(job)
    finally:
        db.close()

    assert exit_code == 0
    assert job.status == "succeeded"
    assert job.snapshot_id == 99
    assert job.persisted_users == 5
    assert job.persisted_groups == 4
    assert job.persisted_shares == 3
    assert job.persisted_permission_entries == 7
    assert job.persisted_effective_permissions == 8
    assert job.share_acl_pairs_used == 2
    assert job.attempt_count == 2
    assert job.error_detail is None
    assert job.started_at is not None
    assert job.finished_at is not None
    assert job.worker_pid is None


def test_worker_run_job_emits_progress_logs_on_success(monkeypatch, capsys) -> None:
    job_id = _create_user_and_job(status="pending", profile="full")
    db = TestingSessionLocal()
    try:
        job = db.get(SyncJob, job_id)
        assert job is not None

        def fake_run_live_sync_job(session, **kwargs):
            kwargs["progress_callback"]("Attempt 1/3: collecting NAS payload via SSH")
            kwargs["progress_callback"]("Attempt 1: sync payload persisted snapshot_id=99 users=5 groups=4 shares=3 acl_pairs=2")
            kwargs["progress_callback"]("Sync completed successfully after 2 attempt(s)")
            return _FakeJobResult(sync_result=_FakeSyncResult(), attempts_used=2)

        monkeypatch.setattr(sync_worker, "run_live_sync_job", fake_run_live_sync_job)

        exit_code = sync_worker._run_job(db, job)
        output = capsys.readouterr().out
    finally:
        db.close()

    assert exit_code == 0
    assert "[sync-job:" in output
    assert "Worker picked up job profile=full trigger=api" in output
    assert "Job marked as running" in output
    assert "Attempt 1/3: collecting NAS payload via SSH" in output
    assert "Sync completed successfully after 2 attempt(s)" in output
    assert "Job marked as succeeded" in output


def test_worker_run_job_marks_failure_on_exception(monkeypatch, capsys) -> None:
    job_id = _create_user_and_job(status="pending")
    db = TestingSessionLocal()
    try:
        job = db.get(SyncJob, job_id)
        assert job is not None

        def fake_run_live_sync_job(session, **kwargs):
            raise RuntimeError("ssh down")

        monkeypatch.setattr(sync_worker, "run_live_sync_job", fake_run_live_sync_job)

        exit_code = sync_worker._run_job(db, job)
        db.refresh(job)
        output = capsys.readouterr().out
    finally:
        db.close()

    assert exit_code == 1
    assert job.status == "failed"
    assert job.finished_at is not None
    assert job.attempt_count == job.max_attempts
    assert job.error_detail == "ssh down"
    assert "Job failed: ssh down" in output


def test_worker_main_returns_2_for_missing_job_and_creates_artifact_dir(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(sync_worker, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(sync_worker, "get_sync_job_artifact_dir", lambda job_id: tmp_path / str(job_id))

    exit_code = sync_worker.main(["--job-id", "404"])
    output = capsys.readouterr().out

    assert exit_code == 2
    assert (tmp_path / "404").exists()
    assert "Job not found" in output


def test_worker_main_executes_existing_job(monkeypatch, tmp_path) -> None:
    job_id = _create_user_and_job(status="pending")
    monkeypatch.setattr(sync_worker, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(sync_worker, "get_sync_job_artifact_dir", lambda value: tmp_path / str(value))

    calls: list[int] = []

    def fake_run_job(db, job):
        calls.append(job.id)
        return 0

    monkeypatch.setattr(sync_worker, "_run_job", fake_run_job)

    exit_code = sync_worker.main(["--job-id", str(job_id)])

    assert exit_code == 0
    assert calls == [job_id]
    assert (tmp_path / str(job_id)).exists()
