from __future__ import annotations

from collections.abc import Generator
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.datetime_compat import UTC
from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.presenze.models import PresenzeAutoSyncConfig, PresenzeCollaborator, PresenzeCredential, PresenzeSyncJob
from app.modules.presenze.schemas import PresenzeAutoSyncConfigUpdate
from app.modules.presenze.services.auto_sync import (
    PRESENZE_PREVIOUS_MONTH_SYNC_CUTOFF_DAY,
    _commit_stale_changes_if_needed,
    _active_employee_codes,
    _auto_sync_failure_superseded_by_completed_job,
    _employee_codes_for_job,
    _open_employee_codes_for_period,
    _is_auto_sync_retry_due,
    _reconcile_and_has_open_sync_job,
    _resolve_auto_sync_period,
    _resolve_trigger_user_id,
    _try_acquire_auto_sync_lock,
    get_auto_sync_config,
    serialize_auto_sync_config,
    trigger_auto_sync_job,
    update_auto_sync_config,
)


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _create_user(
    username: str,
    *,
    is_active: bool = True,
    module_presenze: bool = True,
) -> ApplicationUser:
    db = TestingSessionLocal()
    try:
        user = ApplicationUser(
            username=username,
            email=f"{username}@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=is_active,
            module_accessi=True,
            module_presenze=module_presenze,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _create_credential(db: Session, user: ApplicationUser, *, active: bool = True) -> PresenzeCredential:
    credential = PresenzeCredential(
        application_user_id=user.id,
        label="Auto",
        username=f"{user.username}.inaz",
        password_encrypted="encrypted",
        active=active,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


def _create_auto_sync_job(
    db: Session,
    user: ApplicationUser,
    credential: PresenzeCredential,
    *,
    status: str = "failed",
    created_at: datetime | None = None,
    finished_at: datetime | None = None,
    attempt_count: int = 1,
    max_attempts: int = 3,
) -> PresenzeSyncJob:
    resolved_created_at = created_at or ((finished_at - timedelta(hours=1)) if finished_at is not None else datetime.now(UTC))
    job = PresenzeSyncJob(
        status=status,
        requested_by_user_id=user.id,
        credential_id=credential.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
        attempt_count=attempt_count,
        max_attempts=max_attempts,
        error_detail="Inaz temporary failure",
        params_json={"trigger": "auto", "progress": {"state": status, "error": "Inaz temporary failure"}},
        created_at=resolved_created_at,
        started_at=resolved_created_at,
        finished_at=finished_at,
        worker_pid=1,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _create_collaborators(db: Session, count: int) -> list[str]:
    codes: list[str] = []
    for index in range(1, count + 1):
        code = f"{index:04d}"
        codes.append(code)
        db.add(
            PresenzeCollaborator(
                employee_code=code,
                company_code="53",
                name=f"Collaborator {index:04d}",
                is_active=True,
            )
        )
    db.commit()
    return codes


def test_get_auto_sync_config_creates_default_row() -> None:
    db = TestingSessionLocal()
    try:
        config = get_auto_sync_config(db)
        assert config.id == 1
        assert config.job_enabled is False
        assert db.get(PresenzeAutoSyncConfig, 1) is not None
    finally:
        db.close()


def test_serialize_auto_sync_config_exposes_schedule_metadata() -> None:
    db = TestingSessionLocal()
    try:
        config = get_auto_sync_config(db)
        payload = serialize_auto_sync_config(config)
        assert payload.schedule_times == ["06:00", "12:00", "18:00"]
        assert payload.schedule_cron == "0 6,12,18 * * *"
        assert payload.schedule_timezone == "Europe/Rome"
    finally:
        db.close()


def test_resolve_auto_sync_period_uses_current_month_only_for_non_first_slot() -> None:
    period_start, period_end, target_months, target_scope = _resolve_auto_sync_period(datetime(2026, 7, 3, 12, 0))

    assert period_start == date(2026, 7, 1)
    assert period_end == date(2026, 7, 31)
    assert target_months == ["2026-07"]
    assert target_scope == "current_month_only"


def test_resolve_auto_sync_period_includes_previous_month_on_first_slot_within_cutoff() -> None:
    period_start, period_end, target_months, target_scope = _resolve_auto_sync_period(
        datetime(2026, 7, PRESENZE_PREVIOUS_MONTH_SYNC_CUTOFF_DAY, 6, 0)
    )

    assert period_start == date(2026, 6, 1)
    assert period_end == date(2026, 7, 31)
    assert target_months == ["2026-06", "2026-07"]
    assert target_scope == "previous_and_current_month"


def test_resolve_auto_sync_period_rolls_back_to_previous_year_in_january() -> None:
    period_start, period_end, target_months, target_scope = _resolve_auto_sync_period(
        datetime(2026, 1, PRESENZE_PREVIOUS_MONTH_SYNC_CUTOFF_DAY, 6, 0)
    )

    assert period_start == date(2025, 12, 1)
    assert period_end == date(2026, 1, 31)
    assert target_months == ["2025-12", "2026-01"]
    assert target_scope == "previous_and_current_month"


def test_resolve_auto_sync_period_excludes_previous_month_after_cutoff() -> None:
    period_start, period_end, target_months, target_scope = _resolve_auto_sync_period(
        datetime(2026, 7, PRESENZE_PREVIOUS_MONTH_SYNC_CUTOFF_DAY + 1, 6, 0)
    )

    assert period_start == date(2026, 7, 1)
    assert period_end == date(2026, 7, 31)
    assert target_months == ["2026-07"]
    assert target_scope == "current_month_only"


def test_auto_sync_retry_due_returns_false_without_terminal_dates() -> None:
    job = PresenzeSyncJob(
        status="failed",
        requested_by_user_id=1,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
        params_json={"trigger": "auto"},
    )
    job.created_at = None

    assert _is_auto_sync_retry_due(job, now=datetime.now(UTC)) is False


def test_auto_sync_failure_superseded_by_completed_job_requires_matching_later_completion() -> None:
    user = _create_user("auto_sync_superseded_probe")
    db = TestingSessionLocal()
    try:
        unsaved = PresenzeSyncJob(
            status="failed",
            requested_by_user_id=user.id,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
            params_json={"trigger": "auto"},
        )
        unsaved.created_at = None
        assert _auto_sync_failure_superseded_by_completed_job(db, unsaved) is False

        credential = _create_credential(db, user, active=True)
        failed = _create_auto_sync_job(
            db,
            user,
            credential,
            status="failed",
            created_at=datetime(2026, 7, 2, 10, 0, tzinfo=UTC),
            finished_at=datetime(2026, 7, 2, 22, 0, tzinfo=UTC),
        )
        old_completed = _create_auto_sync_job(
            db,
            user,
            credential,
            status="completed",
            created_at=datetime(2026, 7, 2, 8, 0, tzinfo=UTC),
            finished_at=datetime(2026, 7, 2, 9, 0, tzinfo=UTC),
        )

        assert _auto_sync_failure_superseded_by_completed_job(db, failed) is False

        old_completed.finished_at = datetime(2026, 7, 2, 11, 0, tzinfo=UTC)
        db.add(old_completed)
        db.commit()

        assert _auto_sync_failure_superseded_by_completed_job(db, failed) is True
    finally:
        db.close()


def test_update_auto_sync_config_can_store_disabled_state_without_credential() -> None:
    user = _create_user("auto_sync_editor")
    db = TestingSessionLocal()
    try:
        config = update_auto_sync_config(
            db,
            PresenzeAutoSyncConfigUpdate(job_enabled=False, collaborator_limit=25),
            user_id=user.id,
        )
        assert config.job_enabled is False
        assert config.collaborator_limit == 25
        assert config.updated_by_user_id == user.id
        assert config.updated_at is not None
    finally:
        db.close()


def test_update_auto_sync_config_preserves_enabled_state_when_field_is_omitted() -> None:
    user = _create_user("auto_sync_preserve_enabled")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=True)
        config = get_auto_sync_config(db)
        config.job_enabled = True
        config.credential_id = credential.id
        db.add(config)
        db.commit()

        updated = update_auto_sync_config(
            db,
            PresenzeAutoSyncConfigUpdate(collaborator_limit=18),
            user_id=user.id,
        )

        assert updated.job_enabled is True
        assert updated.collaborator_limit == 18
        assert updated.credential_id == credential.id
    finally:
        db.close()


def test_update_auto_sync_config_rejects_unknown_credential() -> None:
    user = _create_user("auto_sync_missing_cred")
    db = TestingSessionLocal()
    try:
        with pytest.raises(HTTPException) as excinfo:
            update_auto_sync_config(
                db,
                PresenzeAutoSyncConfigUpdate(job_enabled=True, credential_id=99999),
                user_id=user.id,
            )
        assert excinfo.value.status_code == 404
    finally:
        db.close()


def test_update_auto_sync_config_rejects_disabled_credential() -> None:
    user = _create_user("auto_sync_disabled_cred")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=False)
        with pytest.raises(HTTPException) as excinfo:
            update_auto_sync_config(
                db,
                PresenzeAutoSyncConfigUpdate(job_enabled=True, credential_id=credential.id),
                user_id=user.id,
            )
        assert excinfo.value.status_code == 409
    finally:
        db.close()


def test_update_auto_sync_config_rejects_enable_without_credential() -> None:
    user = _create_user("auto_sync_no_cred")
    db = TestingSessionLocal()
    try:
        with pytest.raises(HTTPException) as excinfo:
            update_auto_sync_config(
                db,
                PresenzeAutoSyncConfigUpdate(job_enabled=True),
                user_id=user.id,
            )
        assert excinfo.value.status_code == 409
    finally:
        db.close()


def test_update_auto_sync_config_rejects_enabled_config_when_stored_credential_is_missing() -> None:
    user = _create_user("auto_sync_missing_stored_cred")
    db = TestingSessionLocal()
    try:
        config = get_auto_sync_config(db)
        config.credential_id = 99999
        db.add(config)
        db.commit()

        with pytest.raises(HTTPException) as excinfo:
            update_auto_sync_config(
                db,
                PresenzeAutoSyncConfigUpdate(job_enabled=True),
                user_id=user.id,
            )
        assert excinfo.value.status_code == 404
    finally:
        db.close()


def test_update_auto_sync_config_rejects_enabled_config_when_stored_credential_is_inactive() -> None:
    user = _create_user("auto_sync_inactive_stored_cred")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=False)
        config = get_auto_sync_config(db)
        config.credential_id = credential.id
        db.add(config)
        db.commit()

        with pytest.raises(HTTPException) as excinfo:
            update_auto_sync_config(
                db,
                PresenzeAutoSyncConfigUpdate(job_enabled=True),
                user_id=user.id,
            )
        assert excinfo.value.status_code == 409
    finally:
        db.close()


def test_update_auto_sync_config_can_clear_credential_when_disabled() -> None:
    user = _create_user("auto_sync_clear_cred")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=True)
        config = update_auto_sync_config(
            db,
            PresenzeAutoSyncConfigUpdate(job_enabled=True, credential_id=credential.id),
            user_id=user.id,
        )
        assert config.credential_id == credential.id

        cleared = update_auto_sync_config(
            db,
            PresenzeAutoSyncConfigUpdate(job_enabled=False, credential_id=None),
            user_id=user.id,
        )
        assert cleared.job_enabled is False
        assert cleared.credential_id is None
    finally:
        db.close()


def test_resolve_trigger_user_id_prefers_config_updated_by_user() -> None:
    owner = _create_user("auto_sync_owner")
    fallback = _create_user("auto_sync_fallback")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, fallback, active=True)
        config = PresenzeAutoSyncConfig(id=1, job_enabled=True, credential_id=credential.id, updated_by_user_id=owner.id)
        user_id = _resolve_trigger_user_id(db, config, credential)
        assert user_id == owner.id
    finally:
        db.close()


def test_resolve_trigger_user_id_falls_back_to_credential_owner() -> None:
    owner = _create_user("auto_sync_credential_owner")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, owner, active=True)
        config = PresenzeAutoSyncConfig(id=1, job_enabled=True, credential_id=credential.id, updated_by_user_id=None)
        user_id = _resolve_trigger_user_id(db, config, credential)
        assert user_id == owner.id
    finally:
        db.close()


def test_resolve_trigger_user_id_uses_first_active_inaz_user_when_needed() -> None:
    inactive = _create_user("auto_sync_inactive", is_active=False)
    no_module = _create_user("auto_sync_no_module", module_presenze=False)
    fallback = _create_user("auto_sync_real_fallback")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, fallback, active=True)
        credential.application_user_id = no_module.id
        db.add(credential)
        db.commit()
        config = PresenzeAutoSyncConfig(id=1, job_enabled=True, credential_id=credential.id, updated_by_user_id=inactive.id)
        user_id = _resolve_trigger_user_id(db, config, credential)
        assert user_id == fallback.id
    finally:
        db.close()


def test_resolve_trigger_user_id_raises_when_no_active_inaz_user_exists() -> None:
    inactive = _create_user("auto_sync_none_inactive", is_active=False)
    no_module = _create_user("auto_sync_none_no_module", module_presenze=False)
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, inactive, active=True)
        credential.application_user_id = no_module.id
        db.add(credential)
        db.commit()
        config = PresenzeAutoSyncConfig(id=1, job_enabled=True, credential_id=credential.id, updated_by_user_id=inactive.id)
        with pytest.raises(RuntimeError):
            _resolve_trigger_user_id(db, config, credential)
    finally:
        db.close()


def test_trigger_auto_sync_job_skips_when_disabled() -> None:
    db = TestingSessionLocal()
    try:
        assert trigger_auto_sync_job(db) is None
    finally:
        db.close()


def test_try_acquire_auto_sync_lock_is_noop_outside_postgresql() -> None:
    class FakeDialect:
        name = "sqlite"

    class FakeBind:
        dialect = FakeDialect()

    class FakeDb:
        def get_bind(self) -> FakeBind:
            return FakeBind()

        def execute(self, *_args, **_kwargs):
            raise AssertionError("non-PostgreSQL sessions must not execute advisory lock SQL")

    assert _try_acquire_auto_sync_lock(FakeDb()) is True


def test_try_acquire_auto_sync_lock_uses_postgresql_advisory_lock() -> None:
    class FakeDialect:
        name = "postgresql"

    class FakeBind:
        dialect = FakeDialect()

    class FakeResult:
        def scalar(self) -> bool:
            return False

    class FakeDb:
        params: dict[str, int] | None = None

        def get_bind(self) -> FakeBind:
            return FakeBind()

        def execute(self, _statement, params):
            self.params = params
            return FakeResult()

    db = FakeDb()

    assert _try_acquire_auto_sync_lock(db) is False
    assert db.params == {"lock_key": 760031001}


def test_commit_stale_changes_if_needed_only_commits_changed_state() -> None:
    class FakeDb:
        commits = 0

        def commit(self) -> None:
            self.commits += 1

    db = FakeDb()

    _commit_stale_changes_if_needed(db, False)
    _commit_stale_changes_if_needed(db, True)

    assert db.commits == 1


def test_reconcile_and_has_open_sync_job_reports_stale_changes_without_committing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user("auto_sync_open_probe")
    db = TestingSessionLocal()
    try:
        _create_auto_sync_job(db, user, _create_credential(db, user), status="pending")
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.reconcile_stale_sync_jobs", lambda current_db, commit: True)

        has_open_job, stale_changed = _reconcile_and_has_open_sync_job(db)

        assert has_open_job is True
        assert stale_changed is True
    finally:
        db.close()


def test_trigger_auto_sync_job_skips_when_lock_is_already_held(monkeypatch: pytest.MonkeyPatch) -> None:
    db = TestingSessionLocal()
    try:
        monkeypatch.setattr("app.modules.presenze.services.auto_sync._try_acquire_auto_sync_lock", lambda current_db: False)
        assert trigger_auto_sync_job(db) is None
        assert db.get(PresenzeAutoSyncConfig, 1) is None
    finally:
        db.close()


def test_trigger_auto_sync_job_skips_when_running_job_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _create_user("auto_sync_running")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=True)
        config = get_auto_sync_config(db)
        config.job_enabled = True
        config.credential_id = credential.id
        config.updated_by_user_id = user.id
        db.add(config)
        db.commit()
        monkeypatch.setattr("app.modules.presenze.services.auto_sync._reconcile_and_has_open_sync_job", lambda db: (True, False))
        assert trigger_auto_sync_job(db) is None
    finally:
        db.close()


def test_trigger_auto_sync_job_skips_when_credential_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _create_user("auto_sync_missing_runtime_cred")
    db = TestingSessionLocal()
    try:
        config = get_auto_sync_config(db)
        config.job_enabled = True
        config.credential_id = 9999
        config.updated_by_user_id = user.id
        db.add(config)
        db.commit()
        monkeypatch.setattr("app.modules.presenze.services.auto_sync._reconcile_and_has_open_sync_job", lambda db: (False, False))
        assert trigger_auto_sync_job(db) is None
    finally:
        db.close()


def test_trigger_auto_sync_job_skips_when_credential_inactive(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _create_user("auto_sync_inactive_runtime_cred")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=False)
        config = get_auto_sync_config(db)
        config.job_enabled = True
        config.credential_id = credential.id
        config.updated_by_user_id = user.id
        db.add(config)
        db.commit()
        monkeypatch.setattr("app.modules.presenze.services.auto_sync._reconcile_and_has_open_sync_job", lambda db: (False, False))
        assert trigger_auto_sync_job(db) is None
    finally:
        db.close()


def test_trigger_auto_sync_job_persists_failure_when_worker_launch_crashes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _ = tmp_path
    _ = monkeypatch
    # Auto sync no longer launches a subprocess from the backend; jobs stay queued.


def test_trigger_auto_sync_job_uses_current_month_and_creates_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _ = tmp_path
    user = _create_user("auto_sync_success_case")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=True)
        config = get_auto_sync_config(db)
        config.job_enabled = True
        config.credential_id = credential.id
        config.updated_by_user_id = user.id
        config.collaborator_limit = 7
        db.add(config)
        db.commit()

        monkeypatch.setattr("app.modules.presenze.services.auto_sync._reconcile_and_has_open_sync_job", lambda db: (False, False))
        fake_now = type(
            "FakeDateTime",
            (),
            {"now": staticmethod(lambda _tz=None: datetime(2026, 7, 3, 12, 0))},
        )
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.datetime", fake_now)
        retention_calls: list[Session] = []
        monkeypatch.setattr(
            "app.modules.presenze.services.auto_sync.apply_sync_job_retention",
            lambda current_db: retention_calls.append(current_db) or 0,
        )

        job = trigger_auto_sync_job(db)

        assert job is not None
        assert job.status == "pending"
        assert job.worker_pid is None
        assert job.collaborator_limit == 7
        assert job.params_json["trigger"] == "auto"
        assert job.params_json["auth_mode"] == "credential"
        assert job.params_json["target_scope"] == "current_month_only"
        assert job.params_json["target_months"] == ["2026-07"]
        assert Path(job.worker_log_path or "").name == "worker.log"
        assert Path(job.json_artifact_path or "").name == "presenze_collaboratori.json"
        assert job.period_start == date(2026, 7, 1)
        assert job.period_end == date(2026, 7, 31)
        assert retention_calls == [db]
    finally:
        db.close()


def test_trigger_auto_sync_job_includes_previous_month_at_first_daily_slot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _ = tmp_path
    user = _create_user("auto_sync_prev_month_case")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=True)
        config = get_auto_sync_config(db)
        config.job_enabled = True
        config.credential_id = credential.id
        config.updated_by_user_id = user.id
        db.add(config)
        db.commit()

        monkeypatch.setattr("app.modules.presenze.services.auto_sync._reconcile_and_has_open_sync_job", lambda db: (False, False))
        fake_now = type(
            "FakeDateTime",
            (),
            {"now": staticmethod(lambda _tz=None: datetime(2026, 7, 5, 6, 0))},
        )
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.datetime", fake_now)

        job = trigger_auto_sync_job(db)

        assert job is not None
        assert job.worker_pid is None
        assert job.params_json["target_scope"] == "previous_and_current_month"
        assert job.params_json["target_months"] == ["2026-06", "2026-07"]
        assert job.period_start == date(2026, 6, 1)
        assert job.period_end == date(2026, 7, 31)
    finally:
        db.close()


def test_trigger_auto_sync_job_creates_parallel_shards_for_active_collaborators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user("auto_sync_parallel_shards")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=True)
        _create_collaborators(db, 7)
        config = get_auto_sync_config(db)
        config.job_enabled = True
        config.credential_id = credential.id
        config.updated_by_user_id = user.id
        db.add(config)
        db.commit()

        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_parallel_enabled", True)
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_parallel_chunk_size", 3)
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_parallel_max_jobs", 3)
        fake_now = type(
            "FakeDateTime",
            (),
            {"now": staticmethod(lambda _tz=None: datetime(2026, 7, 3, 12, 0))},
        )
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.datetime", fake_now)

        first_job = trigger_auto_sync_job(db)

        assert first_job is not None
        jobs = db.execute(select(PresenzeSyncJob)).scalars().all()
        jobs = sorted(jobs, key=lambda job: job.params_json["shard_index"])
        assert len(jobs) == 3
        assert {job.status for job in jobs} == {"pending"}
        assert {job.params_json["sync_group_id"] for job in jobs}
        assert [len(job.params_json["employee_codes"]) for job in jobs] == [3, 3, 1]
        assert [job.params_json["shard_index"] for job in jobs] == [1, 2, 3]
        assert all(job.params_json["shard_count"] == 3 for job in jobs)
        assert all(job.params_json["target_scope"] == "current_month_only_shard" for job in jobs)
        queued_codes = [code for job in jobs for code in job.params_json["employee_codes"]]
        assert queued_codes == [f"{index:04d}" for index in range(1, 8)]
    finally:
        db.close()


def test_trigger_auto_sync_job_skips_employee_codes_already_open_for_same_period(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user("auto_sync_parallel_open_codes")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=True)
        _create_collaborators(db, 5)
        config = get_auto_sync_config(db)
        config.job_enabled = True
        config.credential_id = credential.id
        config.updated_by_user_id = user.id
        db.add(config)
        open_job = PresenzeSyncJob(
            status="running",
            requested_by_user_id=user.id,
            credential_id=credential.id,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
            params_json={"trigger": "auto", "employee_codes": ["0001", "0002"]},
        )
        db.add(open_job)
        db.commit()

        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_parallel_enabled", True)
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_parallel_chunk_size", 2)
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_parallel_max_jobs", 4)
        fake_now = type(
            "FakeDateTime",
            (),
            {"now": staticmethod(lambda _tz=None: datetime(2026, 7, 3, 12, 0))},
        )
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.datetime", fake_now)

        first_job = trigger_auto_sync_job(db)

        assert first_job is not None
        jobs = db.execute(select(PresenzeSyncJob).where(PresenzeSyncJob.id != open_job.id)).scalars().all()
        queued_codes = [code for job in jobs for code in job.params_json["employee_codes"]]
        assert queued_codes == ["0003", "0004", "0005"]
    finally:
        db.close()


def test_parallel_helpers_cover_duplicate_limit_and_non_shard_jobs() -> None:
    user = _create_user("auto_sync_parallel_helpers")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=True)
        db.add_all(
            [
                PresenzeCollaborator(employee_code="", company_code="53", name="Blank", is_active=True),
                PresenzeCollaborator(employee_code="0001", company_code="53", name="One", is_active=True),
                PresenzeCollaborator(employee_code="0001", company_code="54", name="One duplicate", is_active=True),
                PresenzeCollaborator(employee_code="0002", company_code="53", name="Two", is_active=True),
            ]
        )
        manual_job = PresenzeSyncJob(
            status="running",
            requested_by_user_id=user.id,
            credential_id=credential.id,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
            params_json={"trigger": "manual", "employee_codes": ["0001"]},
        )
        no_codes_job = PresenzeSyncJob(
            status="running",
            requested_by_user_id=user.id,
            credential_id=credential.id,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
            params_json={"trigger": "auto"},
        )
        db.add_all([manual_job, no_codes_job])
        db.commit()

        assert _active_employee_codes(db, limit=1) == ["0001"]
        assert _employee_codes_for_job(no_codes_job) == []
        assert (
            _open_employee_codes_for_period(
                db,
                credential_id=credential.id,
                period_start=date(2026, 7, 1),
                period_end=date(2026, 7, 31),
            )
            is None
        )
        manual_job.status = "completed"
        db.add(manual_job)
        db.commit()
        assert (
            _open_employee_codes_for_period(
                db,
                credential_id=credential.id,
                period_start=date(2026, 7, 1),
                period_end=date(2026, 7, 31),
            )
            is None
        )
    finally:
        db.close()


def test_trigger_auto_sync_job_returns_none_when_all_parallel_codes_are_already_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user("auto_sync_parallel_all_open")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=True)
        _create_collaborators(db, 2)
        config = get_auto_sync_config(db)
        config.job_enabled = True
        config.credential_id = credential.id
        config.updated_by_user_id = user.id
        open_job = PresenzeSyncJob(
            status="running",
            requested_by_user_id=user.id,
            credential_id=credential.id,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
            params_json={"trigger": "auto", "employee_codes": ["0001", "0002"]},
        )
        db.add_all([config, open_job])
        db.commit()

        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_parallel_enabled", True)
        fake_now = type(
            "FakeDateTime",
            (),
            {"now": staticmethod(lambda _tz=None: datetime(2026, 7, 3, 12, 0))},
        )
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.datetime", fake_now)

        assert trigger_auto_sync_job(db) is None
    finally:
        db.close()


def test_trigger_auto_sync_job_falls_back_to_serial_when_open_codes_are_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user("auto_sync_parallel_unknown_open_codes")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=True)
        config = get_auto_sync_config(db)
        config.job_enabled = True
        config.credential_id = credential.id
        config.updated_by_user_id = user.id
        db.add(config)
        db.commit()

        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_parallel_enabled", True)
        monkeypatch.setattr("app.modules.presenze.services.auto_sync._open_employee_codes_for_period", lambda *_args, **_kwargs: None)
        monkeypatch.setattr("app.modules.presenze.services.auto_sync._reconcile_and_has_open_sync_job", lambda _db: (False, False))
        fake_now = type(
            "FakeDateTime",
            (),
            {"now": staticmethod(lambda _tz=None: datetime(2026, 7, 3, 12, 0))},
        )
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.datetime", fake_now)

        job = trigger_auto_sync_job(db)

        assert job is not None
        assert job.params_json["trigger"] == "auto"
        assert "sync_group_id" not in job.params_json
    finally:
        db.close()


def test_trigger_auto_sync_job_defers_recent_failed_auto_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user("auto_sync_recent_failure")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=True)
        config = get_auto_sync_config(db)
        config.job_enabled = True
        config.credential_id = credential.id
        config.updated_by_user_id = user.id
        db.add(config)
        db.commit()
        failed_job = _create_auto_sync_job(db, user, credential, finished_at=datetime.now(UTC) - timedelta(hours=6))

        monkeypatch.setattr("app.modules.presenze.services.auto_sync._reconcile_and_has_open_sync_job", lambda db: (False, False))
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_retry_delay_hours", 12)
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_parallel_enabled", False)

        assert trigger_auto_sync_job(db) is None
        db.refresh(failed_job)
        assert failed_job.status == "failed"
        assert len(db.execute(select(PresenzeSyncJob)).scalars().all()) == 1
    finally:
        db.close()


def test_trigger_auto_sync_job_ignores_failed_duplicate_when_same_period_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user("auto_sync_superseded_failure")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=True)
        config = get_auto_sync_config(db)
        config.job_enabled = True
        config.credential_id = credential.id
        config.updated_by_user_id = user.id
        db.add(config)
        db.commit()
        completed = _create_auto_sync_job(
            db,
            user,
            credential,
            status="completed",
            created_at=datetime(2026, 7, 2, 9, 59, tzinfo=UTC),
            finished_at=datetime(2026, 7, 2, 16, 0, tzinfo=UTC),
        )
        failed_duplicate = _create_auto_sync_job(
            db,
            user,
            credential,
            status="failed",
            created_at=datetime(2026, 7, 2, 10, 0, tzinfo=UTC),
            finished_at=datetime(2026, 7, 3, 4, 0, tzinfo=UTC),
        )

        monkeypatch.setattr("app.modules.presenze.services.auto_sync._reconcile_and_has_open_sync_job", lambda db: (False, False))
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_retry_delay_hours", 12)
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_parallel_enabled", False)
        fake_now = type(
            "FakeDateTime",
            (),
            {"now": staticmethod(lambda _tz=None: datetime(2026, 7, 3, 12, 0, tzinfo=UTC))},
        )
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.datetime", fake_now)

        fresh_job = trigger_auto_sync_job(db)

        assert fresh_job is not None
        assert fresh_job.id not in {completed.id, failed_duplicate.id}
        assert fresh_job.status == "pending"
        assert fresh_job.params_json["trigger"] == "auto"
        db.refresh(failed_duplicate)
        assert failed_duplicate.status == "failed"
    finally:
        db.close()


@pytest.mark.parametrize(
    "existing_retry_history",
    [None, [{"previous_status": "failed"}]],
)
def test_trigger_auto_sync_job_requeues_failed_auto_sync_after_retry_delay(
    monkeypatch: pytest.MonkeyPatch,
    existing_retry_history: list[dict[str, str]] | None,
) -> None:
    user = _create_user("auto_sync_retry_due")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=True)
        config = get_auto_sync_config(db)
        config.job_enabled = True
        config.credential_id = credential.id
        config.updated_by_user_id = user.id
        db.add(config)
        db.commit()
        failed_job = _create_auto_sync_job(db, user, credential, finished_at=datetime.now(UTC) - timedelta(hours=13))
        if existing_retry_history is not None:
            failed_job.params_json = {
                **failed_job.params_json,
                "auto_retry_history": existing_retry_history,
            }
            db.add(failed_job)
            db.commit()

        monkeypatch.setattr("app.modules.presenze.services.auto_sync._reconcile_and_has_open_sync_job", lambda db: (False, False))
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_retry_delay_hours", 12)
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_parallel_enabled", False)

        retry_job = trigger_auto_sync_job(db)

        assert retry_job is not None
        assert retry_job.id == failed_job.id
        assert retry_job.status == "pending"
        assert retry_job.error_detail is None
        assert retry_job.started_at is None
        assert retry_job.finished_at is None
        assert retry_job.worker_pid is None
        assert retry_job.params_json["progress"]["state"] == "pending"
        assert retry_job.params_json["progress"]["last_event"] == "auto_retry_queued"
        assert "error" not in retry_job.params_json["progress"]
        retry_history = retry_job.params_json["auto_retry_history"][-1]
        assert retry_history["previous_status"] == "failed"
        assert retry_history["previous_started_at"] is not None
        assert retry_history["previous_finished_at"] is not None
        if existing_retry_history is not None:
            assert retry_job.params_json["auto_retry_history"][0] == existing_retry_history[0]
        assert len(db.execute(select(PresenzeSyncJob)).scalars().all()) == 1
    finally:
        db.close()


def test_trigger_auto_sync_job_creates_fresh_job_when_failed_auto_sync_exhausted_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user("auto_sync_retry_exhausted")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, user, active=True)
        config = get_auto_sync_config(db)
        config.job_enabled = True
        config.credential_id = credential.id
        config.updated_by_user_id = user.id
        db.add(config)
        db.commit()
        failed_job = _create_auto_sync_job(
            db,
            user,
            credential,
            finished_at=datetime.now(UTC) - timedelta(hours=13),
            attempt_count=3,
            max_attempts=3,
        )

        monkeypatch.setattr("app.modules.presenze.services.auto_sync._reconcile_and_has_open_sync_job", lambda db: (False, False))
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_retry_delay_hours", 12)
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_parallel_enabled", False)

        fresh_job = trigger_auto_sync_job(db)

        assert fresh_job is not None
        assert fresh_job.id != failed_job.id
        assert fresh_job.status == "pending"
        assert fresh_job.params_json["trigger"] == "auto"
        db.refresh(failed_job)
        assert failed_job.status == "failed"
        assert len(db.execute(select(PresenzeSyncJob)).scalars().all()) == 2
    finally:
        db.close()
