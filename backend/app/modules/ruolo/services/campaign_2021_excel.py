"""Read the 2021 scope without importing accounting movements or evaluating arbitrary formulas."""

from collections import Counter
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from io import BytesIO
from zipfile import BadZipFile

from openpyxl import load_workbook

from app.modules.ruolo.services.notice_import_excel import _validate_archive, digest, json_bytes
from app.modules.ruolo.services.notice_recipient_identity import valid_tax_code

PARSER_VERSION = "campaign-2021-v1"
HEADERS = (
    "Codice fiscale",
    "Soggetto",
    "Avviso",
    "Lista",
    "Ruolo digitale",
    "Carico (Emesso)",
    "648",
    "668",
    "985",
    "Residuo",
    "Somme Versate",
    "Maggiorazione",
    "Interessi",
    "Totale dovuto",
)
AMOUNTS = (
    "load",
    "0648",
    "0668",
    "0985",
    "residual",
    "difference",
    "surcharge",
    "interest",
    "total",
)
BASELINE = {
    "rows": 942,
    "ordinary": 712,
    "digital": 230,
    "distinct_numbers": 942,
    "load": "321015.17",
    "residual": "313954.25",
    "difference": "7060.92",
    "surcharge": "18837.30",
    "interest": "30797.60",
    "total": "363589.15",
}


def decimal(value) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError("Importo o parametro mancante")
    try:
        result = Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError("Importo o parametro non numerico") from exc
    if not result.is_finite() or abs(result) > Decimal("9999999999.99"):
        raise ValueError("Importo o parametro fuori limite")
    return result


def money(value) -> Decimal:
    return decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parameters(sheet) -> dict:
    start, end = sheet["B5"].value, sheet["B6"].value
    if not isinstance(start, datetime) or not isinstance(end, datetime) or end < start:
        raise ValueError("Date interessi assenti o incoerenti")
    result = {
        key: str(decimal(sheet[cell].value))
        for key, cell in (
            ("spread", "B2"),
            ("euribor", "B3"),
            ("rate", "B4"),
            ("days", "B7"),
            ("basis", "B8"),
            ("surcharge", "B9"),
            ("threshold", "B10"),
        )
    }
    if decimal(result["basis"]) <= 0 or decimal(result["days"]) != (end - start).days:
        raise ValueError("Base annua o giorni incoerenti")
    if decimal(result["rate"]) != decimal(result["spread"]) + decimal(result["euribor"]):
        raise ValueError("Tasso annuo diverso da spread più Euribor")
    if sheet["A3"].value != "Euribor 3 mesi":
        raise ValueError("Fonte Euribor diversa dal tracciato 2021")
    return {
        **result,
        "start": start.date().isoformat(),
        "end": end.date().isoformat(),
        "euribor_tenor": "3m",
    }


def excel_charges(residual, digital: bool, params: dict, *, basis=None) -> dict:
    residual = money(residual)
    surcharge = money(residual * decimal(params["surcharge"]))
    interest = (
        money(
            residual
            * decimal(params["rate"])
            * decimal(params["days"])
            / decimal(basis or params["basis"])
        )
        if digital
        else money(0)
    )
    return {
        "surcharge": str(surcharge),
        "interest": str(interest),
        "total": str(residual + surcharge + interest),
    }


def identity_problems(values) -> list[str]:
    cf, name, notice, role, digital = values[:5]
    problems = []
    if (
        not isinstance(notice, str)
        or len(notice) != 15
        or not notice.isascii()
        or not notice.isdigit()
    ):
        problems.append("numero_non_testuale_o_non_valido")
    if not isinstance(cf, str) or not valid_tax_code(cf):
        problems.append("cf_da_revisionare")
    if not isinstance(name, str) or not name.strip():
        problems.append("nominativo_assente")
    if (role, digital) not in {("Ruolo 2021", "No"), ("Ruolo 2021 Digitali", "Sì")}:
        problems.append("classificazione_excel_incoerente")
    return problems


def parse_row(values, number: int, params: dict) -> dict:
    cf, name, notice, role, digital = values[:5]
    amounts = {key: str(money(value)) for key, value in zip(AMOUNTS, values[5:14], strict=True)}
    problems = identity_problems(values)
    expected = {
        "difference": str(money(amounts["load"]) - money(amounts["residual"])),
        **excel_charges(amounts["residual"], digital == "Sì", params),
    }
    problems.extend(
        f"formula_{key}_discordante"
        for key, value in expected.items()
        if money(amounts[key]) != money(value)
    )
    if money(amounts["residual"]) <= decimal(params["threshold"]):
        problems.append("residuo_sotto_soglia")
    return {
        "row": number,
        "number": str(notice or ""),
        "tax_code": str(cf or "").strip().upper(),
        "name": str(name or "").strip(),
        "digital": digital == "Sì",
        "role": role,
        "amounts": amounts,
        "problems": problems,
        "tribute_delta": str(
            sum((money(amounts[k]) for k in ("0648", "0668", "0985")), money(0))
            - money(amounts["load"])
        ),
    }


def summary(rows: list[dict], params: dict) -> dict:
    numbers = Counter(row["number"] for row in rows)
    for row in rows:
        if numbers[row["number"]] > 1:
            row["problems"].append("numero_duplicato")
    totals = {
        key: str(sum((money(row["amounts"][key]) for row in rows), money(0))) for key in AMOUNTS
    }
    counts = {
        "rows": len(rows),
        "digital": sum(r["digital"] for r in rows),
        "distinct_numbers": len(numbers),
    }
    counts["ordinary"] = counts["rows"] - counts["digital"]
    compared = {**counts, **totals}
    return {
        **compared,
        "parameters": params,
        "baseline_differences": {
            k: {"expected": v, "actual": compared[k]}
            for k, v in BASELINE.items()
            if compared[k] != v
        },
        "load_residual_differences": sum(money(r["amounts"]["difference"]) != 0 for r in rows),
        "tribute_differences": sum(money(r["tribute_delta"]) != 0 for r in rows),
        "warnings": [
            "Le Note indicano 956 avvisi (715 ordinari, 241 digitali) e 34 differenze carico/residuo; la conversazione ne cita 943: confrontare con i conteggi effettivi.",
            "La nota Parametri indica Carico x 6%, le formule usano Residuo x 6%.",
            "F-J è una differenza contabile, non un pagamento verificato.",
        ],
    }


def read_workbook(workbook) -> tuple[list[dict], dict]:
    params = parameters(workbook["Parametri"])
    sheet = workbook["Avvisi_2021"]
    if sheet.max_row is None or sheet.max_row > 10000 or sheet.max_column != 14:
        raise ValueError("Dimensioni del foglio 2021 non valide")
    source = sheet.iter_rows(values_only=True)
    if tuple(next(source)) != HEADERS:
        raise ValueError("Intestazioni diverse dal tracciato 2021")
    rows = [
        parse_row(v, n, params)
        for n, v in enumerate(source, 2)
        if any(x is not None for x in v) and v[0] != "Totale"
    ]
    if not rows:
        raise ValueError("Nessun avviso nel foglio 2021")
    return rows, params


def parse_excel(content: bytes) -> dict:
    try:
        _validate_archive(content)
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True, keep_links=False)
        try:
            rows, params = read_workbook(workbook)
            result = summary(rows, params)
            return {
                "file_sha256": digest(content),
                "parser_version": PARSER_VERSION,
                "summary": result,
                "rows": rows,
                "scope_sha256": digest(json_bytes(rows)),
            }
        finally:
            workbook.close()
    except (BadZipFile, KeyError, OSError, SyntaxError, StopIteration) as exc:
        raise ValueError("File XLSX 2021 incompleto o non valido") from exc
