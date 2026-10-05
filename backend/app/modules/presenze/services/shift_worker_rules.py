"""Seven-hour shift rules: no fixed start time or unpaid break is inferred."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import object_session

from app.modules.presenze.models import PresenzeDailyPunch, PresenzeDailyRecord
from app.modules.presenze.services.inaz_absences import covered_inaz_absence_minutes
from app.modules.presenze.services.shift_assignments import shift_assignment_values
from app.modules.presenze.services.shift_ccnl import shift_ccnl_assessment, shift_ccnl_breakdown

SHIFT_WORKER_TYPES = {"acquaiolo", "telecontrollo"}
SHIFT_EXPECTED_MINUTES = 420
REST_CODES = {"SAB", "DOM", "RIPTURN", "SMONTO"}


def shift_worker_type(record):
    value = shift_assignment_values(record)["shift_worker_type"]
    return value if value in SHIFT_WORKER_TYPES else None


def shift_punch_intervals(punches):
    if not punches:
        return None
    intervals = []
    for punch in punches:
        interval = _shift_punch_interval(punch, intervals)
        if interval is None:
            return None
        intervals.append(interval)
    return intervals


def _shift_punch_interval(punch, previous):
    if punch.entry_time is None or punch.exit_time is None:
        return None
    start = punch.entry_time.hour * 60 + punch.entry_time.minute
    end = punch.exit_time.hour * 60 + punch.exit_time.minute
    if end == start:
        return None
    if end < start:
        end += 1440
    if previous and start < previous[0][0]:
        start += 1440
        end += 1440
    if previous and (start < previous[-1][1] or end > previous[0][0] + 1440):
        return None
    return start, end


def shift_punch_minutes(punches):
    intervals = shift_punch_intervals(punches)
    return sum(end - start for start, end in intervals) if intervals is not None else None


def record_shift_punches(record):
    db = object_session(record) if isinstance(record, PresenzeDailyRecord) else None
    if db is None:
        return getattr(record, "shift_punches", [])
    return db.scalars(
        select(PresenzeDailyPunch)
        .where(PresenzeDailyPunch.daily_record_id == record.id)
        .order_by(PresenzeDailyPunch.sequence)
    ).all()


def shift_meal_voucher(record):
    return (
        shift_worker_type(record) is not None
        and record.work_date >= date(2026, 8, 26)
        and (shift_punch_minutes(record_shift_punches(record)) or 0) >= SHIFT_EXPECTED_MINUTES
        and not shift_voucher_travel_review(record)
    )


def shift_voucher_travel_review(record):
    return bool(
        getattr(record, "trasferta_minutes", 0) or getattr(record, "trasferta_montano", False)
    )


def shift_quality(record, punches):
    from app.modules.presenze.services.operational_quality import OperaiOperationalQuality

    kind = shift_worker_type(record)
    worked = shift_punch_minutes(punches)
    expected = shift_expected_minutes(record, punches)
    rest = expected == 0
    covered = min(expected, shift_covered_absence_minutes(record))
    missing = max(0, expected - (worked or 0) - covered)
    status = shift_status(punches, worked, missing)
    notes = [f"Turnista {kind}: 7 ore per turno, orari da timbrature INAZ"]
    notes.extend(shift_punch_notes(worked, rest))
    if record.work_date >= date(2026, 9, 7):
        notes.append("Nessuna flessibilita in ingresso per i turnisti (accordo art. 7)")
    if shift_voucher_travel_review(record):
        notes.append("Buono da verificare: accertare rimborso vitto in trasferta (accordo art. 5)")
    return OperaiOperationalQuality(
        status=status,
        formula_code="TURNISTA_7H",
        expected_minutes=expected,
        worked_minutes=worked,
        missing_minutes=missing,
        mpe_minutes=max(0, (worked or 0) - expected),
        notes=tuple(notes),
    )


def shift_classification(
    record, punches, *, special_day, holiday_kind, grants_recovery_day, calendar=None
):
    from app.modules.presenze.services.day_classification import DayClassification

    worked = shift_punch_minutes(punches)
    if shift_expected_minutes(record, punches) == 0:
        worked = 0
    ordinary = min(worked, SHIFT_EXPECTED_MINUTES) if worked is not None else None
    extra = max(0, worked - SHIFT_EXPECTED_MINUTES) if worked is not None else None
    intervals = shift_punch_intervals(punches) or []
    days = calendar if calendar is not None else [special_day, special_day]
    counts = shift_ccnl_breakdown(intervals, days, SHIFT_EXPECTED_MINUTES)
    (
        _day,
        festive,
        night,
        festive_night,
        extra_day,
        extra_festive,
        extra_night,
        extra_festive_night,
    ) = counts
    return DayClassification(
        special_day=days[0],
        ordinary_minutes=ordinary,
        extra_minutes=extra,
        holiday_kind=holiday_kind,
        grants_recovery_day=grants_recovery_day,
        source="shift-ccnl-v2",
        night_minutes=night + festive_night + extra_night + extra_festive_night,
        festive_minutes=festive + extra_festive,
        festive_night_minutes=festive_night + extra_festive_night,
        ordinary_night_minutes=night,
        overtime_day_minutes=extra_day,
        overtime_night_minutes=extra_night,
        overtime_festive_minutes=extra_festive,
        overtime_festive_night_minutes=extra_festive_night,
        shift_night_minutes=night,
        shift_festive_day_minutes=festive,
        shift_festive_night_minutes=festive_night,
        shift_calendar=days if calendar is not None else None,
        shift_ccnl=shift_ccnl_assessment(counts, calendar is not None)
        if worked is not None
        else None,
    )


def shift_covered_absence_minutes(record):
    return covered_inaz_absence_minutes(record, ("ferie", "permesso"), SHIFT_EXPECTED_MINUTES)


def shift_record_values(record):
    """Assignment and absence diagnostics shared by daily API and GATE snapshots."""
    return {
        **shift_assignment_values(record),
        "shift_covered_absence_minutes": shift_covered_absence_minutes(record)
        if isinstance(record, PresenzeDailyRecord)
        else 0,
    }


def shift_expected_minutes(record, punches):
    return (
        0
        if not punches and (record.schedule_code or "").upper() in REST_CODES
        else SHIFT_EXPECTED_MINUTES
    )


def shift_status(punches, worked, missing):
    return "blocking" if missing or (punches and worked is None) else "ok"


def shift_punch_notes(worked, rest):
    return (
        ["Timbrature complete non disponibili: turno da verificare"]
        if worked is None and not rest
        else []
    )


def daily_quality_kind(collaborator, record):
    if shift_worker_type(record):
        return "shift"
    if collaborator is None or collaborator.contract_kind == "operaio":
        return "operaio"
    return "other"
