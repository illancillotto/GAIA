"""Project STEP assignments onto the notice register (``ruolo_notice_recoveries``).

For every ``ruolo_avvisi`` row with ``linked`` STEP documents, each register
position of that avviso receives the state proven by STEP:

- ``affidato`` while any linked charge is not covered by payments/discharges;
- ``revocato`` when the whole charge was discharged (sgravio);
- ``chiuso`` when it is covered by payments (and discharges).

Writes go through ``assess_recovery`` (document lock, version check, audit).
An operator decision is never overwritten: a position is updated only while
it is ``da_verificare`` or still carries evidence written by this projection.
Absence from STEP is never interpreted: ``non_affidato_verificato`` is not set
and positions without STEP links are left untouched.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.elaborazioni.step.models import StepDocumento, StepRuoloLink
from app.modules.ruolo.notice_register_models import NoticeDocument, NoticePosition, NoticeRecovery
from app.modules.ruolo.notice_register_schemas import OperatorChange, RecoveryDecision
from app.modules.ruolo.services.notice_register import RegisterConflict, assess_recovery

EVIDENCE_PREFIX = "STEP sync"
PUBLISH_COUNTERS = ("updated", "unchanged", "operator_decision", "conflicts", "without_position")
_ZERO = Decimal("0")


@dataclass(frozen=True)
class DesiredRecovery:
    state: str
    case_reference: str
    amount: Decimal


def _amounts(link: StepRuoloLink) -> tuple[Decimal, Decimal, Decimal]:
    return link.imp_carico or _ZERO, link.imp_carico_pagato or _ZERO, link.imp_discaricato or _ZERO


def _covered(link: StepRuoloLink) -> bool:
    charged, paid, discharged = _amounts(link)
    return charged > _ZERO and paid + discharged >= charged


def desired_recovery(links: list[tuple[StepRuoloLink, str]]) -> DesiredRecovery:
    """State proven by the linked STEP documents of one avviso (``(link, num_doc)`` pairs)."""

    amounts = [_amounts(link) for link, _ in links]
    charged = sum((item[0] for item in amounts), _ZERO)
    discharged = sum((item[2] for item in amounts), _ZERO)
    if not all(_covered(link) for link, _ in links):
        state = "affidato"
    elif discharged >= charged:
        state = "revocato"
    else:
        state = "chiuso"
    case_reference = ", ".join(sorted({num_doc for _, num_doc in links}))[:200]
    return DesiredRecovery(state=state, case_reference=case_reference, amount=charged)


def _linked_by_avviso(db: Session) -> dict[uuid.UUID, list[tuple[StepRuoloLink, str]]]:
    rows = db.execute(
        select(StepRuoloLink, StepDocumento.num_doc)
        .join(StepDocumento, StepDocumento.id == StepRuoloLink.documento_id)
        .where(StepRuoloLink.status == "linked")
    ).all()
    grouped: dict[uuid.UUID, list[tuple[StepRuoloLink, str]]] = defaultdict(list)
    for link, num_doc in rows:
        grouped[link.ruolo_avviso_id].append((link, num_doc))
    return grouped


def _is_current(recovery: NoticeRecovery, desired: DesiredRecovery) -> bool:
    return (
        recovery.state == desired.state
        and recovery.case_reference == desired.case_reference
        and recovery.amount == desired.amount
    )


def _owned_by_projection(recovery: NoticeRecovery) -> bool:
    return recovery.state == "da_verificare" or (recovery.evidence_reference or "").startswith(
        EVIDENCE_PREFIX
    )


def _apply(db: Session, position: NoticePosition, desired: DesiredRecovery, context: dict) -> str:
    recovery = db.get(NoticeRecovery, position.id)
    if _is_current(recovery, desired):
        return "unchanged"
    if not _owned_by_projection(recovery):
        return "operator_decision"
    document = db.get(NoticeDocument, position.document_id)
    decision = RecoveryDecision(
        state=desired.state,
        case_reference=desired.case_reference,
        verified_on=context["now"].date(),
        evidence_reference=f"{EVIDENCE_PREFIX} job {context['job_id']} del {context['now'].date().isoformat()}: documenti STEP {desired.case_reference}",
        amount=desired.amount,
    )
    change = OperatorChange(
        actor_id=context["actor_id"],
        reason=f"Pubblicazione automatica stato STEP (job {context['job_id']})",
        expected_version=document.version,
    )
    try:
        assess_recovery(db, position.document_id, position.id, decision, change)
        db.commit()
    except RegisterConflict:
        db.rollback()
        return "conflicts"
    return "updated"


def publish_recoveries(
    db: Session, *, actor_id: int, job_id: int | None, now: datetime
) -> dict[str, int]:
    counts = dict.fromkeys(PUBLISH_COUNTERS, 0)
    linked = _linked_by_avviso(db)
    if not linked:
        return counts
    positions = db.scalars(
        select(NoticePosition)
        .join(NoticeDocument, NoticeDocument.id == NoticePosition.document_id)
        .where(
            NoticePosition.avviso_id.in_(list(linked)), NoticeDocument.reconciled_into_id.is_(None)
        )
        .order_by(NoticePosition.document_id, NoticePosition.id)
    ).all()
    counts["without_position"] = len(set(linked) - {position.avviso_id for position in positions})
    context = {"actor_id": actor_id, "job_id": job_id, "now": now}
    for position in positions:
        counts[_apply(db, position, desired_recovery(linked[position.avviso_id]), context)] += 1
    return counts
