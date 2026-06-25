from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.datetime_compat import UTC
from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.inaz.models import InazSyncJob
from app.modules.inaz.services import sync_runtime


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _create_user(username: str) -> ApplicationUser:
    db = TestingSessionLocal()
    try:
        user = ApplicationUser(
            username=username,
            email=f"{username}@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
            module_accessi=True,
            module_inaz=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _create_sync_job(
    db: Session,
    user: ApplicationUser,
    *,
    status: str = "pending",
    worker_pid: int | None = None,
    created_at: datetime | None = None,
) -> InazSyncJob:
    job = InazSyncJob(
        id=uuid.uuid4(),
        status=status,
        requested_by_user_id=user.id,
        period_start=datetime(2026, 6, 1, tzinfo=UTC).date(),
        period_end=datetime(2026, 6, 30, tzinfo=UTC).date(),
        worker_pid=worker_pid,
        max_attempts=3,
        created_at=created_at or datetime.now(UTC),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_build_period_handles_regular_and_december_months() -> None:
    assert sync_runtime.build_period(2026, 2) == (
        datetime(2026, 2, 1, tzinfo=UTC).date(),
        datetime(2026, 2, 28, tzinfo=UTC).date(),
    )
    assert sync_runtime.build_period(2026, 12) == (
        datetime(2026, 12, 1, tzinfo=UTC).date(),
        datetime(2026, 12, 31, tzinfo=UTC).date(),
    )


def test_as_utc_handles_none_naive_and_aware_datetimes() -> None:
    assert sync_runtime._as_utc(None) is None

    naive = datetime(2026, 6, 1, 12, 0, 0)
    assert sync_runtime._as_utc(naive) == naive.replace(tzinfo=UTC)

    aware = datetime(2026, 6, 1, 14, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    assert sync_runtime._as_utc(aware) == datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


def test_artifact_helpers_resolve_and_delete_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sync_runtime.settings, "inaz_sync_artifacts_path", str(tmp_path))
    job_id = "job-42"
    artifact_dir = tmp_path / job_id
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "summary.json").write_text("{}", encoding="utf-8")

    resolved = sync_runtime.resolve_sync_artifact_path(job_id, "summary")
    assert resolved == (artifact_dir / "summary.json").resolve()

    with pytest.raises(ValueError, match="Unsupported artifact"):
        sync_runtime.resolve_sync_artifact_path(job_id, "bogus")

    sync_runtime.delete_sync_artifact_dir(job_id)
    assert artifact_dir.exists() is False


def test_launch_sync_worker_creates_artifact_dir_and_extends_pythonpath(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    user = _create_user("inaz_runtime_launcher")
    db = TestingSessionLocal()
    try:
        job = _create_sync_job(db, user)
        monkeypatch.setattr(sync_runtime.settings, "inaz_sync_artifacts_path", str(tmp_path))
        monkeypatch.setenv("PYTHONPATH", "/existing/pythonpath")
        captured: dict[str, object] = {}

        class DummyProcess:
            pid = 7654

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

    assert pid == 7654
    assert captured["command"] == [
        sync_runtime.sys.executable,
        "-m",
        "app.modules.inaz.services.sync_worker",
        "--job-id",
        str(job.id),
    ]
    assert captured["cwd"] == sync_runtime.BACKEND_ROOT
    assert captured["stderr"] == sync_runtime.subprocess.STDOUT
    assert captured["start_new_session"] is True
    assert captured["env"]["PYTHONPATH"] == f"{sync_runtime.BACKEND_ROOT}:/existing/pythonpath"
    assert Path(captured["stdout_name"]).name == "worker.log"
    assert (tmp_path / str(job.id) / "worker.log").exists()


def test_stop_sync_worker_and_pid_exists_cover_runtime_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    job = InazSyncJob(
        requested_by_user_id=1,
        status="running",
        period_start=datetime(2026, 6, 1, tzinfo=UTC).date(),
        period_end=datetime(2026, 6, 30, tzinfo=UTC).date(),
    )
    with pytest.raises(RuntimeError, match="no worker PID"):
        sync_runtime.stop_sync_worker(job)

    job.worker_pid = 4321
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(sync_runtime.os, "killpg", lambda pid, sig: calls.append((pid, sig)))
    sync_runtime.stop_sync_worker(job)
    assert calls == [(4321, sync_runtime.signal.SIGTERM)]

    def fake_missing(pid: int, sig: int) -> None:
        raise ProcessLookupError()

    monkeypatch.setattr(sync_runtime.os, "killpg", fake_missing)
    sync_runtime.stop_sync_worker(job)

    def fake_oserror(pid: int, sig: int) -> None:
        raise OSError("boom")

    monkeypatch.setattr(sync_runtime.os, "killpg", fake_oserror)
    with pytest.raises(RuntimeError, match="Unable to stop worker process group 4321"):
        sync_runtime.stop_sync_worker(job)

    monkeypatch.setattr(sync_runtime.os, "kill", lambda pid, sig: None)
    assert sync_runtime._pid_exists(111) is True

    monkeypatch.setattr(sync_runtime.os, "kill", lambda pid, sig: (_ for _ in ()).throw(ProcessLookupError()))
    assert sync_runtime._pid_exists(111) is False

    monkeypatch.setattr(sync_runtime.os, "kill", lambda pid, sig: (_ for _ in ()).throw(PermissionError()))
    assert sync_runtime._pid_exists(111) is True


def test_reconcile_stale_sync_jobs_marks_running_without_process_and_old_pending_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user("inaz_runtime_reconcile")
    db = TestingSessionLocal()
    try:
        running = _create_sync_job(db, user, status="running", worker_pid=3333)
        pending = _create_sync_job(
            db,
            user,
            status="pending",
            created_at=datetime.now(UTC) - timedelta(minutes=30),
        )
        fresh_pending = _create_sync_job(
            db,
            user,
            status="pending",
            created_at=datetime.now(UTC) - timedelta(minutes=5),
        )
        monkeypatch.setattr(sync_runtime, "_pid_exists", lambda pid: False)

        sync_runtime.reconcile_stale_sync_jobs(db)

        db.refresh(running)
        db.refresh(pending)
        db.refresh(fresh_pending)
        assert running.status == "failed"
        assert "Worker process not found" in (running.error_detail or "")
        assert running.finished_at is not None
        assert pending.status == "failed"
        assert pending.error_detail == "Pending sync job expired without worker start"
        assert pending.finished_at is not None
        assert fresh_pending.status == "pending"
        assert fresh_pending.error_detail is None
    finally:
        db.close()


def test_has_running_sync_job_reconciles_first_and_returns_expected_value(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _create_user("inaz_runtime_running_check")
    db = TestingSessionLocal()
    try:
        job = _create_sync_job(db, user, status="pending")
        calls: list[str] = []

        def fake_reconcile(current_db: Session) -> None:
            calls.append("called")

        monkeypatch.setattr(sync_runtime, "reconcile_stale_sync_jobs", fake_reconcile)

        assert sync_runtime.has_running_sync_job(db) is True
        assert calls == ["called"]

        job.status = "failed"
        db.add(job)
        db.commit()

        assert sync_runtime.has_running_sync_job(db) is False
    finally:
        db.close()
