"""Presence prerequisite for manual benefits; never an entitlement calculation."""

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.presenze.models import PresenzeDailyPunch, PresenzeDailyRecord


def lock_for_manual_benefit(
    db: Session, record: PresenzeDailyRecord, *, require_punch: bool
) -> PresenzeDailyRecord:
    """Reload the day under lock before checking punches or changing a benefit."""
    locked = db.scalars(
        select(PresenzeDailyRecord)
        .where(PresenzeDailyRecord.id == record.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    if require_punch:
        _require_punch(db, locked)
    return locked


def _require_punch(db: Session, record: PresenzeDailyRecord) -> None:
    present = db.scalar(
        select(PresenzeDailyPunch.id)
        .where(
            PresenzeDailyPunch.daily_record_id == record.id,
            or_(
                PresenzeDailyPunch.entry_time.is_not(None),
                PresenzeDailyPunch.exit_time.is_not(None),
            ),
        )
        .limit(1)
    )
    if present is None:
        raise HTTPException(
            status_code=422,
            detail="Buoni pasto e KM richiedono almeno una timbratura. "
            "È sempre possibile cancellare i valori errati.",
        )


def validate_manual_km(db: Session, record: PresenzeDailyRecord, value: int | None) -> None:
    if value is not None and value > 0:
        lock_for_manual_benefit(db, record, require_punch=True)
