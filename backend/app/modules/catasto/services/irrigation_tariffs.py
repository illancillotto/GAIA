from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFD", value)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.upper()
    normalized = re.sub(r"[^A-Z0-9]+", " ", normalized)
    return " ".join(normalized.split())


@dataclass(frozen=True)
class IrrigationCropRule:
    label: str
    keywords: tuple[str, ...]
    euro_ha_base_ib_1_00: Decimal


@dataclass(frozen=True)
class IrrigationTariffPreview:
    crop_label: str | None
    crop_group_label: str | None
    indice_territoriale: Decimal | None
    euro_ha_base: Decimal | None
    euro_ha_finale: Decimal | None
    euro_mc_finale: Decimal | None
    sup_irrigata_ha: Decimal | None
    importo_stimato: Decimal | None


IRRIGATION_CROP_RULES: tuple[IrrigationCropRule, ...] = (
    IrrigationCropRule(
        label="Agrumeti, Bosco, Cavolfiore-Cereali, Finocchio, Lattuga, Loietto, Melone, Ulivo, Vigneti",
        keywords=("AGRUM", "BOSCO", "CAVOLF", "CEREAL", "FINOCCH", "LATTUG", "LOIETT", "MELON", "ULIV", "OLIV", "VIGNET", "VITE"),
        euro_ha_base_ib_1_00=Decimal("30.00"),
    ),
    IrrigationCropRule(
        label="Angurie, Carciofi, Carote, Fragole, Frutteti, Patate, Peperoni, Soia, Vivai",
        keywords=("ANGURI", "CARCIOF", "CAROT", "FRAGOL", "FRUTT", "PATAT", "PEPERON", "SOIA", "VIVA"),
        euro_ha_base_ib_1_00=Decimal("50.00"),
    ),
    IrrigationCropRule(
        label="Bietole, Melanzane, Ortive, Pomodori",
        keywords=("BIETOL", "MELANZ", "ORTIV", "POMODOR"),
        euro_ha_base_ib_1_00=Decimal("65.00"),
    ),
    IrrigationCropRule(
        label="Erbai, Medica, Mais, Sorgo",
        keywords=("ERBAI", "MEDICA", "MAIS", "SORGO"),
        euro_ha_base_ib_1_00=Decimal("80.00"),
    ),
    IrrigationCropRule(
        label="Ladino, Prato, Pascolo",
        keywords=("LADINO", "PRATO", "PASCOLO"),
        euro_ha_base_ib_1_00=Decimal("100.00"),
    ),
    IrrigationCropRule(
        label="Risaie",
        keywords=("RISAI", "RISO"),
        euro_ha_base_ib_1_00=Decimal("120.00"),
    ),
    IrrigationCropRule(
        label="Soccorso",
        keywords=("SOCCORSO",),
        euro_ha_base_ib_1_00=Decimal("25.00"),
    ),
)

TERRITORIAL_INDEX_RULES: tuple[tuple[tuple[str, ...], Decimal], ...] = (
    (("BRABAU", "RIORDINO ZEDDIANI", "PAULI BINGIAS", "CABRAS PALUDI", "PESARIA SUD"), Decimal("0.44")),
    (("SANTA LUCIA", "DONIGALA", "SARTUCCINO PERDA LADA", "FENOSU", "SAN NICOLO", "SANT ELENA PAULI LONGA", "SERRA ARENA NORD"), Decimal("0.72")),
    (
        (
            "BARATILI",
            "SINIS NORD EST",
            "SANTA MARIA MERE FOGHE",
            "MILIS",
            "SAN VERO MILIS",
            "TRAMATZA",
            "BAULADU",
            "BENNAXI",
            "GOLENA ZERFALIU",
            "PESARIA NORD",
            "SERRA ARENA SUD",
            "CIMAS NORD",
            "ZINNIGAS",
            "SASSU",
            "3 DISTRETTO ARBOREA",
            "1 DISTRETTO TERRALBA",
            "2 DISTRETTO TERRALBA",
            "3 DISTRETTO TERRALBA",
            "SAN GIOVANNI",
            "CIMAS SUD",
            "SANT ANNA",
        ),
        Decimal("1.00"),
    ),
    (("LOTTO NORD ARBOREA", "LOTTO SUD ARBOREA"), Decimal("1.24")),
)

TERRITORIAL_EURO_MC: dict[Decimal, Decimal] = {
    Decimal("0.44"): Decimal("0.0066"),
    Decimal("0.72"): Decimal("0.0108"),
    Decimal("1.00"): Decimal("0.0150"),
    Decimal("1.24"): Decimal("0.0186"),
}


def resolve_crop_rule(coltura: str | None) -> IrrigationCropRule | None:
    normalized = _normalize(coltura)
    if not normalized:
        return None
    for rule in IRRIGATION_CROP_RULES:
        if any(keyword in normalized for keyword in rule.keywords):
            return rule
    return None


def resolve_territorial_index(
    *,
    nome_distretto: str | None,
    num_distretto: str | None,
    nome_comune: str | None,
) -> Decimal | None:
    normalized_distretto = _normalize(nome_distretto)
    normalized_comune = _normalize(nome_comune)
    normalized_num = (num_distretto or "").strip().lower()

    for aliases, value in TERRITORIAL_INDEX_RULES:
        for alias in aliases:
            if _normalize(alias) in normalized_distretto:
                return value

    if normalized_num in {"291", "292", "293", "29a", "29b", "29c"}:
        return Decimal("1.00")
    if normalized_num == "24":
        return Decimal("1.24")
    if normalized_num == "25":
        return Decimal("1.24")
    if normalized_comune == "ARBOREA":
        return Decimal("1.24")
    return None


def build_irrigation_tariff_preview(
    *,
    coltura: str | None,
    sup_irrigata_ha: Decimal | None,
    nome_distretto: str | None,
    num_distretto: str | None,
    nome_comune: str | None,
) -> IrrigationTariffPreview:
    crop_rule = resolve_crop_rule(coltura)
    indice = resolve_territorial_index(nome_distretto=nome_distretto, num_distretto=num_distretto, nome_comune=nome_comune)
    euro_ha_base = crop_rule.euro_ha_base_ib_1_00 if crop_rule else None
    euro_ha_finale = (euro_ha_base * indice) if euro_ha_base is not None and indice is not None else None
    euro_mc_finale = TERRITORIAL_EURO_MC.get(indice) if indice is not None else None
    importo_stimato = (euro_ha_finale * sup_irrigata_ha) if euro_ha_finale is not None and sup_irrigata_ha is not None else None
    return IrrigationTariffPreview(
        crop_label=coltura,
        crop_group_label=crop_rule.label if crop_rule else None,
        indice_territoriale=indice,
        euro_ha_base=euro_ha_base,
        euro_ha_finale=euro_ha_finale,
        euro_mc_finale=euro_mc_finale,
        sup_irrigata_ha=sup_irrigata_ha,
        importo_stimato=importo_stimato,
    )
