from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


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


_COMUNE_ALIASES = {
    "SILI'*ORISTANO": "SILI",
    "OLLASTRA SIMAXIS": "OLLASTRA",
    "SAN NICOLO ARCIDANO": "SAN NICOLO D'ARCIDANO",
}

ORISTANO_FRAZIONE_SECTION_HINTS = {
    "DONIGALA": "B",
    "DONIGALA FENUGHEDU": "B",
    "MASSAMA": "C",
    "NURAXINIEDDU": "D",
    "SILI": "E",
}


def parse_italian_decimal(raw: str) -> Decimal | None:
    if not raw:
        return None
    cleaned = raw.strip().replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def looks_like_number(value: str) -> bool:
    cleaned = value.replace(".", "").replace(",", ".")
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def normalize_partita_comune_nome(raw: str) -> str:
    value = re.sub(r"\s+", " ", raw.strip())
    value = re.sub(r"\s*\([^)]*\)\s*$", "", value).strip()
    return _COMUNE_ALIASES.get(value.upper(), value)


def resolve_section_hint_for_ruolo_comune(comune_nome: str | None) -> str | None:
    if not comune_nome:
        return None
    comune_norm = normalize_partita_comune_nome(comune_nome).strip().upper()
    return ORISTANO_FRAZIONE_SECTION_HINTS.get(comune_norm)


def parse_particella_line(values: list[str]) -> ParsedParticella | None:
    if not values or len(values) < 4:
        return None
    if any("=" in value for value in values):
        return None

    def safe_decimal(raw: str) -> Decimal | None:
        return parse_italian_decimal(raw) if raw else None

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
        dom, dis, fog, part, sub = values[0], values[1], values[2], values[3], values[4]
        sup_cata_s, sup_irr_s = values[5], values[6]
        if not looks_like_number(values[7]):
            colt = values[7]
            manut_s, irrig_s, ist_s = values[8], values[9], values[10]
        else:
            manut_s, irrig_s, ist_s = values[7], values[8], values[9]
    elif n == 10:
        dom, dis, fog, part = values[0], values[1], values[2], values[3]
        sup_cata_s, sup_irr_s = values[4], values[5]
        if not looks_like_number(values[6]):
            colt = values[6]
            manut_s, irrig_s, ist_s = values[7], values[8], values[9]
        else:
            manut_s, irrig_s, ist_s = values[6], values[7], values[8]
    elif n == 9:
        dis, fog, part = values[0], values[1], values[2]
        if not looks_like_number(values[3]):
            sub = values[3]
            sup_cata_s, sup_irr_s = values[4], values[5]
            manut_s, irrig_s, ist_s = values[6], values[7], values[8]
        else:
            sup_cata_s, sup_irr_s = values[3], values[4]
            manut_s, irrig_s, ist_s = values[6], values[7], values[8]
    elif n == 8:
        dis, fog, part = values[0], values[1], values[2]
        sup_cata_s, sup_irr_s = values[3], values[4]
        manut_s, irrig_s, ist_s = values[5], values[6], values[7]
    elif n == 7:
        dis, fog, part = values[0], values[1], values[2]
        if not looks_like_number(values[3]):
            sub = values[3]
            sup_cata_s, sup_irr_s = values[4], values[5]
            manut_s = values[6]
        else:
            sup_cata_s, sup_irr_s = values[3], values[4]
            manut_s = values[5]
            ist_s = values[6]
    elif n == 6:
        dis, fog, part = values[0], values[1], values[2]
        sup_cata_s, sup_irr_s = values[3], values[4]
        manut_s = values[5]
    elif n == 5:
        fog, part = values[0], values[1]
        sup_cata_s, sup_irr_s = values[2], values[3]
        manut_s = values[4]
    elif n == 4:
        fog, part = values[0], values[1]
        sup_cata_s = values[2]
        manut_s = values[3]
    else:  # pragma: no cover - guarded by length checks above.
        return None

    if not fog.isdigit() or not part.isdigit():
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
