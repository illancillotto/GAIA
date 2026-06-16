"""
Parser del file Ruolo consortile in formato .dmp / PDF testuale.

Formato sorgente: testo pre-formattato generato da Capacitas.
Ogni "Partita CNC" è delimitata da marcatori <inizio> e <-fine->.
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal

from app.modules.ruolo.services.parsing_common import (
    ParsedParticella,
    looks_like_number as _looks_like_number,
    normalize_partita_comune_nome as _normalize_partita_comune_nome,
    parse_italian_decimal as _parse_italian_decimal,
    parse_particella_line as _parse_particella_line,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dataclasses di output del parser
# ---------------------------------------------------------------------------

@dataclass
class ParsedPartita:
    codice_partita: str
    comune_nome: str
    contribuente_cf: str | None
    co_intestati_raw: str | None
    importo_0648: Decimal | None
    importo_0985: Decimal | None
    importo_0668: Decimal | None
    particelle: list[ParsedParticella] = field(default_factory=list)


@dataclass
class ParsedPartitaCNC:
    codice_cnc: str
    codice_fiscale_raw: str
    n2_extra_raw: str | None
    nominativo_raw: str
    domicilio_raw: str | None
    residenza_raw: str | None
    codice_utenza: str | None
    importo_totale_0648: Decimal | None
    importo_totale_0985: Decimal | None
    importo_totale_0668: Decimal | None
    importo_totale_euro: Decimal | None
    importo_totale_lire: Decimal | None
    n4_campo_sconosciuto: str | None
    partite: list[ParsedPartita] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Prefisso NP
# ---------------------------------------------------------------------------

_RE_NP_PREFIX = re.compile(r'^NP\s{2}\d+\s')


def _strip_np_prefix(line: str) -> tuple[str, int]:
    """
    Rimuove il prefisso 'NP ... numero ...' mantenendo l'allineamento colonne.
    Nei file reali la spaziatura non e` perfettamente costante, quindi usiamo
    la lunghezza effettiva del match invece di offset fissi.
    """
    if not line.startswith("NP "):
        return line, 0
    m = re.match(r'^NP\s+\d+', line)
    if not m:
        return line, 0
    offset = m.end()
    if offset < len(line) and line[offset] == " ":
        offset += 1
    return line[offset:], offset


# ---------------------------------------------------------------------------
# Parser particelle: approccio position-based (colonne a larghezza fissa)
# ---------------------------------------------------------------------------

_COLUMN_KEYWORDS = [
    ("dom", "DOM."),
    ("dis", "DIS."),
    ("fog", "FOG."),
    ("part", "PART."),
    ("sub", "SUB"),
    ("sup_cata", "SUP.CATA."),
    ("sup_irr", "SUP.IRR."),
    ("colt", "COLT."),
    ("manut", "MANUT."),
    ("irrig", "IRRIG."),
    ("ist", "IST."),
]


def _looks_like_particelle_header(line: str) -> bool:
    """
    Riconosce header particelle anche quando il file omette DOM./DIS.
    o presenta piccole varianti di spaziatura.
    """
    header_content, _ = _strip_np_prefix(line)
    header_upper = header_content.upper()

    if "ANNO DOMANDA DISTRETTO" in header_upper:
        return False

    required_tokens = ("FOG.", "PART.", "SUP.CATA.")
    if not all(token in header_upper for token in required_tokens):
        return False

    return "MANUT." in header_upper or "SUP.IRR." in header_upper or "IRRIG." in header_upper


def _build_column_positions(header_content: str) -> list[tuple[str, int, int]]:
    """
    Dati il contenuto dell'header (senza prefisso NP), ritorna lista di
    (nome_colonna, start, end) dove end è la posizione di inizio della colonna successiva.
    """
    positions: list[tuple[str, int]] = []
    header_upper = header_content.upper()
    for key, keyword in _COLUMN_KEYWORDS:
        idx = header_upper.find(keyword.upper())
        if idx >= 0:
            positions.append((key, idx))

    positions.sort(key=lambda x: x[1])

    result: list[tuple[str, int, int]] = []
    for i, (key, start) in enumerate(positions):
        end = positions[i + 1][1] if i + 1 < len(positions) else len(header_content) + 200
        result.append((key, start, end))

    return result


def _extract_at_position(content: str, start: int, end: int) -> str:
    """Estrae e trimma il valore in un intervallo di caratteri."""
    if start >= len(content):
        return ""
    return content[start:min(end, len(content))].strip()


def _parse_particella_positional(
    data_content: str,
    col_positions: list[tuple[str, int, int]],
) -> ParsedParticella | None:
    """
    Parse position-based di una riga particella.
    col_positions: lista di (nome_colonna, start, end) dall'header.
    """
    def safe_decimal(s: str) -> Decimal | None:
        return _parse_italian_decimal(s) if s else None

    vals: dict[str, str] = {}
    for key, start, end in col_positions:
        vals[key] = _extract_at_position(data_content, start, end)

    foglio = vals.get("fog", "")
    particella_val = vals.get("part", "")

    if not foglio and not particella_val:
        return None
    if not foglio.isdigit() or not particella_val.isdigit():
        return None
    if any("=" in (vals.get(key) or "") for key in ("dom", "dis", "fog", "part", "sub", "colt")):
        return None

    sup_cata = safe_decimal(vals.get("sup_cata", ""))
    sup_ha = (sup_cata / Decimal("100")) if sup_cata else None

    return ParsedParticella(
        domanda_irrigua=vals.get("dom") or None,
        distretto=vals.get("dis") or None,
        foglio=foglio,
        particella=particella_val,
        subalterno=vals.get("sub") or None,
        sup_catastale_are=sup_cata,
        sup_catastale_ha=sup_ha,
        sup_irrigata_ha=safe_decimal(vals.get("sup_irr", "")),
        coltura=vals.get("colt") or None,
        importo_manut=safe_decimal(vals.get("manut", "")),
        importo_irrig=safe_decimal(vals.get("irrig", "")),
        importo_ist=safe_decimal(vals.get("ist", "")),
    )


_NON_PARTICELLA_PAYLOAD_PATTERNS = (
    "DOMANDA IRRIGUA",
    "FOGLIO CATASTALE",
    "PARTICELLA CATASTALE",
    "SUPERFICIE CATASTALE",
    "SUPERFICIE IRRIGATA",
    "CODICE DISTRETTO",
    "SUBALTERNO",
    "MANUTENZIONE",
    "IRRIGAZIONE",
    "ISTITUZIONALE",
    "COLTURA",
    "CONSUMI DA CONTATORE",
    "CONTATORE",
    "LEGENDA",
    "FINALE IN AVVISO",
    "ELENCO DELLE PARTITE",
)


def _is_non_particella_np_payload(raw: str) -> bool:
    """Riconosce righe NP descrittive che non devono essere lette come particelle."""
    value = raw.strip().upper()
    if not value:
        return True
    if set(value) <= {"=", "-", " "}:
        return True
    return any(pattern in value for pattern in _NON_PARTICELLA_PAYLOAD_PATTERNS)


# ---------------------------------------------------------------------------
# Step A: split in blocchi per partita CNC
# ---------------------------------------------------------------------------

_RE_CNC_HEADER = re.compile(r'Partita CNC\s+([\d.]+)')
_RE_CNC_BLOCK_HEADER = re.compile(
    r'^(?:<qm500>--|---------)?Partita CNC\s+([\d.]+).*?<inizio>\s*$',
    re.MULTILINE,
)
_RE_FINE = re.compile(r'<-fine->')


def _split_blocks_v2(raw_text: str) -> list[tuple[str, str]]:
    """
    Ritorna una lista di (codice_cnc, blocco_testo) per ogni partita CNC trovata.
    """
    results: list[tuple[str, str]] = []
    matches = list(_RE_CNC_BLOCK_HEADER.finditer(raw_text))

    for idx, match in enumerate(matches):
        codice_cnc = match.group(1)
        block_start = match.end()
        block_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw_text)
        block = raw_text[block_start:block_end]
        fine_match = _RE_FINE.search(block)
        if fine_match:
            block = block[:fine_match.start()]
        results.append((codice_cnc, block))
    return results


# ---------------------------------------------------------------------------
# Step B: parse righe N2 + nominativo + domicilio + residenza
# ---------------------------------------------------------------------------

_RE_DOM = re.compile(r'^Dom:\s*(.*)', re.MULTILINE)
_RE_RES = re.compile(r'^Res:\s*(.*)', re.MULTILINE)


def _parse_header(block: str) -> tuple[str, str | None, str, str | None, str | None]:
    """
    Ritorna: (codice_fiscale_raw, n2_extra_raw, nominativo_raw, domicilio_raw, residenza_raw)
    """
    lines = block.strip().splitlines()

    codice_fiscale_raw = ""
    n2_extra_raw = None
    nominativo_raw = ""
    domicilio_raw = None
    residenza_raw = None

    n2_idx = None
    for i, line in enumerate(lines):
        m = re.match(r'^N2\s+(\S+)\s*(.*)', line)
        if m:
            codice_fiscale_raw = m.group(1).strip()
            n2_extra_raw = m.group(2).strip() or None
            n2_idx = i
            break

    if n2_idx is not None and n2_idx + 1 < len(lines):
        nominativo_raw = lines[n2_idx + 1].strip()

    dom_m = _RE_DOM.search(block)
    if dom_m:
        domicilio_raw = dom_m.group(1).strip() or None

    res_m = _RE_RES.search(block)
    if res_m:
        residenza_raw = res_m.group(1).strip() or None

    return codice_fiscale_raw, n2_extra_raw, nominativo_raw, domicilio_raw, residenza_raw


# ---------------------------------------------------------------------------
# Step C + D: parse partite catastali (blocchi NP) e righe particelle
# ---------------------------------------------------------------------------

_RE_NP_PARTITA = re.compile(
    r'NP\s+\d+\s+PARTITA\s+(\S+)\s+BENI IN COMUNE DI\s+(.+)', re.IGNORECASE
)
_RE_NP_CONTRIBUENTE = re.compile(
    r'NP\s+\d+\s+CONTRIBUENTE:\s+.*?C\.F\.\s+(\S+)', re.IGNORECASE
)
_RE_NP_COINTEST = re.compile(r'NP\s+\d+\s+CO-INTESTATO CON:\s+(.*)', re.IGNORECASE)
_RE_NP_TRIBUTO = re.compile(
    r'NP\s+\d+\s+(\d{4})\s+(0648|0985|0668)\s+.+?\s+([\d.,]+)\s+EURO', re.IGNORECASE
)
_RE_NP_LINE = re.compile(r'^NP\s+(\d+)\s+(.*)')
_RE_NP_STOP_PARTICELLE = re.compile(
    r'NP\s+\d+\s+(?:'
    r'CONSUMI DA CONTATORE:|ANNO DOMANDA DISTRETTO|LEGENDA:|'
    r'DOM\.=DOMANDA IRRIGUA|DIS\.=CODICE DISTRETTO|'
    r'FOG\.=FOGLIO CATASTALE|PART\.=PARTICELLA CATASTALE|'
    r'SUP\.CATA\.=SUPERFICIE CATASTALE|SUP\.IRR\.=SUPERFICIE IRRIGATA|'
    r'MANUT\.\s*=MANUTENZIONE|IRRIG\.=IRRIGAZIONE|IST\.=ISTITUZIONALE|'
    r'FINALE IN AVVISO|ELENCO DELLE PARTITE|=+'
    r')',
    re.IGNORECASE,
)


def _parse_partite_block(block: str) -> list[ParsedPartita]:
    """
    Estrae tutte le partite catastali (blocchi NP) da un blocco di partita CNC.
    Usa parsing position-based per le righe particelle.
    """
    lines = block.strip().splitlines()
    partite: list[ParsedPartita] = []
    current_partita: ParsedPartita | None = None
    in_particelle = False
    col_positions: list[tuple[str, int, int]] = []

    for line in lines:
        # Match PARTITA
        m_partita = _RE_NP_PARTITA.match(line)
        if m_partita:
            if current_partita is not None:
                partite.append(current_partita)
            current_partita = ParsedPartita(
                codice_partita=m_partita.group(1).strip(),
                comune_nome=_normalize_partita_comune_nome(m_partita.group(2)),
                contribuente_cf=None,
                co_intestati_raw=None,
                importo_0648=None,
                importo_0985=None,
                importo_0668=None,
                particelle=[],
            )
            in_particelle = False
            col_positions = []
            continue

        if current_partita is None:
            continue

        # Match CONTRIBUENTE
        m_contrib = _RE_NP_CONTRIBUENTE.match(line)
        if m_contrib:
            current_partita.contribuente_cf = m_contrib.group(1).strip()
            in_particelle = False
            continue

        # Match CO-INTESTATO
        m_coint = _RE_NP_COINTEST.match(line)
        if m_coint:
            current_partita.co_intestati_raw = m_coint.group(1).strip()
            in_particelle = False
            continue

        # Match tributo
        m_trib = _RE_NP_TRIBUTO.match(line)
        if m_trib:
            tributo = m_trib.group(2)
            importo = _parse_italian_decimal(m_trib.group(3))
            if tributo == "0648":
                current_partita.importo_0648 = importo
            elif tributo == "0985":
                current_partita.importo_0985 = importo
            elif tributo == "0668":
                current_partita.importo_0668 = importo
            in_particelle = False
            continue

        # Match header colonne particelle → calcola posizioni
        if _looks_like_particelle_header(line):
            header_content, _ = _strip_np_prefix(line)
            col_positions = _build_column_positions(header_content)
            in_particelle = True
            continue

        if _RE_NP_STOP_PARTICELLE.match(line):
            in_particelle = False
            continue

        # Riga NP generica → riga particella
        m_np = _RE_NP_LINE.match(line)
        if m_np and in_particelle:
            data_content, _ = _strip_np_prefix(line)
            stripped = data_content.strip()
            if _is_non_particella_np_payload(stripped):
                continue
            if col_positions:
                particella = _parse_particella_positional(data_content, col_positions)
            else:
                # Fallback: parsing whitespace
                particella = _parse_particella_line(data_content.split())
            if particella and particella.foglio:
                current_partita.particelle.append(particella)
            continue

    if current_partita is not None:
        partite.append(current_partita)

    return partite


# ---------------------------------------------------------------------------
# Step E: parse righe N4 (totali avviso + codice utenza)
# ---------------------------------------------------------------------------

_RE_N4_VALUES = re.compile(
    r'^\s*(\d{4})\s+(0648|0985|0668)\s+([\d.,]+)\s+([\d.,]+)\s+\(L\.\s*([\d., ]+)\)'
)
_RE_N4_UTENZA = re.compile(r'UTENZA\s+(\d+)')
_RE_N4_EURO_SIMPLE = re.compile(
    r'^\s*(\d{4})\s+(0648|0985|0668)\s+\S+\s+([\d.,]+)'
)


def _parse_n4_blocks(block: str) -> dict:
    """
    Estrae i totali dalle righe N4.
    Ritorna dict con chiavi: importo_0648, importo_0985, importo_0668,
    codice_utenza, n4_campo_sconosciuto, importo_lire.
    """
    result: dict = {
        "importo_0648": None,
        "importo_0985": None,
        "importo_0668": None,
        "codice_utenza": None,
        "n4_campo_sconosciuto": None,
        "importo_lire": None,
    }

    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r'^N4\s*$', line.strip()):
            if i + 1 < len(lines):
                val_line = lines[i + 1]
                m = _RE_N4_VALUES.match(val_line)
                if m:
                    tributo = m.group(2)
                    campo_sconosciuto = m.group(3).strip()
                    importo_euro = _parse_italian_decimal(m.group(4))
                    importo_lire_raw = m.group(5).strip().replace(" ", "")
                    importo_lire = _parse_italian_decimal(importo_lire_raw)
                    if tributo == "0648":
                        result["importo_0648"] = importo_euro
                    elif tributo == "0985":
                        result["importo_0985"] = importo_euro
                    elif tributo == "0668":
                        result["importo_0668"] = importo_euro
                    if result["n4_campo_sconosciuto"] is None:
                        result["n4_campo_sconosciuto"] = campo_sconosciuto
                    if importo_lire:
                        result["importo_lire"] = importo_lire
                else:
                    m2 = _RE_N4_EURO_SIMPLE.match(val_line)
                    if m2:
                        tributo = m2.group(2)
                        importo_euro = _parse_italian_decimal(m2.group(3))
                        if tributo == "0648":
                            result["importo_0648"] = importo_euro
                        elif tributo == "0985":
                            result["importo_0985"] = importo_euro
                        elif tributo == "0668":
                            result["importo_0668"] = importo_euro

            if i + 2 < len(lines):
                utenza_line = lines[i + 2]
                m_utenza = _RE_N4_UTENZA.search(utenza_line)
                if m_utenza and result["codice_utenza"] is None:
                    result["codice_utenza"] = m_utenza.group(1)
        i += 1

    return result


# ---------------------------------------------------------------------------
# Funzione principale
# ---------------------------------------------------------------------------

def parse_ruolo_file(raw_text: str) -> list[ParsedPartitaCNC]:
    """
    Parsa il testo grezzo del file Ruolo e ritorna una lista di ParsedPartitaCNC.
    Fault-tolerant: errori per-partita vengono loggati senza interrompere.
    """
    blocks = _split_blocks_v2(raw_text)
    results: list[ParsedPartitaCNC] = []

    for codice_cnc, block in blocks:
        try:
            cf_raw, n2_extra, nominativo, dom, res = _parse_header(block)
            partite = _parse_partite_block(block)
            n4 = _parse_n4_blocks(block)

            t0648 = n4.get("importo_0648")
            t0985 = n4.get("importo_0985")
            t0668 = n4.get("importo_0668")
            parts = [v for v in [t0648, t0985, t0668] if v is not None]
            totale_euro = sum(parts) if parts else None

            results.append(ParsedPartitaCNC(
                codice_cnc=codice_cnc,
                codice_fiscale_raw=cf_raw,
                n2_extra_raw=n2_extra,
                nominativo_raw=nominativo,
                domicilio_raw=dom,
                residenza_raw=res,
                codice_utenza=n4.get("codice_utenza"),
                importo_totale_0648=t0648,
                importo_totale_0985=t0985,
                importo_totale_0668=t0668,
                importo_totale_euro=totale_euro,
                importo_totale_lire=n4.get("importo_lire"),
                n4_campo_sconosciuto=n4.get("n4_campo_sconosciuto"),
                partite=partite,
            ))
        except Exception as exc:
            logger.warning("Errore parsing partita CNC %s: %s", codice_cnc, exc)

    return results


def extract_text_from_content(raw_content: bytes, filename: str = "") -> str:
    """
    Estrae testo da bytes: tenta PDF con pypdf, fallback testo grezzo.
    """
    if filename.lower().endswith(".pdf") or raw_content[:4] == b"%PDF":
        try:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw_content))
            pages_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            result = "\n".join(pages_text)
            if result.strip():
                return result
        except Exception as exc:
            logger.warning("pypdf estrazione fallita: %s — fallback testo grezzo", exc)

    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return raw_content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_content.decode("latin-1", errors="replace")


def detect_anno_tributario(raw_content: bytes, filename: str = "") -> int | None:
    """
    Rileva l'anno tributario dal contenuto del file o dal nome file.
    Considera solo anni 2000-2100 per evitare falsi positivi da date anagrafiche.
    """
    def _valid(year: int) -> bool:
        return 2000 <= year <= 2100

    filename_match = re.search(r"\bR(20\d{2})[.\-_]", filename, flags=re.IGNORECASE)
    if filename_match:
        year = int(filename_match.group(1))
        if _valid(year):
            return year

    generic_filename_years = [
        int(match.group(1))
        for match in re.finditer(r"(20\d{2})", filename)
        if _valid(int(match.group(1)))
    ]
    if generic_filename_years:
        return Counter(generic_filename_years).most_common(1)[0][0]

    text = extract_text_from_content(raw_content, filename=filename)

    cnc_years = [
        int(match.group(1))
        for match in re.finditer(r"Partita\s+CNC\s+\d{2}\.0(20\d{2})\d+", text, flags=re.IGNORECASE)
        if _valid(int(match.group(1)))
    ]
    if cnc_years:
        return Counter(cnc_years).most_common(1)[0][0]

    structured_years: list[int] = []

    for match in re.finditer(r"\b(20\d{2})\s+(?:0648|0985|0668)\b", text):
        year = int(match.group(1))
        if _valid(year):
            structured_years.append(year)

    for match in re.finditer(r"ANNO\s+TRIB(?:UTARIO)?\D{0,40}(20\d{2})", text, flags=re.IGNORECASE):
        year = int(match.group(1))
        if _valid(year):
            structured_years.append(year)

    if structured_years:
        return Counter(structured_years).most_common(1)[0][0]

    generic_text_years = [
        int(match.group(1))
        for match in re.finditer(r"\b(20\d{2})\b", text)
        if _valid(int(match.group(1)))
    ]
    if generic_text_years:
        return Counter(generic_text_years).most_common(1)[0][0]

    return None
