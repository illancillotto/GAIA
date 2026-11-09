"""Strict semantic XLSX decoder. Lossy identity recovery is deliberately forbidden."""

import hashlib
import html
import json
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from zoneinfo import ZoneInfo

from openpyxl import load_workbook

from app.modules.elaborazioni.capacitas.models import CapacitasInCassNoticeRow

MONEY = frozenset(
    {
        "Carico",
        "Sgravio",
        "Riscosso",
        "Differenza",
        "Riporto",
        "Rateizzato",
        "Annullato",
        "Rimborsi",
    }
)
DATES = frozenset({"DataScad", "DataPagamento"})
CODES = frozenset({"Avviso", "Anno", "ID", "IDLista", "CodFisc", "Cap", "StatoPag", "TipAna"})
KNOWN = frozenset(
    field.alias for field in CapacitasInCassNoticeRow.model_fields.values() if field.alias
)
# Every field written by the canonical upsert must be represented, even when null.
REQUIRED = frozenset(
    {
        "Avviso",
        "Anno",
        "ID",
        "CodFisc",
        "Denominaz",
        "DataPagamento",
        "DataScad",
        "IDLista",
        "DescrizioneLista",
        "Indir",
        "Civ",
        "SubCiv",
        "Cap",
        "Citta",
        "Prov",
        "Carico",
        "Sgravio",
        "Riscosso",
        "Differenza",
        "Riporto",
        "Rateizzato",
        "Annullato",
        "TipAna",
        "UltimoInvio",
        "StatoPag",
    }
)


class SnapshotInvalid(ValueError):
    """Only non-personal diagnostic codes may be emitted to logs."""


def text(value: object) -> str | None:
    if value is None:
        return None
    return " ".join(unicodedata.normalize("NFKC", html.unescape(str(value))).split()) or None


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def money(value: object) -> str | None:
    raw = text(value)
    if raw is None:
        return None
    raw = raw.replace("€", "").replace(" ", "")
    if raw.startswith("(") and raw.endswith(")"):
        raw = "-" + raw[1:-1]
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", raw):
        raw = raw.replace(".", "")
    try:
        amount = Decimal(raw)
        rounded = amount.quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise SnapshotInvalid("invalid_money") from exc
    if not amount.is_finite() or amount != rounded:
        raise SnapshotInvalid("invalid_money_precision")
    return format(abs(rounded) if rounded == 0 else rounded, ".2f")


def day(value: object) -> str | None:
    if isinstance(value, datetime):
        local = value.astimezone(ZoneInfo("Europe/Rome")) if value.tzinfo else value
        return local.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raw = text(value)
    if raw is None:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    raise SnapshotInvalid("invalid_date")


def code(value: object, field: str, number_format: str = "General") -> str | None:
    if isinstance(value, bool):
        raise SnapshotInvalid("invalid_code")
    if isinstance(value, int | float):
        if int(value) != value or abs(value) >= 10**15:
            raise SnapshotInvalid("lossy_numeric_code")
        if re.fullmatch(r"0+", number_format):
            return str(int(value)).zfill(len(number_format))
        # Tax codes and postal codes have known lengths; never infer an Avviso width.
        if field in {"CodFisc", "Cap", "Avviso"}:
            raise SnapshotInvalid("unproven_numeric_identifier_width")
        return str(int(value))
    raw = text(value)
    if raw and re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?[eE][+-]?\d+", raw):
        raise SnapshotInvalid("scientific_identifier")
    return raw.upper() if raw else None


def cell_value(cell, field: str) -> str | None:
    if cell.data_type in {"f", "e"}:
        raise SnapshotInvalid("formula_or_excel_error")
    if field in MONEY:
        return money(cell.value)
    if field in DATES:
        return day(cell.value)
    if field in CODES:
        return code(cell.value, field, cell.number_format)
    return text(cell.value)


def canonical_row(raw: dict) -> dict:
    """Also used to compare the ordinary sync's raw JSON without rewriting it."""
    row = {}
    for field, value in raw.items():
        if field not in KNOWN:
            continue
        if field in MONEY:
            row[field] = money(value)
        elif field in DATES:
            row[field] = day(value)
        elif field in CODES:
            row[field] = code(value, field)
        else:
            row[field] = text(value)
    return row


def decode_workbook(content: bytes, expected_rows: int, header_map: dict) -> tuple[dict, list]:
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=False)
    except Exception as exc:
        raise SnapshotInvalid("unreadable_xlsx") from exc
    try:
        if len(workbook.worksheets) != 1:
            raise SnapshotInvalid("unexpected_sheets")
        iterator = workbook.active.iter_rows()
        headers = [header_map.get(text(c.value), text(c.value)) for c in next(iterator, ())]
        if len(headers) != len(set(headers)) or not REQUIRED <= set(headers):
            raise SnapshotInvalid("missing_or_duplicate_columns")
        if set(headers) - KNOWN:
            raise SnapshotInvalid("unexpected_columns")
        rows = _decode_rows(iterator, headers)
        if len(rows) != expected_rows:
            raise SnapshotInvalid("row_count_mismatch")
        return rows, sorted(headers)
    finally:
        workbook.close()


def _decode_rows(iterator, headers: list) -> dict:
    rows = {}
    for cells in iterator:
        if not any(text(c.value) for c in cells):
            continue  # Includes the documented final Reso='\n' row.
        if len(cells) != len(headers):
            raise SnapshotInvalid("row_width_mismatch")
        row = {field: cell_value(cell, field) for field, cell in zip(headers, cells, strict=True)}
        key = row["Avviso"]
        if not key or not row["Anno"] or len(key) > 128:
            raise SnapshotInvalid("invalid_notice_key")
        if key in rows:
            raise SnapshotInvalid("ambiguous_duplicate_notice")
        rows[key] = row
    return rows
