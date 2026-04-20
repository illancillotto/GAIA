from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatAnomalia
from app.schemas.catasto_phase1 import CatAnomaliaListResponse, CatAnomaliaResponse

router = APIRouter(prefix="/catasto/anomalie", tags=["catasto-anomalie"])


@router.get("/", response_model=CatAnomaliaListResponse)
def list_anomalie(
    tipo: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    severita: str | None = Query(None),
    anno: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatAnomaliaListResponse:
    query = select(CatAnomalia).order_by(desc(CatAnomalia.created_at))
    count_query = select(func.count()).select_from(CatAnomalia)

    if tipo:
        query = query.where(CatAnomalia.tipo == tipo)
        count_query = count_query.where(CatAnomalia.tipo == tipo)
    if status_filter:
        query = query.where(CatAnomalia.status == status_filter)
        count_query = count_query.where(CatAnomalia.status == status_filter)
    if severita:
        query = query.where(CatAnomalia.severita == severita)
        count_query = count_query.where(CatAnomalia.severita == severita)
    if anno is not None:
        query = query.where(CatAnomalia.anno_campagna == anno)
        count_query = count_query.where(CatAnomalia.anno_campagna == anno)

    total = db.execute(count_query).scalar_one()
    items = db.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return CatAnomaliaListResponse(
        items=[CatAnomaliaResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
