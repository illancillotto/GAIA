from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.pool import StaticPool

from app.core.datetime_compat import UTC
from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.presenze import models as presenze_models
from app.modules.presenze.models import (
    PresenzeCredential,
    PresenzeImportJob,
    PresenzeSyncJob,
)
from app.modules.presenze.services import sync_runtime

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
            module_presenze=True,
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
    started_at: datetime | None = None,
    params_json: dict | None = None,
    worker_id: str | None = None,
    lease_token: uuid.UUID | None = None,
    lease_generation: int = 0,
    heartbeat_at: datetime | None = None,
    lease_expires_at: datetime | None = None,
    retry_not_before: datetime | None = None,
    priority: int = 100,
    attempt_count: int = 0,
    max_attempts: int = 3,
) -> PresenzeSyncJob:
    job = PresenzeSyncJob(
        id=uuid.uuid4(),
        status=status,
        requested_by_user_id=user.id,
        period_start=datetime(2026, 6, 1, tzinfo=UTC).date(),
        period_end=datetime(2026, 6, 30, tzinfo=UTC).date(),
        worker_pid=worker_pid,
        worker_id=worker_id,
        lease_token=lease_token,
        lease_generation=lease_generation,
        heartbeat_at=heartbeat_at,
        lease_expires_at=lease_expires_at,
        retry_not_before=retry_not_before,
        priority=priority,
        attempt_count=attempt_count,
        max_attempts=max_attempts,
        created_at=created_at or datetime.now(UTC),
        started_at=started_at,
        params_json=params_json,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _create_import_job(db: Session, user: ApplicationUser, *, status: str = "running") -> PresenzeImportJob:
    job = PresenzeImportJob(
        status=status,
        requested_by_user_id=user.id,
        date_from=datetime(2026, 6, 1, tzinfo=UTC).date(),
        date_to=datetime(2026, 6, 30, tzinfo=UTC).date(),
        started_at=datetime.now(UTC),
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

    naive = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC).replace(tzinfo=None)
    assert sync_runtime._as_utc(naive) == naive.replace(tzinfo=UTC)

    aware = datetime(2026, 6, 1, 14, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    assert sync_runtime._as_utc(aware) == datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


def test_presenze_model_compatibility_aliases_and_holiday_property() -> None:
    ordinary = presenze_models.PresenzeHoliday(
        holiday_date=datetime(2026, 8, 15, tzinfo=UTC).date(),
        label="Ferragosto",
        holiday_kind=presenze_models.PRESENZE_HOLIDAY_KIND_ORDINARY,
    )
    override = presenze_models.PresenzeHoliday(
        holiday_date=datetime(2026, 8, 16, tzinfo=UTC).date(),
        label="Apertura",
        holiday_kind=presenze_models.PRESENZE_HOLIDAY_KIND_WORKING_OVERRIDE,
    )
    assert ordinary.is_workday_override is False
    assert override.is_workday_override is True
    assert presenze_models.InazCredential is presenze_models.PresenzeCredential
    assert (
        presenze_models.INAZ_CONTRACT_KIND_OPERAIO
        == presenze_models.PRESENZE_CONTRACT_KIND_OPERAIO
    )
    with pytest.raises(AttributeError):
        presenze_models.__getattr__("InazMissingModel")
    with pytest.raises(AttributeError):
        presenze_models.__getattr__("INAZ_MISSING_CONSTANT")
    with pytest.raises(AttributeError):
        presenze_models.__getattr__("MissingModel")


def test_artifact_helpers_resolve_and_delete_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sync_runtime.settings, "presenze_sync_artifacts_path", str(tmp_path))
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


def test_retention_empty_queue_does_not_commit() -> None:
    db = TestingSessionLocal()
    try:
        assert sync_runtime.apply_sync_job_retention(db, keep_count=2) == 0
    finally:
        db.close()


def test_prepare_sync_job_artifacts_and_claim_next_pending_job(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    user = _create_user("presenze_runtime_claim")
    db = TestingSessionLocal()
    try:
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
        pending = _create_sync_job(db, user, status="pending")
        pending.credential_id = credential.id
        db.add(pending)
        db.commit()
        monkeypatch.setattr(sync_runtime.settings, "presenze_sync_artifacts_path", str(tmp_path))

        claimed = sync_runtime.claim_next_pending_sync_job(db, worker_pid=5555, worker_instance_id="worker-instance-1")

        assert claimed is not None
        assert claimed.id == pending.id
        assert claimed.status == "running"
        assert claimed.worker_pid == 5555
        assert claimed.worker_id == "worker-instance-1"
        assert claimed.lease_token is not None
        assert claimed.lease_generation == 1
        assert claimed.heartbeat_at is not None
        assert claimed.lease_expires_at is not None
        assert claimed.attempt_count == 1
        assert claimed.params_json["worker_mode"] == sync_runtime.QUEUE_WORKER_MODE
        assert claimed.params_json["worker_instance_id"] == "worker-instance-1"
        assert claimed.params_json["worker_claimed_at"]
        assert Path(claimed.worker_log_path or "").name == "worker.log"
        assert Path(claimed.json_artifact_path or "").name == "presenze_collaboratori.json"
    finally:
        db.close()


def test_claim_next_pending_sync_job_returns_none_when_queue_is_empty() -> None:
    db = TestingSessionLocal()
    try:
        assert sync_runtime.claim_next_pending_sync_job(db, worker_pid=5555) is None
    finally:
        db.close()


def test_claim_next_pending_sync_job_honors_priority_retry_and_attempt_limits(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    user = _create_user("presenze_runtime_claim_fair")
    db = TestingSessionLocal()
    now = datetime.now(UTC)
    try:
        credential = PresenzeCredential(
            application_user_id=user.id,
            label="Queue fair",
            username="queue.fair.inaz",
            password_encrypted="encrypted",
            active=True,
        )
        db.add(credential)
        db.commit()
        db.refresh(credential)
        oldest = _create_sync_job(
            db,
            user,
            created_at=now - timedelta(hours=2),
            priority=50,
        )
        preferred = _create_sync_job(
            db,
            user,
            created_at=now - timedelta(minutes=1),
            priority=10,
        )
        delayed = _create_sync_job(
            db,
            user,
            created_at=now - timedelta(hours=3),
            retry_not_before=now + timedelta(minutes=1),
            priority=1,
        )
        exhausted = _create_sync_job(
            db,
            user,
            created_at=now - timedelta(hours=4),
            attempt_count=3,
            max_attempts=3,
            priority=1,
        )
        for job in (oldest, preferred, delayed, exhausted):
            job.credential_id = credential.id
        db.commit()
        monkeypatch.setattr(sync_runtime.settings, "presenze_sync_artifacts_path", str(tmp_path))

        claimed = sync_runtime.claim_next_pending_sync_job(db, worker_pid=5555)

        assert claimed is not None
        assert claimed.id == preferred.id
        assert oldest.status == "pending"
        assert delayed.status == "pending"
        assert exhausted.status == "pending"
    finally:
        db.close()


def test_launch_sync_worker_creates_artifact_dir_and_extends_pythonpath(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    user = _create_user("presenze_runtime_launcher")
    db = TestingSessionLocal()
    try:
        job = _create_sync_job(db, user)
        monkeypatch.setattr(sync_runtime.settings, "presenze_sync_artifacts_path", str(tmp_path))
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
        "app.modules.presenze.services.sync_worker",
        "--job-id",
        str(job.id),
    ]
    assert captured["cwd"] == sync_runtime.BACKEND_ROOT
    assert captured["stderr"] == sync_runtime.subprocess.STDOUT
    assert captured["start_new_session"] is True
    assert captured["env"]["PYTHONPATH"] == f"{sync_runtime.BACKEND_ROOT}:/existing/pythonpath"
    assert Path(captured["stdout_name"]).name == "worker.log"
    assert (tmp_path / str(job.id) / "worker.log").exists()


def test_launch_straordinari_export_worker_creates_artifact_dir_and_extends_pythonpath(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    user = _create_user("presenze_straordinari_export_launcher")
    db = TestingSessionLocal()
    try:
        job = _create_sync_job(db, user)
        monkeypatch.setattr(sync_runtime.settings, "presenze_sync_artifacts_path", str(tmp_path))
        monkeypatch.setenv("PYTHONPATH", "/existing/pythonpath")
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

        pid = sync_runtime.launch_straordinari_export_worker(job)
    finally:
        db.close()

    assert pid == 9876
    assert captured["command"] == [
        sync_runtime.sys.executable,
        "-m",
        "app.modules.presenze.services.straordinari_export_worker",
        "--job-id",
        str(job.id),
    ]
    assert captured["cwd"] == sync_runtime.BACKEND_ROOT
    assert captured["stderr"] == sync_runtime.subprocess.STDOUT
    assert captured["start_new_session"] is True
    assert captured["env"]["PYTHONPATH"] == f"{sync_runtime.BACKEND_ROOT}:/existing/pythonpath"
    assert Path(captured["stdout_name"]).name == "worker.log"
    assert (tmp_path / str(job.id) / "worker.log").exists()


def test_launch_xlsm_export_worker_creates_artifact_dir_and_extends_pythonpath(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    user = _create_user("presenze_xlsm_export_launcher")
    db = TestingSessionLocal()
    try:
        job = _create_sync_job(db, user)
        monkeypatch.setattr(sync_runtime.settings, "presenze_sync_artifacts_path", str(tmp_path))
        monkeypatch.setenv("PYTHONPATH", "/existing/pythonpath")
        captured: dict[str, object] = {}

        class DummyProcess:
            pid = 8765

        def fake_popen(command, cwd, env, stdout, stderr, start_new_session):
            captured["command"] = command
            captured["cwd"] = cwd
            captured["env"] = env
            captured["stdout_name"] = stdout.name
            captured["stderr"] = stderr
            captured["start_new_session"] = start_new_session
            return DummyProcess()

        monkeypatch.setattr(sync_runtime.subprocess, "Popen", fake_popen)

        pid = sync_runtime.launch_xlsm_export_worker(job)
    finally:
        db.close()

    assert pid == 8765
    assert captured["command"] == [
        sync_runtime.sys.executable,
        "-m",
        "app.modules.presenze.services.xlsm_export_worker",
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
    job = PresenzeSyncJob(
        requested_by_user_id=1,
        status="running",
        period_start=datetime(2026, 6, 1, tzinfo=UTC).date(),
        period_end=datetime(2026, 6, 30, tzinfo=UTC).date(),
    )
    with pytest.raises(RuntimeError, match="no worker PID"):
        sync_runtime.stop_sync_worker(job)

    job.worker_pid = 4321
    job.worker_id = "worker-a"
    job.lease_token = uuid.uuid4()
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(sync_runtime.os, "killpg", lambda pid, sig: calls.append((pid, sig)))
    sync_runtime.stop_sync_worker(job)
    assert calls == [(4321, sync_runtime.signal.SIGTERM)]
    assert job.lease_generation == 1
    assert job.worker_id is None
    assert job.lease_token is None
    assert job.worker_pid is None

    def fake_missing(pid: int, sig: int) -> None:
        raise ProcessLookupError()

    monkeypatch.setattr(sync_runtime.os, "killpg", fake_missing)
    job.worker_pid = 4321
    sync_runtime.stop_sync_worker(job)

    def fake_oserror(pid: int, sig: int) -> None:
        raise OSError("boom")

    monkeypatch.setattr(sync_runtime.os, "killpg", fake_oserror)
    job.worker_pid = 4321
    with pytest.raises(RuntimeError, match="Unable to stop worker process group 4321"):
        sync_runtime.stop_sync_worker(job)

    monkeypatch.setattr(sync_runtime.os, "kill", lambda pid, sig: None)
    assert sync_runtime._pid_exists(111) is True

    monkeypatch.setattr(sync_runtime.os, "kill", lambda pid, sig: (_ for _ in ()).throw(ProcessLookupError()))
    assert sync_runtime._pid_exists(111) is False

    monkeypatch.setattr(sync_runtime.os, "kill", lambda pid, sig: (_ for _ in ()).throw(PermissionError()))
    assert sync_runtime._pid_exists(111) is True


def test_reconcile_stale_sync_jobs_marks_running_without_process_and_marks_stale_pending_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user("presenze_runtime_reconcile")
    db = TestingSessionLocal()
    try:
        running = _create_sync_job(db, user, status="running", worker_pid=3333)
        pending_without_process = _create_sync_job(db, user, status="pending", worker_pid=4444)
        pending = _create_sync_job(db, user, status="pending", created_at=datetime.now(UTC) - timedelta(minutes=30))
        fresh_pending = _create_sync_job(
            db,
            user,
            status="pending",
            created_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        monkeypatch.setattr(sync_runtime, "_pid_exists", lambda pid: False)

        sync_runtime.reconcile_stale_sync_jobs(db)

        db.refresh(running)
        db.refresh(pending_without_process)
        db.refresh(pending)
        db.refresh(fresh_pending)
        assert running.status == "failed"
        assert "Worker process not found" in (running.error_detail or "")
        assert running.finished_at is not None
        assert pending_without_process.status == "failed"
        assert "Worker process not found" in (pending_without_process.error_detail or "")
        assert pending_without_process.finished_at is not None
        assert pending.status == "failed"
        assert "Pending sync job had no worker assigned" in (pending.error_detail or "")
        assert pending.finished_at is not None
        assert fresh_pending.status == "pending"
        assert fresh_pending.error_detail is None
    finally:
        db.close()


def test_reconcile_stale_sync_jobs_marks_running_job_failed_after_configured_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user("presenze_runtime_reconcile_timeout")
    db = TestingSessionLocal()
    started_at = datetime.now(UTC) - timedelta(hours=13)
    try:
        running = _create_sync_job(db, user, status="running", worker_pid=3333, started_at=started_at)
        monkeypatch.setattr(sync_runtime.settings, "presenze_sync_running_stale_after_hours", 12)
        monkeypatch.setattr(sync_runtime, "_pid_exists", lambda pid: True)

        sync_runtime.reconcile_stale_sync_jobs(db)

        db.refresh(running)
        assert running.status == "failed"
        assert "configured stale timeout (12h)" in (running.error_detail or "")
        assert sync_runtime._as_utc(running.finished_at) == started_at + timedelta(hours=12)
    finally:
        db.close()


def test_reconcile_stale_sync_jobs_does_not_use_local_pid_check_for_queue_worker_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user("presenze_runtime_reconcile_queue_pid")
    db = TestingSessionLocal()
    try:
        running = _create_sync_job(
            db,
            user,
            status="running",
            worker_pid=3333,
            worker_id="queue-worker",
            lease_token=uuid.uuid4(),
            lease_generation=1,
            heartbeat_at=datetime.now(UTC),
            lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
            started_at=datetime.now(UTC),
            params_json={"worker_mode": sync_runtime.QUEUE_WORKER_MODE},
        )
        monkeypatch.setattr(sync_runtime, "_pid_exists", lambda pid: False)

        changed = sync_runtime.reconcile_stale_sync_jobs(db)

        db.refresh(running)
        assert changed is False
        assert running.status == "running"
        assert running.error_detail is None
    finally:
        db.close()


def test_mark_orphaned_queue_worker_jobs_requeues_only_expired_leases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user("presenze_runtime_orphan_queue")
    db = TestingSessionLocal()
    recovery_at = datetime.now(UTC)
    try:
        import_job = _create_import_job(db, user, status="running")
        running = _create_sync_job(
            db,
            user,
            status="running",
            worker_pid=1,
            worker_id="old-worker",
            lease_token=uuid.uuid4(),
            lease_generation=1,
            heartbeat_at=recovery_at - timedelta(minutes=6),
            lease_expires_at=recovery_at - timedelta(seconds=1),
            attempt_count=1,
            params_json={
                "worker_mode": sync_runtime.QUEUE_WORKER_MODE,
                "worker_instance_id": "old-worker",
            },
        )
        running.import_job_id = import_job.id
        other_pid = _create_sync_job(
            db,
            user,
            status="running",
            worker_pid=2,
            worker_id="new-worker",
            lease_token=uuid.uuid4(),
            lease_generation=1,
            heartbeat_at=recovery_at,
            lease_expires_at=recovery_at + timedelta(minutes=5),
            attempt_count=1,
            params_json={"worker_mode": sync_runtime.QUEUE_WORKER_MODE, "worker_instance_id": "new-worker"},
        )
        subprocess_mode = _create_sync_job(
            db,
            user,
            status="running",
            worker_pid=1,
            params_json={"worker_mode": "subprocess"},
        )
        db.add_all([running, other_pid, subprocess_mode])
        db.commit()
        monkeypatch.setattr(sync_runtime, "_worker_retry_backoff", lambda: timedelta(seconds=30))

        changed = sync_runtime.recover_expired_queue_worker_jobs(db, now=recovery_at)

        db.refresh(running)
        db.refresh(import_job)
        db.refresh(other_pid)
        db.refresh(subprocess_mode)
        assert changed is True
        assert running.status == "pending"
        assert "lease expired" in (running.error_detail or "").lower()
        assert sync_runtime._as_utc(running.retry_not_before) == recovery_at + timedelta(seconds=30)
        assert running.lease_generation == 2
        assert running.worker_id is None
        assert running.lease_token is None
        assert running.worker_pid is None
        assert import_job.status == "running"
        assert other_pid.status == "running"
        assert subprocess_mode.status == "running"
    finally:
        db.close()


def test_mark_orphaned_queue_worker_jobs_preserves_unexpired_jobs() -> None:
    user = _create_user("presenze_runtime_orphan_active")
    db = TestingSessionLocal()
    try:
        running = _create_sync_job(
            db,
            user,
            status="running",
            worker_pid=1,
            worker_id="old-worker",
            lease_token=uuid.uuid4(),
            lease_generation=1,
            heartbeat_at=datetime.now(UTC),
            lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
            params_json={"worker_mode": sync_runtime.QUEUE_WORKER_MODE, "worker_instance_id": "old-worker"},
        )

        changed = sync_runtime.mark_orphaned_queue_worker_jobs(
            db,
            worker_instance_id="new-worker",
            active_job_ids={str(running.id)},
        )

        db.refresh(running)
        assert changed is False
        assert running.status == "running"
    finally:
        db.close()


def test_mark_orphaned_queue_worker_jobs_recovers_legacy_owner_without_lease() -> None:
    user = _create_user("presenze_runtime_orphan_legacy")
    db = TestingSessionLocal()
    try:
        running = _create_sync_job(
            db,
            user,
            status="running",
            worker_pid=1,
            attempt_count=1,
            params_json={"worker_mode": sync_runtime.QUEUE_WORKER_MODE},
        )

        changed = sync_runtime.mark_orphaned_queue_worker_jobs(
            db,
            worker_instance_id="new-worker",
        )

        db.refresh(running)
        assert changed is True
        assert running.status == "pending"
        assert running.lease_generation == 1
        assert running.retry_not_before is not None
    finally:
        db.close()


def test_recover_expired_queue_worker_job_fails_after_max_attempts() -> None:
    user = _create_user("presenze_runtime_expired_max")
    db = TestingSessionLocal()
    recovery_at = datetime.now(UTC)
    try:
        import_job = _create_import_job(db, user, status="running")
        running = _create_sync_job(
            db,
            user,
            status="running",
            worker_pid=1,
            worker_id="expired-worker",
            lease_token=uuid.uuid4(),
            lease_generation=4,
            heartbeat_at=recovery_at - timedelta(minutes=6),
            lease_expires_at=recovery_at - timedelta(seconds=1),
            attempt_count=3,
            max_attempts=3,
            params_json={"worker_mode": sync_runtime.QUEUE_WORKER_MODE},
        )
        running.import_job_id = import_job.id
        db.commit()

        assert sync_runtime.recover_expired_queue_worker_jobs(db, now=recovery_at) is True

        db.refresh(running)
        db.refresh(import_job)
        assert running.status == "failed"
        assert running.lease_generation == 5
        assert running.worker_id is None
        assert "maximum attempts" in (running.error_detail or "")
        assert import_job.status == "failed"
        assert import_job.error_detail == running.error_detail
    finally:
        db.close()


def test_renew_queue_worker_leases_updates_only_matching_active_jobs() -> None:
    user = _create_user("presenze_runtime_renew")
    db = TestingSessionLocal()
    heartbeat_at = datetime.now(UTC)
    try:
        owned = _create_sync_job(
            db,
            user,
            status="running",
            worker_id="worker-a",
            lease_token=uuid.uuid4(),
            lease_generation=1,
            lease_expires_at=heartbeat_at - timedelta(seconds=1),
        )
        other = _create_sync_job(
            db,
            user,
            status="running",
            worker_id="worker-b",
            lease_token=uuid.uuid4(),
            lease_generation=1,
            lease_expires_at=heartbeat_at - timedelta(seconds=1),
        )

        renewed = sync_runtime.renew_queue_worker_leases(
            db,
            worker_id="worker-a",
            active_job_ids={str(owned.id), str(other.id), "not-a-uuid"},
            now=heartbeat_at,
        )

        db.refresh(owned)
        db.refresh(other)
        assert renewed == 1
        assert sync_runtime._as_utc(owned.heartbeat_at) == heartbeat_at
        assert sync_runtime._as_utc(owned.lease_expires_at) == heartbeat_at + sync_runtime._worker_lease_duration()
        assert other.heartbeat_at is None
        assert sync_runtime.renew_queue_worker_leases(
            db,
            worker_id="worker-a",
            active_job_ids={"not-a-uuid"},
        ) == 0
        assert sync_runtime.renew_queue_worker_leases(
            db,
            worker_id="worker-a",
            active_job_ids={str(owned.id)},
            now=heartbeat_at + timedelta(seconds=1),
            commit=False,
        ) == 1
        db.rollback()
    finally:
        db.close()


def test_touch_and_clear_sync_job_lease_require_active_ownership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRESENZE_WORKER_LEASE_SECONDS", "invalid")
    assert sync_runtime._worker_lease_duration() == timedelta(
        seconds=sync_runtime.DEFAULT_WORKER_LEASE_SECONDS
    )
    monkeypatch.setenv("PRESENZE_WORKER_LEASE_SECONDS", "1")
    assert sync_runtime._worker_lease_duration() == timedelta(seconds=30)
    monkeypatch.setenv("PRESENZE_WORKER_RETRY_BACKOFF_SECONDS", "0")
    assert sync_runtime._worker_retry_backoff() == timedelta(seconds=1)

    job = PresenzeSyncJob(
        status="pending",
        requested_by_user_id=1,
        period_start=datetime(2026, 6, 1, tzinfo=UTC).date(),
        period_end=datetime(2026, 6, 30, tzinfo=UTC).date(),
    )
    sync_runtime.touch_sync_job_lease(job)
    assert job.heartbeat_at is None

    heartbeat_at = datetime.now(UTC)
    job.status = "running"
    job.worker_id = "worker-a"
    job.lease_token = uuid.uuid4()
    job.worker_pid = 123
    sync_runtime.touch_sync_job_lease(job, now=heartbeat_at)
    assert job.heartbeat_at == heartbeat_at
    assert job.lease_expires_at == heartbeat_at + timedelta(seconds=30)

    sync_runtime.clear_sync_job_lease(job)
    assert job.worker_id is None
    assert job.lease_token is None
    assert job.heartbeat_at is None
    assert job.lease_expires_at is None
    assert job.worker_pid is None


def test_lease_generation_fences_a_stale_session() -> None:
    user = _create_user("presenze_runtime_fencing")
    seed_db = TestingSessionLocal()
    try:
        job = _create_sync_job(
            seed_db,
            user,
            status="running",
            worker_id="worker-a",
            lease_token=uuid.uuid4(),
            lease_generation=1,
            lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        job_id = job.id
    finally:
        seed_db.close()

    owner_db = TestingSessionLocal()
    recovery_db = TestingSessionLocal()
    try:
        stale_owner = owner_db.get(PresenzeSyncJob, job_id)
        recovered = recovery_db.get(PresenzeSyncJob, job_id)
        assert stale_owner is not None
        assert recovered is not None

        recovered.lease_generation += 1
        recovered.status = "pending"
        sync_runtime.clear_sync_job_lease(recovered)
        recovery_db.commit()

        stale_owner.status = "completed"
        with pytest.raises(StaleDataError):
            owner_db.commit()
    finally:
        owner_db.rollback()
        owner_db.close()
        recovery_db.close()


def test_reconcile_stale_sync_jobs_marks_linked_import_job_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user("presenze_runtime_reconcile_import")
    db = TestingSessionLocal()
    started_at = datetime.now(UTC) - timedelta(hours=13)
    try:
        import_job = _create_import_job(db, user, status="running")
        running = _create_sync_job(db, user, status="running", worker_pid=3333, started_at=started_at)
        running.import_job_id = import_job.id
        db.add(running)
        db.commit()
        monkeypatch.setattr(sync_runtime.settings, "presenze_sync_running_stale_after_hours", 12)
        monkeypatch.setattr(sync_runtime, "_pid_exists", lambda pid: True)

        changed = sync_runtime.reconcile_stale_sync_jobs(db)

        db.refresh(running)
        db.refresh(import_job)
        assert changed is True
        assert running.status == "failed"
        assert import_job.status == "failed"
        assert import_job.error_detail == running.error_detail
        assert sync_runtime._as_utc(import_job.finished_at) == sync_runtime._as_utc(running.finished_at)
    finally:
        db.close()


def test_mark_linked_import_job_terminal_ignores_missing_or_terminal_import() -> None:
    user = _create_user("presenze_runtime_terminal_import")
    db = TestingSessionLocal()
    try:
        no_import = _create_sync_job(db, user)
        completed_import = _create_import_job(db, user, status="completed")
        completed_sync = _create_sync_job(db, user)
        completed_sync.import_job_id = completed_import.id
        db.add(completed_sync)
        db.commit()

        finished_at = datetime.now(UTC)

        assert (
            sync_runtime.mark_linked_import_job_terminal(
                db,
                sync_job=no_import,
                status="failed",
                finished_at=finished_at,
                error_detail="stale",
            )
            is False
        )
        assert (
            sync_runtime.mark_linked_import_job_terminal(
                db,
                sync_job=completed_sync,
                status="failed",
                finished_at=finished_at,
                error_detail="stale",
            )
            is False
        )
        db.refresh(completed_import)
        assert completed_import.status == "completed"
        assert completed_import.error_detail is None
    finally:
        db.close()


def test_has_running_sync_job_reconciles_first_and_returns_expected_value(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _create_user("presenze_runtime_running_check")
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


def test_apply_sync_job_retention_prunes_only_older_terminal_sync_jobs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(sync_runtime.settings, "presenze_sync_artifacts_path", str(tmp_path))
    monkeypatch.setattr(sync_runtime.settings, "presenze_sync_retention_count", 2)
    user = _create_user("presenze_runtime_retention")
    db = TestingSessionLocal()
    try:
        oldest = _create_sync_job(db, user, status="completed", created_at=datetime(2026, 6, 1, tzinfo=UTC))
        middle = _create_sync_job(db, user, status="failed", created_at=datetime(2026, 6, 2, tzinfo=UTC))
        newest = _create_sync_job(db, user, status="cancelled", created_at=datetime(2026, 6, 3, tzinfo=UTC))
        running = _create_sync_job(db, user, status="running", created_at=datetime(2026, 6, 4, tzinfo=UTC))
        export_job = _create_sync_job(
            db,
            user,
            status="completed",
            created_at=datetime(2026, 6, 5, tzinfo=UTC),
            params_json={"mode": "export_xlsm"},
        )

        for job in (oldest, middle, newest, running, export_job):
            artifact_dir = tmp_path / str(job.id)
            artifact_dir.mkdir(parents=True, exist_ok=True)
            (artifact_dir / "summary.json").write_text("{}", encoding="utf-8")

        deleted = sync_runtime.apply_sync_job_retention(db)

        assert deleted == 1
        assert db.get(PresenzeSyncJob, oldest.id) is None
        assert (tmp_path / str(oldest.id)).exists() is False
        assert db.get(PresenzeSyncJob, middle.id) is not None
        assert db.get(PresenzeSyncJob, newest.id) is not None
        assert db.get(PresenzeSyncJob, running.id) is not None
        assert db.get(PresenzeSyncJob, export_job.id) is not None
        assert (tmp_path / str(export_job.id)).exists() is True
    finally:
        db.close()


def test_apply_sync_job_retention_closes_running_import_for_pruned_failed_sync(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(sync_runtime.settings, "presenze_sync_artifacts_path", str(tmp_path))
    user = _create_user("presenze_runtime_retention_import")
    db = TestingSessionLocal()
    try:
        import_job = _create_import_job(db, user, status="running")
        failed = _create_sync_job(
            db,
            user,
            status="failed",
            created_at=datetime(2026, 6, 1, tzinfo=UTC),
            started_at=datetime(2026, 6, 1, 8, tzinfo=UTC),
        )
        failed.import_job_id = import_job.id
        failed.finished_at = datetime(2026, 6, 1, 9, tzinfo=UTC)
        failed.error_detail = "stale sync"
        newest = _create_sync_job(db, user, status="completed", created_at=datetime(2026, 6, 2, tzinfo=UTC))
        db.add_all([failed, newest])
        db.commit()

        for job in (failed, newest):
            artifact_dir = tmp_path / str(job.id)
            artifact_dir.mkdir(parents=True, exist_ok=True)

        deleted = sync_runtime.apply_sync_job_retention(db, keep_count=1)

        db.refresh(import_job)
        assert deleted == 1
        assert db.get(PresenzeSyncJob, failed.id) is None
        assert import_job.status == "failed"
        assert import_job.error_detail == "stale sync"
        assert sync_runtime._as_utc(import_job.finished_at) == datetime(2026, 6, 1, 9, tzinfo=UTC)
    finally:
        db.close()


def test_apply_sync_job_retention_skips_pruning_when_keep_count_is_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(sync_runtime.settings, "presenze_sync_artifacts_path", str(tmp_path))
    user = _create_user("presenze_runtime_retention_zero")
    db = TestingSessionLocal()
    try:
        job = _create_sync_job(db, user, status="completed", created_at=datetime(2026, 6, 1, tzinfo=UTC))
        artifact_dir = tmp_path / str(job.id)
        artifact_dir.mkdir(parents=True, exist_ok=True)

        deleted = sync_runtime.apply_sync_job_retention(db, keep_count=0)

        assert deleted == 0
        assert db.get(PresenzeSyncJob, job.id) is not None
        assert artifact_dir.exists() is True
    finally:
        db.close()
