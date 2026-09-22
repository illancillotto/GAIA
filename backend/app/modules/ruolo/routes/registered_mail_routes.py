from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.registered_mail_schemas import RuoloTributiRegisteredMailAssociationRequest
from app.modules.ruolo.schemas import RuoloTributiRegisteredMailResponse
from app.modules.ruolo.services import registered_mail_association

router = APIRouter(
    prefix="/tributi/raccomandate",
    tags=["ruolo-tributi"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)

Editor = Annotated[ApplicationUser, Depends(require_section("ruolo.tributi.manage_status"))]


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
    avviso = db.get(RuoloAvviso, payload.avviso_id) if payload.avviso_id is not None else None
    if payload.avviso_id is not None and avviso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avviso non trovato")
    updated = registered_mail_association.set_manual_association(
        db,
        mail=mail,
        avviso=avviso,
        updated_by=current_user.id,
    )
    db.commit()
    db.refresh(updated)
    return RuoloTributiRegisteredMailResponse.model_validate(updated)
