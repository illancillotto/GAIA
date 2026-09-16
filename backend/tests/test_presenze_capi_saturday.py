"""Biweekly individual Saturdays take precedence over monthly operaio defaults."""

import uuid
from datetime import date, time, timedelta

import pytest

from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeCollaboratorScheduleAssignment,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
    PresenzeScheduleRule,
    PresenzeScheduleTemplate,
)
from app.modules.presenze.services.operai_schedule_policy import has_individual_saturday
from app.modules.presenze.services.operational_quality import build_daily_operational_quality
from app.modules.presenze.services.schedule_engine import ScheduleContext, classify_daily_record


def scenario(anchor=date(2026, 9, 12), *, group="agrario"):
    collaborator = PresenzeCollaborator(
        id=uuid.uuid4(),
        employee_code="test",
        name="Capo operaio",
        contract_kind="operaio",
        operai_group=group,
    )
    template = PresenzeScheduleTemplate(id=1, code="CAPI_A", label="Capi A", is_active=True)
    assignment = PresenzeCollaboratorScheduleAssignment(
        id=1,
        collaborator_id=collaborator.id,
        template_id=1,
        valid_from=anchor,
    )
    rule = PresenzeScheduleRule(
        id=1,
        template_id=1,
        weekday=5,
        recurrence_kind="alternating_weeks",
        interval_weeks=2,
        anchor_date=anchor,
        start_time=time(7),
        end_time=time(13, 30),
    )
    context = ScheduleContext({}, {str(collaborator.id): [assignment]}, {1: template}, {1: [rule]})
    return collaborator, context, template, rule


def classify(collaborator, context, work_date, code="OPESAB", *, punches=True):
    record = PresenzeDailyRecord(
        id=uuid.uuid4(),
        collaborator_id=collaborator.id,
        work_date=work_date,
        schedule_code=code,
        raw_payload_json={},
    )
    pairs = [PresenzeDailyPunch(entry_time=time(7), exit_time=time(14))] if punches else []
    result = classify_daily_record(collaborator, record, pairs, context)
    quality = build_daily_operational_quality(
        collaborator,
        record,
        pairs,
        classification=result,
        catasto_month_saturday_coverage_count=2,
    )
    return result, quality


@pytest.mark.parametrize("anchor", [date(2026, 9, 12), date(2026, 12, 26)])
@pytest.mark.parametrize("weeks", range(6))
@pytest.mark.parametrize(
    "code,expected",
    [
        ("OPESAB", 390),
        ("SAB", 390),
        ("RIPTURN", 390),
        ("OPE0714", 390),
        ("OPSABE", 390),
        ("OPESACE", 360),
        ("OSAB5.3_11.3", 360),
    ],
)
def test_rotation_across_month_and_year(anchor, weeks, code, expected):
    collaborator, context, _, _ = scenario(anchor)
    result, quality = classify(collaborator, context, anchor + timedelta(weeks=weeks), code)
    holiday = anchor + timedelta(weeks=weeks) == date(2026, 12, 26)
    ordinary = expected if weeks % 2 == 0 and not holiday else 0
    assert result.ordinary_minutes == ordinary
    assert result.extra_minutes == 420 - ordinary
    assert result.overtime_day_minutes == (0 if holiday else 420 - ordinary)
    assert result.overtime_festive_minutes == (420 if holiday else 0)
    assert result.special_day is holiday
    assert quality.expected_minutes == ordinary
    assert quality.mpe_minutes == 420 - ordinary
    assert quality.missing_minutes == 0


def test_two_groups_remain_opposite():
    a, context_a, _, _ = scenario(date(2026, 9, 12))
    b, context_b, _, _ = scenario(date(2026, 9, 19))
    for work_date in [date(2026, 9, 19), date(2026, 9, 26), date(2026, 10, 3)]:
        first, _ = classify(a, context_a, work_date)
        second, _ = classify(b, context_b, work_date)
        assert sorted([first.ordinary_minutes, second.ordinary_minutes]) == [0, 390]


@pytest.mark.parametrize("weeks,expected", [(0, 360), (1, 0), (2, 360)])
def test_empty_catasto_saturday_does_not_use_monthly_coverage(weeks, expected):
    collaborator, context, _, _ = scenario(group="catasto_magazzino")
    _, quality = classify(
        collaborator, context, date(2026, 9, 12) + timedelta(weeks=weeks), punches=False
    )
    assert quality.expected_minutes == expected
    assert quality.mpe_minutes == 0


def test_weekdays_and_non_operai_keep_existing_rules():
    collaborator, context, _, _ = scenario()
    result, quality = classify(collaborator, context, date(2026, 9, 14), "OPE0714")
    assert result.ordinary_minutes == 420
    assert quality.expected_minutes == 420
    collaborator.contract_kind = "impiegato"
    result, _ = classify(collaborator, context, date(2026, 9, 19), "IMP1")
    assert result.source == "imported"
    assert result.operai_day_policy.rule is None


@pytest.mark.parametrize(
    "change",
    [
        "inactive",
        "future",
        "expired",
        "missing",
        "weekly",
        "other_interval",
        "missing_anchor",
        "wrong_anchor",
    ],
)
def test_rotation_requires_valid_explicit_configuration(change):
    _collaborator, _context, template, rule = scenario()
    record = PresenzeDailyRecord(work_date=date(2026, 9, 19))
    if change == "inactive":
        template.is_active = False
    elif change == "future":
        template.valid_from = date(2026, 9, 20)
    elif change == "expired":
        template.valid_to = date(2026, 9, 18)
    elif change == "missing":
        template = None
    elif change == "weekly":
        rule.recurrence_kind = "weekly"
    elif change == "other_interval":
        rule.interval_weeks = 3
    elif change == "missing_anchor":
        rule.anchor_date = None
    else:
        rule.anchor_date = date(2026, 9, 13)
    assert not has_individual_saturday(record, template, [rule])


def test_new_assignment_changes_rotation_without_rewriting_history():
    collaborator, context, _, _ = scenario()
    other = PresenzeScheduleTemplate(id=2, code="CAPI_B", label="Capi B", is_active=True)
    context.templates_by_id[2] = other
    context.rules_by_template_id[2] = [
        PresenzeScheduleRule(
            id=2,
            template_id=2,
            weekday=5,
            recurrence_kind="alternating_weeks",
            interval_weeks=2,
            anchor_date=date(2026, 10, 3),
            start_time=time(7),
            end_time=time(13, 30),
        )
    ]
    context.assignments_by_collaborator[str(collaborator.id)].insert(
        0,
        PresenzeCollaboratorScheduleAssignment(
            id=2,
            collaborator_id=collaborator.id,
            template_id=2,
            valid_from=date(2026, 10, 1),
        ),
    )
    for day in [date(2026, 9, 26), date(2026, 10, 3), date(2026, 10, 17)]:
        result, _ = classify(collaborator, context, day)
        assert result.ordinary_minutes == 390
    result, _ = classify(collaborator, context, date(2026, 10, 10))
    assert result.ordinary_minutes == 0


@pytest.mark.parametrize(
    "weeks,absence,expected,missing", [(0, 390, 390, 0), (0, 120, 390, 270), (1, 0, 0, 0)]
)
def test_absence_only_covers_scheduled_saturday(weeks, absence, expected, missing):
    collaborator, context, _, _ = scenario()
    record = PresenzeDailyRecord(
        id=uuid.uuid4(),
        collaborator_id=collaborator.id,
        work_date=date(2026, 9, 12) + timedelta(weeks=weeks),
        schedule_code="OPESAB",
        resolved_absence_cause="ferie",
        absence_minutes=absence,
    )
    result = classify_daily_record(collaborator, record, [], context)
    quality = build_daily_operational_quality(collaborator, record, [], classification=result)
    assert quality.expected_minutes == expected
    assert quality.missing_minutes == missing
    assert quality.mpe_minutes == 0


def test_holiday_can_be_explicitly_scheduled():
    collaborator, context, _, rule = scenario(date(2026, 12, 26))
    rule.applies_on_holiday = True
    result, quality = classify(collaborator, context, date(2026, 12, 26))
    assert result.ordinary_minutes == 390
    assert result.overtime_festive_minutes == 30
    assert result.special_day is True
    assert quality.expected_minutes == 390


def test_assignment_dates_and_no_assignment_preserve_legacy_calendar():
    collaborator, context, _, _ = scenario()
    assignment = context.assignments_by_collaborator[str(collaborator.id)][0]
    assignment.valid_to = date(2026, 9, 18)
    for day in [date(2026, 9, 5), date(2026, 9, 19)]:
        result, _ = classify(collaborator, context, day)
        assert result.ordinary_minutes == 390  # Generic first/third Saturday.
        assert not result.operai_day_policy.individual_saturday
    context.assignments_by_collaborator.clear()
    result, _ = classify(collaborator, context, date(2026, 9, 26))
    assert result.ordinary_minutes == 0


def test_persisted_calendar_reaches_daily_quality_and_export():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.db.base import Base
    from app.modules.presenze.router.helpers.daily_records import (
        _build_classification_map,
        _build_operational_quality_map,
    )
    from app.modules.presenze.services.operai_daily_policy import effective_extra_values

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    collaborator, context, template, rule = scenario()
    assignment = context.assignments_by_collaborator[str(collaborator.id)][0]
    with Session(engine) as db:
        db.add_all([collaborator, template, rule, assignment])
        rows = [
            PresenzeDailyRecord(
                id=uuid.uuid4(),
                collaborator_id=collaborator.id,
                work_date=day,
                schedule_code="OPESAB",
            )
            for day in [date(2026, 9, 12), date(2026, 9, 19), date(2026, 9, 26)]
        ]
        db.add_all(rows)
        db.add_all(
            [
                PresenzeDailyPunch(
                    daily_record_id=row.id,
                    sequence=1,
                    entry_time=time(7),
                    exit_time=time(14),
                )
                for row in rows
            ]
        )
        db.commit()
        classifications = _build_classification_map(db, rows)
        qualities = _build_operational_quality_map(db, rows, classifications=classifications)
        for row, ordinary in zip(rows, [390, 0, 390], strict=True):
            result = classifications[row.id]
            assert result.ordinary_minutes == ordinary
            assert qualities[row.id].expected_minutes == ordinary
            values = effective_extra_values(row, result)
            assert values["effective_mpe_minutes"] == 420 - ordinary
    engine.dispose()


@pytest.mark.parametrize("override,extra", [(None, 420), (0, 0), (120, 120)])
def test_off_turn_export_overrides_imported_ordinary_and_preserves_admin_adjustments(
    override, extra
):
    from app.modules.presenze.services.operai_daily_policy import effective_extra_values

    collaborator, context, _, _ = scenario()
    record = PresenzeDailyRecord(
        id=uuid.uuid4(),
        collaborator_id=collaborator.id,
        work_date=date(2026, 9, 19),
        schedule_code="OPESAB",
        ordinary_minutes=420,
        mpe_minutes=999,
        straordinario_minutes=999,
        override_mpe_minutes=override,
    )
    punches = [PresenzeDailyPunch(entry_time=time(7), exit_time=time(14))]
    result = classify_daily_record(collaborator, record, punches, context)
    values = effective_extra_values(record, result)
    assert values["ordinary_minutes"] == 0
    assert values["effective_extra_minutes"] == extra
    assert values["effective_mpe_minutes"] == extra
    assert values["effective_straordinario_minutes"] == 0


def test_off_turn_recognition_deduplicates_complete_punches():
    collaborator, context, _, _ = scenario()
    record = PresenzeDailyRecord(
        collaborator_id=collaborator.id,
        work_date=date(2026, 9, 19),
        schedule_code="OPESAB",
    )
    punches = [
        PresenzeDailyPunch(entry_time=time(7), exit_time=time(12)),
        PresenzeDailyPunch(entry_time=time(11), exit_time=time(14)),
    ]
    result = classify_daily_record(collaborator, record, punches, context)
    assert result.extra_minutes == 420
    punches[1].exit_time = None
    result = classify_daily_record(collaborator, record, punches, context)
    assert result.recognized_minutes is None


@pytest.mark.parametrize("day,expected", [(date(2026, 9, 5), 390), (date(2026, 9, 12), 0)])
def test_database_without_assignments_keeps_generic_saturday_rules(day, expected):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.db.base import Base
    from app.modules.presenze.services.schedule_engine import build_schedule_context

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    collaborator, _, _, _ = scenario()
    with Session(engine) as db:
        db.add(collaborator)
        db.commit()
        context = build_schedule_context(
            db,
            collaborator_ids=[collaborator.id],
            date_from=day,
            date_to=day,
        )
        result, quality = classify(collaborator, context, day)
        assert result.ordinary_minutes == expected
        assert result.extra_minutes == 420 - expected
        assert quality.expected_minutes == expected
        assert not result.operai_day_policy.individual_saturday
    engine.dispose()


def test_non_operaio_quality_without_classification_uses_imported_theoretical_minutes():
    collaborator = PresenzeCollaborator(
        id=uuid.uuid4(),
        employee_code="test-impiegato",
        name="Impiegato",
        contract_kind="impiegato",
    )
    record = PresenzeDailyRecord(
        id=uuid.uuid4(),
        collaborator_id=collaborator.id,
        work_date=date(2026, 9, 16),
        schedule_code="IMP1",
        teo_minutes=385,
    )
    punches = [PresenzeDailyPunch(entry_time=time(7), exit_time=time(14))]
    quality = build_daily_operational_quality(collaborator, record, punches)
    assert quality.status == "unknown"
    assert quality.formula_code is None
    assert quality.expected_minutes == 385
    assert quality.worked_minutes == 420
    assert quality.mpe_minutes == 35
