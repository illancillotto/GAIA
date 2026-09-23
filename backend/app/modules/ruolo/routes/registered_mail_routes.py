from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.registered_mail_schemas import RuoloTributiRegisteredMailAssociationRequest
from app.modules.ruolo.schemas import RuoloTributiRegisteredMailResponse
from app.modules.ruolo.services import registered_mail_association
from app.modules.ruolo.services.registered_mail_campaign_preview import preview_campaign

router = APIRouter(
    prefix="/tributi/raccomandate",
    tags=["ruolo-tributi"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)

Editor = Annotated[ApplicationUser, Depends(require_section("ruolo.tributi.manage_status"))]


@router.get("/campaign-preview")
def get_registered_mail_campaign_preview(
    created_before: Annotated[datetime, Query()],
    current_user: Editor,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return preview_campaign(db, created_before=created_before)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


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
    ids = payload.avviso_ids
    if ids is None and payload.avviso_id is not None:
        ids = [payload.avviso_id]
    ids = ids or []
    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Avvisi duplicati")
    avvisi = [db.get(RuoloAvviso, item) for item in ids]
    if any(item is None for item in avvisi):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avviso non trovato")
    avviso = avvisi[0] if avvisi else None
    try:
        updated = registered_mail_association.set_manual_association(
            db,
            mail=mail,
            avviso=avviso,
            avvisi=avvisi,
            updated_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    db.commit()
    db.refresh(updated)
    result = RuoloTributiRegisteredMailResponse.model_validate(updated)
    result.avviso_ids = ids
    return result
