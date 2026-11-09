"""Resolve a dated contract without changing canonical identities or shift profiles."""

from sqlalchemy import select
from sqlalchemy.orm import object_session

from app.modules.presenze.employment_models import PresenzeEmploymentPeriod
from app.modules.presenze.models import PresenzeDailyRecord
from app.modules.presenze.services.personnel_profiles import personnel_profile


def employment_period_values(record):
    db = object_session(record) if isinstance(record, PresenzeDailyRecord) else None
    periods = getattr(record, "employment_periods", ())
    if db is not None:
        cache = db.info.setdefault("presenze_employment_periods", {})
        if record.collaborator_id not in cache:
            cache[record.collaborator_id] = db.scalars(
                select(PresenzeEmploymentPeriod).where(
                    PresenzeEmploymentPeriod.collaborator_id == record.collaborator_id
                )
            ).all()
        periods = cache[record.collaborator_id]
    matching = [p for p in periods if p.valid_from <= record.work_date <= p.valid_to]
    if matching:
        period = max(matching, key=lambda p: p.valid_from)
        return {
            "employment_relationship": period.employment_relationship,
            "employment_valid_from": period.valid_from.isoformat(),
            "employment_valid_to": period.valid_to.isoformat(),
            "employment_source_sha256": period.source_document_sha256,
        }
    # Once dated contracts exist, an old open-ended shift profile cannot extend them.
    if periods:
        return {"employment_relationship": None}
    profile = personnel_profile(record)
    return {"employment_relationship": profile.employment_relationship} if profile else {}
