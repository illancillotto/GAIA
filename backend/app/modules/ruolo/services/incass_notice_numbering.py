"""Rules that keep the existing inCASS avviso number: one notice per avviso, no GAIA number."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloTributiNoticeNumber
from app.modules.ruolo.services.tributi_notice_registry import reserve_notice_number
from app.modules.ruolo.services.tributi_reminder_service import build_batch_reminder_filename
from app.modules.ruolo.tributi_policy_repository import get_calculation_policy_for_year

INCASS_NOTICE_SOURCE = "incass"
INCASS_NOTICE_KEY = "incass_notice_number"
_INCASS_NUMBER = re.compile(r"\d{15}")
_SUMMED_AMOUNTS = (
    ("due_amount", "adjusted_due_amount"),
    ("paid_amount", "paid_amount"),
    ("saldo_amount", "saldo_amount"),
    ("surcharge_amount", "surcharge_amount"),
    ("interest_amount", "interest_amount"),
)


@dataclass(frozen=True)
class NoticeNumber:
    reservation_id: object
    number: str
    progressive: int | None


def incass_year_checker(db: Session) -> Callable[[int], bool]:
    """Per-call cache: whether the active rule of a year keeps the inCASS number."""
    cache: dict[int, bool] = {}

    def keeps_incass_number(year: int) -> bool:
        if year not in cache:
            policy = get_calculation_policy_for_year(db, year)
            cache[year] = policy is not None and policy.notice_number_source == INCASS_NOTICE_SOURCE
        return cache[year]

    return keeps_incass_number


def split_incass_candidates(db: Session, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Give every avviso under an inCASS-number rule its own notice; the rest stay grouped."""
    keeps_incass_number = incass_year_checker(db)
    result: list[dict[str, Any]] = []
    for candidate in candidates:
        own = [
            avviso
            for avviso in candidate["avvisi"]
            if keeps_incass_number(avviso["anno_tributario"])
        ]
        if not own:
            result.append(candidate)
            continue
        rest = [avviso for avviso in candidate["avvisi"] if avviso not in own]
        result.extend(_with_avvisi(candidate, [avviso]) for avviso in own)
        if rest:
            result.append(_with_avvisi(candidate, rest))
    return result


def _with_avvisi(candidate: dict[str, Any], avvisi: list[dict[str, Any]]) -> dict[str, Any]:
    managers = {
        avviso["annuality_manager_label"]
        for avviso in avvisi
        if avviso.get("annuality_manager_label")
    }
    return {
        **candidate,
        "avvisi": avvisi,
        "avvisi_count": len(avvisi),
        "years": sorted({avviso["anno_tributario"] for avviso in avvisi}),
        "annuality_managers": sorted(managers),
        **{
            total: float(
                sum((Decimal(str(avviso.get(field) or 0)) for avviso in avvisi), Decimal("0.00"))
            )
            for total, field in _SUMMED_AMOUNTS
        },
    }


def candidate_notice_number(
    db: Session,
    *,
    emission_year: int,
    candidate: dict[str, Any],
    reference_years: list[int],
) -> NoticeNumber:
    """The avviso's own inCASS number when its rule keeps it, otherwise a reserved GAIA number."""
    avvisi = candidate["avvisi"]
    if len(avvisi) == 1 and incass_year_checker(db)(avvisi[0]["anno_tributario"]):
        number = str(avvisi[0].get("codice_cnc") or "")
        if not _INCASS_NUMBER.fullmatch(number):
            raise ValueError(
                f"Numero avviso inCASS mancante per {candidate['codice_fiscale']} "
                f"({number or 'nessun numero'}): la regola richiede il numero inCASS"
            )
        candidate[INCASS_NOTICE_KEY] = number
        return NoticeNumber(reservation_id=None, number=number, progressive=None)
    reservation = reserve_notice_number(
        db,
        emission_year=emission_year,
        candidate=candidate,
        reference_years=reference_years,
    )
    return NoticeNumber(reservation.id, reservation.notice_number, reservation.progressive)


def incass_payload_overrides(candidate: dict[str, Any]) -> dict[str, str]:
    """With the inCASS number the slip causale is the avviso number itself."""
    number = candidate.get(INCASS_NOTICE_KEY)
    return {"bollettino_causale": number} if number else {}


def notice_filename(candidate: dict[str, Any]) -> str:
    """One notice per inCASS avviso: the number keeps same-year files of a taxpayer apart."""
    filename = build_batch_reminder_filename(
        codice_fiscale=candidate["codice_fiscale"], years=candidate["years"]
    )
    number = candidate.get(INCASS_NOTICE_KEY)
    return filename.replace(".pdf", f"_{number}.pdf") if number else filename


def notice_reservation(db: Session, reservation_id: object) -> RuoloTributiNoticeNumber | None:
    """inCASS-numbered notices reserve nothing in the GAIA register."""
    return db.get(RuoloTributiNoticeNumber, reservation_id) if reservation_id is not None else None
