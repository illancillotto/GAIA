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
from app.modules.presenze.models import PresenzeAutoSyncConfig, PresenzeCredential, PresenzeSyncJob
from app.modules.presenze.schemas import PresenzeAutoSyncConfigUpdate
from app.modules.presenze.services.auto_sync import (
    PRESENZE_PREVIOUS_MONTH_SYNC_CUTOFF_DAY,
    _commit_stale_changes_if_needed,
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
    finished_at: datetime | None = None,
    attempt_count: int = 1,
    max_attempts: int = 3,
) -> PresenzeSyncJob:
    created_at = (finished_at - timedelta(hours=1)) if finished_at is not None else datetime.now(UTC)
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
        created_at=created_at,
        started_at=created_at,
        finished_at=finished_at,
        worker_pid=1,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


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

        assert trigger_auto_sync_job(db) is None
        db.refresh(failed_job)
        assert failed_job.status == "failed"
        assert len(db.execute(select(PresenzeSyncJob)).scalars().all()) == 1
    finally:
        db.close()


def test_trigger_auto_sync_job_requeues_failed_auto_sync_after_retry_delay(
    monkeypatch: pytest.MonkeyPatch,
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

        monkeypatch.setattr("app.modules.presenze.services.auto_sync._reconcile_and_has_open_sync_job", lambda db: (False, False))
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.settings.presenze_auto_sync_retry_delay_hours", 12)

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
        assert retry_job.params_json["auto_retry_history"][-1]["previous_status"] == "failed"
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
