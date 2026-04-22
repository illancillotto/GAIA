from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatAnomalia, CatIntestatario, CatParticella, CatUtenzaIrrigua
from app.schemas.catasto_phase1 import (
    CatAnagraficaBulkSearchRequest,
    CatAnagraficaBulkSearchResponse,
    CatAnagraficaBulkSearchRowResult,
    CatAnagraficaMatch,
    CatAnagraficaSearchResponse,
    CatAnagraficaUtenzaSummary,
    CatIntestatarioResponse,
)

router = APIRouter(prefix="/catasto/anagrafica", tags=["catasto-anagrafica"])


def _norm_str(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    return v if v else None


def _looks_like_int(value: str | None) -> bool:
    if value is None:
        return False
    v = value.strip()
    return v.isdigit()


def _load_intestatari_by_cf(db: Session, cfs: set[str]) -> dict[str, CatIntestatario]:
    if not cfs:
        return {}
    rows = db.execute(select(CatIntestatario).where(CatIntestatario.codice_fiscale.in_(sorted(cfs)))).scalars().all()
    return {r.codice_fiscale: r for r in rows}


def _utenza_summary_from_record(u: CatUtenzaIrrigua | None) -> CatAnagraficaUtenzaSummary | None:
    if u is None:
        return None
    return CatAnagraficaUtenzaSummary(
        id=u.id,
        cco=u.cco,
        anno_campagna=u.anno_campagna,
        stato="importata",
        num_distretto=u.num_distretto,
        nome_distretto=u.nome_distretto_loc or None,
        sup_irrigabile_mq=u.sup_irrigabile_mq,
        denominazione=u.denominazione,
        codice_fiscale=u.codice_fiscale,
        ha_anomalie=u.ha_anomalie,
    )


def _build_match(db: Session, p: CatParticella) -> CatAnagraficaMatch:
    latest_utenza = (
        db.execute(
            select(CatUtenzaIrrigua)
            .where(CatUtenzaIrrigua.particella_id == p.id)
            .order_by(desc(CatUtenzaIrrigua.anno_campagna))
            .limit(1)
        )
        .scalars()
        .first()
    )

    utenze = db.execute(
        select(CatUtenzaIrrigua)
        .where(CatUtenzaIrrigua.particella_id == p.id)
        .order_by(desc(CatUtenzaIrrigua.anno_campagna))
        .limit(25)
    ).scalars().all()

    cfs = {u.codice_fiscale.strip().upper() for u in utenze if u.codice_fiscale and u.codice_fiscale.strip()}
    intestatari_by_cf = _load_intestatari_by_cf(db, cfs)
    intestatari: list[CatIntestatarioResponse] = [
        CatIntestatarioResponse.model_validate(i) for i in intestatari_by_cf.values()
    ]

    anomalie_count = db.execute(
        select(func.count())
        .select_from(CatAnomalia)
        .join(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id)
        .where(CatUtenzaIrrigua.particella_id == p.id)
    ).scalar_one()

    anomalie_types = db.execute(
        select(CatAnomalia.tipo, func.count())
        .select_from(CatAnomalia)
        .join(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id)
        .where(CatUtenzaIrrigua.particella_id == p.id)
        .group_by(CatAnomalia.tipo)
        .order_by(desc(func.count()))
        .limit(5)
    ).all()

    return CatAnagraficaMatch(
        particella_id=p.id,
        comune=p.nome_comune,
        comune_id=p.comune_id,
        cod_comune_capacitas=p.cod_comune_capacitas,
        codice_catastale=p.codice_catastale,
        foglio=p.foglio,
        particella=p.particella,
        subalterno=p.subalterno,
        num_distretto=p.num_distretto,
        nome_distretto=p.nome_distretto,
        superficie_mq=p.superficie_mq,
        utenza_latest=_utenza_summary_from_record(latest_utenza),
        intestatari=intestatari,
        anomalie_count=int(anomalie_count or 0),
        anomalie_top=[{"tipo": t, "count": int(c or 0)} for (t, c) in anomalie_types],
    )


@router.get("/search", response_model=CatAnagraficaSearchResponse)
def search_anagrafica(
    foglio: str = Query(..., min_length=1),
    particella: str = Query(..., min_length=1),
    comune: str | None = Query(None, description="Codice comune Capacitas oppure nome comune (case-insensitive)."),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatAnagraficaSearchResponse:
    comune_norm = _norm_str(comune)
    foglio_norm = _norm_str(foglio) or ""
    particella_norm = _norm_str(particella) or ""

    query = (
        select(CatParticella)
        .where(
            CatParticella.is_current.is_(True),
            CatParticella.foglio == foglio_norm,
            CatParticella.particella == particella_norm,
        )
        .order_by(CatParticella.cod_comune_capacitas, CatParticella.foglio, CatParticella.particella)
    )

    if comune_norm:
        if _looks_like_int(comune_norm):
            query = query.where(CatParticella.cod_comune_capacitas == int(comune_norm))
        else:
            query = query.where(func.lower(func.coalesce(CatParticella.nome_comune, "")) == comune_norm.lower())

    items = db.execute(query.limit(50)).scalars().all()
    matches = [_build_match(db, p) for p in items]
    return CatAnagraficaSearchResponse(matches=matches)


@router.post("/bulk-search", response_model=CatAnagraficaBulkSearchResponse)
def bulk_search_anagrafica(
    payload: CatAnagraficaBulkSearchRequest = Body(...),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatAnagraficaBulkSearchResponse:
    results: list[CatAnagraficaBulkSearchRowResult] = []

    for row in payload.rows:
        comune_norm = _norm_str(row.comune)
        foglio_norm = _norm_str(row.foglio)
        particella_norm = _norm_str(row.particella)

        if not foglio_norm or not particella_norm:
            results.append(
                CatAnagraficaBulkSearchRowResult(
                    row_index=row.row_index,
                    comune_input=row.comune,
                    foglio_input=row.foglio,
                    particella_input=row.particella,
                    esito="INVALID_ROW",
                    message="Campi obbligatori mancanti (foglio/particella).",
                )
            )
            continue

        query = (
            select(CatParticella)
            .where(
                CatParticella.is_current.is_(True),
                CatParticella.foglio == foglio_norm,
                CatParticella.particella == particella_norm,
            )
            .order_by(CatParticella.cod_comune_capacitas, CatParticella.foglio, CatParticella.particella)
        )
        if comune_norm:
            if _looks_like_int(comune_norm):
                query = query.where(CatParticella.cod_comune_capacitas == int(comune_norm))
            else:
                query = query.where(func.lower(func.coalesce(CatParticella.nome_comune, "")) == comune_norm.lower())

        try:
            items = db.execute(query.limit(50)).scalars().all()
            if len(items) == 0:
                results.append(
                    CatAnagraficaBulkSearchRowResult(
                        row_index=row.row_index,
                        comune_input=row.comune,
                        foglio_input=row.foglio,
                        particella_input=row.particella,
                        esito="NOT_FOUND",
                        message="Nessuna particella trovata.",
                    )
                )
                continue

            if len(items) > 1:
                first = items[0]
                results.append(
                    CatAnagraficaBulkSearchRowResult(
                        row_index=row.row_index,
                        comune_input=row.comune,
                        foglio_input=row.foglio,
                        particella_input=row.particella,
                        esito="MULTIPLE_MATCHES",
                        message=f"Trovate {len(items)} particelle. Specifica meglio il comune.",
                        particella_id=first.id,
                        match=_build_match(db, first),
                        matches_count=len(items),
                    )
                )
                continue

            match = _build_match(db, items[0])
            results.append(
                CatAnagraficaBulkSearchRowResult(
                    row_index=row.row_index,
                    comune_input=row.comune,
                    foglio_input=row.foglio,
                    particella_input=row.particella,
                    esito="FOUND",
                    message="OK",
                    particella_id=match.particella_id,
                    match=match,
                    matches_count=1,
                )
            )
        except Exception as exc:
            results.append(
                CatAnagraficaBulkSearchRowResult(
                    row_index=row.row_index,
                    comune_input=row.comune,
                    foglio_input=row.foglio,
                    particella_input=row.particella,
                    esito="ERROR",
                    message=str(exc),
                )
            )

    return CatAnagraficaBulkSearchResponse(results=results)
