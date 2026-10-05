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


_PARTICELLA_LAYOUTS = {
    4: {"foglio": 0, "particella": 1, "sup_catastale_are": 2, "importo_manut": 3},
    5: {
        "foglio": 0, "particella": 1, "sup_catastale_are": 2,
        "sup_irrigata_ha": 3, "importo_manut": 4,
    },
    6: {
        "distretto": 0, "foglio": 1, "particella": 2,
        "sup_catastale_are": 3, "sup_irrigata_ha": 4, "importo_manut": 5,
    },
    7: {
        "distretto": 0, "foglio": 1, "particella": 2,
        "sup_catastale_are": 3, "sup_irrigata_ha": 4,
        "importo_manut": 5, "importo_ist": 6,
    },
    8: {
        "distretto": 0, "foglio": 1, "particella": 2,
        "sup_catastale_are": 3, "sup_irrigata_ha": 4,
        "importo_manut": 5, "importo_irrig": 6, "importo_ist": 7,
    },
    9: {
        "distretto": 0, "foglio": 1, "particella": 2,
        "sup_catastale_are": 3, "sup_irrigata_ha": 4,
        "importo_manut": 6, "importo_irrig": 7, "importo_ist": 8,
    },
    10: {
        "domanda_irrigua": 0, "distretto": 1, "foglio": 2, "particella": 3,
        "sup_catastale_are": 4, "sup_irrigata_ha": 5,
        "importo_manut": 6, "importo_irrig": 7, "importo_ist": 8,
    },
    11: {
        "domanda_irrigua": 0, "distretto": 1, "foglio": 2, "particella": 3,
        "subalterno": 4, "sup_catastale_are": 5, "sup_irrigata_ha": 6,
        "importo_manut": 7, "importo_irrig": 8, "importo_ist": 9,
    },
}

_PARTICELLA_TEXT_LAYOUTS = {
    7: {
        "distretto": 0, "foglio": 1, "particella": 2, "subalterno": 3,
        "sup_catastale_are": 4, "sup_irrigata_ha": 5, "importo_manut": 6,
    },
    9: {
        **_PARTICELLA_LAYOUTS[9],
        "subalterno": 3, "sup_catastale_are": 4, "sup_irrigata_ha": 5,
    },
    10: {
        **_PARTICELLA_LAYOUTS[10],
        "coltura": 6, "importo_manut": 7, "importo_irrig": 8, "importo_ist": 9,
    },
    11: {
        **_PARTICELLA_LAYOUTS[11],
        "coltura": 7, "importo_manut": 8, "importo_irrig": 9, "importo_ist": 10,
    },
}

_PARTICELLA_VARIANT_COLUMNS = {7: 3, 9: 3, 10: 6, 11: 7}


def _particella_columns(values: list[str]) -> dict[str, str]:
    column_count = min(len(values), 11)
    variant_column = _PARTICELLA_VARIANT_COLUMNS.get(column_count)
    layout = _PARTICELLA_LAYOUTS[column_count]
    if variant_column is not None and not looks_like_number(values[variant_column]):
        layout = _PARTICELLA_TEXT_LAYOUTS[column_count]
    return {field: values[index] for field, index in layout.items()}


def parse_particella_line(values: list[str]) -> ParsedParticella | None:
    if not values or len(values) < 4:
        return None
    if any("=" in value for value in values):
        return None

    fields = _particella_columns(values)
    if not fields["foglio"].isdigit() or not fields["particella"].isdigit():
        return None

    sup_cata = parse_italian_decimal(fields["sup_catastale_are"])
    sup_ha = (sup_cata / Decimal("100")) if sup_cata else None

    return ParsedParticella(
        domanda_irrigua=fields.get("domanda_irrigua"),
        distretto=fields.get("distretto"),
        foglio=fields["foglio"],
        particella=fields["particella"],
        subalterno=fields.get("subalterno"),
        sup_catastale_are=sup_cata,
        sup_catastale_ha=sup_ha,
        sup_irrigata_ha=parse_italian_decimal(fields.get("sup_irrigata_ha", "")),
        coltura=fields.get("coltura"),
        importo_manut=parse_italian_decimal(fields["importo_manut"]),
        importo_irrig=parse_italian_decimal(fields.get("importo_irrig", "")),
        importo_ist=parse_italian_decimal(fields.get("importo_ist", "")),
    )
