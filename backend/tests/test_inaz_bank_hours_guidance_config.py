from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.datetime_compat import UTC
from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.inaz.models import InazBankHoursGuidanceConfig, InazBankHoursGuidanceConfigRevision
from app.modules.inaz.schemas import InazBankHoursGuidanceConfigUpdate
from app.modules.inaz.services.bank_hours_guidance_config import (
    get_bank_hours_guidance_config,
    list_bank_hours_guidance_config_revisions,
    serialize_bank_hours_guidance_config_with_user,
    serialize_bank_hours_guidance_revision,
    update_bank_hours_guidance_config,
)


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _create_user(username: str, *, full_name: str | None = None) -> ApplicationUser:
    db = TestingSessionLocal()
    try:
        user = ApplicationUser(
            username=username,
            email=f"{username}@example.local",
            full_name=full_name,
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


def test_get_bank_hours_guidance_config_creates_default_row() -> None:
    db = TestingSessionLocal()
    try:
        config = get_bank_hours_guidance_config(db)
        assert config.id == 1
        assert db.get(InazBankHoursGuidanceConfig, 1) is not None
    finally:
        db.close()


def test_serialize_bank_hours_guidance_config_uses_full_name_when_available() -> None:
    user = _create_user("guidance_full_name", full_name="Mario Rossi")
    db = TestingSessionLocal()
    try:
        config = get_bank_hours_guidance_config(db)
        config.updated_by_user_id = user.id
        config.updated_at = datetime.now(UTC)
        db.add(config)
        db.commit()

        payload = serialize_bank_hours_guidance_config_with_user(db, config)
        assert payload.updated_by_label == "Mario Rossi"
    finally:
        db.close()


def test_serialize_bank_hours_guidance_config_returns_none_for_missing_user() -> None:
    db = TestingSessionLocal()
    try:
        config = get_bank_hours_guidance_config(db)
        config.updated_by_user_id = 999999
        config.updated_at = datetime.now(UTC)
        db.add(config)
        db.commit()

        payload = serialize_bank_hours_guidance_config_with_user(db, config)
        assert payload.updated_by_label is None
    finally:
        db.close()


def test_serialize_bank_hours_guidance_revision_falls_back_to_username() -> None:
    user = _create_user("guidance_username_only")
    db = TestingSessionLocal()
    try:
        revision = InazBankHoursGuidanceConfigRevision(
            config_id=1,
            allow_derived_profile=False,
            include_overtime_day=True,
            include_overtime_night=True,
            include_overtime_festive=True,
            include_overtime_festive_night=True,
            min_suggested_minutes=60,
            changed_at=datetime.now(UTC),
            changed_by_user_id=user.id,
        )
        db.add(InazBankHoursGuidanceConfig(id=1))
        db.add(revision)
        db.commit()
        db.refresh(revision)

        payload = serialize_bank_hours_guidance_revision(db, revision)
        assert payload.changed_by_label == user.username
    finally:
        db.close()


def test_list_bank_hours_guidance_config_revisions_returns_newest_first() -> None:
    db = TestingSessionLocal()
    try:
        config = get_bank_hours_guidance_config(db)
        older = InazBankHoursGuidanceConfigRevision(
            config_id=config.id,
            allow_derived_profile=False,
            include_overtime_day=True,
            include_overtime_night=True,
            include_overtime_festive=True,
            include_overtime_festive_night=True,
            min_suggested_minutes=30,
            changed_at=datetime.now(UTC) - timedelta(days=1),
        )
        newer = InazBankHoursGuidanceConfigRevision(
            config_id=config.id,
            allow_derived_profile=True,
            include_overtime_day=False,
            include_overtime_night=True,
            include_overtime_festive=False,
            include_overtime_festive_night=True,
            min_suggested_minutes=90,
            changed_at=datetime.now(UTC),
        )
        db.add_all([older, newer])
        db.commit()

        revisions = list_bank_hours_guidance_config_revisions(db)
        assert [item.min_suggested_minutes for item in revisions] == [90, 30]
    finally:
        db.close()


def test_update_bank_hours_guidance_config_noop_does_not_create_revision() -> None:
    user = _create_user("guidance_noop")
    db = TestingSessionLocal()
    try:
        config = get_bank_hours_guidance_config(db)
        config.updated_at = None
        config.updated_by_user_id = None
        db.add(config)
        db.commit()

        result = update_bank_hours_guidance_config(
            db,
            InazBankHoursGuidanceConfigUpdate(),
            user_id=user.id,
        )

        assert result.id == config.id
        assert result.updated_at is None
        assert result.updated_by_user_id is None
        assert db.query(InazBankHoursGuidanceConfigRevision).count() == 0
    finally:
        db.close()


def test_update_bank_hours_guidance_config_creates_revision_for_real_change() -> None:
    user = _create_user("guidance_editor")
    db = TestingSessionLocal()
    try:
        config = update_bank_hours_guidance_config(
            db,
            InazBankHoursGuidanceConfigUpdate(
                allow_derived_profile=True,
                include_overtime_day=False,
                include_overtime_night=False,
                include_overtime_festive=False,
                include_overtime_festive_night=False,
                min_suggested_minutes=15,
            ),
            user_id=user.id,
        )

        assert config.allow_derived_profile is True
        assert config.include_overtime_day is False
        assert config.include_overtime_night is False
        assert config.include_overtime_festive is False
        assert config.include_overtime_festive_night is False
        assert config.min_suggested_minutes == 15
        assert config.updated_by_user_id == user.id
        assert config.updated_at is not None

        revisions = db.query(InazBankHoursGuidanceConfigRevision).all()
        assert len(revisions) == 1
        assert revisions[0].changed_by_user_id == user.id
        assert revisions[0].min_suggested_minutes == 15
    finally:
        db.close()
