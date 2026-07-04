from __future__ import annotations

import json
from datetime import date, time

import pytest

from app.modules.presenze.services import parser


def _detail_row(**overrides):
    payload = {
        "detail_title": "  Giorno lavorativo ",
        "detail_status": " Presente ",
        "detail_programmed_schedule": "IMP1 - 07:35-14:00",
        "detail_effective_schedule": "07:40-14:05",
        "detail_time_slots": "07:40-14:05",
        "detail_schedule_type": "Standard",
        "detail_theoretical_hours": "06:25",
        "detail_absence_hours": "00:30",
        "detail_day_summary": {
            " Ore Straordinario ": "01:15",
            "Ore Trasferta": "02:00",
            "Comune montano": "Si",
        },
        "detail_day_totals": {
            " Ore Maggior Presenza ": "00:45",
            "Ore Maggiorazione": "00:30",
            "Ore Assenza Giustificate": "00:20",
        },
        "detail_requests": [
            {
                "Tipo": "Ferie",
                "Descrizione": "Ferie estive",
                "Stato": "Autorizzata",
                "Autorizzato da": "HR",
            }
        ],
        "detail_anomalies": [{"Anomalia giornata": "Timbratura assente"}],
        "detail_punch_rows": [
            {"Ora": "07:40", "EU": "E", "Term": "Ingresso 1"},
            {"Ora": "14:05", "EU": "U", "Term": "Ingresso 1"},
        ],
        "detail_text": "Timbrature 07:40 E BADGE Ingresso 1 14:05 14:05 U BADGE Ingresso 1 14:05 Riepilogo Giornata",
        "detail_error": None,
        "ordinary": "06:00",
        "absence": "00:15",
        "justified": "00:10",
        "maggiorazione": "00:05",
        "mpe": "00:15",
        "straordinario": "00:20",
        "trasferta": "00:25",
        "schedule_code": None,
        "stato": "fallback stato",
        "evidenze": None,
        "teo": "06:10",
    }
    payload.update(overrides)
    return payload


def test_parse_portal_date_parse_clock_and_duration_helpers_cover_supported_shapes() -> None:
    assert parser.parse_portal_date("01/06/2026") == date(2026, 6, 1)
    assert parser.parse_portal_date("  ") is None

    assert parser.parse_clock(None) is None
    assert parser.parse_clock("07:35") == time(7, 35)
    assert parser.parse_clock("07:35:59") == time(7, 35, 59)
    assert parser.parse_clock(" ") is None
    assert parser.parse_clock("bad") is None

    assert parser.duration_to_minutes(None) is None
    assert parser.duration_to_minutes("01:15") == 75
    assert parser.duration_to_minutes("1,5") == 1
    assert parser.duration_to_minutes("1.500,9") == 1500
    assert parser.duration_to_minutes("  ") is None


def test_extract_detail_payload_and_resolution_helpers_prefer_detail_maps() -> None:
    row = _detail_row()
    detail = parser.extract_detail_payload(row)

    assert detail["title"] == "Giorno lavorativo"
    assert detail["status"] == "Presente"
    assert detail["day_summary"]["Ore Straordinario"] == "01:15"
    assert detail["requests"][0]["Tipo"] == "Ferie"

    assert parser.parse_schedule_code_from_detail(" IMP1 - 07:35-14:00 ") == "IMP1"
    assert parser.parse_schedule_code_from_detail(None) is None
    assert parser.resolve_schedule_code(row) == "IMP1"
    assert parser.resolve_stato(row) == "Presente"
    assert parser.resolve_teo_minutes(row) == 385
    assert parser.resolve_ordinary_minutes(row) == 360
    assert parser.resolve_absence_minutes(row) == 30
    assert parser.resolve_justified_minutes(row) == 20
    assert parser.resolve_maggiorazione_minutes(row) == 30
    assert parser.resolve_mpe_minutes(row) == 45
    assert parser.resolve_straordinario_minutes(row) == 75
    assert parser.resolve_trasferta_minutes(row) == 120
    assert parser.resolve_trasferta_montano(row) is True

    no_montano = _detail_row(detail_day_summary={}, detail_day_totals={}, detail_requests=[], detail_status=None, detail_text=None, evidenze=None)
    assert parser.resolve_trasferta_montano(no_montano) is False


def test_request_and_absence_resolution_cover_fallbacks_and_categories() -> None:
    ferie = _detail_row(evidenze="Ferie | Permesso")
    assert parser.resolve_request_type(ferie) == "Ferie"
    assert parser.resolve_request_description(ferie) == "Ferie estive"
    assert parser.resolve_request_status(ferie) == "Autorizzata"
    assert parser.resolve_request_authorized_by(ferie) == "HR"
    assert parser.resolve_absence_cause(ferie) == "ferie"

    permesso = _detail_row(detail_requests=[{"Tipo": "Permesso ordinario"}], detail_anomalies=[], evidenze=None)
    assert parser.resolve_absence_cause(permesso) == "permesso"

    malattia = _detail_row(detail_requests=[], detail_anomalies=[], evidenze="Malattia", detail_status=None, detail_text=None)
    assert parser.resolve_absence_cause(malattia) == "malattia"

    riposo = _detail_row(detail_requests=[], detail_anomalies=[], evidenze="Riposo compensativo")
    assert parser.resolve_absence_cause(riposo) == "riposo"

    festivita = _detail_row(detail_requests=[], detail_anomalies=[], evidenze="Festività goduta")
    assert parser.resolve_absence_cause(festivita) == "festivita"

    banca_ore = _detail_row(detail_requests=[], detail_anomalies=[], evidenze="Banca ore")
    assert parser.resolve_absence_cause(banca_ore) == "banca_ore"

    giustificare = _detail_row(detail_requests=[], detail_anomalies=[], evidenze="Assenza da giustificare")
    assert parser.resolve_absence_cause(giustificare) == "assenza_da_giustificare"


def test_special_day_recovery_and_authoritative_classification_helpers() -> None:
    special = _detail_row(detail_day_summary={"Festività goduta": "1"})
    assert parser.detail_indicates_special_day(special) is True

    ordinary = _detail_row(detail_day_summary={})
    assert parser.detail_indicates_special_day(ordinary) is False

    recovery = _detail_row(detail_day_summary={}, detail_day_totals={}, detail_requests=[{"Descrizione": "Riposo compensativo"}])
    assert parser.detail_indicates_recovery_usage(recovery) is True

    no_recovery = _detail_row(detail_day_summary={}, detail_day_totals={}, detail_requests=[], detail_status=None, detail_text=None)
    assert parser.detail_indicates_recovery_usage(no_recovery) is False

    authoritative_from_totals = _detail_row(detail_day_summary={}, detail_day_totals={"Ore Ordinarie": "06:00"})
    assert parser.detail_has_authoritative_classification(authoritative_from_totals) is True

    authoritative = _detail_row(detail_day_summary={}, detail_day_totals={}, detail_status="Presente")
    assert parser.detail_has_authoritative_classification(authoritative) is True

    not_authoritative = _detail_row(
        detail_day_summary={},
        detail_day_totals={},
        detail_status=None,
        detail_programmed_schedule=None,
        detail_effective_schedule=None,
        detail_time_slots=None,
        detail_theoretical_hours=None,
        detail_absence_hours=None,
    )
    assert parser.detail_has_authoritative_classification(not_authoritative) is False


def test_extract_punch_terminal_labels_supports_structured_rows_and_text_fallback() -> None:
    structured = _detail_row()
    assert parser.extract_punch_terminal_labels(structured) == [
        {"time": "07:40", "direction": "E", "terminal_label": "Ingresso 1"},
        {"time": "14:05", "direction": "U", "terminal_label": "Ingresso 1"},
    ]

    text_fallback = _detail_row(
        detail_punch_rows=[],
        detail_text="Timbrature 07:40 E BADGE Ingresso lato nord 14:05 14:05 U BADGE Ingresso lato nord 14:05 Riepilogo Giornata",
    )
    extracted = parser.extract_punch_terminal_labels(text_fallback)
    assert extracted == [
        {"time": "07:40", "direction": "E", "terminal_label": "Ingresso lato nord"},
        {"time": "14:05", "direction": "U", "terminal_label": "Ingresso lato nord"},
    ]

    empty = _detail_row(detail_punch_rows=[], detail_text="nessun dato utile")
    assert parser.extract_punch_terminal_labels(empty) == []

    blank_text = _detail_row(detail_punch_rows=[], detail_text=None)
    assert parser.extract_punch_terminal_labels(blank_text) == []


def test_extract_punch_terminal_labels_supports_inaz_orario_verso_shape() -> None:
    structured = _detail_row(
        detail_punch_rows=[
            {"Orario": "07:25", "Verso": "E", "TipoTimbratura": "SW", "kterminali": "0", "RicOrario": "07:25"},
            {"Orario": "10:23", "Verso": "U", "TipoTimbratura": "TR", "kterminali": "CBON-Ingresso CBO", "RicOrario": "10:23"},
        ]
    )

    assert parser.extract_punch_terminal_labels(structured) == [
        {"time": "07:25", "direction": "E", "terminal_label": "0"},
        {"time": "10:23", "direction": "U", "terminal_label": "CBON-Ingresso CBO"},
    ]


def test_normalize_helpers_and_evidenze_fallback_behaviour() -> None:
    assert parser.normalize_portal_text("  A   B ") == "A B"
    assert parser.normalize_portal_text(None) is None
    assert parser.normalize_portal_key(" Festività ") == "festività"

    row = _detail_row(
        detail_requests=[{"Descrizione": "Permesso breve"}, {"Descrizione": "Permesso breve"}],
        detail_anomalies=[{"Anomalia giornata": "Badge non letto"}, {"col_1": "Badge non letto"}],
        evidenze=None,
    )
    assert parser.resolve_evidenze(row) == "Badge non letto | Permesso breve"

    explicit = _detail_row(evidenze="Voce esplicita")
    assert parser.resolve_evidenze(explicit) == "Voce esplicita"

    no_labels = _detail_row(detail_requests=[], detail_anomalies=[], evidenze=None)
    assert parser.resolve_evidenze(no_labels) is None

    unknown = _detail_row(detail_requests=[], detail_anomalies=[], evidenze="Voce neutra")
    assert parser.resolve_absence_cause(unknown) is None


def test_load_json_payload_and_parse_import_payload_handle_errors_and_defaults() -> None:
    payload = {
        "period_start": "01/06/2026",
        "period_end": "30/06/2026",
        "employees": [
            {
                "collaborator": {"employee_code": "AA1", "name": "Alpha"},
                "company_label": "Consorzio",
                "period_start": "05/06/2026",
                "daily_rows": [{"work_date": "05/06/2026"}, "skip"],
                "summary_rows": [{"code": "TOT"}, 1],
            },
            {
                "collaborator": {"name": "Missing code"},
                "daily_rows": [],
                "summary_rows": [],
            },
        ],
    }

    encoded = json.dumps(payload).encode("utf-8")
    loaded = parser.load_json_payload(encoded)
    parsed = parser.parse_import_payload(loaded)

    assert parsed.period_start == date(2026, 6, 1)
    assert parsed.period_end == date(2026, 6, 30)
    assert len(parsed.collaborators) == 1
    assert parsed.collaborators[0].period_start == date(2026, 6, 5)
    assert parsed.collaborators[0].period_end == date(2026, 6, 30)
    assert parsed.collaborators[0].daily_rows == [{"work_date": "05/06/2026"}]
    assert parsed.collaborators[0].summary_rows == [{"code": "TOT"}]
    assert parsed.errors == ["employee 2: missing employee_code"]

    with pytest.raises(ValueError, match="Unsupported JSON payload"):
        parser.load_json_payload(json.dumps(["bad"]).encode("utf-8"))

    with pytest.raises(ValueError, match="Payload missing period_start/period_end"):
        parser.parse_import_payload({"period_start": None, "period_end": None, "employees": []})
