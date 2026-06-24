from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.inaz.models import InazBankHoursGuidanceConfig, InazBankHoursGuidanceConfigRevision
from app.modules.inaz.schemas import InazBankHoursGuidanceConfigResponse, InazBankHoursGuidanceConfigRevisionResponse, InazBankHoursGuidanceConfigUpdate


def get_bank_hours_guidance_config(db: Session) -> InazBankHoursGuidanceConfig:
    config = db.get(InazBankHoursGuidanceConfig, 1)
    if config is not None:
        return config

    config = InazBankHoursGuidanceConfig(
        id=1,
        allow_derived_profile=settings.inaz_bank_hours_guidance_allow_derived_profile,
        include_overtime_day=settings.inaz_bank_hours_guidance_include_overtime_day,
        include_overtime_night=settings.inaz_bank_hours_guidance_include_overtime_night,
        include_overtime_festive=settings.inaz_bank_hours_guidance_include_overtime_festive,
        include_overtime_festive_night=settings.inaz_bank_hours_guidance_include_overtime_festive_night,
        min_suggested_minutes=settings.inaz_bank_hours_guidance_min_suggested_minutes,
    )
    db.add(config)
    db.flush()
    return config


def _user_label(user: ApplicationUser | None) -> str | None:
    if user is None:
        return None
    return user.full_name or user.username


def serialize_bank_hours_guidance_config_with_user(
    db: Session,
    config: InazBankHoursGuidanceConfig,
) -> InazBankHoursGuidanceConfigResponse:
    return InazBankHoursGuidanceConfigResponse(
        allow_derived_profile=config.allow_derived_profile,
        include_overtime_day=config.include_overtime_day,
        include_overtime_night=config.include_overtime_night,
        include_overtime_festive=config.include_overtime_festive,
        include_overtime_festive_night=config.include_overtime_festive_night,
        min_suggested_minutes=config.min_suggested_minutes,
        updated_at=config.updated_at,
        updated_by_user_id=config.updated_by_user_id,
        updated_by_label=_user_label(db.get(ApplicationUser, config.updated_by_user_id)) if config.updated_by_user_id is not None else None,
    )


def serialize_bank_hours_guidance_revision(
    db: Session,
    revision: InazBankHoursGuidanceConfigRevision,
) -> InazBankHoursGuidanceConfigRevisionResponse:
    return InazBankHoursGuidanceConfigRevisionResponse(
        id=revision.id,
        allow_derived_profile=revision.allow_derived_profile,
        include_overtime_day=revision.include_overtime_day,
        include_overtime_night=revision.include_overtime_night,
        include_overtime_festive=revision.include_overtime_festive,
        include_overtime_festive_night=revision.include_overtime_festive_night,
        min_suggested_minutes=revision.min_suggested_minutes,
        changed_at=revision.changed_at,
        changed_by_user_id=revision.changed_by_user_id,
        changed_by_label=_user_label(db.get(ApplicationUser, revision.changed_by_user_id)) if revision.changed_by_user_id is not None else None,
    )


def list_bank_hours_guidance_config_revisions(db: Session) -> list[InazBankHoursGuidanceConfigRevision]:
    return (
        db.query(InazBankHoursGuidanceConfigRevision)
        .order_by(
            InazBankHoursGuidanceConfigRevision.changed_at.desc(),
            InazBankHoursGuidanceConfigRevision.id.desc(),
        )
        .all()
    )


def update_bank_hours_guidance_config(
    db: Session,
    payload: InazBankHoursGuidanceConfigUpdate,
    *,
    user_id: int,
) -> InazBankHoursGuidanceConfig:
    config = get_bank_hours_guidance_config(db)
    fields = payload.model_fields_set
    changed = False

    if "allow_derived_profile" in fields and payload.allow_derived_profile is not None:
        next_value = bool(payload.allow_derived_profile)
        changed = changed or config.allow_derived_profile != next_value
        config.allow_derived_profile = next_value
    if "include_overtime_day" in fields and payload.include_overtime_day is not None:
        next_value = bool(payload.include_overtime_day)
        changed = changed or config.include_overtime_day != next_value
        config.include_overtime_day = next_value
    if "include_overtime_night" in fields and payload.include_overtime_night is not None:
        next_value = bool(payload.include_overtime_night)
        changed = changed or config.include_overtime_night != next_value
        config.include_overtime_night = next_value
    if "include_overtime_festive" in fields and payload.include_overtime_festive is not None:
        next_value = bool(payload.include_overtime_festive)
        changed = changed or config.include_overtime_festive != next_value
        config.include_overtime_festive = next_value
    if "include_overtime_festive_night" in fields and payload.include_overtime_festive_night is not None:
        next_value = bool(payload.include_overtime_festive_night)
        changed = changed or config.include_overtime_festive_night != next_value
        config.include_overtime_festive_night = next_value
    if "min_suggested_minutes" in fields and payload.min_suggested_minutes is not None:
        changed = changed or config.min_suggested_minutes != payload.min_suggested_minutes
        config.min_suggested_minutes = payload.min_suggested_minutes

    if not changed:
        return config

    config.updated_at = datetime.now(UTC)
    config.updated_by_user_id = user_id
    db.add(config)
    db.flush()
    db.add(
        InazBankHoursGuidanceConfigRevision(
            config_id=config.id,
            allow_derived_profile=config.allow_derived_profile,
            include_overtime_day=config.include_overtime_day,
            include_overtime_night=config.include_overtime_night,
            include_overtime_festive=config.include_overtime_festive,
            include_overtime_festive_night=config.include_overtime_festive_night,
            min_suggested_minutes=config.min_suggested_minutes,
            changed_at=config.updated_at,
            changed_by_user_id=user_id,
        )
    )
    db.commit()
    db.refresh(config)
    return config
