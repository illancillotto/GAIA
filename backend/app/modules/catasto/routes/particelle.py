from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatParticella, CatParticellaHistory
from app.schemas.catasto_phase1 import CatParticellaDetailResponse, CatParticellaHistoryResponse, CatParticellaResponse

router = APIRouter(prefix="/catasto/particelle", tags=["catasto-particelle"])


@router.get("/", response_model=list[CatParticellaResponse])
def list_particelle(
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
    comune: int | None = Query(None),
    foglio: str | None = Query(None),
    particella: str | None = Query(None),
    distretto: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[CatParticella]:
    query = select(CatParticella).where(CatParticella.is_current.is_(True)).order_by(
        CatParticella.cod_comune_istat, CatParticella.foglio, CatParticella.particella
    )
    if comune is not None:
        query = query.where(CatParticella.cod_comune_istat == comune)
    if foglio:
        query = query.where(CatParticella.foglio == foglio)
    if particella:
        query = query.where(CatParticella.particella == particella)
    if distretto:
        query = query.where(CatParticella.num_distretto == distretto)
    return list(db.execute(query.limit(limit)).scalars().all())


@router.get("/{particella_id}", response_model=CatParticellaDetailResponse)
def get_particella(particella_id: UUID, db: Session = Depends(get_db), _: ApplicationUser = Depends(require_active_user)) -> CatParticellaDetailResponse:
    item = db.get(CatParticella, particella_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Particella not found")
    payload = CatParticellaDetailResponse.model_validate(item)
    payload.fuori_distretto = item.fuori_distretto
    return payload


@router.get("/{particella_id}/history", response_model=list[CatParticellaHistoryResponse])
def get_particella_history(
    particella_id: UUID,
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> list[CatParticellaHistory]:
    return list(
        db.execute(
            select(CatParticellaHistory)
            .where(CatParticellaHistory.particella_id == particella_id)
            .order_by(desc(CatParticellaHistory.changed_at))
        ).scalars().all()
    )
