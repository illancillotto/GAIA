"""Ordinary-plus-overtime entitlement and shift rules through real serializers."""

from datetime import date, time
from types import SimpleNamespace

import pytest
from openpyxl import Workbook
from test_presenze_api import (
    TestingSessionLocal,
    _create_user,
    _login,
    client,
    setup_database,  # noqa: F401 - shared isolated API database fixture
)
from test_presenze_meal_vouchers import _record
from test_presenze_personnel_profiles import profile, technician_day
from test_presenze_shift_workers import punch

from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
)
from app.modules.presenze.personnel_profile_models import PresenzePersonnelProfile
from app.modules.presenze.router.helpers.daily_records import (
    _build_catasto_saturday_coverage_counts,
)
from app.modules.presenze.services.meal_vouchers import meal_voucher_values
from app.modules.presenze.services.shift_worker_rules import shift_quality
from app.modules.presenze.services.xlsm_export import (
    ExportTimesheetRow,
    write_archive2_daily_values,
)
from app.services.gate_mobile_sync import build_presenze_giornaliere_push_payload


@pytest.mark.parametrize(
    "ordinary,extra,expected",
    [
        (420, 120, 1),
        (385, 148, 1),
        (None, 732, 0),
        (385, 204, 1),
        (0, 120, 0),
        (0, 732, 0),
        (1, 120, 1),
        (419, 180, 1),
        (420, 119, 0),
        (420, None, 0),
    ],
)
def test_non_shift_requires_ordinary_work_and_two_recognized_extra_hours(ordinary, extra, expected):
    record = SimpleNamespace(work_date=date(2026, 10, 1))
    result = meal_voucher_values(
        record, SimpleNamespace(extra_minutes=extra, ordinary_minutes=ordinary)
    )
    assert result["meal_voucher_count"] == expected
    assert result["meal_voucher_sources"] == (["automatic"] if expected else [])


@pytest.mark.parametrize(
    "schedule,entry,exit,expected",
    [
        ("OPE0613", "06:00", "15:00", 1),
        ("OPE0613", "06:00", "15:30", 1),
        ("OPE0714", "07:00", "16:00", 0),
        ("OPE0714", "07:00", "16:30", 1),
    ],
)
def test_non_shift_api_and_sync_use_recognized_extra_without_a_second_lunch_deduction(
    schedule, entry, exit, expected
):
    actor = _create_user("voucher-lunch")
    record_id, _ = _record(actor.id)
    with TestingSessionLocal() as db:
        record = db.get(PresenzeDailyRecord, record_id)
        record.schedule_code = schedule
        record.mpe_minutes = 120
        db.add(
            PresenzeDailyPunch(
                daily_record_id=record_id,
                sequence=1,
                entry_time=time.fromisoformat(entry),
                exit_time=time.fromisoformat(exit),
            )
        )
        db.commit()
        payload = build_presenze_giornaliere_push_payload(db, month="2026-10")
        assert payload["giornaliere"][0]["meal_voucher_count"] == expected
        if not expected:
            assert payload["giornaliere"][0]["export_extra_minutes"] == 90
    response = client.get(
        f"/presenze/giornaliere/{record_id}",
        headers={"Authorization": "Bearer " + _login(actor.username)},
    )
    assert response.status_code == 200, response.text
    assert response.json()["meal_voucher_count"] == expected


@pytest.mark.parametrize("code", ["SAB", "OPE0613", "TELEC_1"])
@pytest.mark.parametrize("minutes,expected", [(186, 0), (419, 0), (420, 1)])
def test_technician_voucher_uses_profile_even_on_a_non_shift_schedule(code, minutes, expected):
    record = technician_day(code, 420)
    record.shift_punches = [punch("06:00", f"{6 + minutes // 60:02}:{minutes % 60:02}")]
    result = meal_voucher_values(record, SimpleNamespace(extra_minutes=186, ordinary_minutes=0))
    assert result["meal_voucher_count"] == expected
    assert result["meal_voucher_sources"] == (["shift"] if expected else [])


def test_rest_saturday_without_work_earns_neither_voucher_nor_calendar_credit():
    actor = _create_user("voucher-rest")
    record_id, collaborator_id = _record(actor.id)
    with TestingSessionLocal() as db:
        db.get(PresenzeCollaborator, collaborator_id).operai_group = "catasto_magazzino"
        record = db.get(PresenzeDailyRecord, record_id)
        record.work_date = date(2026, 10, 24)
        record.schedule_code = "SAB"
        record.ordinary_minutes = 0
        db.commit()
        person = db.get(PresenzeCollaborator, collaborator_id)
        counts = _build_catasto_saturday_coverage_counts(db, [record], {collaborator_id: person})
        assert counts[(collaborator_id, 2026, 10)] == 0
    response = client.get(
        f"/presenze/giornaliere/{record_id}",
        headers={"Authorization": "Bearer " + _login(actor.username)},
    )
    assert response.status_code == 200, response.text
    assert response.json()["meal_voucher_count"] == 0
    assert response.json()["operational_worked_minutes"] is None


def test_profile_revocation_travel_review_and_manual_grants_keep_their_precedence():
    record = technician_day("TELEC_1", 420)
    record.work_date = date(2026, 9, 6)
    record.shift_punches = [punch("06:00", "13:00")]
    totals = SimpleNamespace(ordinary_minutes=420, extra_minutes=0)
    record.shift_worker_source = "gate"
    assert meal_voucher_values(record, totals)["meal_voucher_count"] == 0
    record.shift_worker_type = "telecontrollo"
    assert meal_voucher_values(record, totals)["meal_voucher_count"] == 1
    record.trasferta_minutes = 60
    quality = shift_quality(record, record.shift_punches)
    assert not any("flessibilita" in note for note in quality.notes)
    assert any("rimborso vitto" in note for note in quality.notes)
    assert meal_voucher_values(record, totals)["meal_voucher_count"] == 0
    record.meal_voucher_manual = True
    assert meal_voucher_values(record, totals)["meal_voucher_sources"] == ["manual"]


@pytest.mark.parametrize("technician", [False, True])
@pytest.mark.parametrize(
    "work_date,schedule,minutes",
    [(date(2026, 10, 24), "SAB", 186), (date(2026, 10, 25), "DOM", 732)],
)
def test_api_matrix_mobile_snapshot_and_xlsm_agree_on_overtime_only_days(
    technician, work_date, schedule, minutes
):
    actor = _create_user("voucher-policy")
    record_id, collaborator_id = _record(actor.id)
    with TestingSessionLocal() as db:
        record = db.get(PresenzeDailyRecord, record_id)
        record.work_date = work_date
        record.schedule_code = schedule
        record.ordinary_minutes = 0
        record.mpe_minutes = minutes
        db.add(
            PresenzeDailyPunch(
                daily_record_id=record_id,
                sequence=1,
                entry_time=time(6, 0),
                exit_time=time(6 + minutes // 60, minutes % 60),
            )
        )
        if technician:
            fields = vars(profile()).copy()
            fields["supervisor_user_id"] = actor.id
            fields["source_note"] = "Synthetic meal voucher regression"
            db.add(PresenzePersonnelProfile(collaborator_id=collaborator_id, **fields))
        db.commit()
        snapshot = build_presenze_giornaliere_push_payload(db, month="2026-10")
        row = next(row for row in snapshot["giornaliere"] if row["record_id"] == str(record_id))
        expected = int(technician and minutes >= 420)
        assert row["meal_voucher_count"] == expected
        assert row["meal_voucher_sources"] == (["shift"] if expected else [])
        person = db.get(PresenzeCollaborator, collaborator_id)
        workbook = Workbook()
        write_archive2_daily_values(workbook.active, 5, ExportTimesheetRow(person, [record], {}))
        assert workbook.active.cell(5, 349 + work_date.day - 1).value == expected
        workbook.close()
    headers = {"Authorization": "Bearer " + _login(actor.username)}
    response = client.get(f"/presenze/giornaliere/{record_id}", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["meal_voucher_count"] == expected
    response = client.get(
        "/presenze/giornaliere/matrix",
        headers=headers,
        params={"date_from": work_date.isoformat(), "date_to": work_date.isoformat()},
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["meal_voucher_count"] == expected
