from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from openpyxl import load_workbook


HEADER_ALIASES: dict[str, str] = {
    "ID": "excel_id",
    "PUNTO_CONS": "punto_consegna",
    "PUNTO DI CONSEGNA": "punto_consegna",
    "COD_CONT": "matricola",
    "MATRIC.": "matricola",
    "MATRICOLA": "matricola",
    "SIGILLO": "sigillo",
    "TIPOLOGIA": "tipologia_idrante",
    "TIPOLOGIA IDRANTE": "tipologia_idrante",
    "TIPO": "record_type",
    "FIRMWARE": "firmware_version",
    "VERSIONE FIRMWARE": "firmware_version",
    "BATTERIA": "battery_level",
    "LIVELLO BATTERIA": "battery_level",
    "LETTURA FINALE 2024": "lettura_iniziale",
    "LETTURA INIZIALE 2025": "lettura_iniziale",
    "LETTURA INTERMEDIA 2025": "lettura_iniziale",
    "LETTURA FINALE 2025": "lettura_finale",
    "TOTALE M3 2025": "consumo_mc",
    "CONSUMO 2025 TOT. M3": "consumo_mc",
    "DATA LETTURA": "data_lettura",
    "OPERATORE LETTURA": "operatore_lettura",
    "INTERVENTO DA ESEGUIRE": "intervento_da_eseguire",
    "INTERVENTO ESEGUITO": "intervento_eseguito",
    "OPERATORE INTERVENTO": "operatore_intervento",
    "DATA INTERVENTO": "data_intervento",
    "TITOLARE DUI 2025": "dui",
    "D.U.I.": "dui",
    "COD. FISC": "codice_fiscale",
    "COD FISCALE": "codice_fiscale",
    "COLTURA": "coltura",
    "TARIFFA": "tariffa",
    "FONDO CHIUSO": "fondo_chiuso",
    "NOTE": "note",
    "TELEFONO": "telefono",
}


class MeterReadingsParseError(ValueError):
    """Raised when the uploaded workbook cannot be parsed safely."""


_SPREADSHEETML_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


@dataclass
class ParsedMeterReadingRow:
    row_number: int
    data: dict[str, Any]


@dataclass
class ParsedMeterReadingsFile:
    filename: str
    anno: int | None
    distretto_code: str | None
    rows: list[ParsedMeterReadingRow]


def normalize_header(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = str(value).strip()
    if not text:
        return None
    normalized = text
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _detect_header_row(sheet) -> int:
    best_row = 1
    best_score = -1
    for idx, row in enumerate(sheet.iter_rows(min_row=1, max_row=min(10, sheet.max_row), values_only=True), start=1):
        headers = [normalize_header(cell) for cell in row if normalize_header(cell)]
        score = sum(1 for header in headers if header in HEADER_ALIASES)
        if score > best_score:
            best_row = idx
            best_score = score
    return best_row


def _extract_filename_metadata(filename: str) -> tuple[str | None, int | None]:
    stem = Path(filename).stem
    year_match = re.search(r"(20\d{2})", stem)
    anno = int(year_match.group(1)) if year_match else None
    distretto_code: str | None = None

    explicit_match = re.search(r"\bD(?:ISTRETTO)?\s*[-_ ]?\s*0*([0-9]{1,3}[A-Za-z]?)\b", stem, flags=re.IGNORECASE)
    if explicit_match:
        distretto_code = explicit_match.group(1)
    else:
        normalized_stem = unicodedata.normalize("NFD", stem)
        normalized_stem = "".join(char for char in normalized_stem if not unicodedata.combining(char))
        for candidate in re.findall(r"\b0*([0-9]{1,3}[A-Za-z]?)\b", normalized_stem):
            if anno is not None and candidate.isdigit() and int(candidate) == anno:
                continue
            distretto_code = candidate
            break

    return (distretto_code.upper() if distretto_code else None, anno)


def _sanitize_stylesheet_font_family(file_bytes: bytes) -> bytes | None:
    try:
        with ZipFile(BytesIO(file_bytes), "r") as source:
            if "xl/styles.xml" not in source.namelist():
                return None
            styles_xml = source.read("xl/styles.xml")
            root = ET.fromstring(styles_xml)
            changed = False
            for family in root.findall(f".//{{{_SPREADSHEETML_NS}}}family"):
                raw = family.get("val")
                if raw is None:
                    continue
                try:
                    numeric = int(raw)
                except ValueError:
                    continue
                if numeric > 14:
                    family.set("val", "14")
                    changed = True
            if not changed:
                return None

            updated_styles = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            output = BytesIO()
            with ZipFile(output, "w", compression=ZIP_DEFLATED) as target:
                for name in source.namelist():
                    payload = updated_styles if name == "xl/styles.xml" else source.read(name)
                    target.writestr(name, payload)
            return output.getvalue()
    except (BadZipFile, ET.ParseError, KeyError):
        return None


def _load_workbook_with_fallback(file_bytes: bytes):
    try:
        return load_workbook(filename=BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as exc:
        repaired = _sanitize_stylesheet_font_family(file_bytes)
        if repaired is not None:
            try:
                return load_workbook(filename=BytesIO(repaired), read_only=True, data_only=True)
            except Exception:
                pass
        raise MeterReadingsParseError(
            "File Excel non leggibile. Salvare nuovamente il file come .xlsx da Excel o LibreOffice e riprovare."
        ) from exc


def parse_meter_readings_excel(file_bytes: bytes, filename: str) -> ParsedMeterReadingsFile:
    workbook = _load_workbook_with_fallback(file_bytes)
    sheet = workbook[workbook.sheetnames[0]]
    header_row = _detect_header_row(sheet)
    header_values = next(sheet.iter_rows(min_row=header_row, max_row=header_row, values_only=True))
    mapped_headers: dict[int, str] = {}
    for index, value in enumerate(header_values):
        alias = HEADER_ALIASES.get(normalize_header(value))
        if alias:
            mapped_headers[index] = alias

    parsed_rows: list[ParsedMeterReadingRow] = []
    for row_number, row in enumerate(sheet.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
        item: dict[str, Any] = {}
        has_values = False
        for index, field_name in mapped_headers.items():
            raw_value = row[index] if index < len(row) else None
            if raw_value not in (None, ""):
                has_values = True
            if field_name in {"lettura_iniziale", "lettura_finale", "consumo_mc"}:
                item[field_name] = _parse_decimal(raw_value)
            elif field_name in {"data_lettura", "data_intervento"}:
                item[field_name] = _parse_date(raw_value)
            else:
                item[field_name] = _clean_string(raw_value)
        if not has_values:
            continue
        parsed_rows.append(ParsedMeterReadingRow(row_number=row_number, data=item))

    distretto_code, anno = _extract_filename_metadata(filename)
    return ParsedMeterReadingsFile(
        filename=filename,
        anno=anno,
        distretto_code=distretto_code,
        rows=parsed_rows,
    )
