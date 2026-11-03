"""Synthetic positions only: no names, identifiers or rows from the supplied workbook."""

from datetime import datetime
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import Workbook

from app.modules.ruolo.services import campaign_2021_excel as excel
from app.modules.ruolo.services import campaign_2021_reconciliation as reconciliation

CF = "RSSMRA80A01H501U"
NUMBER = "020210000000010"
PARAMS = {
    "spread": "0.025",
    "euribor": "0.02676",
    "rate": "0.05176",
    "days": "1369",
    "basis": "360",
    "surcharge": "0.06",
    "threshold": "30",
    "start": "2023-01-31",
    "end": "2026-10-31",
    "euribor_tenor": "3m",
}


def values(digital=False, residual="100.00"):
    charges = excel.excel_charges(residual, digital, PARAMS)
    return [
        CF,
        "CONTRIBUENTE ESEMPIO",
        NUMBER,
        "Ruolo 2021 Digitali" if digital else "Ruolo 2021",
        "Sì" if digital else "No",
        100,
        100,
        0,
        0,
        residual,
        str(Decimal(100) - Decimal(residual)),
        charges["surcharge"],
        charges["interest"],
        charges["total"],
    ]


def row(digital=False, residual="100.00"):
    return excel.parse_row(values(digital, residual), 2, PARAMS)


def facts():
    return {
        "number": NUMBER,
        "avviso_id": "00000000-0000-0000-0000-000000000001",
        "incass_id": "00000000-0000-0000-0000-000000000002",
        "year": "2021",
        "tax_code": CF,
        "ruolo_tax_code": CF,
        "name": "CONTRIBUENTE ESEMPIO",
        "ruolo_name": "CONTRIBUENTE ESEMPIO",
        "synced_at": "2026-11-02T10:00:00Z",
        "accounting": {
            "importo_carico": "100,00",
            "importo_residuo": "100,00",
            "importo_riscosso": "0,00",
            "importo_rateizzato": "0,00",
            "importo_annullato": "0,00",
            "importo_sgravio": "0,00",
            "importo_riporto": "0,00",
        },
        "engine": {
            "workflow_status": None,
            "capacitas_avviso_code": NUMBER,
            "calculation_policy": "internal_gaia",
            "surcharge_amount": "6.00",
            "interest_amount": "0.00",
            "saldo_amount": "106.00",
        },
        "policy": {"basis": 365},
        "partitario_available": True,
        "history": [
            {
                "source": "manual",
                "year": 2021,
                "tax_code": CF,
                "notification": "nessuna_evidenza",
                "notified_on": None,
                "evidence": None,
                "recovery": "non_affidato_verificato",
                "recovery_reference": "Fascicolo sintetico STEP 1",
                "attempts": [],
            }
        ],
        "ambiguous_history": False,
        "step_assigned": False,
        "last_delivery": None,
        "mailing_delivery": None,
        "pec_documented": False,
        "print_policy": {
            "due_date": "2026-12-15",
            "payment_deadline_mode": "fixed_date",
            "print_bollettino": True,
        },
        "sha256": "a" * 64,
    }


def workbook_bytes(rows=None, change=None):
    book = Workbook()
    sheet = book.active
    sheet.title = "Avvisi_2021"
    sheet.append(excel.HEADERS)
    for v in [values()] if rows is None else rows:
        sheet.append(v)
    sheet.append(["Totale"])
    params = book.create_sheet("Parametri")
    for cell, value in {
        "A3": "Euribor 3 mesi",
        "B2": 0.025,
        "B3": 0.02676,
        "B4": 0.05176,
        "B5": datetime(2023, 1, 31),
        "B6": datetime(2026, 10, 31),
        "B7": 1369,
        "B8": 360,
        "B9": 0.06,
        "B10": 30,
    }.items():
        params[cell] = value
    book.create_sheet("Note")["A1"] = "Solo dati sintetici"
    if change:
        change(book)
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def test_942_synthetic_rows_preserve_numbers_and_counts():
    rows = []
    for i in range(942):
        v = values(i < 230)
        v[2] = f"02021{i:010d}"
        rows.append(v)
    report = excel.parse_excel(workbook_bytes(rows))
    assert (
        report["summary"]["rows"],
        report["summary"]["ordinary"],
        report["summary"]["digital"],
    ) == (942, 712, 230)
    assert report["summary"]["distinct_numbers"] == 942
    assert report["rows"][0]["number"].startswith("0")
    assert "baseline_differences" in report["summary"]
    assert len(report["summary"]["warnings"]) == 3
    duplicated = excel.parse_excel(workbook_bytes([values(), values()]))
    assert all("numero_duplicato" in r["problems"] for r in duplicated["rows"])


@pytest.mark.parametrize("value", [None, True, "nan", "inf", "text", "10000000000"])
def test_invalid_money_cannot_become_zero(value):
    with pytest.raises(ValueError):
        excel.money(value)


def test_decimal_rounding_and_base_360_365_are_explicit():
    assert excel.money("1.005") == Decimal("1.01")
    assert excel.money("1,01") == Decimal("1.01")
    assert excel.excel_charges(100, True, PARAMS)["interest"] == "19.68"
    assert excel.excel_charges(100, True, PARAMS, basis=365)["interest"] == "19.41"
    assert excel.excel_charges(100, False, PARAMS)["interest"] == "0.00"


@pytest.mark.parametrize(
    "index,value,problem",
    [
        (0, "C", "cf_da_revisionare"),
        (1, None, "nominativo_assente"),
        (2, 20210000000010, "numero_non_testuale_o_non_valido"),
        (2, None, "numero_non_testuale_o_non_valido"),
        (3, "Ruolo 2022", "classificazione_excel_incoerente"),
        (10, 1, "formula_difference_discordante"),
        (11, 7, "formula_surcharge_discordante"),
        (12, 1, "formula_interest_discordante"),
        (13, 100, "formula_total_discordante"),
    ],
)
def test_row_anomalies_are_quarantined(index, value, problem):
    v = values()
    v[index] = value
    assert problem in excel.parse_row(v, 2, PARAMS)["problems"]
    assert "residuo_sotto_soglia" in row(residual="30")["problems"]


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b["Parametri"].__setitem__("B5", None),
        lambda b: b["Parametri"].__setitem__("B8", 0),
        lambda b: b["Parametri"].__setitem__("B7", 3),
        lambda b: b["Parametri"].__setitem__("B4", 1),
        lambda b: b["Parametri"].__setitem__("A3", "Euribor 6 mesi"),
        lambda b: b["Avvisi_2021"].__setitem__("A1", "Altro"),
        lambda b: b["Avvisi_2021"].__setitem__("A10001", "fuori limite"),
        lambda b: b.remove(b["Parametri"]),
    ],
)
def test_invalid_workbook_contract_is_rejected(change):
    with pytest.raises(ValueError):
        excel.parse_excel(workbook_bytes(change=change))


def test_missing_rows_cached_values_and_corrupt_archives_fail_closed():
    for content in [b"", b"bad", workbook_bytes([])]:
        with pytest.raises(ValueError):
            excel.parse_excel(content)
    with pytest.raises(ValueError):
        excel.parse_excel(
            workbook_bytes(change=lambda b: b["Avvisi_2021"].__setitem__("K2", "=F2-J2"))
        )


def test_reconciliation_requires_evidence_not_the_digital_flag():
    ordinary = reconciliation.reconcile(row(), facts(), PARAMS)
    assert ordinary["blockers"] == [] and ordinary["reviews"] == []
    current = facts()
    current["history"] = []
    assert (
        "storico_non_verificato" in reconciliation.reconcile(row(True), current, PARAMS)["blockers"]
    )
    current = facts()
    current["history"][0].update(
        notification="perfezionata", notified_on="2024-01-01", evidence="Ricevuta sintetica"
    )
    assert reconciliation.reconcile(row(), current, PARAMS)["kind"] == "sollecito_documentato"


@pytest.mark.parametrize(
    "field,value,block",
    [
        ("year", "2022", "annualita_incass_discordante"),
        ("tax_code", "OTHER", "identita_discordante"),
        ("name", "ALTRO DESTINATARIO", "nominativo_discordante"),
        ("synced_at", None, "contabilita_incompleta"),
        ("partitario_available", False, "partitario_assente"),
        ("step_assigned", True, "step_o_storico_ambiguo"),
        ("ambiguous_history", True, "step_o_storico_ambiguo"),
        ("last_delivery", "BOL", "invio_incass_da_riconciliare"),
        ("policy", None, "policy_non_verificata"),
    ],
)
def test_data_and_history_blocks(field, value, block):
    current = facts()
    current[field] = value
    assert block in reconciliation.reconcile(row(), current, PARAMS)["blockers"]


@pytest.mark.parametrize(
    "key,value,block",
    [
        ("importo_carico", None, "contabilita_incompleta"),
        ("importo_residuo", None, "contabilita_incompleta"),
        ("importo_riscosso", "non disponibile", "riscossioni_non_verificate"),
        ("importo_residuo", "99,00", "residuo_corrente_discordante"),
        ("importo_residuo", "0", "saldo_non_esigibile"),
        ("importo_residuo", "-1", "saldo_non_esigibile"),
        ("importo_annullato", "100", "posizione_bloccata"),
    ],
)
def test_accounting_blocks(key, value, block):
    current = facts()
    current["accounting"][key] = value
    assert block in reconciliation.reconcile(row(), current, PARAMS)["blockers"]


@pytest.mark.parametrize(
    "change,expected",
    [
        ({"recovery": "affidato"}, "step_non_liberato"),
        ({"notification": "da_verificare"}, "notifica_da_verificare"),
        ({"notification": "perfezionata"}, "prova_notifica_assente"),
        ({"attempts": ["attempt"]}, "invii_non_chiariti"),
        ({"year": 2022}, "storico_discordante"),
    ],
)
def test_document_evidence_blocks(change, expected):
    current = facts()
    current["history"][0].update(change)
    assert expected in reconciliation.reconcile(row(), current, PARAMS)["blockers"]


def test_rateization_partial_invalid_cf_and_engine_source_are_not_silenced():
    current = facts()
    current["accounting"].update(
        importo_rateizzato="106", importo_riscosso="50", importo_residuo="50"
    )
    result = reconciliation.reconcile(row(True, "50"), current, PARAMS)
    assert result["kind"] == "rateizzazione_con_residuo"
    assert {
        "oneri_rateizzazione_da_riconciliare",
        "base_360_365",
        "euribor_3m_6m",
        "decorrenza_interessi",
        "differenza_contabile_non_prova_pagamento",
    } <= set(result["reviews"])
    current["accounting"]["importo_rateizzato"] = "0"
    assert (
        reconciliation.reconcile(row(residual="50"), current, PARAMS)["kind"]
        == "parzialmente_saldato"
    )
    current["engine"].update(
        workflow_status="sospeso", capacitas_avviso_code="other", interest_amount=None
    )
    assert {"posizione_bloccata", "motore_avviso_discordante"} <= set(
        reconciliation.reconcile(row(), current, PARAMS)["blockers"]
    )
    invalid = row()
    invalid["problems"] = ["cf_da_revisionare", "numero_duplicato"]
    assert reconciliation.reconcile(invalid, {"match_error": "assente"}, PARAMS)["blockers"] == [
        "assente",
        "numero_duplicato",
    ]
    assert reconciliation.amount("") is None
