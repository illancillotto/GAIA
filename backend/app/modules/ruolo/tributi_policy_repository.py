from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloTributiCalculationPolicy
from app.modules.ruolo.services.notice_payment_deadline import (
    apply_payment_deadline,
    payment_deadline_payload,
)
from app.modules.ruolo.services.policy_notice_layout import apply_notice_layout

INTEREST_START_MODES = {"fixed_date", "notification_date"}
BOLLETTINO_POLICY_FIELDS = ("bollettino_causale", "bollettino_esercizio", "bollettino_version")


@dataclass(frozen=True)
class CalculationPolicyUpsert:
    name: str
    year_from: int | None
    year_to: int | None
    bonario_due_date: date | None
    surcharge_rate_percent: object
    surcharge_from: date | None
    interest_rate_percent: object
    interest_from: date | None
    interest_start_mode: str
    is_active: bool
    notes: str | None
    updated_by: int | None
    policy_id: uuid.UUID | None = None
    euribor_6m_rate_percent: object = 0
    euribor_source_url: str | None = None
    euribor_reference_period: str | None = None
    euribor_fetched_at: datetime | None = None
    bollettino_causale: str | None = None
    bollettino_esercizio: str | None = None
    only_unnotified: bool = False
    print_bollettino: bool = True
    bollettino_version: str = "v1"
    notice_number_source: str = "gaia"
    payment_due_date: date | None = None
    payment_deadline_mode: str = "fixed_date"


def list_calculation_policies(db: Session) -> list[RuoloTributiCalculationPolicy]:
    return list(
        db.scalars(
            select(RuoloTributiCalculationPolicy).order_by(
                RuoloTributiCalculationPolicy.year_from.asc().nullsfirst(),
                RuoloTributiCalculationPolicy.year_to.asc().nullsfirst(),
                RuoloTributiCalculationPolicy.name,
            )
        ).all()
    )


def get_calculation_policy_for_year(db: Session, year: int) -> RuoloTributiCalculationPolicy | None:
    return db.execute(
        select(RuoloTributiCalculationPolicy)
        .where(
            RuoloTributiCalculationPolicy.is_active.is_(True),
            or_(RuoloTributiCalculationPolicy.year_from.is_(None), RuoloTributiCalculationPolicy.year_from <= year),
            or_(RuoloTributiCalculationPolicy.year_to.is_(None), RuoloTributiCalculationPolicy.year_to >= year),
        )
        .order_by(RuoloTributiCalculationPolicy.year_from.desc().nullslast())
        .limit(1)
    ).scalar_one_or_none()


def upsert_calculation_policy(db: Session, **values: object) -> RuoloTributiCalculationPolicy:
    return _upsert_calculation_policy(db, CalculationPolicyUpsert(**values))


def _upsert_calculation_policy(db: Session, command: CalculationPolicyUpsert) -> RuoloTributiCalculationPolicy:
    surcharge_rate = _rate(command.surcharge_rate_percent)
    euribor_rate = _rate(command.euribor_6m_rate_percent)
    interest_rate = _rate(command.interest_rate_percent)
    if min(surcharge_rate, euribor_rate, interest_rate) < 0:
        raise ValueError("Le percentuali di maggiorazione, Euribor e interessi non possono essere negative")
    if command.interest_start_mode not in INTEREST_START_MODES:
        raise ValueError("Modalita decorrenza interessi non valida")

    policy = db.get(RuoloTributiCalculationPolicy, command.policy_id) if command.policy_id is not None else None
    if command.policy_id is not None and policy is None:
        raise ValueError("Policy di calcolo non trovata")
    _validate_policy_range(db, command, exclude_id=policy.id if policy else None)
    if policy is None:
        policy = RuoloTributiCalculationPolicy()
        db.add(policy)

    policy.name = command.name.strip()
    _apply_policy_schedule(policy, command)
    policy.surcharge_rate_percent = surcharge_rate
    policy.euribor_6m_rate_percent = euribor_rate
    policy.euribor_source_url = command.euribor_source_url
    policy.euribor_reference_period = command.euribor_reference_period
    policy.euribor_fetched_at = command.euribor_fetched_at
    policy.interest_rate_percent = interest_rate
    _apply_notice_print_options(policy, command)
    policy.is_active = command.is_active
    policy.notes = command.notes
    policy.updated_by = command.updated_by
    db.flush()
    return policy


def _apply_policy_schedule(policy: RuoloTributiCalculationPolicy, command: CalculationPolicyUpsert) -> None:
    policy.only_unnotified = command.only_unnotified
    policy.year_from = command.year_from
    policy.year_to = command.year_to
    policy.bonario_due_date = command.bonario_due_date
    policy.surcharge_from = command.bonario_due_date + timedelta(days=1) if command.bonario_due_date else command.surcharge_from
    policy.interest_from = command.interest_from
    policy.interest_start_mode = command.interest_start_mode


def _apply_notice_print_options(policy: RuoloTributiCalculationPolicy, command: CalculationPolicyUpsert) -> None:
    _apply_bollettino_codes(policy, command)
    policy.print_bollettino = command.print_bollettino
    apply_payment_deadline(policy, command)


def _apply_bollettino_codes(policy: RuoloTributiCalculationPolicy, command: CalculationPolicyUpsert) -> None:
    if command.bollettino_version not in {"v1", "v2"}:
        raise ValueError("Versione bollettino non valida")
    policy.bollettino_causale = _optional_code(command.bollettino_causale)
    policy.bollettino_esercizio = _optional_code(command.bollettino_esercizio)
    apply_notice_layout(policy, command)


def delete_calculation_policy(db: Session, policy_id: uuid.UUID) -> bool:
    policy = db.get(RuoloTributiCalculationPolicy, policy_id)
    if policy is None:
        return False
    db.delete(policy)
    db.flush()
    return True


def bollettino_policy_payload(db: Session, years: list[int]) -> dict[str, str]:
    policy = get_calculation_policy_for_year(db, max(years)) if years else None
    if policy is None:
        return {}
    return {
        key: getattr(policy, key) for key in BOLLETTINO_POLICY_FIELDS if getattr(policy, key)
    }


def notice_print_policy_payload(db: Session, years: list[int]) -> dict[str, object]:
    """Slip codes and payment date of the latest year; the slip only if every year's rule prints it."""
    if not years:
        return {}
    policies = [get_calculation_policy_for_year(db, year) for year in set(years)]
    payload: dict[str, object] = {
        **bollettino_policy_payload(db, years),
        "print_bollettino": all(policy.print_bollettino for policy in policies if policy is not None),
    }
    latest = get_calculation_policy_for_year(db, max(years))
    return {**payload, **payment_deadline_payload(latest, require_date=payload["print_bollettino"])}


def _validate_policy_range(
    db: Session,
    command: CalculationPolicyUpsert,
    *,
    exclude_id: uuid.UUID | None,
) -> None:
    if command.year_from is not None and command.year_to is not None and command.year_from > command.year_to:
        raise ValueError("year_from non puo essere maggiore di year_to")
    if not command.is_active:
        return
    policies = db.scalars(
        select(RuoloTributiCalculationPolicy).where(RuoloTributiCalculationPolicy.is_active.is_(True))
    ).all()
    for policy in policies:
        if exclude_id is not None and policy.id == exclude_id:
            continue
        if _ranges_overlap(command, policy):
            raise ValueError(f"Range annualita sovrapposto a {policy.name}")


def _ranges_overlap(command: CalculationPolicyUpsert, policy: RuoloTributiCalculationPolicy) -> bool:
    first_start = command.year_from if command.year_from is not None else -9999
    first_end = command.year_to if command.year_to is not None else 9999
    second_start = policy.year_from if policy.year_from is not None else -9999
    second_end = policy.year_to if policy.year_to is not None else 9999
    return first_start <= second_end and second_start <= first_end


def _rate(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _optional_code(value: str | None) -> str | None:
    return value.strip() if value else None
