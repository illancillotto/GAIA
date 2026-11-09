"""Ordinary permits and profile vouchers: synthetic reproductions of October incidents."""

from datetime import date, time
from types import SimpleNamespace

import pytest
from test_presenze_personnel_profiles import profile, technician_day
from test_presenze_shift_workers import punch

from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyRecord
from app.modules.presenze.services.inaz_absences import covered_inaz_absence_minutes
from app.modules.presenze.services.meal_vouchers import meal_voucher_values
from app.modules.presenze.services.operational_quality import build_operai_operational_quality
from app.modules.presenze.services.ordinary_permits import (
    ordinary_permit_minutes,
    permit_approved,
    permit_clock,
    permit_interval,
)
from app.modules.presenze.services.shift_voucher_policy import shift_voucher_profile


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


@pytest.mark.parametrize("entry,exit", [("06:00", "13:00"), ("14:00", "21:00"), ("22:00", "05:00")])
def test_dated_profile_grants_voucher_independently_of_schedule_band(entry, exit):
    record = technician_day("OPE0613", 420)
    record.shift_punches = [punch(entry, exit)]
    values = meal_voucher_values(record, 0)
    assert values["shift_worker_type"] == "none"
    assert values["meal_voucher_shift"] and values["meal_voucher_count"] == 1
    assert values["meal_voucher_sources"] == ["shift"]
    assert record.schedule_code == "OPE0613"


def test_profile_duration_revocation_travel_and_untrusted_assignment():
    record = technician_day("OPE0613", 420)
    record.shift_punches = [punch("06:00", "12:59")]
    assert meal_voucher_values(record, 120)["meal_voucher_count"] == 0
    record.shift_punches[0].exit_time = time(13)
    record.shift_worker_source = "gate"
    assert not shift_voucher_profile(record)
    record.shift_worker_type = "tecnico_turnista"
    assert shift_voucher_profile(record)
    record.trasferta_minutes = 60
    assert meal_voucher_values(record, 0)["meal_voucher_count"] == 0
    record.meal_voucher_manual = True
    assert meal_voucher_values(record, 0)["meal_voucher_count"] == 1
    assert not shift_voucher_profile(
        SimpleNamespace(
            shift_worker_type="tecnico_turnista",
            shift_worker_source="gate",
            work_date=date(2026, 10, 1),
        )
    )


def test_shift_detail_preserves_contract_date_and_travel_review():
    from app.modules.presenze.services.shift_worker_rules import shift_quality

    record = technician_day("TELEC_1", 420)
    record.work_date = date(2026, 9, 6)
    record.shift_punches = [punch("06:00", "13:00")]
    record.trasferta_minutes = 60
    result = shift_quality(record, record.shift_punches)
    assert result.status == "ok"
    assert not any("flessibilita" in note for note in result.notes)
    assert any("rimborso vitto" in note for note in result.notes)
    assert meal_voucher_values(record, 0)["meal_voucher_count"] == 0
