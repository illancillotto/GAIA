from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from app.modules.presenze.models import (
    PRESENZE_CONTRACT_KIND_ALTRO,
    PRESENZE_CONTRACT_KIND_IMPIEGATO,
    PRESENZE_CONTRACT_KIND_OPERAIO,
    PRESENZE_CONTRACT_KIND_QUADRO,
    PRESENZE_OPERAI_GROUP_AGRARIO,
    PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO,
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


EMPTY_PRESENZE_CONTRACT_PROFILE = PresenzeContractProfile(contract_kind=None, standard_daily_minutes=None)


def infer_contract_profile_from_template_code(template_code: str | None) -> PresenzeContractProfile:
    """Deduce il profilo dal codice orario Inaz, sia esso un template assegnato o il
    codice della singola giornata: OPE, OP, OSAB, ADD e IRR sono operai, IMP e TELEC
    impiegati. I minuti sono quelli della giornata ordinaria del collaboratore, non
    quelli del giorno: un codice sabato descrive comunque un operaio da sette ore."""
    if template_code is None:
        return EMPTY_PRESENZE_CONTRACT_PROFILE
    normalized = template_code.strip().upper()
    if not normalized:
        return EMPTY_PRESENZE_CONTRACT_PROFILE
    if normalized.startswith("OPE0736"):
        return PresenzeContractProfile(contract_kind=PRESENZE_CONTRACT_KIND_OPERAIO, standard_daily_minutes=456)
    if normalized.startswith("TELEC"):
        return PresenzeContractProfile(contract_kind=PRESENZE_CONTRACT_KIND_IMPIEGATO, standard_daily_minutes=480)
    if normalized.startswith("IMP") or "RIENTRO IMP" in normalized:
        return PresenzeContractProfile(contract_kind=PRESENZE_CONTRACT_KIND_IMPIEGATO, standard_daily_minutes=385)
    if (
        normalized.startswith("OP")
        or normalized.startswith("OSAB")
        or normalized.startswith("ADD")
        or normalized.startswith("IRR")
        or "OPESAB" in normalized
    ):
        return PresenzeContractProfile(contract_kind=PRESENZE_CONTRACT_KIND_OPERAIO, standard_daily_minutes=420)
    return EMPTY_PRESENZE_CONTRACT_PROFILE


def infer_contract_profile_from_schedule_codes(schedule_codes: Iterable[str | None]) -> PresenzeContractProfile:
    """Profilo dedotto dai codici orario delle giornate, per i collaboratori senza
    assegnazione di orario. Decide il codice piu ricorrente, cosi un codice di sabato
    o di turno non prevale su quello ordinario, e un codice operaio batte uno
    impiegato: i turnisti del telecontrollo portano TELEC solo nei giorni di turno."""
    counts = Counter(code.strip().upper() for code in schedule_codes if code and code.strip())
    operaio: PresenzeContractProfile | None = None
    impiegato: PresenzeContractProfile | None = None
    for code, _count in counts.most_common():
        profile = infer_contract_profile_from_template_code(code)
        if profile.contract_kind == PRESENZE_CONTRACT_KIND_OPERAIO and operaio is None:
            operaio = profile
        elif profile.contract_kind == PRESENZE_CONTRACT_KIND_IMPIEGATO and impiegato is None:
            impiegato = profile
    return operaio or impiegato or EMPTY_PRESENZE_CONTRACT_PROFILE


def resolve_contract_profile(
    contract_kind: str | None,
    standard_daily_minutes: int | None,
    *,
    template_code: str | None = None,
    schedule_codes: Iterable[str | None] | None = None,
) -> PresenzeContractProfile:
    normalized_contract_kind = normalize_contract_kind(contract_kind)
    if normalized_contract_kind is not None:
        return PresenzeContractProfile(
            contract_kind=normalized_contract_kind,
            standard_daily_minutes=standard_daily_minutes,
        )
    inferred = infer_contract_profile_from_template_code(template_code)
    if inferred.contract_kind is None:
        inferred = infer_contract_profile_from_schedule_codes(schedule_codes or ())
    if inferred.contract_kind is None:
        return PresenzeContractProfile(contract_kind=None, standard_daily_minutes=standard_daily_minutes)
    # I minuti impostati a mano restano quelli decisi da HR: si deduce solo il tipo
    # contratto mancante, altrimenti il collaboratore resta fuori dalle regole operai.
    return PresenzeContractProfile(
        contract_kind=inferred.contract_kind,
        standard_daily_minutes=standard_daily_minutes if standard_daily_minutes is not None else inferred.standard_daily_minutes,
    )
