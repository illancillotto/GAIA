from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.presenze.models import (
    PRESENZE_HOLIDAY_KIND_ORDINARY,
    PRESENZE_HOLIDAY_KIND_SUPPRESSED,
    PresenzeCollaborator,
    PresenzeCollaboratorScheduleAssignment,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
    PresenzeHoliday,
    PresenzeScheduleRule,
    PresenzeScheduleTemplate,
)
from app.modules.presenze.services.parser import detail_has_authoritative_classification, detail_indicates_special_day
from app.modules.presenze.services.operational_quality import build_operai_operational_quality

RECURRENCE_WEEKLY = "weekly"
RECURRENCE_FIRST_WEEKDAY = "first_weekday_of_month"
RECURRENCE_NTH_WEEKDAY = "nth_weekday_of_month"
RECURRENCE_ALTERNATING = "alternating_weeks"


@dataclass(frozen=True)
class DayClassification:
    special_day: bool
    ordinary_minutes: int | None
    extra_minutes: int | None
    holiday_kind: str | None
    grants_recovery_day: bool
    source: str
    night_minutes: int = 0
    festive_minutes: int = 0
    festive_night_minutes: int = 0
    ordinary_night_minutes: int = 0
    overtime_day_minutes: int = 0
    overtime_night_minutes: int = 0
    overtime_festive_minutes: int = 0
    overtime_festive_night_minutes: int = 0
    shift_festive_day_minutes: int = 0
    shift_night_minutes: int = 0
    shift_festive_night_minutes: int = 0


@dataclass(frozen=True)
class WorkedMinuteBuckets:
    actual_minutes: int
    ordinary_minutes: int
    extra_minutes: int
    night_minutes: int
    festive_minutes: int
    festive_night_minutes: int
    ordinary_night_minutes: int
    overtime_day_minutes: int
    overtime_night_minutes: int
    overtime_festive_minutes: int
    overtime_festive_night_minutes: int
    shift_festive_day_minutes: int
    shift_night_minutes: int
    shift_festive_night_minutes: int


@dataclass
class ScheduleContext:
    holidays_by_key: dict[tuple[date, str | None], list[PresenzeHoliday]]
    assignments_by_collaborator: dict[str, list[PresenzeCollaboratorScheduleAssignment]]
    templates_by_id: dict[int, PresenzeScheduleTemplate]
    rules_by_template_id: dict[int, list[PresenzeScheduleRule]]


def build_schedule_context(
    db: Session,
    *,
    collaborator_ids: list[uuid.UUID],
    date_from: date,
    date_to: date,
) -> ScheduleContext:
    holiday_rows = db.execute(
        select(PresenzeHoliday).where(PresenzeHoliday.holiday_date >= date_from, PresenzeHoliday.holiday_date <= date_to)
    ).scalars().all()
    assignments = db.execute(
        select(PresenzeCollaboratorScheduleAssignment).where(
            PresenzeCollaboratorScheduleAssignment.collaborator_id.in_(collaborator_ids)
        )
    ).scalars().all()
    template_ids = sorted({item.template_id for item in assignments})
    templates = []
    rules = []
    if template_ids:
        templates = db.execute(select(PresenzeScheduleTemplate).where(PresenzeScheduleTemplate.id.in_(template_ids))).scalars().all()
        rules = db.execute(select(PresenzeScheduleRule).where(PresenzeScheduleRule.template_id.in_(template_ids))).scalars().all()

    holidays_by_key: dict[tuple[date, str | None], list[PresenzeHoliday]] = {}
    for row in holiday_rows:
        holidays_by_key.setdefault((row.holiday_date, row.company_code), []).append(row)

    assignments_by_collaborator: dict[str, list[PresenzeCollaboratorScheduleAssignment]] = {}
    for row in assignments:
        assignments_by_collaborator.setdefault(str(row.collaborator_id), []).append(row)
    for rows in assignments_by_collaborator.values():
        rows.sort(key=lambda item: (item.valid_from or date.min, item.id), reverse=True)

    rules_by_template_id: dict[int, list[PresenzeScheduleRule]] = {}
    for row in rules:
        rules_by_template_id.setdefault(row.template_id, []).append(row)
    for template_rules in rules_by_template_id.values():
        template_rules.sort(key=lambda item: (item.sort_order, item.id))

    return ScheduleContext(
        holidays_by_key=holidays_by_key,
        assignments_by_collaborator=assignments_by_collaborator,
        templates_by_id={item.id: item for item in templates},
        rules_by_template_id=rules_by_template_id,
    )


def classify_daily_record(
    collaborator: PresenzeCollaborator,
    record: PresenzeDailyRecord,
    punches: list[PresenzeDailyPunch],
    context: ScheduleContext | None,
) -> DayClassification:
    holiday = resolve_holiday(record.work_date, collaborator, context)
    holiday_kind = holiday.holiday_kind if holiday is not None else None
    raw_payload = record.raw_payload_json if isinstance(record.raw_payload_json, dict) else None
    imported_special_day = raw_payload is not None and detail_indicates_special_day(raw_payload)
    schedule_code = (record.schedule_code or "").strip().upper()
    special_day = record.work_date.weekday() >= 5 or holiday_kind == PRESENZE_HOLIDAY_KIND_ORDINARY or imported_special_day
    if schedule_code == "OPESAB" and holiday is None:
        # The imported source already marked this Saturday as a scheduled workday for the collaborator.
        special_day = False
    grants_recovery_day = holiday_kind == PRESENZE_HOLIDAY_KIND_SUPPRESSED
    effective_straordinario = (
        record.override_straordinario_minutes
        if record.override_straordinario_minutes is not None
        else record.straordinario_minutes
    )
    effective_mpe = record.override_mpe_minutes if record.override_mpe_minutes is not None else record.mpe_minutes
    imported_extra = (effective_straordinario or 0) + (effective_mpe or 0)
    imported_extra_value = imported_extra or None
    assignment = resolve_assignment(collaborator, record.work_date, context) if context is not None else None
    template = context.templates_by_id.get(assignment.template_id) if assignment is not None and context is not None else None
    rules = context.rules_by_template_id.get(template.id, []) if template is not None and context is not None else []
    matched_rules = [
        rule
        for rule in rules
        if rule_matches_date(rule, record.work_date, holiday_day=holiday is not None) and template_matches_date(template, record.work_date)
    ] if template is not None and template.is_active else []
    if matched_rules and holiday is None:
        # A scheduled Saturday/weekday should be exported as ordinary ferial, not festive.
        special_day = False

    operai_quality = build_operai_operational_quality(collaborator, record, punches)
    if operai_quality.is_applicable and operai_quality.worked_minutes is not None:
        if holiday is None:
            special_day = False
        ordinary_minutes = min(operai_quality.worked_minutes, operai_quality.expected_minutes or 0)
        worked_buckets = classify_worked_minute_buckets(
            punches,
            matched_rules,
            special_day=special_day,
        )
        return DayClassification(
            special_day=special_day,
            ordinary_minutes=ordinary_minutes,
            extra_minutes=operai_quality.mpe_minutes or None,
            holiday_kind=holiday_kind,
            grants_recovery_day=grants_recovery_day,
            night_minutes=worked_buckets.night_minutes,
            festive_minutes=worked_buckets.festive_minutes,
            festive_night_minutes=worked_buckets.festive_night_minutes,
            ordinary_night_minutes=worked_buckets.ordinary_night_minutes,
            overtime_day_minutes=operai_quality.mpe_minutes,
            overtime_night_minutes=0,
            overtime_festive_minutes=0,
            overtime_festive_night_minutes=0,
            shift_festive_day_minutes=worked_buckets.shift_festive_day_minutes,
            shift_night_minutes=worked_buckets.shift_night_minutes,
            shift_festive_night_minutes=worked_buckets.shift_festive_night_minutes,
            source="operai_formula",
        )

    if raw_payload is not None and detail_has_authoritative_classification(raw_payload):
        worked_buckets = classify_worked_minute_buckets(
            punches,
            matched_rules,
            special_day=special_day,
        )
        return DayClassification(
            special_day=special_day,
            ordinary_minutes=record.ordinary_minutes,
            extra_minutes=imported_extra_value,
            holiday_kind=holiday_kind,
            grants_recovery_day=grants_recovery_day,
            night_minutes=worked_buckets.night_minutes,
            festive_minutes=worked_buckets.festive_minutes,
            festive_night_minutes=worked_buckets.festive_night_minutes,
            ordinary_night_minutes=worked_buckets.ordinary_night_minutes,
            overtime_day_minutes=worked_buckets.overtime_day_minutes,
            overtime_night_minutes=worked_buckets.overtime_night_minutes,
            overtime_festive_minutes=worked_buckets.overtime_festive_minutes,
            overtime_festive_night_minutes=worked_buckets.overtime_festive_night_minutes,
            shift_festive_day_minutes=worked_buckets.shift_festive_day_minutes,
            shift_night_minutes=worked_buckets.shift_night_minutes,
            shift_festive_night_minutes=worked_buckets.shift_festive_night_minutes,
            source="detail",
        )

    if context is None or not punches:
        return DayClassification(
            special_day=special_day,
            ordinary_minutes=record.ordinary_minutes,
            extra_minutes=imported_extra_value,
            holiday_kind=holiday_kind,
            grants_recovery_day=grants_recovery_day,
            source="imported",
        )

    if assignment is None:
        return DayClassification(
            special_day=special_day,
            ordinary_minutes=record.ordinary_minutes,
            extra_minutes=imported_extra_value,
            holiday_kind=holiday_kind,
            grants_recovery_day=grants_recovery_day,
            source="imported",
        )

    if template is None or not template.is_active:
        return DayClassification(
            special_day=special_day,
            ordinary_minutes=record.ordinary_minutes,
            extra_minutes=imported_extra_value,
            holiday_kind=holiday_kind,
            grants_recovery_day=grants_recovery_day,
            source="imported",
        )

    if not matched_rules:
        return DayClassification(
            special_day=special_day,
            ordinary_minutes=record.ordinary_minutes,
            extra_minutes=imported_extra_value,
            holiday_kind=holiday_kind,
            grants_recovery_day=grants_recovery_day,
            source="imported",
        )

    worked_buckets = classify_worked_minute_buckets(punches, matched_rules, special_day=special_day)
    return DayClassification(
        special_day=special_day,
        ordinary_minutes=worked_buckets.ordinary_minutes,
        extra_minutes=worked_buckets.extra_minutes,
        holiday_kind=holiday_kind,
        grants_recovery_day=grants_recovery_day,
        night_minutes=worked_buckets.night_minutes,
        festive_minutes=worked_buckets.festive_minutes,
        festive_night_minutes=worked_buckets.festive_night_minutes,
        ordinary_night_minutes=worked_buckets.ordinary_night_minutes,
        overtime_day_minutes=worked_buckets.overtime_day_minutes,
        overtime_night_minutes=worked_buckets.overtime_night_minutes,
        overtime_festive_minutes=worked_buckets.overtime_festive_minutes,
        overtime_festive_night_minutes=worked_buckets.overtime_festive_night_minutes,
        shift_festive_day_minutes=worked_buckets.shift_festive_day_minutes,
        shift_night_minutes=worked_buckets.shift_night_minutes,
        shift_festive_night_minutes=worked_buckets.shift_festive_night_minutes,
        source="template",
    )


def compute_punch_minutes(punches: list[PresenzeDailyPunch]) -> int:
    return len(_minute_set_from_punches(punches))


def compute_overlap_minutes(punches: list[PresenzeDailyPunch], rules: list[PresenzeScheduleRule]) -> int:
    return len(_minute_set_from_punches(punches) & _minute_set_from_rules(rules))


def classify_worked_minute_buckets(
    punches: list[PresenzeDailyPunch],
    rules: list[PresenzeScheduleRule],
    *,
    special_day: bool,
) -> WorkedMinuteBuckets:
    actual_set = _minute_set_from_punches(punches)
    ordinary_set = actual_set & _minute_set_from_rules(rules)
    extra_set = actual_set - ordinary_set
    night_set = _night_minute_set()
    festive_set = actual_set if special_day else set()
    festive_night_set = festive_set & night_set
    festive_day_set = festive_set - night_set
    ordinary_night_set = ordinary_set & night_set
    shift_night_set = ordinary_night_set if not special_day else set()
    shift_festive_night_set = ordinary_night_set if special_day else set()
    shift_festive_day_set = (ordinary_set - night_set) if special_day else set()
    overtime_night_set = extra_set & night_set
    overtime_day_set = extra_set - night_set
    overtime_festive_night_set = overtime_night_set if special_day else set()
    overtime_festive_day_set = overtime_day_set if special_day else set()
    overtime_night_ferial_set = overtime_night_set if not special_day else set()
    overtime_day_ferial_set = overtime_day_set if not special_day else set()
    ordinary_night_ferial_set = ordinary_night_set if not special_day else set()
    return WorkedMinuteBuckets(
        actual_minutes=len(actual_set),
        ordinary_minutes=len(ordinary_set),
        extra_minutes=len(extra_set),
        night_minutes=len(actual_set & night_set),
        festive_minutes=len(festive_day_set),
        festive_night_minutes=len(festive_night_set),
        ordinary_night_minutes=len(ordinary_night_ferial_set),
        overtime_day_minutes=len(overtime_day_ferial_set),
        overtime_night_minutes=len(overtime_night_ferial_set),
        overtime_festive_minutes=len(overtime_festive_day_set),
        overtime_festive_night_minutes=len(overtime_festive_night_set),
        shift_festive_day_minutes=len(shift_festive_day_set),
        shift_night_minutes=len(shift_night_set),
        shift_festive_night_minutes=len(shift_festive_night_set),
    )


def _minute_set_from_punches(punches: list[PresenzeDailyPunch]) -> set[int]:
    worked_minutes: set[int] = set()
    for punch in punches:
        if punch.entry_time is None or punch.exit_time is None:
            continue
        worked_minutes.update(_minute_range(to_minutes(punch.entry_time), to_minutes(punch.exit_time)))
    return worked_minutes


def _minute_set_from_rules(rules: list[PresenzeScheduleRule]) -> set[int]:
    scheduled_minutes: set[int] = set()
    for rule in rules:
        scheduled_minutes.update(_minute_range(to_minutes(rule.start_time), to_minutes(rule.end_time)))
    return scheduled_minutes


def _minute_range(start_minutes: int, end_minutes: int) -> range:
    if start_minutes == end_minutes:
        return range(0)
    if end_minutes < start_minutes:
        end_minutes += 24 * 60
    return range(start_minutes, end_minutes)


def _night_minute_set() -> set[int]:
    return set(range(0, 6 * 60)) | set(range(22 * 60, 30 * 60))


def resolve_assignment(
    collaborator: PresenzeCollaborator,
    work_date: date,
    context: ScheduleContext,
) -> PresenzeCollaboratorScheduleAssignment | None:
    for assignment in context.assignments_by_collaborator.get(str(collaborator.id), []):
        if assignment.valid_from and work_date < assignment.valid_from:
            continue
        if assignment.valid_to and work_date > assignment.valid_to:
            continue
        return assignment
    return None


def template_matches_date(template: PresenzeScheduleTemplate, work_date: date) -> bool:
    if template.valid_from and work_date < template.valid_from:
        return False
    if template.valid_to and work_date > template.valid_to:
        return False
    return True


def rule_matches_date(rule: PresenzeScheduleRule, work_date: date, *, holiday_day: bool) -> bool:
    if rule.weekday is not None and work_date.weekday() != rule.weekday:
        return False
    if holiday_day and not rule.applies_on_holiday:
        return False
    if not season_matches(rule, work_date):
        return False

    recurrence = rule.recurrence_kind or RECURRENCE_WEEKLY
    if recurrence == RECURRENCE_WEEKLY:
        return True
    if recurrence == RECURRENCE_FIRST_WEEKDAY:
        return day_occurrence_in_month(work_date) == 1
    if recurrence == RECURRENCE_NTH_WEEKDAY:
        return rule.week_of_month is not None and day_occurrence_in_month(work_date) == rule.week_of_month
    if recurrence == RECURRENCE_ALTERNATING:
        if rule.anchor_date is None:
            return False
        interval = rule.interval_weeks or 2
        delta_days = (work_date - rule.anchor_date).days
        if delta_days < 0:
            return False
        return (delta_days // 7) % interval == 0
    return False


def scheduled_minutes_for_day(
    collaborator: PresenzeCollaborator,
    work_date: date,
    context: ScheduleContext | None,
) -> int:
    if context is None:
        return 0
    assignment = resolve_assignment(collaborator, work_date, context)
    if assignment is None:
        return 0
    template = context.templates_by_id.get(assignment.template_id)
    if template is None or not template.is_active or not template_matches_date(template, work_date):
        return 0
    holiday = resolve_holiday(work_date, collaborator, context)
    matched_rules = [
        rule
        for rule in context.rules_by_template_id.get(template.id, [])
        if rule_matches_date(rule, work_date, holiday_day=holiday is not None) and template_matches_date(template, work_date)
    ]
    return len(_minute_set_from_rules(matched_rules))


def season_matches(rule: PresenzeScheduleRule, work_date: date) -> bool:
    if (
        rule.season_start_month is None
        or rule.season_start_day is None
        or rule.season_end_month is None
        or rule.season_end_day is None
    ):
        return True

    start_key = (rule.season_start_month, rule.season_start_day)
    end_key = (rule.season_end_month, rule.season_end_day)
    current_key = (work_date.month, work_date.day)
    if start_key <= end_key:
        return start_key <= current_key <= end_key
    return current_key >= start_key or current_key <= end_key


def day_occurrence_in_month(work_date: date) -> int:
    return ((work_date.day - 1) // 7) + 1

def resolve_holiday(
    work_date: date,
    collaborator: PresenzeCollaborator,
    context: ScheduleContext | None,
) -> PresenzeHoliday | None:
    if context is not None:
        for key in ((work_date, collaborator.company_code), (work_date, None)):
            rows = context.holidays_by_key.get(key, [])
            if rows:
                return rows[0]

    default_holidays = default_holidays_for_year(work_date.year)
    if work_date in default_holidays:
        return PresenzeHoliday(
            holiday_date=work_date,
            label=default_holidays[work_date],
            company_code=None,
            holiday_kind=PRESENZE_HOLIDAY_KIND_ORDINARY,
        )
    return None


def default_holidays_for_year(year: int) -> dict[date, str]:
    easter_sunday = compute_easter_sunday(year)
    pasquetta = easter_sunday + timedelta(days=1)
    martedi_grasso = easter_sunday - timedelta(days=47)
    return {
        date(year, 1, 1): "Capodanno",
        date(year, 1, 6): "Epifania",
        date(year, 2, 13): "Patrono",
        martedi_grasso: "Martedi della Sartiglia",
        pasquetta: "Pasquetta",
        date(year, 4, 25): "Liberazione",
        date(year, 5, 1): "Festa del lavoro",
        date(year, 6, 2): "Festa della Repubblica",
        date(year, 8, 14): "Vigilia Ferragosto",
        date(year, 8, 15): "Ferragosto",
        date(year, 8, 16): "Recupero Ferragosto",
        date(year, 9, 8): "Festivita locale",
        date(year, 9, 14): "Festivita locale",
        date(year, 11, 1): "Ognissanti",
        date(year, 12, 8): "Immacolata",
        date(year, 12, 24): "Vigilia Natale",
        date(year, 12, 25): "Natale",
        date(year, 12, 26): "Santo Stefano",
        date(year, 12, 31): "San Silvestro",
    }


def seed_holidays_for_year(db: Session, year: int) -> list[PresenzeHoliday]:
    created: list[PresenzeHoliday] = []
    defaults = default_holidays_for_year(year)
    for holiday_date, label in defaults.items():
        existing = db.execute(
            select(PresenzeHoliday).where(
                PresenzeHoliday.holiday_date == holiday_date,
                PresenzeHoliday.company_code.is_(None),
                PresenzeHoliday.label == label,
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue
        row = PresenzeHoliday(
            holiday_date=holiday_date,
            label=label,
            company_code=None,
            holiday_kind=PRESENZE_HOLIDAY_KIND_ORDINARY,
        )
        db.add(row)
        created.append(row)
    db.flush()
    return created


def compute_easter_sunday(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute
