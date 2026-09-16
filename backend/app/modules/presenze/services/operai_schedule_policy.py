"""Individual Saturday calendars override the generic operaio monthly calendar."""

from dataclasses import dataclass, replace
from types import SimpleNamespace

from app.modules.presenze.services.operai_daily_policy import (
    _complete_day_pairs,
    assigned_daily_start,
    recognized_daily_minutes,
)
from app.modules.presenze.services.operai_recognized_minutes import RecognizedOperaiMinutes
from app.modules.presenze.services.operai_rules import (
    SUMMER_SATURDAY_MINUTES,
    ResolvedOperaiRule,
    resolve_operai_rule,
    resolve_operai_schedule_code,
)


@dataclass(frozen=True)
class OperaiDayPolicy:
    rule: ResolvedOperaiRule | None
    recognized_minutes: RecognizedOperaiMinutes | None = None
    individual_saturday: bool = False


def has_individual_saturday(record, template, rules):
    if record.work_date.weekday() != 5 or template is None or not template.is_active:
        return False
    if template.valid_from and record.work_date < template.valid_from:
        return False
    if template.valid_to and record.work_date > template.valid_to:
        return False
    return any(_is_biweekly_saturday(rule) for rule in rules)


def _is_biweekly_saturday(rule):
    return (
        rule.weekday == 5
        and rule.recurrence_kind == "alternating_weeks"
        and (rule.interval_weeks or 2) == 2
        and rule.anchor_date is not None
        and rule.anchor_date.weekday() == 5
    )


def resolve_individual_operai_rule(collaborator, record, configs, individual_saturday):
    rule = resolve_operai_rule(collaborator, record, configs)
    if rule is not None or not individual_saturday:
        return rule
    if resolve_operai_schedule_code(record) not in {"SAB", "RIPTURN"}:
        return None
    # A rest-day code does not override the explicitly assigned Saturday calendar.
    scheduled_record = SimpleNamespace(work_date=record.work_date, schedule_code="OPESAB")
    return resolve_operai_rule(collaborator, scheduled_record, configs)


def build_operai_day_policy(rule, record, punches, matched_rules, individual_saturday):
    if rule is None:
        return OperaiDayPolicy(None)
    if individual_saturday:
        scheduled = bool(matched_rules)
        minutes = SUMMER_SATURDAY_MINUTES.get(
            rule.formula_code, rule.rule.saturday_expected_minutes
        )
        rule = replace(
            rule, expected_minutes=minutes if scheduled else 0, saturday_is_scheduled=scheduled
        )
    if individual_saturday and rule.expected_minutes == 0:
        return OperaiDayPolicy(rule, _recognize_unscheduled_saturday(punches), True)
    starts = {item.start_time for item in matched_rules}
    start = assigned_daily_start(record, rule, starts)
    return OperaiDayPolicy(
        rule,
        recognized_daily_minutes(punches, rule, scheduled_start=start),
        individual_saturday,
    )


def _recognize_unscheduled_saturday(punches):
    pairs = _complete_day_pairs(punches)
    if not pairs:
        return None
    worked = {minute for pair in pairs for minute in pair.minutes()}
    return RecognizedOperaiMinutes(
        ordinary_minutes=0,
        overtime_minutes=len(worked),
        ordinary_night_minutes=0,
        missing_minutes=0,
        excluded_early_minutes=0,
        excluded_break_minutes=0,
        excluded_overtime_minutes=0,
    )
