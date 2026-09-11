from dataclasses import replace
from datetime import date, time
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeCollaboratorScheduleAssignment,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
    PresenzeScheduleRule,
    PresenzeScheduleTemplate,
)
from app.modules.presenze.services.gate_mobile_payloads import presenze_extra_minutes
from app.modules.presenze.services.operai_daily_policy import (
    effective_extra_values,
    recognized_daily_minutes,
)
from app.modules.presenze.services.operai_rules import resolve_operai_rule
from app.modules.presenze.services.operational_quality import build_daily_operational_quality
from app.modules.presenze.services.schedule_engine import ScheduleContext, classify_daily_record


def _day(code="OPE0714", pairs=((time(6, 40), time(14, 20)),)):
    collaborator = PresenzeCollaborator(
        id=uuid4(), contract_kind="operaio", operai_group="catasto_magazzino"
    )
    record = PresenzeDailyRecord(
        id=uuid4(),
        collaborator_id=collaborator.id,
        work_date=date(2026, 9, 10),
        schedule_code=code,
        ordinary_minutes=420,
        straordinario_minutes=13,
        mpe_minutes=99,
    )
    punches = [
        PresenzeDailyPunch(entry_time=entry, exit_time=exit_time, sequence=index)
        for index, (entry, exit_time) in enumerate(pairs)
    ]
    return collaborator, record, punches


@pytest.mark.parametrize(
    ("exit_minute", "extra"),
    [(10, 0), (14, 0), (15, 15), (20, 20), (30, 30), (31, 31), (44, 44), (45, 45), (59, 59)],
)
def test_exit_policy_is_consistent_in_classification_quality_and_gate(exit_minute, extra):
    collaborator, record, punches = _day(pairs=((time(6, 40), time(14, exit_minute)),))
    result = classify_daily_record(collaborator, record, punches, None)
    quality = build_daily_operational_quality(collaborator, record, punches, classification=result)
    serialized = SimpleNamespace(**effective_extra_values(record, result))
    assert result.ordinary_minutes == 420
    assert result.extra_minutes == result.overtime_day_minutes == extra
    assert quality.mpe_minutes == extra
    assert result.recognized_minutes.excluded_early_minutes == 20
    assert presenze_extra_minutes(serialized, result) == extra
    assert presenze_extra_minutes(serialized) == extra
    assert record.straordinario_minutes == 13
    assert record.mpe_minutes == 99


@pytest.mark.parametrize("split", [False, True])
def test_lunch_is_relative_to_standard_hours_and_is_not_deducted_twice(split):
    pairs = (
        ((time(5, 15), time(12, 30)), (time(13), time(16))) if split else ((time(5, 15), time(16)),)
    )
    collaborator, record, punches = _day("OP_5.3_12.3", pairs)
    result = classify_daily_record(collaborator, record, punches, None)
    assert result.ordinary_minutes == 420
    assert result.extra_minutes == 180
    assert result.ordinary_night_minutes == 30
    assert result.night_minutes == 30
    assert result.overtime_night_minutes == 0
    assert result.recognized_minutes.excluded_break_minutes == (0 if split else 30)


def test_shift_start_is_attested_by_assignment_not_inferred_from_punches():
    collaborator, record, punches = _day(pairs=((time(5, 15), time(12, 50)),))
    template = PresenzeScheduleTemplate(id=1, is_active=True)
    assignment = PresenzeCollaboratorScheduleAssignment(
        collaborator_id=collaborator.id, template_id=1
    )
    rule = PresenzeScheduleRule(
        start_time=time(5, 30),
        end_time=time(12, 30),
        weekday=3,
        recurrence_kind="weekly",
        applies_on_holiday=False,
    )
    context = ScheduleContext({}, {str(collaborator.id): [assignment]}, {1: template}, {1: [rule]})
    result = classify_daily_record(collaborator, record, punches, context)
    quality = build_daily_operational_quality(collaborator, record, punches, classification=result)
    assert result.ordinary_minutes == 420
    assert result.ordinary_night_minutes == 30
    assert result.extra_minutes == quality.mpe_minutes == 20
    assert quality.missing_minutes == 0


@pytest.mark.parametrize(
    ("mpe", "straordinario", "extra"), [(0, None, 0), (5, None, 5), (None, 30, 50)]
)
def test_explicit_authorized_adjustments_remain_distinct_from_imported_minutes(
    mpe, straordinario, extra
):
    collaborator, record, punches = _day()
    record.override_mpe_minutes = mpe
    record.override_straordinario_minutes = straordinario
    result = classify_daily_record(collaborator, record, punches, None)
    serialized = SimpleNamespace(**effective_extra_values(record, result))
    assert result.extra_minutes == extra
    assert presenze_extra_minutes(serialized) == extra
    assert presenze_extra_minutes(serialized, result) == extra


def test_imported_larger_extra_does_not_override_canonical_zero():
    collaborator, record, punches = _day(pairs=((time(6, 40), time(14, 10)),))
    result = classify_daily_record(collaborator, record, punches, None)
    assert presenze_extra_minutes(SimpleNamespace(effective_extra_minutes=99), result) == 0


@pytest.mark.parametrize(
    "pairs", [(), ((None, time(14)),), ((time(7), None),), ((time(22), time(6)),)]
)
def test_missing_or_overnight_pairs_do_not_invent_a_daytime_recognition(pairs):
    collaborator, record, punches = _day(pairs=pairs)
    rule = resolve_operai_rule(collaborator, record)
    assert recognized_daily_minutes(punches, rule) is None


def test_unknown_schedule_and_zero_standard_are_not_guessed():
    collaborator, record, punches = _day()
    rule = resolve_operai_rule(collaborator, record)
    assert recognized_daily_minutes(punches, replace(rule, formula_code="UNKNOWN")) is None
    assert recognized_daily_minutes(punches, replace(rule, expected_minutes=0)) is None
    assert recognized_daily_minutes(punches, rule, scheduled_start=time(23)) is None


def test_unrecognized_classification_preserves_legacy_effective_values():
    _, record, _ = _day()
    assert effective_extra_values(record, SimpleNamespace()) == {
        "effective_straordinario_minutes": 13,
        "effective_mpe_minutes": 99,
        "effective_extra_minutes": 112,
    }
    record.override_straordinario_minutes = 0
    record.override_mpe_minutes = 0
    assert effective_extra_values(record, SimpleNamespace())["effective_extra_minutes"] is None


def test_impiegato_keeps_imported_extra_and_early_punches():
    collaborator, record, punches = _day()
    collaborator.contract_kind = "impiegato"
    result = classify_daily_record(collaborator, record, punches, None)
    assert result.recognized_minutes is None
    assert result.extra_minutes == 112
    assert presenze_extra_minutes(SimpleNamespace(effective_extra_minutes=150), result) == 150


def test_lunch_starts_after_standard_hours_are_completed_when_arriving_late():
    collaborator, record, punches = _day(pairs=((time(7, 20), time(16)),))
    result = classify_daily_record(collaborator, record, punches, None)
    assert result.ordinary_minutes == 420
    assert result.extra_minutes == 70
    assert result.recognized_minutes.excluded_break_minutes == 30


@pytest.mark.parametrize(
    ("code", "entry", "exit_time", "extra", "excluded_break"),
    [
        ("OPE0613", time(6), time(14, 30), 90, 0),
        ("OPE0613", time(6), time(15), 120, 0),
        ("OPE0613", time(6), time(15, 59), 179, 0),
        ("OPE0613", time(6), time(16), 150, 30),
        ("OPE0613", time(6), time(16, 1), 151, 30),
        ("OPE0714", time(7), time(15), 60, 0),
        ("OPE0714", time(7), time(15, 59), 119, 0),
        ("OPE0714", time(7), time(16), 90, 30),
        ("OPE0714", time(7), time(16, 1), 91, 30),
        ("OPE0714", time(7), time(17), 150, 30),
        ("OP_5.3_12.3", time(5, 30), time(15, 59), 209, 0),
        ("OP_5.3_12.3", time(5, 30), time(16), 180, 30),
    ],
)
def test_lunch_starts_at_fixed_1600_inclusive_for_all_daytime_shifts(
    code, entry, exit_time, extra, excluded_break
):
    collaborator, record, punches = _day(code, ((entry, exit_time),))
    result = classify_daily_record(collaborator, record, punches, None)
    quality = build_daily_operational_quality(collaborator, record, punches, classification=result)
    assert result.ordinary_minutes == 420
    assert result.extra_minutes == result.overtime_day_minutes == quality.mpe_minutes == extra
    assert result.recognized_minutes.excluded_break_minutes == excluded_break
    serialized = SimpleNamespace(**effective_extra_values(record, result))
    assert presenze_extra_minutes(serialized, result) == extra


def test_punched_lunch_before_1600_is_still_excluded_from_worked_time():
    collaborator, record, punches = _day("OPE0613", ((time(6), time(13)), (time(13, 30), time(15))))
    result = classify_daily_record(collaborator, record, punches, None)
    assert result.ordinary_minutes == 420
    assert result.extra_minutes == 90
    assert result.recognized_minutes.excluded_break_minutes == 0


def test_exit_at_1600_without_completed_standard_hours_does_not_deduct_lunch():
    collaborator, record, punches = _day(pairs=((time(10), time(16)),))
    result = classify_daily_record(collaborator, record, punches, None)
    assert result.ordinary_minutes == 360
    assert result.extra_minutes == 0
    assert result.recognized_minutes.missing_minutes == 60
    assert result.recognized_minutes.excluded_break_minutes == 0


def test_lunch_interval_is_clipped_at_day_end_for_late_standard_completion():
    collaborator, record, punches = _day(pairs=((time(16, 50), time(23, 59)),))
    result = classify_daily_record(collaborator, record, punches, None)
    assert result.ordinary_minutes == 420
    assert result.extra_minutes == 0
    assert result.recognized_minutes.excluded_break_minutes == 9


def test_early_exit_preserves_missing_hours_without_lunch_deduction():
    collaborator, record, punches = _day(pairs=((time(6, 40), time(13)),))
    result = classify_daily_record(collaborator, record, punches, None)
    assert result.ordinary_minutes == 360
    assert result.extra_minutes == 0
    assert result.recognized_minutes.missing_minutes == 60
    assert result.recognized_minutes.excluded_break_minutes == 0


def test_overnight_work_keeps_existing_classification_without_a_daytime_lunch():
    collaborator, record, punches = _day("OP_5.3_12.3", ((time(22), time(5, 30)),))
    result = classify_daily_record(collaborator, record, punches, None)
    assert result.recognized_minutes is None
    assert result.source == "operai_formula"
    assert result.ordinary_minutes == 420
    assert result.extra_minutes == 30


@pytest.mark.parametrize(
    ("entry", "exit_time", "extra"),
    [(time(5, 50), time(13, 10), 0), (time(5, 44), time(13), 0),
     (time(5, 40), time(13, 14), 0), (time(5, 40), time(13, 15), 15),
     (time(5, 40), time(13, 26), 26)],
)
def test_alternative_template_starts_do_not_authorize_early_overtime(entry, exit_time, extra):
    collaborator, record, punches = _day("OPE0613", ((entry, exit_time),))
    template = PresenzeScheduleTemplate(id=1, is_active=True)
    assignment = PresenzeCollaboratorScheduleAssignment(
        collaborator_id=collaborator.id, template_id=1
    )
    rules = [PresenzeScheduleRule(
        start_time=start, end_time=end, weekday=3,
        recurrence_kind="weekly", applies_on_holiday=False,
    ) for start, end in [(time(5, 30), time(12, 30)), (time(7), time(14))]]
    context = ScheduleContext({}, {str(collaborator.id): [assignment]}, {1: template}, {1: rules})
    result = classify_daily_record(collaborator, record, punches, context)
    quality = build_daily_operational_quality(collaborator, record, punches, classification=result)
    assert result.ordinary_minutes == 420
    assert result.ordinary_night_minutes == 0
    assert result.extra_minutes == result.overtime_day_minutes == quality.mpe_minutes == extra
    assert presenze_extra_minutes(SimpleNamespace(effective_extra_minutes=99), result) == extra


@pytest.mark.parametrize("group", [None, "agrario", "catasto_magazzino"])
@pytest.mark.parametrize(
    ("code", "entry", "exit_time", "day", "ordinary", "extra", "night"),
    [("OPEF0613", time(6, 4), time(13, 6), 6, 420, 0, 0),
     ("OPEF0613", time(5, 45), time(13, 15), 6, 420, 15, 0),
     ("OPESACE", time(5, 49), time(12), 29, 360, 0, 0),
     ("OPESACE", time(5, 49), time(12, 15), 29, 360, 15, 0),
     ("OPSABE", time(5, 45), time(12, 44), 29, 390, 0, 0),
     ("OPSABE", time(5, 45), time(12, 45), 29, 390, 15, 0),
     ("OSAB5.3_11.3", time(5, 15), time(11, 44), 8, 360, 0, 30),
     ("OSAB5.3_11.3", time(5, 15), time(11, 45), 8, 360, 15, 30)],
)
def test_effective_summer_variants_use_daily_duration_and_same_overtime_policy(
    group, code, entry, exit_time, day, ordinary, extra, night
):
    collaborator, record, punches = _day(code, ((entry, exit_time),))
    collaborator.operai_group = group
    record.work_date = date(2026, 8, day)
    result = classify_daily_record(collaborator, record, punches, None)
    assert result.ordinary_minutes == ordinary
    assert result.extra_minutes == result.overtime_day_minutes == extra
    assert result.ordinary_night_minutes == night
    assert presenze_extra_minutes(SimpleNamespace(effective_extra_minutes=99), result) == extra


@pytest.mark.parametrize(
    ("entry", "exit_time", "ordinary", "extra"),
    [(time(5, 35), time(17, 30), 420, 240),
     (time(5, 59), time(13, 14), 420, 0),
     (time(6), time(13, 15), 420, 15),
     (time(5, 30), time(13), 360, 0),
     (time(6, 1), time(14, 15), 420, 15),
     (time(5, 45), time(12, 59), 359, 0),
     (time(5, 45), time(22, 1), 420, 451)],
)
def test_confirmed_summer_switch_excludes_early_minutes(entry, exit_time, ordinary, extra):
    collaborator, record, punches = _day("OPE0714", ((entry, exit_time),))
    result = classify_daily_record(collaborator, record, punches, None)
    assert result.ordinary_minutes == ordinary
    assert result.ordinary_night_minutes == 0
    assert result.extra_minutes == result.overtime_day_minutes == extra


@pytest.mark.parametrize("effective", ["OPE0613 - NOFLEX", "OPE0714 - NOFLEX", "", None])
def test_daily_effective_schedule_supersedes_generic_seasonal_template(effective):
    collaborator, record, punches = _day("OPE0613", ((time(5, 50), time(13, 10)),))
    record.raw_payload_json = {"detail_effective_schedule": effective}
    template = PresenzeScheduleTemplate(id=1, is_active=True)
    assignment = PresenzeCollaboratorScheduleAssignment(
        collaborator_id=collaborator.id, template_id=1
    )
    rule = PresenzeScheduleRule(
        start_time=time(5, 30), end_time=time(12, 30), weekday=3,
        recurrence_kind="weekly", applies_on_holiday=False,
    )
    context = ScheduleContext({}, {str(collaborator.id): [assignment]}, {1: template}, {1: [rule]})
    result = classify_daily_record(collaborator, record, punches, context)
    assert result.extra_minutes == (0 if effective == "OPE0613 - NOFLEX" else 20)
    assert result.ordinary_night_minutes == (0 if effective == "OPE0613 - NOFLEX" else 10)


@pytest.mark.parametrize("code", ["OPE0613", "OPEF0613", "OP_5.3_12.3"])
def test_explicit_seven_hour_shift_on_saturday_excludes_early_minutes(code):
    entry, exit_time = (time(5, 10), time(12, 40)) if code == "OP_5.3_12.3" else (time(5, 40), time(13, 10))
    collaborator, record, punches = _day(code, ((entry, exit_time),))
    record.work_date = date(2026, 8, 8)
    result = classify_daily_record(collaborator, record, punches, None)
    assert result.ordinary_minutes == 420
    assert result.extra_minutes == 0
    assert result.recognized_minutes.excluded_early_minutes == 20
