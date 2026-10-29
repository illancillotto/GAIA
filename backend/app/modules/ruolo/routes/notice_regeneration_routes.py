"""Regenerate generated reminder PDFs one by one, so the page can show progress and stop."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo.models import RuoloTributiReminderBatchItem
from app.modules.ruolo.services import notice_pdf_regeneration as regeneration

MANAGE = "ruolo.tributi.manage_status"
router = APIRouter(
    prefix="/tributi/solleciti",
    tags=["ruolo-tributi"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section(MANAGE))],
)


class RegenerationTarget(BaseModel):
    item_id: UUID
    batch_id: UUID
    display_name: str | None
    codice_fiscale: str


class RegenerationTargets(BaseModel):
    items: list[RegenerationTarget]
    excluded_drafts: int


class RegenerationRequest(BaseModel):
    mode: Literal["template", "recompute"]


class RegenerationResult(BaseModel):
    item_id: UUID
    outcome: Literal["regenerated", "skipped", "failed"]
    detail: str | None = None


@router.get("/regeneration-targets", response_model=RegenerationTargets)
def list_regeneration_targets(batch_id: UUID | None = None, db: Session = Depends(get_db)):
    items, excluded = regeneration.regeneration_targets(db, batch_id)
    return RegenerationTargets(
        items=[
            RegenerationTarget(
                item_id=item.id,
                batch_id=item.batch_id,
                display_name=item.display_name,
                codice_fiscale=item.codice_fiscale,
            )
            for item in items
        ],
        excluded_drafts=excluded,
    )


@router.post("/items/{item_id}/regenerate", response_model=RegenerationResult)
def regenerate_reminder_item(
    item_id: UUID,
    body: RegenerationRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section(MANAGE)),
):
    item = db.get(RuoloTributiReminderBatchItem, item_id)
    if item is None:
        raise HTTPException(404, detail="Sollecito batch non trovato")
    try:
        regeneration.regenerate_batch_item(
            db, item, body.mode, actor_id=current_user.id, reason=regeneration.REASONS[body.mode]
        )
    except (regeneration.RegenerationSkipped, regeneration.RegenerationFailed) as exc:
        db.rollback()
        outcome = "skipped" if isinstance(exc, regeneration.RegenerationSkipped) else "failed"
        return RegenerationResult(item_id=item_id, outcome=outcome, detail=str(exc))
    db.commit()
    return RegenerationResult(item_id=item_id, outcome="regenerated")
