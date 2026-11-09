"""Boundary and precedence controls for the derived Avventizio presentation."""

from datetime import date
from types import SimpleNamespace

import pytest
from test_presenze_avventizio_absence import synthetic, values

from app.modules.presenze.services.employment_periods import employment_period_values
from app.modules.presenze.services.xlsm_export import resolve_export_absence_code


def contract(start, end, relationship="avventizio", digest="a"):
    return SimpleNamespace(
        valid_from=date.fromisoformat(start),
        valid_to=date.fromisoformat(end),
        employment_relationship=relationship,
        source_document_sha256=digest * 64,
    )


@pytest.mark.parametrize("work_date", [date(2026, 10, 1), date(2026, 10, 31)])
def test_contract_boundaries_are_inclusive(work_date):
    record = synthetic(
        work_date=work_date,
        employment_periods=[contract("2026-10-01", "2026-10-31")],
    )
    assert values(record)["avventizio_no_punches"] is True


@pytest.mark.parametrize("reverse", [False, True])
def test_latest_start_wins_for_overlaps_regardless_of_input_order(reverse):
    periods = [
        contract("2026-01-01", "2026-12-31"),
        contract("2026-10-01", "2026-10-31", "determinato", "b"),
    ]
    record = synthetic(employment_periods=periods[::-1] if reverse else periods)
    result = employment_period_values(record)
    assert result["employment_relationship"] == "determinato"
    assert result["employment_source_sha256"] == "b" * 64
    assert not values(record).get("avventizio_no_punches")


def test_contract_gap_does_not_fall_back_to_an_open_ended_legacy_profile():
    record = synthetic(
        employment_periods=[
            contract("2026-01-01", "2026-09-30"),
            contract("2026-10-03", "2026-12-31"),
        ],
        personnel_profile=SimpleNamespace(
            valid_from=date(2026, 1, 1),
            valid_to=None,
            employment_relationship="avventizio",
        ),
    )
    assert values(record) == {"employment_relationship": None}


@pytest.mark.parametrize("cause", ["ferie", "malattia", "permesso", "riposo"])
def test_real_absence_takes_precedence_over_ag_even_when_hours_are_missing(cause):
    record = synthetic(
        resolved_absence_cause=cause,
        raw_payload_json={"detail_anomalies": [{"code": "OREM"}]},
    )
    assert not values(record).get("avventizio_no_punches")


@pytest.mark.parametrize(
    "raw",
    [
        {"detail_anomalies": [{"code": "OREM"}, {"code": "OTHER"}]},
        {"detail_error": "sync failed", "detail_anomalies": [{"code": "OREM"}]},
    ],
)
def test_technical_diagnostics_are_not_hidden_by_missing_hours_projection(raw):
    record = synthetic(raw_payload_json=raw)
    result = values(record)
    assert result["operational_status"] == "in_analysis"
    assert result["operational_missing_minutes"] == 0
    assert result["operational_notes"] == [
        "Assenza di timbrature (Avventizio)",
        "source note",
    ]
    assert record.raw_payload_json == raw


@pytest.mark.parametrize(
    "description,cause,expected",
    [
        ("P. ORD - Permesso", "malattia", "P"),
        ("SCONOSCIUTO - Richiesta", "malattia", "M"),
        ("", "ferie", "F"),
        (None, "riposo", "RS"),
        (None, None, None),
    ],
)
def test_export_keeps_request_then_cause_precedence(description, cause, expected):
    record = synthetic(
        employment_periods=[],
        request_description=description,
        resolved_absence_cause=cause,
    )
    assert resolve_export_absence_code(record) == expected


@pytest.mark.parametrize(
    "classification,quality",
    [
        (None, None),
        (None, SimpleNamespace(expected_minutes=420, notes=())),
        (SimpleNamespace(special_day=False, ordinary_minutes=0, extra_minutes=0), None),
    ],
)
def test_detached_record_with_incomplete_context_does_not_invent_ag(classification, quality):
    from app.modules.presenze.services.avventizio_absence import avventizio_absence_values

    assert not avventizio_absence_values(
        synthetic(), classification, quality, today=date(2026, 11, 6)
    ).get("avventizio_no_punches")


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "unavailable",
        {},
        {
            "detail_requests": [
                {
                    "Tipo": "Permesso",
                    "Descrizione": "P. ORD - Permesso",
                    "Stato": "ACC",
                    "Autorizzato da": "Responsabile sintetico",
                }
            ],
        },
    ],
)
@pytest.mark.parametrize("explicit", [None, "", "Esplicito"])
def test_request_projection_preserves_explicit_values_and_source_fallbacks(payload, explicit):
    from app.modules.presenze.router.helpers.daily_records import _daily_record_request_values

    record = synthetic(
        raw_payload_json=payload,
        request_type=explicit,
        request_description=explicit,
        request_status=explicit,
        request_authorized_by=explicit,
    )
    fallback = {
        "request_type": "Permesso",
        "request_description": "P. ORD - Permesso",
        "request_status": "ACC",
        "request_authorized_by": "Responsabile sintetico",
    }
    expected = {key: None for key in fallback}
    if payload:
        if isinstance(payload, dict):
            expected = fallback
    if explicit:
        expected = {key: explicit for key in fallback}
    before = record.__dict__.copy()
    assert _daily_record_request_values(record) == expected
    assert record.__dict__ == before
