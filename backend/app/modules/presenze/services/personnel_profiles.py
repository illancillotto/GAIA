"""Resolve an attested personnel profile for the date of a daily record."""

from sqlalchemy import select
from sqlalchemy.orm import object_session

from app.modules.presenze.models import PresenzeDailyRecord
from app.modules.presenze.personnel_profile_models import PresenzePersonnelProfile

TECHNICIAN_PROFILE = "tecnico_turnista"


def personnel_profile(record):
    db = object_session(record) if isinstance(record, PresenzeDailyRecord) else None
    if db is None:
        profile = getattr(record, "personnel_profile", None)
        return (
            profile
            if profile is not None and profile_covers_date(profile, record.work_date)
            else None
        )
    cache = db.info.setdefault("presenze_personnel_profiles", {})
    if record.collaborator_id not in cache:
        cache[record.collaborator_id] = db.scalars(
            select(PresenzePersonnelProfile).where(
                PresenzePersonnelProfile.collaborator_id == record.collaborator_id
            )
        ).all()
    matching = [
        row for row in cache[record.collaborator_id] if profile_covers_date(row, record.work_date)
    ]
    return max(matching, key=lambda row: row.valid_from, default=None)


def personnel_profile_values(record):
    profile = personnel_profile(record)
    if profile is None:
        return {}
    return {
        "profile_type": profile.profile_type,
        "profile_label": profile.profile_label,
        "personnel_shift_schedule_codes": profile.shift_schedule_codes,
        "duty": profile.duty,
        "employment_relationship": profile.employment_relationship,
        "personnel_area": profile.personnel_area,
        "personnel_supervisor_gaia_user_id": str(profile.supervisor_user_id),
        "personnel_profile_valid_from": profile.valid_from.isoformat(),
        "personnel_profile_valid_to": profile.valid_to.isoformat() if profile.valid_to else None,
        "personnel_profile_source_sha256": profile.source_document_sha256,
    }


def technician_profile(record):
    profile = personnel_profile(record)
    return (
        profile
        if profile is not None
        and profile.profile_type == TECHNICIAN_PROFILE
        and profile.personnel_area == "IMPIANTI"
        else None
    )


def profile_covers_date(profile, work_date):
    return profile.valid_from <= work_date and (
        profile.valid_to is None or work_date <= profile.valid_to
    )


def technician_shift_type(record, assignment):
    profile = technician_profile(record)
    if profile is None:
        return (
            "none"
            if assignment["shift_worker_type"] == TECHNICIAN_PROFILE
            else assignment["shift_worker_type"]
        )
    if (record.schedule_code or "").upper() not in profile.shift_schedule_codes:
        return "none"
    if assignment["shift_worker_source"] is not None and assignment["shift_worker_type"] == "none":
        return "none"
    return TECHNICIAN_PROFILE
