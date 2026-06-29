from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.catasto.services.colture import build_colture_overview
from app.schemas.catasto_phase1 import CatColturaOverviewResponse

router = APIRouter(prefix="/catasto/colture", tags=["catasto-colture"])


@router.get("/overview", response_model=CatColturaOverviewResponse)
def get_colture_overview(
    anno: int | None = Query(None),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatColturaOverviewResponse:
    return build_colture_overview(db, anno=anno)
