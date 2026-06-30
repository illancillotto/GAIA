from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.catasto.services.indici_overview import get_indici_overview_cached
from app.schemas.catasto_phase1 import CatIndiceOverviewResponse

router = APIRouter(prefix="/catasto/indici", tags=["catasto-indici"])


@router.get("/overview", response_model=CatIndiceOverviewResponse)
def get_indici_overview(
    anno: int | None = Query(None),
    refresh: bool = Query(False, description="Forza il ricalcolo della snapshot annuale."),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatIndiceOverviewResponse:
    return get_indici_overview_cached(db, anno=anno, refresh=refresh)
