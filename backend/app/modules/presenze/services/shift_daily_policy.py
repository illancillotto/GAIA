"""Technician shifts follow INAZ theory; legacy shift profiles retain seven hours."""

from app.modules.presenze.services.personnel_profiles import TECHNICIAN_PROFILE, technician_profile


def shift_ordinary_limit(record):
    if technician_profile(record) is None:
        return 420
    minutes = getattr(record, "teo_minutes", None)
    return minutes if type(minutes) is int and 0 < minutes <= 1440 else None


def shift_countable_limit(record):
    limit = shift_ordinary_limit(record)
    return limit if limit is not None else 0


def shift_work_totals(record, punches):
    from app.modules.presenze.services.shift_worker_rules import (
        shift_expected_minutes,
        shift_punch_minutes,
    )

    worked = shift_punch_minutes(punches)
    if shift_expected_minutes(record, punches) == 0:
        return 0, 0, 0, 0
    limit = shift_ordinary_limit(record)
    if limit is None:
        worked = None
    ordinary = min(worked, limit) if worked is not None else None
    extra = max(0, worked - limit) if worked is not None else None
    return worked, ordinary, extra, shift_countable_limit(record)


def shift_voucher_worked_minutes(record):
    from app.modules.presenze.services.shift_worker_rules import (
        record_shift_punches,
        shift_punch_minutes,
    )

    worked = shift_punch_minutes(record_shift_punches(record)) or 0
    return min(worked, shift_countable_limit(record))


def shift_quality_values(record, punches):
    from app.modules.presenze.services.shift_worker_rules import (
        shift_covered_absence_minutes,
        shift_expected_minutes,
        shift_punch_minutes,
        shift_status,
        shift_worker_type,
    )

    kind = shift_worker_type(record)
    worked = shift_punch_minutes(punches)
    expected = shift_expected_minutes(record, punches)
    covered = min(expected or 0, shift_covered_absence_minutes(record))
    missing = max(0, (expected or 0) - (worked or 0) - covered)
    status = shift_status(punches, worked, missing) if expected is not None else "blocking"
    formula = "TURNISTA_INAZ" if kind == TECHNICIAN_PROFILE else "TURNISTA_7H"
    notes = shift_operational_notes(record, kind, worked, expected)
    return dict(
        status=status,
        formula_code=formula,
        expected_minutes=expected,
        worked_minutes=worked,
        missing_minutes=missing,
        mpe_minutes=max(0, (worked or 0) - (expected or 0)),
        notes=tuple(notes),
    )


def shift_operational_notes(record, kind, worked, expected):
    from app.modules.presenze.services.shift_worker_rules import (
        shift_punch_notes,
        shift_voucher_travel_review,
    )

    notes = [
        f"Turnista {kind}: teorico INAZ {expected} minuti"
        if kind == TECHNICIAN_PROFILE
        else f"Turnista {kind}: 7 ore per turno, orari da timbrature INAZ"
    ]
    notes.extend(shift_punch_notes(worked, expected == 0))
    if expected is None:
        notes.append("Teorico INAZ mancante: calcolo turno da verificare")
    if record.work_date.isoformat() >= "2026-09-07":
        notes.append("Nessuna flessibilita in ingresso per i turnisti (accordo art. 7)")
    if shift_voucher_travel_review(record):
        notes.append("Buono da verificare: accertare rimborso vitto in trasferta (accordo art. 5)")
    return notes
