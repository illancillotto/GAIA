from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo.models import RuoloAvviso, RuoloTributiRegisteredMail
from app.modules.ruolo.registered_mail_schemas import (
    RegisteredMailReferenceCheckRequest,
    RuoloTributiRegisteredMailAssociationRequest,
    RuoloTributiRegisteredMailSummaryResponse,
)
from app.modules.ruolo.schemas import RuoloTributiRegisteredMailResponse
from app.modules.ruolo.services import registered_mail_association
from app.modules.ruolo.services.registered_mail_campaign_preview import preview_campaign
from app.modules.ruolo.services.registered_mail_documents import validate_subject_change
from app.modules.ruolo.services.registered_mail_reference_check import verify_workbook_references
from app.modules.ruolo.services.registered_mail_review_evidence import (
    association_ids,
    record_review_evidence,
    validate_review_evidence,
)

router = APIRouter(
    prefix="/tributi/raccomandate",
    tags=["ruolo-tributi"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)

Editor = Annotated[ApplicationUser, Depends(require_section("ruolo.tributi.manage_status"))]


@router.get("/summary", response_model=RuoloTributiRegisteredMailSummaryResponse)
def get_registered_mail_summary(
    db: Session = Depends(get_db),
) -> RuoloTributiRegisteredMailSummaryResponse:
    associated_filter = and_(
        RuoloTributiRegisteredMail.avviso_id.is_not(None),
        RuoloTributiRegisteredMail.match_status == "matched",
        RuoloTributiRegisteredMail.anomaly_key.is_(None),
    )
    total, associated = db.execute(
        select(
            func.count(RuoloTributiRegisteredMail.id),
            func.count(RuoloTributiRegisteredMail.id).filter(associated_filter),
        )
    ).one()
    return RuoloTributiRegisteredMailSummaryResponse(
        total=total,
        associated=associated,
        anomalies=total - associated,
    )


@router.get("/campaign-preview")
def get_registered_mail_campaign_preview(
    created_before: Annotated[datetime, Query()],
    current_user: Editor,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return preview_campaign(db, created_before=created_before)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.patch("/{mail_id}/association", response_model=RuoloTributiRegisteredMailResponse)
def update_registered_mail_association(
    mail_id: uuid.UUID,
    payload: RuoloTributiRegisteredMailAssociationRequest,
    current_user: Editor,
    db: Session = Depends(get_db),
) -> RuoloTributiRegisteredMailResponse:
    mail = registered_mail_association.get_registered_mail(db, mail_id)
    if mail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Raccomandata non trovata"
        )
    ids = association_ids(payload)
    if len(set(ids)) != len(ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Avvisi duplicati"
        )
    avvisi = [db.get(RuoloAvviso, item) for item in ids]
    if any(item is None for item in avvisi):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avviso non trovato")
    validate_review_evidence(db, mail, ids, payload.review_evidence)
    previous_ids = [str(item) for item in registered_mail_association.associated_avviso_ids(mail)]
    validate_subject_change(db, mail.id, avvisi)
    try:
        updated = registered_mail_association.set_manual_association(
            db,
            mail=mail,
            avviso=None,
            avvisi=avvisi,
            updated_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    record_review_evidence(db, updated, previous_ids=previous_ids, ids=ids, evidence=payload.review_evidence)
    db.commit()
    db.refresh(updated)
    result = RuoloTributiRegisteredMailResponse.model_validate(updated)
    result.avviso_ids = ids
    return result


@router.post("/{mail_id}/reference-check")
def check_registered_mail_references(
    mail_id: uuid.UUID,
    payload: RegisteredMailReferenceCheckRequest,
    current_user: Editor,
    db: Session = Depends(get_db),
) -> dict[str, str | bool]:
    return verify_workbook_references(
        db, mail_id=mail_id, ref_2022=payload.ref_2022, ref_2023=payload.ref_2023
    )
