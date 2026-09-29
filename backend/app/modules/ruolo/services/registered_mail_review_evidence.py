"""Validate and retain operator workbook provenance for confirmed associations."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloTributiRegisteredMail
from app.modules.ruolo.notice_register_models import NoticeAttempt, NoticeAudit
from app.modules.ruolo.registered_mail_schemas import (
    RegisteredMailReviewEvidence,
    RuoloTributiRegisteredMailAssociationRequest,
)
from app.modules.ruolo.services.registered_mail_reference_check import verify_workbook_references


def association_ids(payload: RuoloTributiRegisteredMailAssociationRequest) -> list[uuid.UUID]:
    if payload.avviso_ids is not None:
        return payload.avviso_ids
    return [payload.avviso_id] if payload.avviso_id is not None else []


def validate_review_evidence(
    db: Session,
    mail: RuoloTributiRegisteredMail,
    ids: list[uuid.UUID],
    evidence: RegisteredMailReviewEvidence | None,
) -> None:
    if evidence is None:
        return
    checked = verify_workbook_references(
        db, mail_id=mail.id, ref_2022=evidence.ref_2022, ref_2023=evidence.ref_2023
    )
    if not checked["verified"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=checked["reason"]
        )
    candidates = (mail.raw_payload_json or {}).get("candidate_avviso_ids") or []
    if {str(item) for item in ids} != set(candidates):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Coppia selezionata diversa dai candidati verificati",
        )


def record_review_evidence(
    db: Session,
    mail: RuoloTributiRegisteredMail,
    *,
    previous_ids: list[str],
    ids: list[uuid.UUID],
    evidence: RegisteredMailReviewEvidence | None,
) -> None:
    if evidence is None:
        return
    payload = dict(mail.raw_payload_json or {})
    association = dict(payload.get("manual_association") or {})
    association["review_evidence"] = evidence.model_dump()
    payload["manual_association"] = association
    history = list(association.get("history") or [])
    history.append(
        {
            "previous_avviso_ids": previous_ids,
            "avviso_ids": [str(item) for item in ids],
            "updated_by": association.get("updated_by"),
            "updated_at": association.get("updated_at"),
            "review_evidence": evidence.model_dump(),
        }
    )
    association["history"] = history
    payload["manual_association"] = association
    mail.raw_payload_json = payload
    attempt = db.scalar(select(NoticeAttempt).where(NoticeAttempt.registered_mail_id == mail.id))
    if attempt is None:
        return
    audit = db.scalar(
        select(NoticeAudit)
        .where(NoticeAudit.document_id == attempt.document_id)
        .order_by(NoticeAudit.version.desc())
        .limit(1)
    )
    if audit is not None:
        audit.after_json = {
            **audit.after_json,
            "review_evidence": evidence.model_dump(),
            "previous_avviso_ids": previous_ids,
        }
