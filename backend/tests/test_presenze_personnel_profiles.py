"""Dated HR profiles, distinct OPE calendar, and no effect on other workers."""

from datetime import date, time
from types import SimpleNamespace

import pytest
from test_presenze_api import (  # noqa: F401 - shared isolated database fixture
    TestingSessionLocal,
    _create_user,
    setup_database,
)
from test_presenze_meal_vouchers import _record

from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyRecord
from app.modules.presenze.personnel_profile_models import PresenzePersonnelProfile
from app.modules.presenze.services.gate_mobile_payloads import _gate_record_feature_values
from app.modules.presenze.services.operai_rules import resolve_operai_rule
from app.modules.presenze.services.operai_schedule_policy import build_operai_day_policy
from app.modules.presenze.services.personnel_profiles import (
    personnel_profile,
    personnel_profile_values,
    technician_profile,
)
from app.modules.presenze.services.technician_operai_rules import (
    individual_saturday_eligible,
    resolve_technician_operai_rule,
)


def profile(**fields):
    return SimpleNamespace(
        profile_type="tecnico_turnista",
        profile_label="Tecnico/Turnista",
        duty="Tecnico / Turnista",
        employment_relationship="avventizio",
        personnel_area="IMPIANTI",
        supervisor_user_id=232,
        valid_from=date(2026, 1, 1),
        valid_to=None,
        source_document_sha256="a" * 64,
        shift_schedule_codes=[
            "TELEC_1",
            "TELEC_2",
            "TELEC_3",
            "ADD_9",
            "IRRSE",
            "IRRSEA",
            "SMONTO",
            "RIPTURN",
        ],
        **fields,
    )


def day(code="OPESAB", work_date=date(2026, 10, 3), hr=True):
    return SimpleNamespace(
        schedule_code=code,
        work_date=work_date,
        raw_payload_json={},
        personnel_profile=profile() if hr else None,
    )


@pytest.mark.parametrize(
    "work_date,expected,scheduled",
    [
        (date(2026, 10, 3), 390, True),
        (date(2026, 10, 10), 0, False),
        (date(2026, 10, 17), 390, True),
        (date(2026, 10, 24), 0, False),
        (date(2026, 10, 31), 0, False),
    ],
)
def test_only_first_and_third_saturday_for_technicians(work_date, expected, scheduled):
    record = day(work_date=work_date)
    worker = SimpleNamespace(contract_kind="operaio", operai_group=None)
    rule = resolve_operai_rule(worker, record)
    assert (rule.expected_minutes, rule.saturday_is_scheduled) == (expected, scheduled)
    assert rule.rule.operai_group == "tecnico_turnista"
    # A stale individual alternating-week template cannot turn 2/4/5 into workdays.
    assert individual_saturday_eligible(record, SimpleNamespace(is_active=True)) is False
    policy = build_operai_day_policy(rule, record, [], [SimpleNamespace(start_time=None)], False)
    assert policy.rule.expected_minutes == expected
    assert policy.individual_saturday is False


@pytest.mark.parametrize(
    "code,date_value,expected",
    [
        ("OPE0714", date(2026, 10, 1), 420),
        ("OPE0714", date(2026, 10, 3), 420),
        ("OPE0714", date(2026, 10, 10), 0),
        ("OPESACE", date(2026, 10, 3), 360),
        ("OPESAC", date(2026, 10, 3), 390),
        ("OPESAC", date(2026, 10, 10), 0),
        ("OPESAC", date(2026, 10, 17), 390),
        ("OPESAC", date(2026, 10, 24), 0),
        ("OPSABE", date(2026, 10, 17), 390),
        ("OPE0736", date(2026, 10, 1), 420),
    ],
)
def test_effective_ope_duration_and_saturday_scope(code, date_value, expected):
    assert resolve_technician_operai_rule(day(code, date_value)).expected_minutes == expected


@pytest.mark.parametrize("code", ["TELEC_1", "SAB", "RIPTURN", "SMONTO", "IRRSEA", None])
def test_technician_calendar_does_not_apply_to_non_ope_days(code):
    assert resolve_technician_operai_rule(day(code)) is None


def test_other_workers_retain_existing_rules():
    assert resolve_technician_operai_rule(day(hr=False)) is None
    worker = SimpleNamespace(contract_kind="operaio", operai_group="catasto_magazzino")
    result = resolve_operai_rule(worker, day(work_date=date(2026, 10, 10), hr=False))
    assert result.expected_minutes == 360
    worker.operai_group = None
    assert (
        resolve_operai_rule(worker, day(work_date=date(2026, 10, 10), hr=False)).expected_minutes
        == 420
    )


def test_detached_and_non_technician_profiles():
    record = day()
    assert personnel_profile(record) is record.personnel_profile
    assert personnel_profile_values(day(hr=False)) == {}
    record.personnel_profile.profile_type = "capo_reparto"
    assert technician_profile(record) is None
    record.personnel_profile.valid_to = date(2026, 12, 31)
    assert personnel_profile_values(record)["personnel_profile_valid_to"] == "2026-12-31"


def test_persisted_profile_effective_dates_cache_and_snapshot():
    user = _create_user("personnel-admin")
    record_id, collaborator_id = _record(user.id)
    with TestingSessionLocal() as db:
        record = db.get(PresenzeDailyRecord, record_id)
        assert personnel_profile(record) is None
        first = PresenzePersonnelProfile(
            collaborator_id=collaborator_id,
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 9, 30),
            profile_type="tecnico_turnista",
            profile_label="Tecnico/Turnista",
            duty="Tecnico / Turnista",
            employment_relationship="avventizio",
            personnel_area="IMPIANTI",
            supervisor_user_id=user.id,
            shift_schedule_codes=[
                "TELEC_1",
                "TELEC_2",
                "TELEC_3",
                "ADD_9",
                "IRRSE",
                "IRRSEA",
                "SMONTO",
                "RIPTURN",
            ],
            source_document_sha256="a" * 64,
            source_note="PDF attested by manager",
        )
        second = PresenzePersonnelProfile(
            collaborator_id=collaborator_id,
            valid_from=date(2026, 10, 1),
            profile_type="capo_reparto",
            profile_label="Capo Reparto",
            duty="Capo Reparto",
            employment_relationship="indeterminato",
            personnel_area="IMPIANTI",
            supervisor_user_id=user.id,
            shift_schedule_codes=[
                "TELEC_1",
                "TELEC_2",
                "TELEC_3",
                "ADD_9",
                "IRRSE",
                "IRRSEA",
                "SMONTO",
                "RIPTURN",
            ],
            source_document_sha256="b" * 64,
            source_note="Later attestation",
        )
        db.add_all([first, second])
        db.flush()
        db.info.clear()
        assert personnel_profile(record) is second
        record.work_date = date(2026, 9, 30)
        assert personnel_profile(record) is first
        assert technician_profile(record) is first
        assert _gate_record_feature_values(record)["employment_relationship"] == "avventizio"
        assert personnel_profile_values(record)["personnel_profile_valid_to"] == "2026-09-30"
        record.work_date = date(2025, 12, 31)
        assert personnel_profile(record) is None
        record.work_date = date(2026, 10, 1)
        payload = _gate_record_feature_values(record)
        assert payload["profile_label"] == "Capo Reparto"
        assert payload["personnel_supervisor_gaia_user_id"] == str(user.id)
        assert payload["personnel_profile_valid_to"] is None
        assert db.get(PresenzeCollaborator, collaborator_id).operai_group == "agrario"


def test_profile_date_and_area_fail_closed():
    record = day(work_date=date(2025, 12, 31))
    assert personnel_profile(record) is None
    record.work_date = date(2026, 10, 3)
    record.personnel_profile.personnel_area = "AGRARIO"
    assert technician_profile(record) is None
    record.personnel_profile.valid_to = date(2026, 9, 30)
    assert personnel_profile(record) is None


def technician_day(code="TELEC_1", minutes=480):
    record = day(code)
    record.teo_minutes = minutes
    record.shift_worker_type = "none"
    record.shift_worker_source = None
    record.justified_minutes = 0
    record.absence_minutes = 0
    record.raw_payload_json = {}
    record.request_description = None
    record.request_status = None
    record.resolved_absence_cause = None
    record.meal_voucher_manual = False
    record.shift_punches = []
    return record


@pytest.mark.parametrize(
    "code,minutes,worked,ordinary,extra",
    [
        ("TELEC_1", 480, 480, 480, 0),
        ("TELEC_2", 480, 540, 480, 60),
        ("TELEC_3", 480, 420, 420, 0),
        ("ADD_9", 420, 420, 420, 0),
        ("IRRSE", 420, 480, 420, 60),
        ("IRRSEA", 420, 420, 420, 0),
    ],
)
def test_technician_shift_uses_inaz_theory_and_daily_export(code, minutes, worked, ordinary, extra):
    from datetime import time

    from app.modules.presenze.services.shift_worker_rules import (
        shift_classification,
        shift_meal_voucher,
        shift_quality,
        shift_record_values,
        shift_worker_type,
    )

    record = technician_day(code, minutes)
    punches = [SimpleNamespace(entry_time=time(6), exit_time=time(6 + worked // 60))]
    record.shift_punches = punches
    assert shift_worker_type(record) == "tecnico_turnista"
    assert shift_record_values(record)["shift_worker_type"] == "tecnico_turnista"
    quality = shift_quality(record, punches)
    assert quality.expected_minutes == minutes
    assert quality.formula_code == "TURNISTA_INAZ"
    assert quality.missing_minutes == max(0, minutes - worked)
    result = shift_classification(
        record,
        punches,
        special_day=False,
        holiday_kind=None,
        grants_recovery_day=False,
        calendar=[False, False],
    )
    assert (result.ordinary_minutes, result.extra_minutes) == (ordinary, extra)
    assert shift_meal_voucher(record) is True


def test_ope_rest_revocation_missing_theory_and_short_shift():
    from datetime import time

    from app.modules.presenze.services.shift_worker_rules import (
        shift_classification,
        shift_meal_voucher,
        shift_quality,
        shift_worker_type,
    )

    record = technician_day("OPE0714", 420)
    record.shift_worker_type = "telecontrollo"
    record.shift_worker_source = "gate"
    assert shift_worker_type(record) is None
    record.schedule_code = "TELEC_1"
    record.shift_worker_type = "none"
    assert shift_worker_type(record) is None
    record.shift_worker_source = None
    record.schedule_code = "SMONTO"
    record.teo_minutes = 0
    assert shift_quality(record, []).expected_minutes == 0
    result = shift_classification(
        record, [], special_day=False, holiday_kind=None, grants_recovery_day=False
    )
    assert (result.ordinary_minutes, result.extra_minutes) == (0, 0)
    record.schedule_code = "TELEC_1"
    record.teo_minutes = None
    record.shift_punches = [SimpleNamespace(entry_time=time(6), exit_time=time(14))]
    quality = shift_quality(record, record.shift_punches)
    assert quality.status == "blocking" and quality.expected_minutes is None
    assert "Teorico INAZ mancante" in " ".join(quality.notes)
    assert shift_meal_voucher(record) is False
    result = shift_classification(
        record,
        record.shift_punches,
        special_day=False,
        holiday_kind=None,
        grants_recovery_day=False,
    )
    assert (
        result.ordinary_minutes is None
        and result.extra_minutes is None
        and result.shift_ccnl is None
    )
    record.teo_minutes = 360
    assert shift_meal_voucher(record) is False
    record.personnel_profile = None
    record.shift_worker_type = "tecnico_turnista"
    assert shift_worker_type(record) is None


def test_opesac_uses_confirmed_six_and_half_hours_without_changing_inaz():
    from app.modules.presenze.services.operai_daily_policy import recognized_daily_minutes

    record = day("OPESAC", date(2026, 10, 17))
    record.teo_minutes = 456
    punches = [SimpleNamespace(entry_time=time(7), exit_time=time(13, 30))]
    rule = resolve_technician_operai_rule(record)
    recognized = recognized_daily_minutes(punches, rule)
    assert (
        recognized.ordinary_minutes,
        recognized.overtime_minutes,
        recognized.missing_minutes,
    ) == (390, 0, 0)
    assert (record.schedule_code, record.teo_minutes) == ("OPESAC", 456)
    assert resolve_technician_operai_rule(day("OPESAC", hr=False)) is None


@pytest.mark.parametrize(
    "work_date,template,eligible",
    [
        (
            date(2026, 10, 3),
            SimpleNamespace(is_active=True, valid_from=date(2026, 10, 10), valid_to=None),
            False,
        ),
        (date(2026, 10, 3), SimpleNamespace(is_active=True, valid_from=None, valid_to=None), True),
        (
            date(2026, 10, 3),
            SimpleNamespace(is_active=True, valid_from=date(2026, 1, 1), valid_to=date(2026, 9, 30)),
            False,
        ),
        (
            date(2026, 10, 3),
            SimpleNamespace(is_active=True, valid_from=None, valid_to=date(2026, 10, 31)),
            True,
        ),
    ],
)
def test_other_worker_individual_calendar_validity(work_date, template, eligible):
    assert individual_saturday_eligible(day(work_date=work_date, hr=False), template) is eligible
