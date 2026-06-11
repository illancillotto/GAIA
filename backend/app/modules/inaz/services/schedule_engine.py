from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.inaz.models import (
    InazCollaborator,
    InazCollaboratorScheduleAssignment,
    InazDailyPunch,
    InazDailyRecord,
    InazHoliday,
    InazScheduleRule,
    InazScheduleTemplate,
)
from app.modules.inaz.services.parser import detail_has_authoritative_classification, detail_indicates_special_day

RECURRENCE_WEEKLY = "weekly"
RECURRENCE_FIRST_WEEKDAY = "first_weekday_of_month"
RECURRENCE_NTH_WEEKDAY = "nth_weekday_of_month"
RECURRENCE_ALTERNATING = "alternating_weeks"


@dataclass(frozen=True)
class DayClassification:
    special_day: bool
    ordinary_minutes: int | None
    extra_minutes: int | None
    source: str


@dataclass
class ScheduleContext:
    holidays_by_key: dict[tuple[date, str | None], list[InazHoliday]]
    assignments_by_collaborator: dict[str, list[InazCollaboratorScheduleAssignment]]
    templates_by_id: dict[int, InazScheduleTemplate]
    rules_by_template_id: dict[int, list[InazScheduleRule]]


def build_schedule_context(
    db: Session,
    *,
    collaborator_ids: list[uuid.UUID],
    date_from: date,
    date_to: date,
) -> ScheduleContext:
    holiday_rows = db.execute(
        select(InazHoliday).where(InazHoliday.holiday_date >= date_from, InazHoliday.holiday_date <= date_to)
    ).scalars().all()
    assignments = db.execute(
        select(InazCollaboratorScheduleAssignment).where(
            InazCollaboratorScheduleAssignment.collaborator_id.in_(collaborator_ids)
        )
    ).scalars().all()
    template_ids = sorted({item.template_id for item in assignments})
    templates = []
    rules = []
    if template_ids:
        templates = db.execute(select(InazScheduleTemplate).where(InazScheduleTemplate.id.in_(template_ids))).scalars().all()
        rules = db.execute(select(InazScheduleRule).where(InazScheduleRule.template_id.in_(template_ids))).scalars().all()

    holidays_by_key: dict[tuple[date, str | None], list[InazHoliday]] = {}
    for row in holiday_rows:
        holidays_by_key.setdefault((row.holiday_date, row.company_code), []).append(row)

    assignments_by_collaborator: dict[str, list[InazCollaboratorScheduleAssignment]] = {}
    for row in assignments:
        assignments_by_collaborator.setdefault(str(row.collaborator_id), []).append(row)
    for rows in assignments_by_collaborator.values():
        rows.sort(key=lambda item: (item.valid_from or date.min, item.id), reverse=True)

    rules_by_template_id: dict[int, list[InazScheduleRule]] = {}
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
    collaborator: InazCollaborator,
    record: InazDailyRecord,
    punches: list[InazDailyPunch],
    context: ScheduleContext | None,
) -> DayClassification:
    holiday = resolve_holiday(record.work_date, collaborator, context)
    raw_payload = record.raw_payload_json if isinstance(record.raw_payload_json, dict) else None
    imported_special_day = raw_payload is not None and detail_indicates_special_day(raw_payload)
    schedule_code = (record.schedule_code or "").strip().upper()
    special_day = record.work_date.weekday() >= 5 or (holiday is not None and not holiday.is_workday_override) or imported_special_day
    if schedule_code == "OPESAB" and holiday is None:
        # Inaz already marked this Saturday as a scheduled workday for the collaborator.
        special_day = False
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

    if raw_payload is not None and detail_has_authoritative_classification(raw_payload):
        return DayClassification(
            special_day=special_day,
            ordinary_minutes=record.ordinary_minutes,
            extra_minutes=imported_extra_value,
            source="detail",
        )

    if context is None or not punches:
        return DayClassification(
            special_day=special_day,
            ordinary_minutes=record.ordinary_minutes,
            extra_minutes=imported_extra_value,
            source="imported",
        )

    if assignment is None:
        return DayClassification(
            special_day=special_day,
            ordinary_minutes=record.ordinary_minutes,
            extra_minutes=imported_extra_value,
            source="imported",
        )

    if template is None or not template.is_active:
        return DayClassification(
            special_day=special_day,
            ordinary_minutes=record.ordinary_minutes,
            extra_minutes=imported_extra_value,
            source="imported",
        )

    if not matched_rules:
        actual_minutes = compute_punch_minutes(punches)
        return DayClassification(
            special_day=special_day,
            ordinary_minutes=0 if actual_minutes > 0 else record.ordinary_minutes,
            extra_minutes=actual_minutes if actual_minutes > 0 else imported_extra_value,
            source="template",
        )

    ordinary_minutes = compute_overlap_minutes(punches, matched_rules)
    actual_minutes = compute_punch_minutes(punches)
    extra_minutes = max(actual_minutes - ordinary_minutes, 0)
    return DayClassification(
        special_day=special_day,
        ordinary_minutes=ordinary_minutes,
        extra_minutes=extra_minutes,
        source="template",
    )


def compute_punch_minutes(punches: list[InazDailyPunch]) -> int:
    total = 0
    for punch in punches:
        if punch.entry_time is None or punch.exit_time is None:
            continue
        start_minutes = to_minutes(punch.entry_time)
        end_minutes = to_minutes(punch.exit_time)
        if end_minutes > start_minutes:
            total += end_minutes - start_minutes
    return total


def compute_overlap_minutes(punches: list[InazDailyPunch], rules: list[InazScheduleRule]) -> int:
    total = 0
    for punch in punches:
        if punch.entry_time is None or punch.exit_time is None:
            continue
        punch_start = to_minutes(punch.entry_time)
        punch_end = to_minutes(punch.exit_time)
        for rule in rules:
            rule_start = to_minutes(rule.start_time)
            rule_end = to_minutes(rule.end_time)
            overlap = max(0, min(punch_end, rule_end) - max(punch_start, rule_start))
            total += overlap
    return total


def resolve_assignment(
    collaborator: InazCollaborator,
    work_date: date,
    context: ScheduleContext,
) -> InazCollaboratorScheduleAssignment | None:
    for assignment in context.assignments_by_collaborator.get(str(collaborator.id), []):
        if assignment.valid_from and work_date < assignment.valid_from:
            continue
        if assignment.valid_to and work_date > assignment.valid_to:
            continue
        return assignment
    return None


def template_matches_date(template: InazScheduleTemplate, work_date: date) -> bool:
    if template.valid_from and work_date < template.valid_from:
        return False
    if template.valid_to and work_date > template.valid_to:
        return False
    return True


def rule_matches_date(rule: InazScheduleRule, work_date: date, *, holiday_day: bool) -> bool:
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
    collaborator: InazCollaborator,
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
    total = 0
    for rule in matched_rules:
        rule_end = to_minutes(rule.end_time)
        rule_start = to_minutes(rule.start_time)
        if rule_end > rule_start:
            total += rule_end - rule_start
    return total


def season_matches(rule: InazScheduleRule, work_date: date) -> bool:
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
    collaborator: InazCollaborator,
    context: ScheduleContext | None,
) -> InazHoliday | None:
    default_holidays = default_holidays_for_year(work_date.year)
    if work_date in default_holidays:
        return InazHoliday(holiday_date=work_date, label=default_holidays[work_date], company_code=None, is_workday_override=False)

    if context is None:
        return None
    for key in ((work_date, collaborator.company_code), (work_date, None)):
        rows = context.holidays_by_key.get(key, [])
        if rows:
            return rows[0]
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


def seed_holidays_for_year(db: Session, year: int) -> list[InazHoliday]:
    created: list[InazHoliday] = []
    defaults = default_holidays_for_year(year)
    for holiday_date, label in defaults.items():
        existing = db.execute(
            select(InazHoliday).where(
                InazHoliday.holiday_date == holiday_date,
                InazHoliday.company_code.is_(None),
                InazHoliday.label == label,
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue
        row = InazHoliday(
            holiday_date=holiday_date,
            label=label,
            company_code=None,
            is_workday_override=False,
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
