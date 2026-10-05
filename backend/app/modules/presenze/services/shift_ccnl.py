"""CCNL Bonifica artt. 47/49/80/83/137: dated buckets, never inferred payroll."""

SHIFT_CCNL_VERSION = "bonifica-2023-2026-v1"
SHIFT_CCNL_BUCKETS = (
    "ordinary_day",
    "ordinary_festive_day",
    "ordinary_night",
    "ordinary_festive_night",
    "overtime_day",
    "overtime_festive_day",
    "overtime_night",
    "overtime_festive_night",
)
SHIFT_CCNL_RATES = {
    "title_ii": {"articles": [80, 83], "percentages": [0, 10, 15, 20, 25, 50, 50, 75]},
    "avventizio": {"articles": [137], "percentages": [0, 39, 10, 15, 25, 50, 38, 66]},
}


def shift_ccnl_breakdown(intervals, calendar, ordinary_limit):
    counts = [0] * 8
    worked = 0
    for start, end in intervals:
        for minute in range(start, end):
            night = minute % 1440 < 360 or minute % 1440 >= 1320
            festive = calendar[minute // 1440]
            index = int(worked >= ordinary_limit) * 4 + int(night) * 2 + int(festive)
            counts[index] += 1
            worked += 1
    return counts


def shift_ccnl_assessment(counts, calendar_attested):
    return {
        "version": SHIFT_CCNL_VERSION,
        "calendar_attested": calendar_attested,
        "premium_minutes": dict(zip(SHIFT_CCNL_BUCKETS, counts, strict=True)),
        "rate_candidates": SHIFT_CCNL_RATES,
        "payroll_status": "requires_hr_regime_and_overtime_authorization",
        "ordinary_minutes_source": "company_shift_duration",
        "overtime_requires_prior_authorization": True,
    }


def shift_classification_values(classification, prefix=""):
    """Export CCNL provenance only when the two-day calendar was resolved."""
    if getattr(classification, "shift_calendar", None) is None:
        return {}
    return {
        f"{prefix}shift_calendar": classification.shift_calendar,
        "shift_ccnl": classification.shift_ccnl,
        "shift_rules_version": classification.source,
    }


def shift_calendar(work_date, collaborator, context):
    from datetime import timedelta

    from app.modules.presenze.services.schedule_engine import resolve_holiday

    days = [work_date, work_date + timedelta(days=1)]
    holidays = [resolve_holiday(day, collaborator, context) for day in days]
    # Art. 47: Saturday alone is never a holiday; art. 83 includes Sunday.
    return [
        day.weekday() == 6 or (holiday is not None and holiday.holiday_kind == "ordinary")
        for day, holiday in zip(days, holidays, strict=True)
    ]
