from __future__ import annotations

from dataclasses import dataclass

from app.modules.presenze.models import (
    PRESENZE_CONTRACT_KIND_ALTRO,
    PRESENZE_CONTRACT_KIND_IMPIEGATO,
    PRESENZE_CONTRACT_KIND_OPERAIO,
    PRESENZE_OPERAI_GROUP_AGRARIO,
    PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO,
    PRESENZE_CONTRACT_KIND_QUADRO,
)

VALID_PRESENZE_CONTRACT_KINDS = {
    PRESENZE_CONTRACT_KIND_OPERAIO,
    PRESENZE_CONTRACT_KIND_IMPIEGATO,
    PRESENZE_CONTRACT_KIND_QUADRO,
    PRESENZE_CONTRACT_KIND_ALTRO,
}
VALID_PRESENZE_OPERAI_GROUPS = {
    PRESENZE_OPERAI_GROUP_AGRARIO,
    PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO,
}


@dataclass(frozen=True)
class PresenzeContractProfile:
    contract_kind: str | None
    standard_daily_minutes: int | None



def normalize_contract_kind(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized not in VALID_PRESENZE_CONTRACT_KINDS:
        return None
    return normalized


def normalize_operai_group(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized not in VALID_PRESENZE_OPERAI_GROUPS:
        return None
    return normalized


def infer_contract_profile_from_template_code(template_code: str | None) -> PresenzeContractProfile:
    if template_code is None:
        return PresenzeContractProfile(contract_kind=None, standard_daily_minutes=None)
    normalized = template_code.strip().upper()
    if not normalized:
        return PresenzeContractProfile(contract_kind=None, standard_daily_minutes=None)
    if normalized.startswith("OPE0736"):
        return PresenzeContractProfile(contract_kind=PRESENZE_CONTRACT_KIND_OPERAIO, standard_daily_minutes=456)
    if (
        normalized.startswith("OPE")
        or normalized.startswith("OP_")
        or normalized.startswith("OSAB")
        or "OPESAB" in normalized
    ):
        return PresenzeContractProfile(contract_kind=PRESENZE_CONTRACT_KIND_OPERAIO, standard_daily_minutes=420)
    if normalized.startswith("IMP") or "RIENTRO IMP" in normalized:
        return PresenzeContractProfile(contract_kind=PRESENZE_CONTRACT_KIND_IMPIEGATO, standard_daily_minutes=385)
    return PresenzeContractProfile(contract_kind=None, standard_daily_minutes=None)


def resolve_contract_profile(
    contract_kind: str | None,
    standard_daily_minutes: int | None,
    *,
    template_code: str | None = None,
) -> PresenzeContractProfile:
    normalized_contract_kind = normalize_contract_kind(contract_kind)
    if normalized_contract_kind is not None or standard_daily_minutes is not None:
        return PresenzeContractProfile(
            contract_kind=normalized_contract_kind,
            standard_daily_minutes=standard_daily_minutes,
        )
    return infer_contract_profile_from_template_code(template_code)
