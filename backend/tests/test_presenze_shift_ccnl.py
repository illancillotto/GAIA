"""Shared golden CCNL cases and civil-day/calendar integration."""

import json
from datetime import date, time
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.modules.presenze.services.daily_details import classification_breakdown_values
from app.modules.presenze.services.schedule_engine import classify_daily_record
from app.modules.presenze.services.shift_ccnl import (
    SHIFT_CCNL_RATES,
    shift_calendar,
    shift_ccnl_assessment,
    shift_ccnl_breakdown,
)
from app.modules.presenze.services.shift_worker_rules import (
    shift_classification,
    shift_punch_intervals,
)

CASES = json.loads((Path(__file__).parent / "fixtures/shift-ccnl.json").read_text())


def punch(start, end):
    return SimpleNamespace(
        entry_time=time(start % 1440 // 60, start % 60),
        exit_time=time(end % 1440 // 60, end % 60),
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_shared_contractual_buckets(case):
    counts = shift_ccnl_breakdown(case["intervals"], case["calendar"], 420)
    assert counts == case["expected"]
    record = SimpleNamespace(schedule_code="TELEC_1" if case["intervals"] else "RIPTURN")
    result = shift_classification(
        record,
        [punch(*interval) for interval in case["intervals"]],
        special_day=case["calendar"][0],
        holiday_kind=None,
        grants_recovery_day=False,
        calendar=case["calendar"],
    )
    exported = classification_breakdown_values(result, "export_")
    assert exported["export_shift_calendar"] == case["calendar"]
    assert result.ordinary_minutes == sum(counts[:4])
    assert result.extra_minutes == sum(counts[4:])
    assert result.shift_ccnl["premium_minutes"] == dict(
        zip(
            (
                "ordinary_day",
                "ordinary_festive_day",
                "ordinary_night",
                "ordinary_festive_night",
                "overtime_day",
                "overtime_festive_day",
                "overtime_night",
                "overtime_festive_night",
            ),
            counts,
            strict=True,
        )
    )
    assert result.shift_ccnl["overtime_requires_prior_authorization"] is True


def test_saturday_and_sunday_are_distinct_and_company_holidays_win():
    collaborator = SimpleNamespace(company_code="53")
    assert shift_calendar(date(2026, 10, 3), collaborator, None) == [False, True]
    assert shift_calendar(date(2026, 10, 4), collaborator, None) == [True, False]
    context = SimpleNamespace(
        holidays_by_key={
            (date(2026, 10, 3), "53"): [SimpleNamespace(holiday_kind="ordinary")],
        }
    )
    assert shift_calendar(date(2026, 10, 3), collaborator, context) == [True, True]
    assert shift_calendar(date(2026, 10, 31), collaborator, None) == [False, True]
    assert shift_calendar(date(2026, 12, 31), collaborator, None) == [True, True]


def test_daily_classifier_uses_calendar_instead_of_weekend_or_raw_special_flag():
    collaborator = SimpleNamespace(company_code="53")
    record = SimpleNamespace(
        work_date=date(2026, 10, 3),
        schedule_code="TELEC_3",
        raw_payload_json={},
        shift_worker_type="acquaiolo",
    )
    result = classify_daily_record(collaborator, record, [punch(1320, 1800)], None)
    assert result.special_day is False
    assert result.ordinary_night_minutes == 120
    assert result.shift_festive_night_minutes == 300
    assert result.overtime_festive_night_minutes == 60


def test_invalid_and_legacy_assessments_do_not_claim_contractual_completeness():
    record = SimpleNamespace(schedule_code="TELEC_3")
    result = shift_classification(
        record,
        [SimpleNamespace(entry_time=None, exit_time=None)],
        special_day=False,
        holiday_kind=None,
        grants_recovery_day=False,
    )
    assert result.shift_ccnl is None
    assert result.ordinary_minutes is None
    assert "shift_ccnl" not in classification_breakdown_values(result)
    assert shift_punch_intervals([punch(1320, 1740), punch(1260, 1380)]) is None
    assert shift_ccnl_assessment([0] * 8, False)["calendar_attested"] is False
    assert SHIFT_CCNL_RATES["title_ii"]["percentages"] == [0, 10, 15, 20, 25, 50, 50, 75]
    assert SHIFT_CCNL_RATES["avventizio"]["percentages"] == [0, 39, 10, 15, 25, 50, 38, 66]


def test_company_calendar_includes_the_day_after_the_export_month():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.modules.presenze.models import (
        PresenzeCollaboratorScheduleAssignment,
        PresenzeHoliday,
        PresenzeOperaiRuleConfig,
    )
    from app.modules.presenze.services.schedule_engine import build_schedule_context

    engine = create_engine("sqlite://")
    PresenzeHoliday.__table__.create(engine)
    PresenzeOperaiRuleConfig.__table__.create(engine)
    PresenzeCollaboratorScheduleAssignment.__table__.create(engine)
    with Session(engine) as db:
        holiday = PresenzeHoliday(
            holiday_date=date(2026, 11, 2),
            company_code="53",
            label="Festivita aziendale",
            holiday_kind="ordinary",
        )
        db.add(holiday)
        db.commit()
        context = build_schedule_context(
            db, collaborator_ids=[], date_from=date(2026, 11, 1), date_to=date(2026, 11, 1)
        )
        assert shift_calendar(date(2026, 11, 1), SimpleNamespace(company_code="53"), context) == [
            True,
            True,
        ]
        db.delete(holiday)
        db.commit()


def test_shift_metadata_survives_the_daily_api_schema():
    from app.modules.presenze.shift_worker_schemas import ShiftWorkerFields

    assessment = shift_ccnl_assessment([0, 0, 120, 300, 0, 0, 0, 60], True)
    result = ShiftWorkerFields(
        shift_worker_type="telecontrollo", shift_calendar=[False, True], shift_ccnl=assessment
    ).model_dump()
    assert result["shift_ccnl"] == assessment
    assert result["shift_calendar"] == [False, True]


def test_shift_voucher_effective_date_and_other_contract_quality():
    from app.modules.presenze.services.shift_worker_rules import (
        daily_quality_kind,
        shift_meal_voucher,
    )

    record = SimpleNamespace(
        shift_worker_type="acquaiolo", work_date=date(2026, 8, 25), shift_punches=[punch(360, 780)]
    )
    assert shift_meal_voucher(record) is False
    record.work_date = date(2026, 8, 26)
    assert shift_meal_voucher(record) is True
    assert daily_quality_kind(None, record) == "shift"
    record.shift_worker_type = "none"
    assert daily_quality_kind(None, record) == "operaio"
    assert daily_quality_kind(SimpleNamespace(contract_kind="impiegato"), record) == "other"


def test_short_shifts_and_travel_require_voucher_verification():
    from test_presenze_shift_workers import simple

    from app.modules.presenze.services.meal_vouchers import meal_voucher_values
    from app.modules.presenze.services.shift_worker_rules import shift_meal_voucher, shift_quality

    record = simple(punches=[punch(360, 779)])
    assert shift_meal_voucher(record) is False

    record.shift_punches = [punch(360, 780)]
    assert shift_meal_voucher(record) is True
    record.trasferta_minutes = 60
    assert shift_meal_voucher(record) is False
    assert "rimborso vitto" in " ".join(shift_quality(record, record.shift_punches).notes)
    record.meal_voucher_manual = True
    assert meal_voucher_values(record, 0)["meal_voucher_count"] == 1
    record.trasferta_minutes = 0
    record.trasferta_montano = True
    assert shift_meal_voucher(record) is False


def test_shift_flexibility_note_follows_the_operational_effective_date():
    from test_presenze_shift_workers import simple

    from app.modules.presenze.services.shift_worker_rules import shift_quality

    punches = [punch(360, 780)]
    record = simple(punches=punches)
    record.work_date = date(2026, 9, 6)
    assert "Nessuna flessibilita" not in " ".join(shift_quality(record, punches).notes)
    record.work_date = date(2026, 9, 7)
    assert "Nessuna flessibilita" in " ".join(shift_quality(record, punches).notes)


def test_non_shift_worker_holiday_and_legacy_buckets_are_preserved():
    from uuid import uuid4

    from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyRecord
    from app.modules.presenze.services.schedule_engine import (
        _recognized_operai_buckets,
        classify_worked_minute_buckets,
    )

    person = PresenzeCollaborator(
        id=uuid4(), name="Test", employee_code="test", company_code="53", contract_kind="operaio"
    )
    record = PresenzeDailyRecord(
        id=uuid4(), collaborator_id=person.id, work_date=date(2026, 5, 1), schedule_code="OPE0714"
    )
    result = classify_daily_record(person, record, [punch(420, 840)], None)
    assert result.shift_calendar is None
    assert result.shift_festive_day_minutes == 420
    buckets = classify_worked_minute_buckets([], [], special_day=True)
    assert (
        _recognized_operai_buckets(SimpleNamespace(recognized_minutes=None), buckets, True)
        == buckets
    )
