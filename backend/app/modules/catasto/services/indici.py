from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class CatIndiceMetadata:
    key: str
    label: str
    sort_order: int
    hectares_reference: Decimal | None = None


INDICE_UNKNOWN_KEY = "non_classificato"

INDICE_GROUPS: dict[str, tuple[str, int]] = {
    "alta_pressione": ("Alta pressione", 10),
    "bassa_pressione": ("Bassa pressione", 20),
    "canaletta": ("Canaletta", 30),
    INDICE_UNKNOWN_KEY: ("Non classificato", 99),
}

DISTRETTO_INDEX_CATALOG: dict[str, CatIndiceMetadata] = {
    "01": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("1800")),
    "02": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("2400")),
    "03": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("600")),
    "04": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("970")),
    "05": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("790")),
    "06": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("220")),
    "07": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("600")),
    "08": CatIndiceMetadata("canaletta", "Canaletta", 30, Decimal("1200")),
    "09": CatIndiceMetadata("bassa_pressione", "Bassa pressione", 20, Decimal("110")),
    "10": CatIndiceMetadata("bassa_pressione", "Bassa pressione", 20, Decimal("470")),
    "11": CatIndiceMetadata("canaletta", "Canaletta", 30, Decimal("1100")),
    "12": CatIndiceMetadata("bassa_pressione", "Bassa pressione", 20, Decimal("200")),
    "13": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("2200")),
    "14": CatIndiceMetadata("bassa_pressione", "Bassa pressione", 20, Decimal("230")),
    "15": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("2300")),
    "16": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("35")),
    "17": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("570")),
    "18": CatIndiceMetadata("canaletta", "Canaletta", 30, Decimal("650")),
    "19": CatIndiceMetadata("bassa_pressione", "Bassa pressione", 20, Decimal("1035")),
    "20": CatIndiceMetadata("bassa_pressione", "Bassa pressione", 20, Decimal("1100")),
    "21": CatIndiceMetadata("bassa_pressione", "Bassa pressione", 20, Decimal("1750")),
    "22": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("970")),
    "23": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("400")),
    "24": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("2960")),
    "25": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("1976")),
    "26": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("1875")),
    "27": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("148")),
    "28": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("1026")),
    "29a": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("382")),
    "29b": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("440")),
    "29c": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("840")),
    "30": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("447")),
    "31": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("1775")),
    "32": CatIndiceMetadata("bassa_pressione", "Bassa pressione", 20, Decimal("190")),
    "33": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("400")),
    "34": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("1705")),
    "35": CatIndiceMetadata("alta_pressione", "Alta pressione", 10, Decimal("1000")),
}


# Nei dati sorgente lo stesso distretto compare con codifiche diverse: senza zero
# iniziale ("8" per "08") e con suffissi numerici al posto delle lettere ("291" per "29a").
_DISTRETTO_CODE_ALIASES: dict[str, str] = {
    "291": "29a",
    "292": "29b",
    "293": "29c",
}


def normalize_num_distretto(num_distretto: str | None) -> str | None:
    if not num_distretto:
        return None
    normalized = num_distretto.strip().lower()
    if not normalized:
        return None
    normalized = _DISTRETTO_CODE_ALIASES.get(normalized, normalized)
    if len(normalized) == 1 and normalized.isdigit():
        normalized = normalized.zfill(2)
    return normalized


def get_indice_metadata(num_distretto: str | None) -> CatIndiceMetadata:
    normalized = normalize_num_distretto(num_distretto)
    if normalized and normalized in DISTRETTO_INDEX_CATALOG:
        return DISTRETTO_INDEX_CATALOG[normalized]
    label, sort_order = INDICE_GROUPS[INDICE_UNKNOWN_KEY]
    return CatIndiceMetadata(INDICE_UNKNOWN_KEY, label, sort_order)


def expand_distretto_code_variants(code: str) -> list[str]:
    normalized = normalize_num_distretto(code)
    if not normalized:
        return [code]
    variants = {code, normalized, normalized.upper()}
    if len(normalized) == 2 and normalized.startswith("0"):
        variants.add(normalized[1:])
    for alias, canonical in _DISTRETTO_CODE_ALIASES.items():
        if canonical == normalized:
            variants.add(alias)
    return sorted(variants)


def list_distretti_for_indice(indice_key: str) -> list[str]:
    normalized = indice_key.strip()
    codes = sorted(
        [code for code, metadata in DISTRETTO_INDEX_CATALOG.items() if metadata.key == normalized],
        key=lambda value: (DISTRETTO_INDEX_CATALOG[value].sort_order, value),
    )
    expanded: list[str] = []
    for code in codes:
        for variant in expand_distretto_code_variants(code):
            if variant not in expanded:
                expanded.append(variant)
    return expanded
