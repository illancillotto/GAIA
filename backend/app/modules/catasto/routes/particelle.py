from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, exists, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import (
    CatAnomalia,
    CatComune,
    CatConsorzioUnit,
    CatParticella,
    CatParticellaHistory,
    CatUtenzaIrrigua,
)
from app.schemas.catasto_phase1 import (
    CatAnomaliaResponse,
    CatConsorzioOccupancyResponse,
    CatConsorzioUnitSummaryResponse,
    CatParticellaDetailResponse,
    CatParticellaConsorzioResponse,
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
    codice_catastale: str | None = Query(None, description="Codice catastale comune (es. A357)."),
    nome_comune: str | None = Query(None, description="Nome comune (ricerca parziale, case-insensitive)."),
    foglio: str | None = Query(None),
    particella: str | None = Query(None),
    distretto: str | None = Query(None),
    anno: int | None = Query(None),
    cf: str | None = Query(None),
    intestatario: str | None = Query(None, description="Ricerca parziale sulla denominazione utenza (case-insensitive)."),
    ha_anomalie: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[CatParticellaResponse]:
    query = select(CatParticella).where(CatParticella.is_current.is_(True)).order_by(
        CatParticella.cod_comune_capacitas, CatParticella.foglio, CatParticella.particella
    )
    if comune is not None:
        query = query.where(CatParticella.cod_comune_capacitas == comune)
    if codice_catastale:
        query = query.where(CatParticella.codice_catastale == codice_catastale.strip().upper())
    if nome_comune:
        query = query.where(CatParticella.nome_comune.ilike(f"%{nome_comune.strip()}%"))
    if foglio:
        query = query.where(CatParticella.foglio == foglio)
    if particella:
        query = query.where(CatParticella.particella == particella)
    if distretto:
        query = query.where(CatParticella.num_distretto == distretto)

    if anno is not None or cf or intestatario or ha_anomalie is not None:
        utenze_filters: list = [CatUtenzaIrrigua.particella_id == CatParticella.id]
        if anno is not None:
            utenze_filters.append(CatUtenzaIrrigua.anno_campagna == anno)
        if cf:
            utenze_filters.append(CatUtenzaIrrigua.codice_fiscale == cf.strip().upper())
        if intestatario:
            utenze_filters.append(CatUtenzaIrrigua.denominazione.ilike(f"%{intestatario.strip()}%"))
        if ha_anomalie is True:
            utenze_filters.append(
                exists(select(CatAnomalia.id).where(CatAnomalia.utenza_id == CatUtenzaIrrigua.id))
            )
        if ha_anomalie is False:
            utenze_filters.append(
                ~exists(select(CatAnomalia.id).where(CatAnomalia.utenza_id == CatUtenzaIrrigua.id))
            )
        query = query.where(exists(select(CatUtenzaIrrigua.id).where(*utenze_filters)))

    items = list(db.execute(query.limit(limit)).scalars().all())
    if not items:
        return []

    particella_ids = [p.id for p in items]
    rn_col = func.row_number().over(
        partition_by=CatUtenzaIrrigua.particella_id,
        order_by=desc(CatUtenzaIrrigua.anno_campagna),
    ).label("rn")
    ranked_sq = (
        select(
            CatUtenzaIrrigua.particella_id,
            CatUtenzaIrrigua.codice_fiscale,
            CatUtenzaIrrigua.denominazione,
            rn_col,
        )
        .where(CatUtenzaIrrigua.particella_id.in_(particella_ids))
        .subquery()
    )
    latest_rows = db.execute(select(ranked_sq).where(ranked_sq.c.rn == 1)).all()
    utenza_map = {row.particella_id: row for row in latest_rows}

    responses: list[CatParticellaResponse] = []
    for p in items:
        r = CatParticellaResponse.model_validate(p)
        u = utenza_map.get(p.id)
        if u:
            r.utenza_cf = u.codice_fiscale
            r.utenza_denominazione = u.denominazione
        responses.append(r)
    return responses


@router.get("/{particella_id}", response_model=CatParticellaDetailResponse)
def get_particella(particella_id: UUID, db: Session = Depends(get_db), _: ApplicationUser = Depends(require_active_user)) -> CatParticellaDetailResponse:
    item = db.get(CatParticella, particella_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Particella not found")
    payload = CatParticellaDetailResponse.model_validate(item)
    payload.fuori_distretto = item.fuori_distretto
    return payload


@router.get("/{particella_id}/consorzio", response_model=CatParticellaConsorzioResponse)
def get_particella_consorzio(
    particella_id: UUID,
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatParticellaConsorzioResponse:
    item = db.get(CatParticella, particella_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Particella not found")

    units = (
        db.execute(
            select(CatConsorzioUnit)
            .where(CatConsorzioUnit.particella_id == particella_id)
            .order_by(desc(CatConsorzioUnit.source_last_seen), desc(CatConsorzioUnit.created_at))
        )
        .scalars()
        .all()
    )

    payload_units: list[CatConsorzioUnitSummaryResponse] = []
    for unit in units:
        comune_record = db.get(CatComune, unit.comune_id) if unit.comune_id else None
        source_comune_record = db.get(CatComune, unit.source_comune_id) if unit.source_comune_id else None
        base_payload = CatConsorzioUnitSummaryResponse.model_validate(unit).model_dump(
            exclude={"comune_label", "source_comune_resolved_label", "occupancies"}
        )
        payload_units.append(
            CatConsorzioUnitSummaryResponse(
                **base_payload,
                comune_label=comune_record.nome_comune if comune_record else None,
                source_comune_resolved_label=source_comune_record.nome_comune if source_comune_record else None,
                occupancies=[CatConsorzioOccupancyResponse.model_validate(occ) for occ in unit.occupancies],
            )
        )

    return CatParticellaConsorzioResponse(particella_id=particella_id, units=payload_units)


@router.get("/{particella_id}/geojson")
def get_particella_geojson(
    particella_id: UUID,
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> dict:
    item = db.get(CatParticella, particella_id)
    if item is None or item.geometry is None:
        raise HTTPException(status_code=404, detail="Particella o geometria non trovata")

    geojson = db.execute(select(func.ST_AsGeoJSON(CatParticella.geometry)).where(CatParticella.id == particella_id)).scalar_one_or_none()
    geom_type = db.execute(select(func.ST_GeometryType(CatParticella.geometry)).where(CatParticella.id == particella_id)).scalar_one_or_none()
    centroid = db.execute(select(func.ST_AsGeoJSON(func.ST_Centroid(CatParticella.geometry))).where(CatParticella.id == particella_id)).scalar_one_or_none()

    if geojson is None:
        raise HTTPException(status_code=404, detail="Particella o geometria non trovata")

    return {
        "type": "Feature",
        "geometry": json.loads(geojson),
        "properties": {
            "id": str(item.id),
            "foglio": item.foglio,
            "particella": item.particella,
            "subalterno": item.subalterno,
            "cod_comune_capacitas": item.cod_comune_capacitas,
            "nome_comune": item.nome_comune,
            "num_distretto": item.num_distretto,
            "nome_distretto": item.nome_distretto,
            "source_type": item.source_type,
            "geometry_type": geom_type,
            "centroid": json.loads(centroid) if centroid else None,
        },
    }


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
