from __future__ import annotations

from collections.abc import Generator
from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.presenze.models import PresenzeAutoSyncConfig, PresenzeCredential, PresenzeSyncJob
from app.modules.presenze.schemas import PresenzeAutoSyncConfigUpdate
from app.modules.presenze.services.auto_sync import (
    PRESENZE_PREVIOUS_MONTH_SYNC_CUTOFF_DAY,
    _resolve_auto_sync_period,
    _resolve_trigger_user_id,
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
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.has_running_sync_job", lambda db: True)
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
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.has_running_sync_job", lambda db: False)
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
        monkeypatch.setattr("app.modules.presenze.services.auto_sync.has_running_sync_job", lambda db: False)
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

        monkeypatch.setattr("app.modules.presenze.services.auto_sync.has_running_sync_job", lambda db: False)
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

        monkeypatch.setattr("app.modules.presenze.services.auto_sync.has_running_sync_job", lambda db: False)
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
