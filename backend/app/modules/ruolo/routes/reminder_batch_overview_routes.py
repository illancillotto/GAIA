"""Per-batch summary for the «Lotti generati» list."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.modules.ruolo.services.reminder_batch_overview import batch_overview

router = APIRouter(
    prefix="/tributi/solleciti",
    tags=["ruolo-tributi"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)


class BatchOverviewItem(BaseModel):
    item_id: UUID
    label: str
    status: str
    sendable: bool
    pec_sent: bool


class BatchOverview(BaseModel):
    batch_id: UUID
    items: list[BatchOverviewItem]


@router.get("/batch-overview", response_model=list[BatchOverview])
def list_batch_overview(
    batch_id: Annotated[list[UUID], Query(max_length=100)],
    db: Session = Depends(get_db),
):
    overview = batch_overview(db, batch_id)
    return [BatchOverview(batch_id=key, items=overview.get(key, [])) for key in batch_id]
