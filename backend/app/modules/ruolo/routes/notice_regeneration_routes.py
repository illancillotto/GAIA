"""Regenerate reminder PDFs and make the missing ones of a year, in small steps.

Each call does little work, so the page can show progress and stop between two calls.
"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloTributiReminderBatchItem
from app.modules.ruolo.services import notice_pdf_regeneration as regeneration
from app.modules.ruolo.services import year_notice_generation as year_notices

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


class FailedNotice(BaseModel):
    item_id: UUID
    label: str


class MissingNotice(BaseModel):
    label: str
    avviso_ids: list[UUID]


class YearStatus(BaseModel):
    year: int
    total: int
    ready: int
    failed: list[FailedNotice]
    missing: list[MissingNotice]


class YearGenerationRequest(BaseModel):
    avviso_ids: list[UUID] = Field(min_length=1, max_length=200)


class NoticeProblem(BaseModel):
    label: str
    detail: str


class YearGenerationResult(BaseModel):
    batch_id: UUID | None
    generated: int
    problems: list[NoticeProblem]


@router.get("/years/{year}/status", response_model=YearStatus)
def get_year_status(year: int, db: Session = Depends(get_db)):
    return year_notices.year_status(db, year)


@router.post("/years/{year}/generate", response_model=YearGenerationResult)
def generate_year_notices(
    year: int,
    body: YearGenerationRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_section(MANAGE)),
):
    batch = year_notices.generate_missing(db, year, body.avviso_ids, actor_id=current_user.id)
    if batch is None:
        return YearGenerationResult(batch_id=None, generated=0, problems=[])
    db.commit()
    items = repo.list_reminder_batch_items(db, batch.id)
    return YearGenerationResult(
        batch_id=batch.id,
        generated=batch.items_generated,
        problems=[
            NoticeProblem(
                label=item.display_name or item.codice_fiscale,
                detail=item.error_detail or "motivo non registrato",
            )
            for item in items
            if item.status == regeneration.FAILED
        ],
    )
