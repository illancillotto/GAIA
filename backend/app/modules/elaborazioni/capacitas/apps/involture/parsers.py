from __future__ import annotations

import json5
import re
from datetime import date, datetime
from urllib.parse import unquote

from bs4 import BeautifulSoup

from app.modules.elaborazioni.bonifica_oristanese.parsers import clean_html_text
from app.modules.elaborazioni.capacitas.models import (
    CapacitasLookupOption,
    CapacitasIntestatario,
    CapacitasTerreniSearchResult,
    CapacitasTerrenoCertificato,
    CapacitasCertificatoTerreno,
    CapacitasTerrenoDetail,
    CapacitasTerrenoRow,
)


def parse_lookup_options(payload: str) -> list[CapacitasLookupOption]:
    rows = _parse_jsish_payload(payload, context="lookup_options")
    return parse_lookup_option_rows(rows)


def parse_lookup_option_rows(rows: list[object]) -> list[CapacitasLookupOption]:
    options: list[CapacitasLookupOption] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item_id = str(row.get("ID", "")).strip()
        display = clean_html_text(unquote(str(row.get("Display", "")).replace("+", " ")))
        if not item_id or not display:
            continue
        options.append(CapacitasLookupOption(id=item_id, display=display))
    return options


def parse_terreni_search_result(payload: str | list | dict) -> CapacitasTerreniSearchResult:
    if isinstance(payload, list):
        rows_raw = [row for row in payload if isinstance(row, dict)]
    elif isinstance(payload, dict):
        rows_raw = [payload]
    else:
        rows_raw = _parse_jsish_payload(payload, context="terreni_search_result")
    rows = [_normalize_terreno_row(row) for row in rows_raw]
    return CapacitasTerreniSearchResult(total=len(rows), rows=rows)


def parse_certificato_html(html: str) -> CapacitasTerrenoCertificato:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("#Capacitas_ContentMain_ContentCertificatoPre")
    text = clean_html_text(container or html)

    partita_match = re.search(r"PARTITA:\s*([^\s]+)\s*-\s*(.*?)\s*-\s*STATO:\s*(.*?)(?:UTENZA:|$)", text)
    utenza_match = re.search(r"UTENZA:\s*([^\s]+)\s*-\s*STATO CNC:\s*(.*?)(?:DI:|$)", text)

    intestatari = _parse_capacitas_intestatari(container) if container else []

    terreni: list[CapacitasCertificatoTerreno] = []
    terreno_rows = list(container.select(".rpt-riga-terreno") if container else [])
    for idx, row in enumerate(terreno_rows):
        row_text = clean_html_text(row)
        row_id = row.get("data-id")
        if "Riordino:" in row_text:
            continue

        riordino_text = ""
        if idx + 1 < len(terreno_rows):
            next_text = clean_html_text(terreno_rows[idx + 1])
            if "Riordino:" in next_text:
                riordino_text = next_text

        terrain = _parse_certificato_terreno_row(row_text, row_id)
        terrain.riordino_code = _extract_optional(riordino_text, r"Riordino:\s*([^ ]+\s*\d+/\d+)")
        terrain.riordino_maglia = _extract_optional(riordino_text, r"Maglia:\s*([^\s]+)")
        terrain.riordino_lotto = _extract_optional(riordino_text, r"Lotto:\s*([^\s]+)")
        terreni.append(terrain)

    return CapacitasTerrenoCertificato(
        cco=_extract_optional_from_url_or_html(html, "CCO"),
        fra=_extract_optional_from_url_or_html(html, "FRA"),
        ccs=_extract_optional_from_url_or_html(html, "CCS"),
        pvc=_extract_optional_from_url_or_html(html, "PVC"),
        com=_extract_optional_from_url_or_html(html, "COM"),
        partita_code=partita_match.group(1).strip() if partita_match else None,
        comune_label=clean_html_text(partita_match.group(2)) if partita_match else None,
        partita_status=clean_html_text(partita_match.group(3)) if partita_match else None,
        utenza_code=utenza_match.group(1).strip() if utenza_match else None,
        utenza_status=clean_html_text(utenza_match.group(2)) if utenza_match else None,
        ruolo_status=clean_html_text(partita_match.group(3)) if partita_match else None,
        intestatari=intestatari,
        terreni=terreni,
        raw_text=text,
        raw_html=html,
    )


def _parse_capacitas_intestatari(container: BeautifulSoup) -> list[CapacitasIntestatario]:
    rows = list(container.select(".rpt-riga-ana"))
    results: list[CapacitasIntestatario] = []
    for row in rows:
        den = row.select_one(".rpt-testo-evid")
        denominazione = clean_html_text(den) if den else None
        row_text = clean_html_text(row)
        codice_fiscale_match = re.search(r"\bC\.F\.\s*([A-Z0-9]{11,16})\b", row_text, flags=re.IGNORECASE)
        event_span = next(
            (span for span in row.select("span") if any(cls.startswith("evento-") for cls in (span.get("class") or []))),
            None,
        )
        lines = _collect_intestatario_detail_lines(row)
        birth_data = _parse_birth_line(lines)
        res_data = _parse_residenza_line(lines)
        titoli = _parse_titoli_line(lines)
        deceduto_text = clean_html_text(event_span) if event_span else ""
        results.append(
            CapacitasIntestatario(
                idxana=_strip_value(row.get("data-idxana")),
                idxesa=_strip_value(row.get("data-idxesa")),
                codice_fiscale=codice_fiscale_match.group(1).upper() if codice_fiscale_match else None,
                denominazione=denominazione,
                data_nascita=birth_data[0],
                luogo_nascita=birth_data[1],
                residenza=res_data[0],
                comune_residenza=res_data[1],
                cap=res_data[2],
                titoli=titoli,
                deceduto="decedut" in deceduto_text.casefold(),
            )
        )
    return results


def parse_terreno_detail_html(html: str) -> CapacitasTerrenoDetail:
    soup = BeautifulSoup(html, "html.parser")
    params: dict[str, str] = {}

    for row in _extract_load_data_grid_rows(html):
        key = str(row.get("Parametro", "")).strip()
        if not key:
            continue
        params[key] = clean_html_text(row.get("VStr") or row.get("VINT") or row.get("VFLO") or "")

    return CapacitasTerrenoDetail(
        external_row_id=_extract_optional_from_url_or_html(html, "ID"),
        foglio=_extract_input_value(soup, "Capacitas_ContentMain_txtFoglioDt"),
        particella=_extract_input_value(soup, "Capacitas_ContentMain_txtParticDt"),
        sub=_extract_input_value(soup, "Capacitas_ContentMain_txtSubDt"),
        riordino_code=params.get("RIORDINO_F"),
        riordino_maglia=params.get("MAGLIA_RF"),
        riordino_lotto=params.get("LOTTO_RF"),
        irridist=params.get("IRRIDIST") or params.get("OLDIRRIDIS"),
        parameters=params,
        raw_html=html,
    )


def _parse_certificato_terreno_row(row_text: str, row_id: str | None) -> CapacitasCertificatoTerreno:
    compact = " ".join(row_text.split())
    match = re.search(r"^\s*(\S+)\s+(\S+)\s+(\S+)\s+(.*?)\s+([\d\.,]+)\s", compact)
    if match:
        return CapacitasCertificatoTerreno(
            external_row_id=row_id,
            foglio=match.group(2).strip(),
            particella=match.group(3).strip(),
            sub=None if not match.group(4).strip() else match.group(4).strip(),
            superficie_text=match.group(5).strip(),
        )
    return CapacitasCertificatoTerreno(external_row_id=row_id)


def _collect_intestatario_detail_lines(row) -> list[str]:
    lines: list[str] = []
    sibling = row.find_next_sibling()
    while sibling is not None:
        classes = sibling.get("class") or []
        if "rpt-riga-ana" in classes or "rpt-riga-terreno" in classes or "rpt-sep" in classes:
            break
        if "rpt-riga-vuota" in classes:
            break
        if "rpt-riga" in classes:
            lines.append(clean_html_text(sibling))
        sibling = sibling.find_next_sibling()
    return lines


def _parse_birth_line(lines: list[str]) -> tuple[date | None, str | None]:
    for line in lines:
        match = re.search(r"nat[oa]\s+il\s+(\d{2}/\d{2}/\d{4})\s+in\s+<?[^>]*>?\s*(.+)$", line, flags=re.IGNORECASE)
        if not match:
            continue
        date_value = None
        try:
            date_value = datetime.strptime(match.group(1), "%d/%m/%Y").date()
        except ValueError:
            date_value = None
        return date_value, clean_html_text(match.group(2))
    return None, None


def _parse_residenza_line(lines: list[str]) -> tuple[str | None, str | None, str | None]:
    for line in lines:
        if not line.startswith("RES:"):
            continue
        cleaned = clean_html_text(line[4:])
        cap_match = re.match(r"(\d{5})\s+(.*)$", cleaned)
        cap = cap_match.group(1) if cap_match else None
        remainder = cap_match.group(2) if cap_match else cleaned
        comune_match = re.search(r"(.+?)\s*\(([A-Z]{2})\)\s*-\s*(.+)$", remainder)
        if comune_match:
            comune = clean_html_text(comune_match.group(1))
            indirizzo = clean_html_text(comune_match.group(3))
            return f"{(cap + ' ') if cap else ''}{comune} ({comune_match.group(2)}) - {indirizzo}".strip(), comune, cap
        return cleaned or None, None, cap
    return None, None, None


def _parse_titoli_line(lines: list[str]) -> str | None:
    for line in lines:
        if line.startswith("TITOLI:"):
            return clean_html_text(line[7:])
    return None


def _normalize_terreno_row(row: dict) -> CapacitasTerrenoRow:
    item = CapacitasTerrenoRow.model_validate(row)
    item.foglio = _strip_value(item.foglio)
    item.particella = _strip_value(item.particella)
    item.sub = _strip_value(item.sub)
    item.sez = _strip_value(item.sez)
    item.superficie = _strip_value(item.superficie)
    item.row_visual_state = _derive_row_visual_state(item.ta_ext)
    return item


def _derive_row_visual_state(value: str | None) -> str | None:
    normalized = _strip_value(value)
    if not normalized:
        return "current_black"
    if normalized.startswith("#"):
        return "historic_red"
    if normalized.startswith("*"):
        return "historic_marker"
    return "current_black"


def _parse_jsish_payload(payload: str, context: str = "payload") -> list[dict]:
    cleaned = payload.strip().lstrip("\ufeff")
    if not cleaned:
        return []
    try:
        parsed = json5.loads(cleaned)
    except Exception as exc:
        snippet = clean_html_text(cleaned)[:240]
        raise ValueError(f"Capacitas parser error ({context}): payload inatteso: {snippet}") from exc
    if isinstance(parsed, dict):
        return [parsed]
    return [row for row in parsed if isinstance(row, dict)]


def _extract_load_data_grid_rows(html: str) -> list[dict]:
    match = re.search(r'loadDataGridV2\([^,]+,\s*(".*?"|\'.*?\')\s*,\s*false\)', html, flags=re.DOTALL)
    if not match:
        return []
    encoded = match.group(1)[1:-1]
    decoded = encoded.encode("utf-8").decode("unicode_escape")
    return _parse_jsish_payload(decoded, context="detail_grid")


def _extract_optional(value: str, pattern: str) -> str | None:
    match = re.search(pattern, value)
    if not match:
        return None
    return clean_html_text(match.group(1))


def _extract_optional_from_url_or_html(html: str, param: str) -> str | None:
    match = re.search(rf"[?&]{param}=([^&\"']+)", html)
    if not match:
        return None
    return match.group(1)


def _extract_input_value(soup: BeautifulSoup, field_id: str) -> str | None:
    field = soup.select_one(f"#{field_id}")
    if field is None:
        return None
    return _strip_value(field.get("value"))


def _strip_value(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
