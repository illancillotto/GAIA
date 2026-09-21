"""Safe STEP report parser using an explicit, operator-approved column map.

The STEP provider contract is not available yet.  This parser therefore never
guesses column names or derives an assignment from tax code, amount, or year.
It only creates immutable observation rows for a later staging workflow.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO, StringIO
from zipfile import BadZipFile, ZipFile

from openpyxl import load_workbook

from app.modules.ruolo.services.notice_import_excel import MAX_BYTES, MAX_ROWS, digest

PARSER_VERSION = "step-observation-v1"
REQUIRED_FIELDS = ("practice_id", "status")
OPTIONAL_FIELDS = (
    "event_id",
    "event_date",
    "document_number",
    "tax_code",
    "annuality",
    "amount_total",
    "amount_paid",
    "amount_residual",
    "reason",
)


@dataclass(frozen=True)
class StepSnapshot:
    content: bytes
    rows: list[dict]
    summary: dict


def _text(value: object) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _jsonable(value: object) -> object:
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def _validate(content: bytes) -> None:
    if not content or len(content) > MAX_BYTES:
        raise ValueError("File STEP vuoto o oltre il limite di 12 MiB")


def _rows_from_csv(content: bytes) -> list[dict[str, object]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV STEP non codificato in UTF-8") from exc
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ValueError("Intestazione CSV STEP assente")
    rows = [dict(row) for row in reader]
    return rows


def _rows_from_xlsx(content: bytes) -> list[dict[str, object]]:
    try:
        with ZipFile(BytesIO(content)) as archive:
            if sum(item.file_size for item in archive.infolist()) > 64 * 1024 * 1024:
                raise ValueError("Cartella Excel STEP oltre 64 MiB decompressi")
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True, keep_links=False)
    except (BadZipFile, KeyError, OSError, SyntaxError) as exc:
        raise ValueError("Cartella Excel STEP non valida") from exc
    try:
        sheet = workbook.active
        values = sheet.iter_rows(values_only=True)
        headers = [_text(value) for value in next(values, ())]
        if not headers or any(value is None for value in headers):
            raise ValueError("Intestazione Excel STEP assente o duplicata")
        rows = [dict(zip(headers, row, strict=False)) for row in values]
        return rows
    finally:
        workbook.close()


def _source_rows(content: bytes, filename: str) -> list[dict[str, object]]:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "csv":
        return _rows_from_csv(content)
    if suffix in {"xlsx", "xlsm"}:
        return _rows_from_xlsx(content)
    raise ValueError("Formato STEP non supportato: usare CSV o XLSX")


def parse_report(content: bytes, *, filename: str, mapping: dict[str, str]) -> StepSnapshot:
    """Parse a report into observations without matching or publishing them."""

    _validate(content)
    missing_mapping = [field for field in REQUIRED_FIELDS if not _text(mapping.get(field))]
    if missing_mapping:
        raise ValueError(f"Mapping STEP obbligatorio assente: {', '.join(missing_mapping)}")
    rows = _source_rows(content, filename)
    if len(rows) > MAX_ROWS:
        raise ValueError("Report STEP oltre il limite di 10000 righe")
    if not rows:
        raise ValueError("Report STEP vuoto")
    source_rows: list[dict] = []
    for row_number, original in enumerate(rows, 2):
        canonical = {field: _text(original.get(column)) for field, column in mapping.items() if field in REQUIRED_FIELDS + OPTIONAL_FIELDS}
        anomalies = ["step_da_verificare"]
        if not canonical.get("practice_id"):
            anomalies.append("pratica_step_assente")
        if not canonical.get("status"):
            anomalies.append("stato_step_assente")
        payload = {
            "source_namespace": "step",
            "practice_id": canonical.get("practice_id"),
            "event_id": canonical.get("event_id"),
            "status": canonical.get("status"),
            "event_date": canonical.get("event_date"),
            "document_number": canonical.get("document_number"),
            "tax_code": canonical.get("tax_code"),
            "annuality": canonical.get("annuality"),
            "amount_total": canonical.get("amount_total"),
            "amount_paid": canonical.get("amount_paid"),
            "amount_residual": canonical.get("amount_residual"),
            "reason": canonical.get("reason"),
            "original": {key: _jsonable(value) for key, value in original.items()},
        }
        fingerprint = digest(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode())
        source_rows.append({
            "row_number": row_number,
            "source_key": canonical.get("event_id") or canonical.get("practice_id") or f"row-{row_number}",
            "fingerprint": fingerprint,
            "payload": payload,
            "anomalies": anomalies,
        })
    snapshot = {"filename": filename, "parser_version": PARSER_VERSION, "rows": len(source_rows)}
    return StepSnapshot(content=content, rows=source_rows, summary={**snapshot, "unlinked_rows": len(source_rows)})
