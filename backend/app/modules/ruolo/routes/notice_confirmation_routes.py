"""Protected confirmation command; no export or delivery endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo.notice_confirmation_schemas import (
    NoticeGenerationConfirmationResponse,
    NoticeGenerationConfirmRequest,
)
from app.modules.ruolo.services.notice_draft_review import DraftReviewBlocked, confirm_generation
from app.modules.ruolo.services.notice_revision import (
    GenerationRevisionChanged,
    RevisionProtocolUnavailable,
)

router = APIRouter(
    prefix="/tributi",
    tags=["ruolo-tributi"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)


@router.post(
    "/solleciti/batches/{batch_id}/confirm",
    response_model=NoticeGenerationConfirmationResponse,
    dependencies=[Depends(require_section("ruolo.tributi.manage_status"))],
)
def confirm_reminder_batch(
    batch_id: uuid.UUID,
    payload: NoticeGenerationConfirmRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section("ruolo.tributi.manage_status")),
) -> NoticeGenerationConfirmationResponse:
    if not payload.batch:
        raise HTTPException(
            status_code=422, detail="La conferma del singolo avviso usa il percorso dedicato"
        )
    try:
        confirmation = confirm_generation(db, batch_id, batch=True, actor_id=current_user.id)
        db.commit()
        db.refresh(confirmation)
    except (DraftReviewBlocked, GenerationRevisionChanged) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RevisionProtocolUnavailable as exc:
        db.rollback()
        raise HTTPException(
            status_code=503, detail="Protocollo di conferma non disponibile"
        ) from exc
    return NoticeGenerationConfirmationResponse.model_validate(confirmation)
