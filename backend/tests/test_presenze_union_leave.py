from datetime import date, time

import pytest

from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
)
from app.modules.presenze.services.daily_details import (
    is_missing_hours_anomaly,
    normalized_daily_detail,
)
from app.modules.presenze.services.inaz_absences import (
    inaz_event_code,
    union_leave_covers_day,
    union_leave_minutes,
)
from app.modules.presenze.services.operational_quality import build_operai_operational_quality
from app.modules.presenze.services.parser import resolve_absence_cause, resolve_request_code


def record(code="PSIRSA", status="FRU", justified=120, ordinary=300, teo=420):
    return PresenzeDailyRecord(
        work_date=date(2026, 10, 1),
        schedule_code="OPE0613",
        teo_minutes=teo,
        ordinary_minutes=ordinary,
        absence_minutes=420,
        justified_minutes=justified,
        request_description=code + " - descrizione generica",
        request_status=status,
        resolved_absence_cause="permesso",
        raw_payload_json={
            "detail_requests": [{"KEvento": code + " - descrizione generica", "Stato": status}],
            "detail_anomalies": [{"anomaliagiornata": "OREM-Ore mancanti"}],
        },
    )


@pytest.mark.parametrize("code", ["ASS.SIN", "PSIEST", "PSIRSA"])
def test_structured_union_code_without_text_matching(code):
    day = record(code)
    assert resolve_request_code(day.raw_payload_json) == code
    assert resolve_absence_cause(day.raw_payload_json) == "permesso_sindacale"
    assert union_leave_minutes(day) == 120
    assert union_leave_covers_day(day)
    assert normalized_daily_detail(day)["anomalies"] == []
    assert day.raw_payload_json["detail_anomalies"]  # imported evidence never removed


@pytest.mark.parametrize(
    "status,justified,expected",
    [
        ("FRU", 120, 120),
        ("ACC", 120, 120),
        ("RIF", 120, 0),
        ("PENDING", 120, 0),
        ("FRU", None, 0),
        ("FRU", -1, 0),
    ],
)
def test_leave_must_be_valid_and_quantified(status, justified, expected):
    assert union_leave_minutes(record(status=status, justified=justified)) == expected


def test_partial_leave_does_not_hide_missing_hours_or_missing_punch():
    day = record(justified=60)
    assert normalized_daily_detail(day)["anomalies"]
    person = PresenzeCollaborator(contract_kind="operaio", operai_group="agrario")
    punches = [PresenzeDailyPunch(entry_time=time(6), exit_time=time(11))]
    quality = build_operai_operational_quality(person, day, punches)
    assert quality.missing_minutes == 60 and quality.status == "blocking"
    day.justified_minutes = 120
    quality = build_operai_operational_quality(person, day, punches)
    assert quality.missing_minutes == 0 and quality.status == "ok"
    day.raw_payload_json["detail_anomalies"].append(
        {"anomaliagiornata": "TIMB-Timbratura mancante"}
    )
    day.raw_payload_json["detail_error"] = "errore tecnico"
    detail = normalized_daily_detail(day)
    assert len(detail["anomalies"]) == 1 and detail["error"] == "errore tecnico"


def test_other_causes_missing_theoretical_and_legacy_payloads_remain_visible():
    day = record(code="ASSG")
    assert resolve_absence_cause(day.raw_payload_json) is None
    assert union_leave_minutes(day) is None
    assert normalized_daily_detail(day)["anomalies"]
    day = record(teo=None)
    assert not union_leave_covers_day(day)
    day.raw_payload_json = []
    assert union_leave_minutes(day) == 120
    assert normalized_daily_detail(day)["anomalies"] == []
    assert inaz_event_code(None) is None
    assert not is_missing_hours_anomaly({})
    assert is_missing_hours_anomaly({"code": "OREM"})
    day.raw_payload_json = {
        "detail_requests": [{"KEvento": "ASSG", "Descrizione": "PSIRSA - permesso sindacale"}]
    }
    assert union_leave_minutes(day) is None  # structured code wins over descriptive text


def test_normalized_daily_cause_preserves_other_overrides_and_exposes_union():
    from app.modules.presenze.services.daily_details import normalized_daily_absence_cause

    assert normalized_daily_absence_cause(record()) == "permesso_sindacale"
    other = record(code="FERIE")
    other.resolved_absence_cause = "riposo"
    assert normalized_daily_absence_cause(other) == "riposo"
    other.resolved_absence_cause = None
    other.request_description = None
    other.raw_payload_json = []
    assert normalized_daily_absence_cause(other) is None


def test_other_absence_coverage_preserves_allowed_causes_and_amounts():
    from app.modules.presenze.services.inaz_absences import covered_inaz_absence_minutes

    day = record(code="FERIE", justified=60)
    day.resolved_absence_cause = " Ferie "
    assert covered_inaz_absence_minutes(day, ("ferie",), 420) == 420
    day.resolved_absence_cause = None
    assert covered_inaz_absence_minutes(day, ("ferie",), 420) == 0
    day.resolved_absence_cause = "malattia"
    assert covered_inaz_absence_minutes(day, ("ferie",), 420) == 0
    assert covered_inaz_absence_minutes(record(justified=500), (), 420) == 420


def test_legacy_parser_fallbacks_preserve_empty_values_and_diagnostics():
    from app.modules.presenze.services import parser

    assert parser.duration_to_minutes("12") == 12
    assert (
        parser.minutes_from_detail_maps(
            {"detail_day_summary": {"Ore teoriche": ""}}, "Ore teoriche"
        )
        is None
    )
    assert parser.resolve_evidenze({"detail_requests": [{}]}) is None
    assert (
        parser.resolve_request_code({"detail_requests": [{"KEvento": "", "event_code": "PSIRSA"}]})
        == "PSIRSA"
    )
    assert parser.extract_punch_terminal_labels({"detail_punch_rows": [{"Ora": "06:00"}]}) == []


def test_request_fallback_skips_empty_rows_and_blank_alias_values():
    from app.modules.presenze.services import parser

    assert parser.resolve_request_code({"detail_requests": [{}, {"KEvento": "PSIRSA"}]}) == "PSIRSA"
    assert (
        parser._request_value({"KEvento": "  ", "event_code": "PSIRSA"}, "KEvento", "event_code")
        == "PSIRSA"
    )


def test_special_day_scans_past_ordinary_hour_labels():
    from app.modules.presenze.services import parser

    assert parser.detail_indicates_special_day(
        {"detail_day_summary": {"Ore ordinarie": "07:00", "Riposo goduto": "01:00"}}
    )
    assert not parser.detail_indicates_special_day(
        {"detail_day_summary": {"Ore ordinarie": "07:00"}}
    )
