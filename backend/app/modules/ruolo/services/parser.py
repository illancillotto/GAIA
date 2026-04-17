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
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dataclasses di output del parser
# ---------------------------------------------------------------------------

@dataclass
class ParsedParticella:
    domanda_irrigua: str | None
    distretto: str | None
    foglio: str
    particella: str
    subalterno: str | None
    sup_catastale_are: Decimal | None
    sup_catastale_ha: Decimal | None
    sup_irrigata_ha: Decimal | None
    coltura: str | None
    importo_manut: Decimal | None
    importo_irrig: Decimal | None
    importo_ist: Decimal | None


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
# Utility di conversione numeri in formato italiano
# ---------------------------------------------------------------------------

def _parse_italian_decimal(raw: str) -> Decimal | None:
    """
    Converte un numero in formato italiano (punto = migliaia, virgola = decimale).
    Es: '1.455' → Decimal('1455'), '6,05' → Decimal('6.05'), '1.679.520' → Decimal('1679520')
    """
    if not raw:
        return None
    cleaned = raw.strip()
    # Rimuovi punti separatore migliaia, poi sostituisci virgola con punto
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _looks_like_number(s: str) -> bool:
    """Ritorna True se la stringa sembra un numero (decimale italiano o intero)."""
    cleaned = s.replace(".", "").replace(",", ".")
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Prefisso NP
# ---------------------------------------------------------------------------

_RE_NP_PREFIX = re.compile(r'^NP\s{2}\d+\s')


def _strip_np_prefix(line: str) -> tuple[str, int]:
    """
    Rimuove il prefisso 'NP  N  ' o 'NP  NN ' dalla riga mantenendo l'allineamento colonne.
    Il prefisso ha larghezza fissa di 7 caratteri: 'NP  ' (4) + numero (1-2 cifre) + spazi.
    Per 1 cifra: 'NP  4  ' = 7 chars. Per 2 cifre: 'NP  10 ' = 7 chars.
    """
    if not line.startswith("NP "):
        return line, 0
    # Individua la fine del numero di riga
    m = re.match(r'^NP\s{2}(\d+)', line)
    if not m:
        return line, 0
    # Offset fisso = 4 ("NP  ") + lunghezza numero + spazi a riempire fino a 7
    num_len = len(m.group(1))
    # Total prefix width: 4 (NP + 2 spaces) + number field (3 chars, right-aligned with trailing spaces)
    # = sempre 7 per numeri 1-99
    offset = 4 + max(num_len, 2) + 1  # "NP  " + 2-char number field + 1 space = 7
    if num_len == 1:
        offset = 7  # NP(2) + 2spaces(2) + 1digit(1) + 2spaces(2) = 7
    elif num_len == 2:
        offset = 7  # NP(2) + 2spaces(2) + 2digits(2) + 1space(1) = 7
    else:
        offset = 4 + num_len + 1  # per numeri >99
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


def _parse_particella_line(values: list[str]) -> ParsedParticella | None:
    """
    Parse whitespace-split di una riga particella (usato nei test unitari).

    Struttura osservata nel formato reale (token presenti, DOM/DIS/SUB/COLT possono mancare):
    - Con 6 token (caso più comune senza DOM, DIS, IRRIG, IST vuoti):
      [DIS, FOG, PART, SUP_CATA, SUP_IRR, MANUT]
    - Con 7 token:
      [DIS, FOG, PART, SUP_CATA, SUP_IRR, MANUT, IST]
      oppure [DOM, DIS, FOG, PART, SUP_CATA, SUP_IRR, MANUT]
    - Caso con SUB letterale (7 token):
      [DIS, FOG, PART, SUB, SUP_CATA, SUP_IRR, MANUT]

    Il mapping corretto con 6 token è: [DIS, FOG, PART, SUP_CATA, SUP_IRR, MANUT]
    con DOM=None, SUB=None, IRRIG=None, IST=None.
    """
    if not values or len(values) < 4:
        return None

    def safe_decimal(s: str) -> Decimal | None:
        return _parse_italian_decimal(s) if s else None

    n = len(values)

    dom: str | None = None
    dis: str | None = None
    fog = ""
    part = ""
    sub: str | None = None
    sup_cata_s = ""
    sup_irr_s = ""
    colt: str | None = None
    manut_s = ""
    irrig_s = ""
    ist_s = ""

    if n >= 11:
        # dom dis fog part sub sup_cata sup_irr colt manut irrig ist
        dom, dis, fog, part, sub = values[0], values[1], values[2], values[3], values[4]
        sup_cata_s, sup_irr_s = values[5], values[6]
        if not _looks_like_number(values[7]):
            colt = values[7]
            manut_s, irrig_s, ist_s = values[8], values[9], values[10]
        else:
            manut_s, irrig_s, ist_s = values[7], values[8], values[9]
    elif n == 10:
        dom, dis, fog, part = values[0], values[1], values[2], values[3]
        sup_cata_s, sup_irr_s = values[4], values[5]
        if not _looks_like_number(values[6]):
            colt = values[6]
            manut_s, irrig_s, ist_s = values[7], values[8], values[9]
        else:
            manut_s, irrig_s, ist_s = values[6], values[7], values[8]
    elif n == 9:
        # con sub: [dis, fog, part, sub, sup_cata, sup_irr, manut, irrig, ist]
        # oppure: [dom, dis, fog, part, sup_cata, sup_irr, manut, irrig, ist]
        dis, fog, part = values[0], values[1], values[2]
        if not _looks_like_number(values[3]):
            # values[3] è SUB letterale
            sub = values[3]
            sup_cata_s, sup_irr_s = values[4], values[5]
            manut_s, irrig_s, ist_s = values[6], values[7], values[8]
        else:
            sup_cata_s, sup_irr_s = values[3], values[4]
            manut_s, irrig_s, ist_s = values[6], values[7], values[8]
    elif n == 8:
        # [dis, fog, part, sup_cata, sup_irr, manut, irrig, ist]
        dis, fog, part = values[0], values[1], values[2]
        sup_cata_s, sup_irr_s = values[3], values[4]
        manut_s, irrig_s, ist_s = values[5], values[6], values[7]
    elif n == 7:
        # Casi:
        # [dis, fog, part, sub_letterale, sup_cata, sup_irr, manut]
        # [dis, fog, part, sup_cata, sup_irr, manut, ist]
        dis, fog, part = values[0], values[1], values[2]
        if not _looks_like_number(values[3]):
            sub = values[3]
            sup_cata_s, sup_irr_s = values[4], values[5]
            manut_s = values[6]
        else:
            sup_cata_s, sup_irr_s = values[3], values[4]
            manut_s = values[5]
            ist_s = values[6]
    elif n == 6:
        # Caso più comune: [DIS, FOG, PART, SUP_CATA, SUP_IRR, MANUT]
        dis, fog, part = values[0], values[1], values[2]
        sup_cata_s, sup_irr_s = values[3], values[4]
        manut_s = values[5]
    elif n == 5:
        # [FOG, PART, SUP_CATA, SUP_IRR, MANUT]
        fog, part = values[0], values[1]
        sup_cata_s, sup_irr_s = values[2], values[3]
        manut_s = values[4]
    elif n == 4:
        # [FOG, PART, SUP_CATA, MANUT]
        fog, part = values[0], values[1]
        sup_cata_s = values[2]
        manut_s = values[3]
    else:
        return None

    sup_cata = safe_decimal(sup_cata_s)
    sup_ha = (sup_cata / Decimal("100")) if sup_cata else None

    return ParsedParticella(
        domanda_irrigua=dom,
        distretto=dis,
        foglio=fog,
        particella=part,
        subalterno=sub,
        sup_catastale_are=sup_cata,
        sup_catastale_ha=sup_ha,
        sup_irrigata_ha=safe_decimal(sup_irr_s),
        coltura=colt,
        importo_manut=safe_decimal(manut_s),
        importo_irrig=safe_decimal(irrig_s) if irrig_s else None,
        importo_ist=safe_decimal(ist_s) if ist_s else None,
    )


# ---------------------------------------------------------------------------
# Step A: split in blocchi per partita CNC
# ---------------------------------------------------------------------------

_RE_CNC_HEADER = re.compile(r'Partita CNC\s+([\d.]+)')
_RE_INIZIO = re.compile(r'<inizio>')
_RE_FINE = re.compile(r'<-fine->')


def _split_blocks_v2(raw_text: str) -> list[tuple[str, str]]:
    """
    Ritorna una lista di (codice_cnc, blocco_testo) per ogni partita CNC trovata.
    """
    results: list[tuple[str, str]] = []
    inizio_positions = [m.start() for m in _RE_INIZIO.finditer(raw_text)]

    for pos in inizio_positions:
        preceding = raw_text[max(0, pos - 300):pos]
        cnc_match = None
        for m in _RE_CNC_HEADER.finditer(preceding):
            cnc_match = m
        codice_cnc = cnc_match.group(1) if cnc_match else "UNKNOWN"

        after = raw_text[pos + len("<inizio>"):]
        fine_match = _RE_FINE.search(after)
        block = after[:fine_match.start()] if fine_match else after

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
_RE_NP_HEADER_PART = re.compile(
    r'NP\s+\d+\s+DOM\.\s+DIS\.\s+FOG\.\s+PART\.',
    re.IGNORECASE,
)
_RE_NP_LINE = re.compile(r'^NP\s+(\d+)\s+(.*)')


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
                comune_nome=m_partita.group(2).strip(),
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
        if _RE_NP_HEADER_PART.match(line):
            header_content, _ = _strip_np_prefix(line)
            col_positions = _build_column_positions(header_content)
            in_particelle = True
            continue

        # Riga NP generica → riga particella
        m_np = _RE_NP_LINE.match(line)
        if m_np and in_particelle:
            data_content, _ = _strip_np_prefix(line)
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
