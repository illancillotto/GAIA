from __future__ import annotations

import html
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.modules.elaborazioni.capacitas.models import (
    CapacitasInCassPartitarioDetail,
    CapacitasInCassPartitarioParcel,
    CapacitasInCassPartitarioPartita,
    CapacitasInCassNoticeDetail,
    CapacitasInCassNoticePdf,
    CapacitasInCassNoticeRow,
    CapacitasInCassSearchResult,
)
from app.modules.ruolo.services.parsing_common import (
    looks_like_number as _looks_like_number,
    normalize_partita_comune_nome as _normalize_partita_comune_nome,
    parse_particella_line as _parse_particella_line,
)


_WHITESPACE_RE = re.compile(r"\s+")
_URL_RE = re.compile(r"(?:href|location\.href|window\.open)\s*[:=]?\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)


def parse_incass_search_result(payload: object, *, base_url: str) -> CapacitasInCassSearchResult:
    rows_payload: list[object]
    if isinstance(payload, dict):
        candidate_rows = payload.get("rows", payload.get("Rows", payload.get("data", payload.get("Data", []))))
        rows_payload = candidate_rows if isinstance(candidate_rows, list) else []
    elif isinstance(payload, list):
        rows_payload = payload
    else:
        rows_payload = []

    rows: list[CapacitasInCassNoticeRow] = []
    for item in rows_payload:
        if not isinstance(item, dict):
            continue
        row = CapacitasInCassNoticeRow.model_validate(item)
        if row.avviso:
            row.detail_url = f"{base_url}/pages/dettaglioAvviso.aspx?avviso={row.avviso}"
        row.stato_pagamento_label = _derive_payment_status(row)
        rows.append(row)
    return CapacitasInCassSearchResult(total=len(rows), rows=rows)


def parse_incass_notice_detail(html: str, *, detail_url: str, base_url: str, avviso: str) -> CapacitasInCassNoticeDetail:
    soup = BeautifulSoup(html, "html.parser")
    pdf_links: list[CapacitasInCassNoticePdf] = []
    seen_urls: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        absolute = _normalize_asset_url(base_url, href)
        if not absolute or absolute in seen_urls:
            continue
        if _looks_like_pdf_or_download(absolute):
            seen_urls.add(absolute)
            pdf_links.append(
                CapacitasInCassNoticePdf(
                    label=_normalize_text(anchor.get_text(" ", strip=True)) or "Documento avviso",
                    filename=_extract_filename(absolute),
                    url=absolute,
                )
            )

    for url in _extract_script_urls(html):
        absolute = _normalize_asset_url(base_url, url)
        if not absolute or absolute in seen_urls:
            continue
        if _looks_like_pdf_or_download(absolute):
            seen_urls.add(absolute)
            pdf_links.append(
                CapacitasInCassNoticePdf(
                    label="Documento avviso",
                    filename=_extract_filename(absolute),
                    url=absolute,
                )
            )

    info_text = _normalize_text(soup.get_text("\n", strip=True))
    return CapacitasInCassNoticeDetail(
        avviso=avviso,
        detail_url=detail_url,
        info_html=html,
        info_text=info_text,
        pdf_links=pdf_links,
        raw_html=html,
    )


def parse_incass_partitario_html(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    return _normalize_text(soup.get_text("\n", strip=True))


_RE_PARTITARIO_PARTITA = re.compile(r"^Partita\s+(\S+)\s+beni\s+in\s+comune\s+di\s+(.+)$", re.IGNORECASE)
_RE_PARTITARIO_CONTRIBUENTE = re.compile(r"^Contribuente:\s*(.*?)\s*(?:C\.F\.\s*(\S+))?$", re.IGNORECASE)
_RE_PARTITARIO_COINTEST = re.compile(r"^Co-?intestato\s+con:\s*(.*)$", re.IGNORECASE)
_RE_PARTITARIO_TRIBUTO = re.compile(r"^(\d{4})\s+(0648|0985|0668)\s+.+?\s+([\d.,]+)\s+euro$", re.IGNORECASE)


def parse_incass_partitario_dialog(
    html_content: str,
    *,
    avviso: str,
) -> CapacitasInCassPartitarioDetail | None:
    soup = BeautifulSoup(html_content, "html.parser")
    text_source = soup.get_text("\n", strip=False)
    lines = _extract_partitario_lines(text_source)
    if not lines:
        return None
    lines = _coalesce_partitario_lines(lines)

    partite: list[CapacitasInCassPartitarioPartita] = []
    current_partita: CapacitasInCassPartitarioPartita | None = None

    for line in lines:
        m_partita = _RE_PARTITARIO_PARTITA.match(line)
        if m_partita:
            if current_partita is not None:
                partite.append(current_partita)
            current_partita = CapacitasInCassPartitarioPartita(
                codice_partita=m_partita.group(1).strip(),
                comune_nome=_normalize_partita_comune_nome(m_partita.group(2).strip()),
            )
            continue

        if current_partita is None:
            continue

        m_contribuente = _RE_PARTITARIO_CONTRIBUENTE.match(line)
        if m_contribuente:
            current_partita.contribuente = _normalize_text(m_contribuente.group(1))
            current_partita.contribuente_cf = _normalize_text(m_contribuente.group(2))
            continue

        m_cointestato = _RE_PARTITARIO_COINTEST.match(line)
        if m_cointestato:
            current_partita.co_intestati_raw = _normalize_text(m_cointestato.group(1))
            continue

        m_tributo = _RE_PARTITARIO_TRIBUTO.match(line)
        if m_tributo:
            tributo = m_tributo.group(2)
            importo = m_tributo.group(3).strip()
            if tributo == "0648":
                current_partita.importo_0648_euro = importo
            elif tributo == "0985":
                current_partita.importo_0985_euro = importo
            elif tributo == "0668":
                current_partita.importo_0668_euro = importo
            continue

        if _looks_like_partitario_header(line):
            continue
        if _looks_like_partitario_separator(line):
            continue

        parsed_particella = _parse_particella_line(line.split())
        if parsed_particella is None:
            continue
        current_partita.particelle.append(
            CapacitasInCassPartitarioParcel(
                domanda_irrigua=parsed_particella.domanda_irrigua,
                distretto=parsed_particella.distretto,
                foglio=parsed_particella.foglio,
                particella=parsed_particella.particella,
                subalterno=parsed_particella.subalterno,
                sup_catastale_are=_decimal_to_string(parsed_particella.sup_catastale_are),
                sup_catastale_ha=_decimal_to_string(parsed_particella.sup_catastale_ha),
                sup_irrigata_ha=_decimal_to_string(parsed_particella.sup_irrigata_ha),
                coltura=parsed_particella.coltura,
                importo_manut_euro=_decimal_to_string(parsed_particella.importo_manut),
                importo_irrig_euro=_decimal_to_string(parsed_particella.importo_irrig),
                importo_ist_euro=_decimal_to_string(parsed_particella.importo_ist),
            )
        )

    if current_partita is not None:
        partite.append(current_partita)

    normalized_text = _normalize_partitario_text(lines)
    if not partite and normalized_text is None:
        return None
    return CapacitasInCassPartitarioDetail(
        avviso=avviso,
        info_html=html_content,
        info_text=normalized_text,
        partite=partite,
        raw_html=html_content,
    )


def _derive_payment_status(row: CapacitasInCassNoticeRow) -> str | None:
    carico = _to_float(row.carico)
    differenza = _to_float(row.differenza)
    riscosso = _to_float(row.riscosso)
    sgravio = _to_float(row.sgravio)
    riporto = _to_float(row.riporto)
    annullato = _to_float(row.annullato)
    rateizzato = _to_float(row.rateizzato)
    pag_post_chiu = _to_int(row.pag_post_chiu)
    reg_post_chiu = _to_int(row.reg_post_chiu)

    if pag_post_chiu == 1:
        return "Pagamento tardivo"
    if reg_post_chiu == 1:
        return "Pagamento tardivo registrato post-chiusura"
    if annullato != 0:
        if rateizzato == 0:
            return "Annullato"
        if differenza == 0:
            return "Rateizzato totalmente pagato"
        if riscosso != 0:
            return "Rateizzato e pagato in parte"
        return "Rateizzato senza pagamenti"
    if riporto != 0:
        return "A riporto"
    if abs(carico) == abs(sgravio) and differenza == 0 and carico != 0:
        return "Totalmente sgravato"
    if differenza < 0:
        return "Con esubero"
    if carico == differenza and carico > 0:
        return "Non pagato"
    if differenza == 0 and carico != 0:
        return "Pagato"
    if differenza > 0:
        return "Parzialmente pagato"
    return None


def _to_float(value: str | None) -> float:
    if value is None:
        return 0.0
    normalized = str(value).strip().replace(".", "").replace(",", ".")
    if not normalized:
        return 0.0
    try:
        return float(normalized)
    except ValueError:
        return 0.0


def _to_int(value: str | None) -> int:
    if value is None:
        return 0
    try:
        return int(str(value).strip() or "0")
    except ValueError:
        return 0


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _WHITESPACE_RE.sub(" ", value).strip()
    return normalized or None


def _extract_partitario_lines(raw_text: str) -> list[str]:
    normalized = html.unescape(raw_text).replace("\xa0", " ")
    return [
        line
        for raw_line in normalized.splitlines()
        if (line := " ".join(raw_line.split()).strip())
    ]


def _coalesce_partitario_lines(lines: list[str]) -> list[str]:
    if len(lines) < 2:
        return lines

    merged: list[str] = []
    index = 0
    while index < len(lines):
        current = lines[index]
        if index + 1 < len(lines):
            maybe_merged = _merge_wrapped_particella_lines(current, lines[index + 1])
            if maybe_merged is not None:
                merged.append(maybe_merged)
                index += 2
                continue
        merged.append(current)
        index += 1
    return merged


def _merge_wrapped_particella_lines(current: str, following: str) -> str | None:
    current_tokens = current.split()
    following_tokens = following.split()

    # Capacitas sometimes wraps one logical row on two <br> lines.
    # Example:
    #   7 6 1349 186.086 679,26 485,11
    #   1598 7 6 1349 186.086 1.000 FRUTTETO 4,07
    # We need to rebuild:
    #   1598 7 6 1349 186.086 1.000 FRUTTETO 679,26 4,07 485,11
    if len(current_tokens) != 6 or len(following_tokens) != 8:
        return None
    if not all(token.isdigit() for token in current_tokens[:3]):
        return None
    if not following_tokens[0].isdigit():
        return None
    if following_tokens[1:5] != current_tokens[:4]:
        return None
    if not all(_looks_like_number(token) for token in (current_tokens[4], current_tokens[5], following_tokens[5], following_tokens[7])):
        return None
    if _looks_like_number(following_tokens[6]):
        return None

    merged_tokens = [
        following_tokens[0],
        following_tokens[1],
        following_tokens[2],
        following_tokens[3],
        following_tokens[4],
        following_tokens[5],
        following_tokens[6],
        current_tokens[4],
        following_tokens[7],
        current_tokens[5],
    ]
    return " ".join(merged_tokens)


def _looks_like_partitario_header(line: str) -> bool:
    header = line.upper()
    return "FOG." in header and "PART." in header and "SUP.CATA." in header


def _looks_like_partitario_separator(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if set(stripped) <= {"=", "-"}:
        return True
    return stripped.upper().startswith("ELENCO DELLE PARTITE")


def _normalize_partitario_text(lines: list[str]) -> str | None:
    normalized = "\n".join(lines).strip()
    return normalized or None


def _decimal_to_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _normalize_asset_url(base_url: str, url: str | None) -> str | None:
    if not url:
        return None
    candidate = url.strip().replace("&amp;", "&")
    if candidate.startswith("javascript:"):
        return None
    return urljoin(base_url, candidate)


def _looks_like_pdf_or_download(url: str) -> bool:
    normalized = url.lower()
    return any(
        token in normalized
        for token in (".pdf", "otpstampaavviso.aspx", "download.aspx", "stampapdfavviso.aspx", "stampaavviso.aspx")
    )


def _extract_script_urls(html: str) -> list[str]:
    return [match.group(1).replace("&amp;", "&") for match in _URL_RE.finditer(html)]


def _extract_filename(url: str) -> str | None:
    tail = url.rstrip("/").rsplit("/", maxsplit=1)[-1]
    return tail or None
