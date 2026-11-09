"""Ordinary permits and profile vouchers: synthetic reproductions of October incidents."""

from datetime import date

import pytest
from test_presenze_personnel_profiles import profile
from test_presenze_shift_workers import punch

from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyRecord
from app.modules.presenze.services.inaz_absences import covered_inaz_absence_minutes
from app.modules.presenze.services.operational_quality import build_operai_operational_quality
from app.modules.presenze.services.ordinary_permits import (
    ordinary_permit_minutes,
    permit_approved,
    permit_clock,
    permit_interval,
)


def permit_day(day=17, end="13:30", theory=390):
    return PresenzeDailyRecord(
        work_date=date(2026, 10, day),
        schedule_code="OPESAB" if day == 17 else "OPE0714",
        teo_minutes=theory,
        ordinary_minutes=0,
        absence_minutes=theory,
        justified_minutes=None,
        request_status="RIC",
        request_authorized_by="Responsabile",
        request_description="P. ORD - Permesso ordinario",
        resolved_absence_cause="permesso",
        raw_payload_json={
            "detail_requests": [
                {
                    "KEvento": "P. ORD - Permesso ordinario",
                    "Stato": "RIC",
                    "Author": "Responsabile",
                    "Dalle": "07:00",
                    "Alle": end,
                }
            ]
        },
    )


@pytest.mark.parametrize("day,end,theory", [(17, "13:30", 390), (27, "14:00", 420)])
def test_first_level_permit_covers_the_real_daily_theory(day, end, theory):
    record = permit_day(day, end, theory)
    record.personnel_profile = profile()
    assert ordinary_permit_minutes(record) == theory
    assert covered_inaz_absence_minutes(record, ("permesso",), theory) == theory
    person = PresenzeCollaborator(contract_kind="operaio", operai_group=None)
    result = build_operai_operational_quality(person, record, [])
    assert (result.expected_minutes, result.missing_minutes, result.status) == (theory, 0, "ok")
    assert record.justified_minutes is None and record.absence_minutes == theory


def test_partial_permit_does_not_borrow_the_full_residual_absence():
    record = permit_day(27, "09:00", 420)
    person = PresenzeCollaborator(contract_kind="operaio", operai_group="agrario")
    assert ordinary_permit_minutes(record) == 120
    result = build_operai_operational_quality(person, record, [punch("10:00", "14:00")])
    assert result.missing_minutes == 60 and result.status == "blocking"
    record.request_authorized_by = None
    assert ordinary_permit_minutes(record) == 0
    record.request_status = "ACC"
    record.justified_minutes = 180
    assert ordinary_permit_minutes(record) == 180
    record.raw_payload_json = []
    assert ordinary_permit_minutes(record) == 180


def test_interval_union_and_invalid_or_cancelled_requests():
    record = permit_day()
    row = record.raw_payload_json["detail_requests"][0]
    record.raw_payload_json["detail_requests"] += [
        dict(row),
        {**row, "Dalle": "13:00", "Alle": "14:00"},
    ]
    assert ordinary_permit_minutes(record) == 420
    for variant in [
        {"KEvento": "Var. Timbrature"},
        {"Stato": "RIF"},
        {"richiestacanc": "SI"},
        {"Dalle": "bad"},
        {"Alle": "bad"},
        {"Dalle": "14:00", "Alle": "07:00"},
    ]:
        assert permit_interval({**row, **variant}) is None
    assert permit_interval(
        {"Descrizione": "Permesso ordinario", "Stato": "AUT", "Dalle": "07:00", "Alle": "08:00"}
    ) == (420, 480)
    assert permit_interval({}) is None
    assert permit_clock(None) is None
    assert permit_clock("24:00") is None
    assert not permit_approved(None, None)
    assert not permit_approved("RIC", " ")
