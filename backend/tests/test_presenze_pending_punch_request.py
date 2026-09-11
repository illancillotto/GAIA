from datetime import date, time
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
)
from app.modules.presenze.services.gate_mobile_payloads import presenze_extra_minutes
from app.modules.presenze.services.operai_daily_policy import (
    PENDING_PUNCH_REQUEST_SOURCE,
    effective_extra_values,
)
from app.modules.presenze.services.schedule_engine import classify_daily_record

DETAIL = {"detail_day_summary": {"Ore Ordinarie": "00:00"}}


def _operaio() -> PresenzeCollaborator:
    return PresenzeCollaborator(
        id=uuid4(),
        employee_code="1395",
        name="MASTROLILLI MATTIA",
        contract_kind="operaio",
        operai_group="catasto_magazzino",
    )


def _unscheduled_saturday(person: PresenzeCollaborator, **values) -> PresenzeDailyRecord:
    fields = {
        "id": uuid4(),
        "collaborator_id": person.id,
        "work_date": date(2026, 8, 29),
        "schedule_code": "SAB",
        "ordinary_minutes": None,
        "straordinario_minutes": 0,
        "mpe_minutes": 0,
        "request_type": "Var. Timbrature",
        "request_description": "Inserimento - 06:00 E",
        "request_status": "RIC",
        "raw_payload_json": DETAIL,
    }
    return PresenzeDailyRecord(**{**fields, **values})


def _punches(record: PresenzeDailyRecord, *pairs) -> list[PresenzeDailyPunch]:
    return [
        PresenzeDailyPunch(
            daily_record_id=record.id, sequence=index, entry_time=entry, exit_time=exit_
        )
        for index, (entry, exit_) in enumerate(pairs, start=1)
    ]


def test_mastrolilli_pending_saturday_insertion_keeps_worked_minutes() -> None:
    person = _operaio()
    record = _unscheduled_saturday(person)

    result = classify_daily_record(person, record, _punches(record, (time(6), time(12, 4))), None)

    assert result.source == PENDING_PUNCH_REQUEST_SOURCE
    assert (result.ordinary_minutes, result.extra_minutes, result.special_day) == (None, 364, True)
    assert (result.overtime_festive_minutes, result.overtime_festive_night_minutes) == (364, 0)
    assert result.overtime_day_minutes == result.overtime_night_minutes == 0
    values = effective_extra_values(record, result)
    assert values == {
        "effective_straordinario_minutes": 0,
        "effective_mpe_minutes": 364,
        "effective_extra_minutes": 364,
        "ordinary_minutes": None,
    }
    assert presenze_extra_minutes(SimpleNamespace(**values), result) == 364


def test_pending_insertion_splits_pre_dawn_saturday_minutes_as_festive_night() -> None:
    person = _operaio()
    record = _unscheduled_saturday(person)

    result = classify_daily_record(person, record, _punches(record, (time(5, 50), time(12))), None)

    assert result.extra_minutes == 370
    assert (result.overtime_festive_minutes, result.overtime_festive_night_minutes) == (360, 10)


def test_pending_request_is_read_from_inaz_detail_when_record_fields_are_empty() -> None:
    person = _operaio()
    record = _unscheduled_saturday(
        person,
        request_type=None,
        request_status=None,
        raw_payload_json={
            **DETAIL,
            "detail_requests": [{"Tipo": "Var. Timbrature", "Stato": "RIC"}],
        },
    )

    result = classify_daily_record(person, record, _punches(record, (time(6), time(12))), None)

    assert (result.source, result.extra_minutes) == (PENDING_PUNCH_REQUEST_SOURCE, 360)


def test_pending_insertion_on_worked_sunday_is_festive_overtime() -> None:
    person = _operaio()
    record = _unscheduled_saturday(person, work_date=date(2026, 7, 26), schedule_code="DOM")

    result = classify_daily_record(
        person, record, _punches(record, (time(7, 52), time(17, 30))), None
    )

    assert (result.source, result.special_day) == (PENDING_PUNCH_REQUEST_SOURCE, True)
    assert (result.extra_minutes, result.overtime_festive_minutes) == (578, 578)


@pytest.mark.parametrize(
    ("values", "pairs", "extra"),
    [
        ({"work_date": date(2026, 8, 17), "schedule_code": "ADD_7"}, [(time(3), time(10))], None),
        ({"request_status": "ACC"}, [(time(6), time(12))], None),
        ({"request_type": "Eventi"}, [(time(6), time(12))], None),
        (
            {"request_type": None, "request_status": None, "raw_payload_json": None},
            [(time(6), time(12))],
            None,
        ),
        ({"straordinario_minutes": 60}, [(time(6), time(12))], 60),
        ({"ordinary_minutes": 360}, [(time(6), time(12))], None),
        ({"override_mpe_minutes": 0}, [(time(6), time(12))], None),
        ({}, [(time(6), None)], None),
        ({}, [], None),
        ({}, [(time(6), time(6))], None),
    ],
)
def test_pending_rule_leaves_accounted_or_unproven_days_unchanged(values, pairs, extra) -> None:
    person = _operaio()
    record = _unscheduled_saturday(person, **values)

    result = classify_daily_record(person, record, _punches(record, *pairs), None)

    assert result.source != PENDING_PUNCH_REQUEST_SOURCE
    assert result.extra_minutes == extra
    assert effective_extra_values(record, result)["effective_extra_minutes"] == extra
