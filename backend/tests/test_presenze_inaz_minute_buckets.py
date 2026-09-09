from datetime import date, time
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
    PresenzeHoliday,
)
from app.modules.presenze.services.inaz_minute_buckets import (
    inaz_special_day,
    reconcile_inaz_minute_buckets,
)
from app.modules.presenze.services.schedule_engine import (
    build_schedule_context,
    classify_daily_record,
    classify_worked_minute_buckets,
    resolve_holiday,
)


@pytest.mark.parametrize("day,label", [(14, "Vigilia Ferragosto"), (16, "Recupero Ferragosto")])
def test_august_calendar_holidays_keep_existing_festive_classification(day, label):
    person = PresenzeCollaborator(id=uuid4(), contract_kind="operaio")
    record = PresenzeDailyRecord(
        collaborator_id=person.id,
        work_date=date(2026, 8, day),
        schedule_code="OPE0613",
        ordinary_minutes=420,
        mpe_minutes=4,
        raw_payload_json={"detail_day_summary": {"Ore Ordinarie": "07:00"}},
    )
    holiday = resolve_holiday(record.work_date, person, None)
    assert holiday.label == label
    assert holiday.holiday_kind == "ordinary"
    result = classify_daily_record(
        person,
        record,
        [PresenzeDailyPunch(sequence=1, entry_time=time(6), exit_time=time(13, 4))],
        None,
    )
    assert result.special_day is True
    assert (result.ordinary_minutes, result.extra_minutes) == (420, 4)
    assert (result.shift_festive_day_minutes, result.overtime_festive_minutes) == (420, 4)
    assert result.grants_recovery_day is False


def test_murgia_scheduled_saturday_preserves_inaz_six_hours_and_one_mpe_minute():
    collaborator = PresenzeCollaborator(
        id=uuid4(), employee_code="135", name="Operaio", contract_kind="operaio"
    )
    record = PresenzeDailyRecord(
        id=uuid4(),
        collaborator_id=collaborator.id,
        work_date=date(2026, 8, 8),
        schedule_code="OSAB5.3_11.3",
        ordinary_minutes=360,
        mpe_minutes=1,
        raw_payload_json={"detail_day_summary": {"Ore Ordinarie": "06:00"}},
    )
    punches = [
        PresenzeDailyPunch(
            daily_record_id=record.id, sequence=1, entry_time=time(5, 15), exit_time=time(11, 31)
        )
    ]
    result = classify_daily_record(collaborator, record, punches, None)
    assert (result.ordinary_minutes, result.extra_minutes, result.special_day) == (360, 1, False)
    assert result.overtime_day_minutes == 1
    assert result.overtime_festive_minutes == result.overtime_festive_night_minutes == 0
    assert result.ordinary_night_minutes == result.overtime_night_minutes == 0


@pytest.mark.parametrize("special", [False, True])
def test_inaz_totals_replace_unreconciled_raw_punch_categories(special):
    punches = [PresenzeDailyPunch(sequence=1, entry_time=time(5, 15), exit_time=time(11, 31))]
    raw = classify_worked_minute_buckets(punches, [], special_day=special)
    result = reconcile_inaz_minute_buckets(raw, 360, 1, special_day=special)
    assert result.actual_minutes == 376
    assert (result.ordinary_minutes, result.extra_minutes) == (360, 1)
    assert result.overtime_day_minutes + result.overtime_festive_minutes == 1
    assert result.shift_festive_day_minutes == (360 if special else 0)
    assert result.festive_minutes == (361 if special else 0)
    assert result.night_minutes == result.overtime_night_minutes == 0


def test_matching_breakdown_is_retained_including_night_work():
    punches = [PresenzeDailyPunch(sequence=1, entry_time=time(22), exit_time=time(23))]
    raw = classify_worked_minute_buckets(punches, [], special_day=False)
    result = reconcile_inaz_minute_buckets(raw, None, 60, special_day=False)
    assert result is raw
    assert result.overtime_night_minutes == 60


def test_month_context_without_local_assignments_keeps_only_in_month_holidays():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            db.add_all(
                [
                    PresenzeHoliday(
                        holiday_date=date(2026, 8, 15), label="Ferragosto", holiday_kind="ordinary"
                    ),
                    PresenzeHoliday(
                        holiday_date=date(2026, 7, 31), label="Fuori mese", holiday_kind="ordinary"
                    ),
                ]
            )
            db.commit()
            result = build_schedule_context(
                db,
                collaborator_ids=[uuid4()],
                date_from=date(2026, 8, 1),
                date_to=date(2026, 8, 31),
            )
            assert (
                result.assignments_by_collaborator
                == result.templates_by_id
                == result.rules_by_template_id
                == {}
            )
            assert set(result.holidays_by_key) == {(date(2026, 8, 15), None)}
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "code,contract,ordinary,day,holiday,expected",
    [
        ("OSAB5.3_11.3", "operaio", 360, 8, None, False),
        ("OSAB5.3_11.3", None, 360, 8, None, False),
        ("OSAB5.3_11.3", "operaio", 360, 15, "ordinary", True),
        ("OSAB5.3_11.3", "operaio", 360, 8, "suppressed", False),
        ("OSAB5.3_11.3", "operaio", 360, 9, None, True),
        ("IMP", "impiegato", 360, 8, None, True),
        ("SAB", "operaio", 360, 8, None, True),
        (None, "operaio", 360, 8, None, True),
        ("OSAB5.3_11.3", "operaio", None, 8, None, True),
    ],
)
def test_only_scheduled_operaio_saturdays_lose_automatic_festive_flag(
    code, contract, ordinary, day, holiday, expected
):
    person = PresenzeCollaborator(contract_kind=contract)
    record = PresenzeDailyRecord(
        work_date=date(2026, 8, day), schedule_code=code, ordinary_minutes=ordinary
    )
    assert inaz_special_day(record, person, True, holiday) is expected
    assert inaz_special_day(record, person, False, holiday) is False
