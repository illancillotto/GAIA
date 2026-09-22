from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.ruolo.enums import (
    RuoloTributiPaymentRecordStatus,
    RuoloTributiRegisteredMailMatchStatus,
    RuoloTributiRegisteredMailRecoveryStatus,
)
from app.modules.ruolo.models import RuoloAvviso, RuoloTributiPayment, RuoloTributiRegisteredMail

MANUAL_ASSOCIATION_KEY = "manual_association"


def get_registered_mail(db: Session, mail_id: uuid.UUID) -> RuoloTributiRegisteredMail | None:
    return db.get(RuoloTributiRegisteredMail, mail_id)


def set_manual_association(
    db: Session,
    *,
    mail: RuoloTributiRegisteredMail,
    avviso: RuoloAvviso | None,
    updated_by: int,
) -> RuoloTributiRegisteredMail:
    payload = dict(mail.raw_payload_json or {})
    payload[MANUAL_ASSOCIATION_KEY] = {
        "active": True,
        "avviso_id": str(avviso.id) if avviso is not None else None,
        "updated_by": updated_by,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    mail.raw_payload_json = payload
    mail.avviso_id = avviso.id if avviso is not None else None
    mail.subject_id = avviso.subject_id if avviso is not None else None
    mail.match_status = (
        RuoloTributiRegisteredMailMatchStatus.MATCHED.value
        if avviso is not None
        else RuoloTributiRegisteredMailMatchStatus.UNMATCHED.value
    )
    mail.match_score = 100 if avviso is not None else None
    mail.match_reason = (
        "Associazione manuale impostata dall'operatore"
        if avviso is not None
        else "Associazione manuale rimossa dall'operatore"
    )
    mail.anomaly_key = None if avviso is not None else "manual_unlinked"
    mail.recovery_status = _recovery_status(db, avviso)
    db.flush()
    return mail


def resolve_import_match(
    db: Session,
    mail: RuoloTributiRegisteredMail | None,
    automatic_match: dict[str, Any],
) -> dict[str, Any]:
    association = manual_association(mail)
    return manual_match(db, association) or automatic_match


def preserve_manual_association(
    payload: dict[str, Any],
    mail: RuoloTributiRegisteredMail | None,
) -> dict[str, Any]:
    association = manual_association(mail)
    if association is not None:
        payload[MANUAL_ASSOCIATION_KEY] = association
    return payload


def manual_association(mail: RuoloTributiRegisteredMail | None) -> dict[str, Any] | None:
    if mail is None or not isinstance(mail.raw_payload_json, dict):
        return None
    value = mail.raw_payload_json.get(MANUAL_ASSOCIATION_KEY)
    return dict(value) if isinstance(value, dict) and value.get("active") is True else None


def manual_match(db: Session, association: dict[str, Any] | None) -> dict[str, Any] | None:
    if association is None:
        return None
    raw_avviso_id = association.get("avviso_id")
    if raw_avviso_id is None:
        return _unmatched("Associazione manuale rimossa dall'operatore", "manual_unlinked")
    try:
        avviso = db.get(RuoloAvviso, uuid.UUID(str(raw_avviso_id)))
    except ValueError:
        avviso = None
    if avviso is None:
        return _unmatched(
            "Avviso dell'associazione manuale non disponibile", "manual_target_missing"
        )
    return {
        "match_status": RuoloTributiRegisteredMailMatchStatus.MATCHED.value,
        "match_score": 100,
        "match_reason": "Associazione manuale impostata dall'operatore",
        "avviso": avviso,
        "candidates": [avviso],
    }


def _unmatched(reason: str, anomaly_key: str) -> dict[str, Any]:
    return {
        "match_status": RuoloTributiRegisteredMailMatchStatus.UNMATCHED.value,
        "match_score": None,
        "match_reason": reason,
        "anomaly_key": anomaly_key,
        "candidates": [],
    }


def _recovery_status(db: Session, avviso: RuoloAvviso | None) -> str:
    if avviso is None:
        return RuoloTributiRegisteredMailRecoveryStatus.PENDING.value
    paid_amount = db.scalar(
        select(func.coalesce(func.sum(RuoloTributiPayment.amount), 0)).where(
            RuoloTributiPayment.avviso_id == avviso.id,
            RuoloTributiPayment.status == RuoloTributiPaymentRecordStatus.VALID.value,
        )
    )
    if Decimal(str(paid_amount or 0)) > Decimal("0"):
        return RuoloTributiRegisteredMailRecoveryStatus.READY_ON_PAYMENT.value
    return RuoloTributiRegisteredMailRecoveryStatus.PENDING.value
