"""Attested monthly assignments replace the ungrouped legacy Saturday fallback."""

from datetime import date, time
from types import SimpleNamespace

import pytest

from app.modules.presenze.services.inaz_assigned_calendar import (
    assigned_saturday_minutes,
    is_inaz_monthly_calendar,
)
from app.modules.presenze.services.operai_rules import resolve_operai_rule
from app.modules.presenze.services.operai_schedule_policy import (
    build_operai_day_policy,
    has_individual_saturday,
    resolve_individual_operai_rule,
)


def test_unrelated_templates_do_not_enable_monthly_override():
    assert not is_inaz_monthly_calendar(None)
    assert not is_inaz_monthly_calendar(SimpleNamespace(code="OPE0736_STD"))
    rule = SimpleNamespace(
        rule=SimpleNamespace(code="OPERAI_AGRARIO_1E3SAB", saturday_expected_minutes=390)
    )
    monthly = SimpleNamespace(weekday=5, recurrence_kind="first_weekday_of_month")
    assert assigned_saturday_minutes(rule, [monthly]) == 390
    assert assigned_saturday_minutes(rule, []) == 390
    legacy = SimpleNamespace(
        rule=SimpleNamespace(code="OPERAI_LEGACY_FALLBACK", saturday_expected_minutes=420)
    )
    assert (
        assigned_saturday_minutes(legacy, [SimpleNamespace(weekday=0, recurrence_kind="weekly")])
        == 420
    )
    assert (
        assigned_saturday_minutes(legacy, [SimpleNamespace(weekday=5, recurrence_kind="weekly")])
        == 420
    )


@pytest.mark.parametrize("day,expected", [(3, 390), (10, 0), (17, 390), (24, 0), (31, 0)])
@pytest.mark.parametrize("code", ["OPESAB", "OPE0714", "SAB"])
def test_first_and_third_saturday_have_six_and_a_half_hours_without_hr_group(day, expected, code):
    record = SimpleNamespace(work_date=date(2026, 10, day), schedule_code=code, raw_payload_json={})
    collaborator = SimpleNamespace(contract_kind="operaio", operai_group=None)
    template = SimpleNamespace(
        code="OPE0714_1E3SAB", is_active=True, valid_from=None, valid_to=None
    )
    monthly = SimpleNamespace(
        weekday=5, recurrence_kind="first_weekday_of_month", start_time=time(7)
    )
    assert has_individual_saturday(record, template, [monthly])
    rule = resolve_individual_operai_rule(collaborator, record, None, True)
    policy = build_operai_day_policy(rule, record, [], [monthly] if expected else [], True)
    assert policy.rule.expected_minutes == expected
    assert policy.rule.saturday_is_scheduled is bool(expected)
    assert policy.individual_saturday
    # The generic fallback remains unchanged if no personal calendar is assigned.
    fallback = resolve_operai_rule(collaborator, record)
    if fallback is not None:
        assert fallback.rule.code == "OPERAI_LEGACY_FALLBACK"
        assert fallback.expected_minutes == 420
