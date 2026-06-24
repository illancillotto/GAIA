from __future__ import annotations

from dataclasses import dataclass

from app.modules.inaz.models import (
    INAZ_CONTRACT_KIND_ALTRO,
    INAZ_CONTRACT_KIND_IMPIEGATO,
    INAZ_CONTRACT_KIND_OPERAIO,
    INAZ_CONTRACT_KIND_QUADRO,
)

VALID_INAZ_CONTRACT_KINDS = {
    INAZ_CONTRACT_KIND_OPERAIO,
    INAZ_CONTRACT_KIND_IMPIEGATO,
    INAZ_CONTRACT_KIND_QUADRO,
    INAZ_CONTRACT_KIND_ALTRO,
}


@dataclass(frozen=True)
class InazContractProfile:
    contract_kind: str | None
    standard_daily_minutes: int | None


def normalize_contract_kind(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized not in VALID_INAZ_CONTRACT_KINDS:
        return None
    return normalized


def infer_contract_profile_from_template_code(template_code: str | None) -> InazContractProfile:
    if template_code is None:
        return InazContractProfile(contract_kind=None, standard_daily_minutes=None)
    normalized = template_code.strip().upper()
    if not normalized:
        return InazContractProfile(contract_kind=None, standard_daily_minutes=None)
    if normalized.startswith("OPE0736"):
        return InazContractProfile(contract_kind=INAZ_CONTRACT_KIND_OPERAIO, standard_daily_minutes=456)
    if normalized.startswith("OPE") or "OPESAB" in normalized:
        return InazContractProfile(contract_kind=INAZ_CONTRACT_KIND_OPERAIO, standard_daily_minutes=420)
    if normalized.startswith("IMP") or "RIENTRO IMP" in normalized:
        return InazContractProfile(contract_kind=INAZ_CONTRACT_KIND_IMPIEGATO, standard_daily_minutes=385)
    return InazContractProfile(contract_kind=None, standard_daily_minutes=None)


def resolve_contract_profile(
    contract_kind: str | None,
    standard_daily_minutes: int | None,
    *,
    template_code: str | None = None,
) -> InazContractProfile:
    normalized_contract_kind = normalize_contract_kind(contract_kind)
    if normalized_contract_kind is not None or standard_daily_minutes is not None:
        return InazContractProfile(
            contract_kind=normalized_contract_kind,
            standard_daily_minutes=standard_daily_minutes,
        )
    return infer_contract_profile_from_template_code(template_code)
