from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, exists, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatAnomalia, CatParticella, CatParticellaHistory, CatUtenzaIrrigua
from app.schemas.catasto_phase1 import (
    CatAnomaliaResponse,
    CatParticellaDetailResponse,
    CatParticellaHistoryResponse,
    CatParticellaResponse,
    CatUtenzaIrriguaResponse,
)

router = APIRouter(prefix="/catasto/particelle", tags=["catasto-particelle"])


@router.get("/", response_model=list[CatParticellaResponse])
def list_particelle(
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
    comune: int | None = Query(None),
    foglio: str | None = Query(None),
    particella: str | None = Query(None),
    distretto: str | None = Query(None),
    anno: int | None = Query(None),
    cf: str | None = Query(None),
    ha_anomalie: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[CatParticella]:
    query = select(CatParticella).where(CatParticella.is_current.is_(True)).order_by(
        CatParticella.cod_comune_capacitas, CatParticella.foglio, CatParticella.particella
    )
    if comune is not None:
        query = query.where(CatParticella.cod_comune_capacitas == comune)
    if foglio:
        query = query.where(CatParticella.foglio == foglio)
    if particella:
        query = query.where(CatParticella.particella == particella)
    if distretto:
        query = query.where(CatParticella.num_distretto == distretto)

    if anno is not None or cf or ha_anomalie is not None:
        utenze_filters: list = [CatUtenzaIrrigua.particella_id == CatParticella.id]
        if anno is not None:
            utenze_filters.append(CatUtenzaIrrigua.anno_campagna == anno)
        if cf:
            utenze_filters.append(CatUtenzaIrrigua.codice_fiscale == cf.strip().upper())
        if ha_anomalie is True:
            utenze_filters.append(
                exists(select(CatAnomalia.id).where(CatAnomalia.utenza_id == CatUtenzaIrrigua.id))
            )
        if ha_anomalie is False:
            utenze_filters.append(
                ~exists(select(CatAnomalia.id).where(CatAnomalia.utenza_id == CatUtenzaIrrigua.id))
            )
        query = query.where(exists(select(CatUtenzaIrrigua.id).where(*utenze_filters)))

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


@router.get("/{particella_id}/utenze", response_model=list[CatUtenzaIrriguaResponse])
def get_particella_utenze(
    particella_id: UUID,
    anno: int | None = Query(None),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> list[CatUtenzaIrrigua]:
    filters = [CatUtenzaIrrigua.particella_id == particella_id]
    if anno is not None:
        filters.append(CatUtenzaIrrigua.anno_campagna == anno)
    return list(
        db.execute(select(CatUtenzaIrrigua).where(*filters).order_by(desc(CatUtenzaIrrigua.anno_campagna))).scalars().all()
    )


@router.get("/{particella_id}/anomalie", response_model=list[CatAnomaliaResponse])
def get_particella_anomalie(
    particella_id: UUID,
    anno: int | None = Query(None),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> list[CatAnomalia]:
    query = (
        select(CatAnomalia)
        .join(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id)
        .where(CatUtenzaIrrigua.particella_id == particella_id)
        .order_by(desc(CatAnomalia.created_at))
    )
    if anno is not None:
        query = query.where(CatAnomalia.anno_campagna == anno)
    return list(db.execute(query).scalars().all())
