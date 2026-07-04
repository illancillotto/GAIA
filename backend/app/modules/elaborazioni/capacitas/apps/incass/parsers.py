from __future__ import annotations

import html
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
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
    normalize_partita_comune_nome as _normalize_partita_comune_nome,
    parse_italian_decimal as _parse_italian_decimal,
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
    # La modale è testo monospace a colonne fisse: le righe raw (spaziatura
    # preservata) guidano il parse posizionale, quelle collassate i match testuali.
    raw_lines = _extract_partitario_raw_lines(html_content)
    collapsed_lines = [" ".join(raw.split()).strip() for raw in raw_lines]
    nonempty_lines = [line for line in collapsed_lines if line]
    if not nonempty_lines:
        return None

    partite: list[CapacitasInCassPartitarioPartita] = []
    current_partita: CapacitasInCassPartitarioPartita | None = None
    header_spec: list[tuple[str, int, int]] | None = None
    in_particelle_table = False
    in_consumi_block = False
    pending_summary: _IncassRow | None = None

    def _flush_pending_summary() -> None:
        nonlocal pending_summary
        if pending_summary is not None and current_partita is not None:
            current_partita.particelle.append(_row_to_parcel(pending_summary))
        pending_summary = None

    for raw_line, line in zip(raw_lines, collapsed_lines):
        m_partita = _RE_PARTITARIO_PARTITA.match(line)
        if m_partita:
            _flush_pending_summary()
            if current_partita is not None:
                partite.append(current_partita)
            current_partita = CapacitasInCassPartitarioPartita(
                codice_partita=m_partita.group(1).strip(),
                comune_nome=_normalize_partita_comune_nome(m_partita.group(2).strip()),
            )
            in_particelle_table = False
            in_consumi_block = False
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
            header_spec = _parse_partitario_header_spec(raw_line)
            in_particelle_table = True
            in_consumi_block = False
            continue
        if _looks_like_consumption_summary(line):
            # Da qui fino a Legenda/nuova partita ci sono solo righe consumi
            # (qualunque sia l'anno): mai interpretarle come particelle.
            _flush_pending_summary()
            in_consumi_block = True
            continue
        if _looks_like_consumption_header(line):
            continue
        if _looks_like_partitario_separator(line) or line.upper().startswith("LEGENDA"):
            _flush_pending_summary()
            in_particelle_table = False
            in_consumi_block = False
            continue
        if line.upper().startswith("ANNO TRIB"):
            continue
        if not in_particelle_table or in_consumi_block:
            continue

        row: _IncassRow | None = None
        if header_spec is not None:
            row = _parse_particella_row_by_columns(raw_line, header_spec)
        if row is None:
            row = _parse_particella_row_by_tokens(line.split())
        if row is None:
            continue

        if row.kind == "summary":
            _flush_pending_summary()
            pending_summary = row
            continue

        if pending_summary is not None and _is_same_parcel(pending_summary, row):
            row.importo_manut = pending_summary.importo_manut
            row.importo_ist = pending_summary.importo_ist
            row.subalterno = row.subalterno or pending_summary.subalterno
            pending_summary = None
        else:
            _flush_pending_summary()
        current_partita.particelle.append(_row_to_parcel(row))

    _flush_pending_summary()
    if current_partita is not None:
        partite.append(current_partita)

    normalized_text = _normalize_partitario_text(nonempty_lines)
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


_RE_BR_TAG = re.compile(r"<br\s*/?>", re.IGNORECASE)
_RE_HTML_TAG = re.compile(r"<[^>]+>")
_RE_TOKEN = re.compile(r"\S+")
# Gli importi della modale hanno sempre la virgola decimale ("2,30", "1.727,51"):
# è ciò che li distingue da classe coltura ("1") e superfici intere ("186.086").
_RE_IMPORTO_EURO = re.compile(r"^\d{1,3}(?:\.\d{3})*,\d+$")
_RE_INTERO_PUNTATO = re.compile(r"^\d{1,3}(?:\.\d{3})*$")
_PARTITARIO_COLUMN_NAMES = (
    "Dom.", "Dis.", "Fog.", "Part.", "Sub",
    "Sup.Cata.", "Sup.Irr.", "Colt.", "Manut.", "Irrig.", "Ist.",
)
# I valori numerici sono allineati a destra sul bordo del titolo colonna
# (scarto massimo osservato sulle modali reali: 1 carattere).
_COLUMN_EDGE_TOLERANCE = 2


@dataclass
class _IncassRow:
    # kind: "summary" = riga riepilogo partita (importi Manut./Ist., cioè 0648+0985);
    #       "detail"  = riga domanda irrigua (coltura + importo Irrig., cioè 0668).
    kind: str
    foglio: str
    particella: str
    domanda_irrigua: str | None = None
    distretto: str | None = None
    subalterno: str | None = None
    sup_catastale_are: Decimal | None = None
    sup_irrigata_ha: Decimal | None = None
    coltura: str | None = None
    importo_manut: Decimal | None = None
    importo_irrig: Decimal | None = None
    importo_ist: Decimal | None = None


def _extract_partitario_raw_lines(html_content: str) -> list[str]:
    if _RE_BR_TAG.search(html_content):
        segments = _RE_BR_TAG.split(html_content)
    else:
        segments = html_content.splitlines()
    lines: list[str] = []
    for segment in segments:
        cleaned = html.unescape(_RE_HTML_TAG.sub("", segment)).replace("\xa0", " ")
        for piece in cleaned.splitlines():
            if piece.strip():
                lines.append(piece)
    return lines


def _parse_partitario_header_spec(raw_header_line: str) -> list[tuple[str, int, int]] | None:
    tokens = [(m.group(0), m.start(), m.end()) for m in _RE_TOKEN.finditer(raw_header_line)]
    if tuple(token for token, _, _ in tokens) != _PARTITARIO_COLUMN_NAMES:
        return None
    # Gli offset hanno senso solo se l'header conserva la spaziatura originale
    # (input già collassato, es. info_text storico a DB, non ne ha).
    if not re.search(r"\S {2,}\S", raw_header_line):
        return None
    return tokens


def _looks_like_subalterno(value: str) -> bool:
    return value.isalpha() and len(value) <= 3


def _parse_particella_row_by_columns(
    raw_line: str,
    header_spec: list[tuple[str, int, int]],
) -> _IncassRow | None:
    tokens = [(m.group(0), m.start(), m.end()) for m in _RE_TOKEN.finditer(raw_line)]
    if not tokens:
        return None

    buckets: dict[str, list[str]] = {}
    for token, _start, end in tokens:
        name, _col_start, col_end = min(header_spec, key=lambda col: abs(col[2] - end))
        if name != "Colt." and abs(col_end - end) > _COLUMN_EDGE_TOLERANCE:
            return None
        buckets.setdefault(name, []).append(token)

    for name in _PARTITARIO_COLUMN_NAMES:
        if name != "Colt." and len(buckets.get(name, [])) > 1:
            return None

    def _single(name: str) -> str | None:
        values = buckets.get(name)
        return values[0] if values else None

    dom = _single("Dom.")
    dis = _single("Dis.")
    fog = _single("Fog.")
    part = _single("Part.")
    sub = _single("Sub")
    cata = _single("Sup.Cata.")
    sup_irr = _single("Sup.Irr.")
    colt_tokens = buckets.get("Colt.", [])
    manut = _single("Manut.")
    irrig = _single("Irrig.")
    ist = _single("Ist.")

    if dom is not None and not dom.isdigit():
        return None
    if dis is None or not dis.isdigit():
        return None
    if fog is None or not fog.isdigit():
        return None
    # La particella può non essere numerica (es. "acque" a Marrubiu).
    if part is None or not part.isalnum():
        return None
    if sub is not None and not _looks_like_subalterno(sub):
        return None
    if cata is None or not _RE_INTERO_PUNTATO.match(cata):
        return None
    if sup_irr is not None and not _RE_INTERO_PUNTATO.match(sup_irr):
        return None
    for amount in (manut, irrig, ist):
        if amount is not None and not _RE_IMPORTO_EURO.match(amount):
            return None

    if dom is None:
        if colt_tokens or sup_irr is not None or irrig is not None:
            return None
        if manut is None or ist is None:
            return None
        return _IncassRow(
            kind="summary",
            foglio=fog,
            particella=part,
            distretto=dis,
            subalterno=sub,
            sup_catastale_are=_parse_italian_decimal(cata),
            importo_manut=_parse_italian_decimal(manut),
            importo_ist=_parse_italian_decimal(ist),
        )

    # I token oltre il primo in Colt. sono classe/flag ("MAIS 1 I"), non importi.
    if not colt_tokens or not any(ch.isalpha() for ch in colt_tokens[0]):
        return None
    if manut is not None or ist is not None:
        return None
    return _IncassRow(
        kind="detail",
        foglio=fog,
        particella=part,
        domanda_irrigua=dom,
        distretto=dis,
        subalterno=sub,
        sup_catastale_are=_parse_italian_decimal(cata),
        sup_irrigata_ha=_parse_incass_domanda_surface_ha(sup_irr) if sup_irr else None,
        coltura=colt_tokens[0],
        importo_irrig=_parse_italian_decimal(irrig) if irrig else None,
    )


def _parse_particella_row_by_tokens(values: list[str]) -> _IncassRow | None:
    row = _parse_detail_row_tokens(values)
    if row is not None:
        return row
    row = _parse_summary_row_tokens(values)
    if row is not None:
        return row
    return _parse_combined_row_tokens(values)


def _parse_summary_row_tokens(values: list[str]) -> _IncassRow | None:
    if len(values) not in (6, 7):
        return None
    dis, fog, part = values[0], values[1], values[2]
    if not dis.isdigit() or not fog.isdigit() or not part.isalnum():
        return None
    index = 3
    sub: str | None = None
    if len(values) == 7:
        sub = values[3]
        index = 4
        if not _looks_like_subalterno(sub):
            return None
    cata, manut, ist = values[index], values[index + 1], values[index + 2]
    if not _RE_INTERO_PUNTATO.match(cata):
        return None
    if not _RE_IMPORTO_EURO.match(manut) or not _RE_IMPORTO_EURO.match(ist):
        return None
    return _IncassRow(
        kind="summary",
        foglio=fog,
        particella=part,
        distretto=dis,
        subalterno=sub,
        sup_catastale_are=_parse_italian_decimal(cata),
        importo_manut=_parse_italian_decimal(manut),
        importo_ist=_parse_italian_decimal(ist),
    )


def _parse_detail_row_tokens(values: list[str]) -> _IncassRow | None:
    if len(values) < 6:
        return None
    if not all(token.isdigit() for token in values[:4]):
        return None
    dom, dis, fog, part = values[:4]
    index = 4
    sub: str | None = None
    if index < len(values) and _looks_like_subalterno(values[index]):
        sub = values[index]
        index += 1
    if index >= len(values) or not _RE_INTERO_PUNTATO.match(values[index]):
        return None
    cata = values[index]
    index += 1
    sup_irr: str | None = None
    if index < len(values) and _RE_INTERO_PUNTATO.match(values[index]):
        sup_irr = values[index]
        index += 1
    if index >= len(values):
        return None
    coltura = values[index]
    if not any(ch.isalpha() for ch in coltura):
        return None
    index += 1

    amounts: list[str] = []
    for token in values[index:]:
        if _RE_IMPORTO_EURO.match(token):
            amounts.append(token)
        elif len(token) <= 2:
            # Classe/flag della coltura (es. "1", "I" in "MAIS 1 I").
            continue
        else:
            return None

    manut: str | None = None
    irrig: str | None = None
    ist: str | None = None
    if len(amounts) == 1:
        # Invariante verificata sulle modali reali: la riga domanda porta
        # un solo importo, sempre nella colonna Irrig. (tributo 0668).
        irrig = amounts[0]
    elif len(amounts) == 2:
        manut, ist = amounts
    elif len(amounts) == 3:
        # Righe già fuse dal vecchio parser (info_text storico a DB).
        manut, irrig, ist = amounts
    elif len(amounts) > 3:
        return None

    return _IncassRow(
        kind="detail",
        foglio=fog,
        particella=part,
        domanda_irrigua=dom,
        distretto=dis,
        subalterno=sub,
        sup_catastale_are=_parse_italian_decimal(cata),
        sup_irrigata_ha=_parse_incass_domanda_surface_ha(sup_irr) if sup_irr else None,
        coltura=coltura,
        importo_manut=_parse_italian_decimal(manut) if manut else None,
        importo_irrig=_parse_italian_decimal(irrig) if irrig else None,
        importo_ist=_parse_italian_decimal(ist) if ist else None,
    )


def _parse_combined_row_tokens(values: list[str]) -> _IncassRow | None:
    # Riga riepilogo + riga domanda finite sulla stessa riga logica
    # (prodotte dal coalesce del parser precedente in info_text storici).
    if len(values) < 12:
        return None
    for split_at in (6, 7):
        summary = _parse_summary_row_tokens(values[:split_at])
        if summary is None:
            continue
        detail = _parse_detail_row_tokens(values[split_at:])
        if detail is None:
            continue
        if not _is_same_parcel(summary, detail):
            continue
        detail.importo_manut = summary.importo_manut
        detail.importo_ist = summary.importo_ist
        detail.subalterno = detail.subalterno or summary.subalterno
        return detail
    return None


def _is_same_parcel(summary: _IncassRow, detail: _IncassRow) -> bool:
    if summary.distretto != detail.distretto:
        return False
    if summary.foglio != detail.foglio or summary.particella != detail.particella:
        return False
    if summary.subalterno and detail.subalterno and summary.subalterno != detail.subalterno:
        return False
    return _decimal_to_string(summary.sup_catastale_are) == _decimal_to_string(detail.sup_catastale_are)


def _row_to_parcel(row: _IncassRow) -> CapacitasInCassPartitarioParcel:
    sup_are = row.sup_catastale_are
    sup_ha = (sup_are / Decimal("100")) if sup_are is not None else None
    return CapacitasInCassPartitarioParcel(
        domanda_irrigua=row.domanda_irrigua,
        distretto=row.distretto,
        foglio=row.foglio,
        particella=row.particella,
        subalterno=row.subalterno,
        sup_catastale_are=_decimal_to_string(sup_are),
        sup_catastale_ha=_decimal_to_string(sup_ha),
        sup_irrigata_ha=_decimal_to_string(row.sup_irrigata_ha),
        coltura=row.coltura,
        importo_manut_euro=_decimal_to_string(row.importo_manut),
        importo_irrig_euro=_decimal_to_string(row.importo_irrig),
        importo_ist_euro=_decimal_to_string(row.importo_ist),
    )


def _parse_incass_domanda_surface_ha(raw: str) -> Decimal | None:
    if not raw:
        return None
    value = raw.strip()
    if not value:
        return None
    if "," in value:
        # Defensive fallback: if the source already uses decimals, keep the parsed value.
        return _parse_italian_decimal(value)
    normalized = value.replace(".", "")
    try:
        mq_value = Decimal(normalized)
    except InvalidOperation:
        return None
    return mq_value / Decimal("10000")


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


def _looks_like_consumption_summary(line: str) -> bool:
    upper = line.upper()
    return upper.startswith("CONSUMI DA CONTATORE:")


def _looks_like_consumption_header(line: str) -> bool:
    upper = line.upper()
    return upper.startswith("ANNO DOMANDA DISTRETTO SUP.DOMANDA")


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
