from __future__ import annotations

import json
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatAnomalia, CatDistretto, CatParticella, CatUtenzaIrrigua
from app.schemas.catasto_phase1 import CatDistrettoKpiResponse, CatDistrettoResponse

router = APIRouter(prefix="/catasto/distretti", tags=["catasto-distretti"])


def _build_kpi(db: Session, distretto: CatDistretto, anno: int | None) -> CatDistrettoKpiResponse:
    num_distretto_int = int(distretto.num_distretto) if distretto.num_distretto.isdigit() else None
    utenze_filters = [CatUtenzaIrrigua.num_distretto == num_distretto_int] if num_distretto_int is not None else []
    if anno is not None:
        utenze_filters.append(CatUtenzaIrrigua.anno_campagna == anno)

    particelle_count = db.execute(
        select(func.count()).select_from(CatParticella).where(
            CatParticella.num_distretto == distretto.num_distretto,
            CatParticella.is_current.is_(True),
        )
    ).scalar_one()
    utenze_count = db.execute(select(func.count()).select_from(CatUtenzaIrrigua).where(*utenze_filters)).scalar_one()
    aggregati = db.execute(
        select(
            func.coalesce(func.sum(CatUtenzaIrrigua.importo_0648), 0),
            func.coalesce(func.sum(CatUtenzaIrrigua.importo_0985), 0),
            func.coalesce(func.sum(CatUtenzaIrrigua.sup_irrigabile_mq), 0),
        ).where(*utenze_filters)
    ).one()
    anomalie_count = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(case((CatAnomalia.severita == "error", 1), else_=0)), 0),
        )
        .select_from(CatAnomalia)
        .join(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id)
        .where(*utenze_filters)
    ).one()
    return CatDistrettoKpiResponse(
        distretto_id=distretto.id,
        anno=anno,
        num_distretto=distretto.num_distretto,
        totale_particelle=particelle_count,
        totale_utenze=utenze_count,
        totale_anomalie=int(anomalie_count[0] or 0),
        anomalie_error=int(anomalie_count[1] or 0),
        importo_totale_0648=Decimal(aggregati[0] or 0),
        importo_totale_0985=Decimal(aggregati[1] or 0),
        superficie_irrigabile_mq=Decimal(aggregati[2] or 0),
    )


@router.get("/", response_model=list[CatDistrettoResponse])
def list_distretti(db: Session = Depends(get_db), _: ApplicationUser = Depends(require_active_user)) -> list[CatDistretto]:
    return list(db.execute(select(CatDistretto).order_by(CatDistretto.num_distretto)).scalars().all())


@router.get("/{distretto_id}", response_model=CatDistrettoResponse)
def get_distretto(distretto_id: UUID, db: Session = Depends(get_db), _: ApplicationUser = Depends(require_active_user)) -> CatDistretto:
    distretto = db.get(CatDistretto, distretto_id)
    if distretto is None:
        raise HTTPException(status_code=404, detail="Distretto not found")
    return distretto


@router.get("/{distretto_id}/kpi", response_model=CatDistrettoKpiResponse)
def get_distretto_kpi(
    distretto_id: UUID,
    anno: int | None = Query(None),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatDistrettoKpiResponse:
    distretto = db.get(CatDistretto, distretto_id)
    if distretto is None:
        raise HTTPException(status_code=404, detail="Distretto not found")
    return _build_kpi(db, distretto, anno)


@router.get("/{distretto_id}/geojson")
def get_distretto_geojson(distretto_id: UUID, db: Session = Depends(get_db), _: ApplicationUser = Depends(require_active_user)) -> dict:
    distretto = db.get(CatDistretto, distretto_id)
    if distretto is None or distretto.geometry is None:
        raise HTTPException(status_code=404, detail="Distretto o geometria non trovata")
    geojson = db.execute(
        select(func.ST_AsGeoJSON(CatDistretto.geometry)).where(CatDistretto.id == distretto_id)
    ).scalar_one_or_none()
    if geojson is None:
        raise HTTPException(status_code=404, detail="Distretto o geometria non trovata")
    return {
        "type": "Feature",
        "geometry": json.loads(geojson),
        "properties": {
            "id": str(distretto.id),
            "num_distretto": distretto.num_distretto,
            "nome_distretto": distretto.nome_distretto,
        },
    }
