from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatDistretto, CatParticella, CatParticellaHistory
from app.modules.catasto.services.indici_overview import (
    build_ruolo_excluded_particelle,
    get_indici_overview_cached,
    resolve_anno_riferimento,
)
from app.schemas.catasto_phase1 import (
    CatIndiceOverviewResponse,
    CatIndiceRuoloAssignDistrettoRequest,
    CatIndiceRuoloAssignDistrettoResponse,
    CatIndiceRuoloExcludedParticelleResponse,
)

router = APIRouter(prefix="/catasto/indici", tags=["catasto-indici"])


@router.get("/overview", response_model=CatIndiceOverviewResponse)
def get_indici_overview(
    anno: int | None = Query(None),
    refresh: bool = Query(False, description="Forza il ricalcolo della snapshot annuale."),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatIndiceOverviewResponse:
    return get_indici_overview_cached(db, anno=anno, refresh=refresh)


@router.get("/ruolo-esclusi", response_model=CatIndiceRuoloExcludedParticelleResponse)
def get_indici_ruolo_esclusi(
    anno: int | None = Query(None),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatIndiceRuoloExcludedParticelleResponse:
    return build_ruolo_excluded_particelle(db, resolve_anno_riferimento(db, anno))


@router.post("/ruolo-esclusi/assegna-distretto", response_model=CatIndiceRuoloAssignDistrettoResponse)
def assign_distretto_to_ruolo_excluded_particella(
    payload: CatIndiceRuoloAssignDistrettoRequest,
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatIndiceRuoloAssignDistrettoResponse:
    particella = db.get(CatParticella, payload.cat_particella_id)
    if particella is None:
        raise HTTPException(status_code=404, detail="Particella catastale non trovata")
    if not particella.is_current:
        raise HTTPException(status_code=409, detail="La particella catastale non è corrente")

    distretto = db.get(CatDistretto, payload.distretto_id)
    if distretto is None:
        raise HTTPException(status_code=404, detail="Distretto non trovato")
    if not distretto.attivo:
        raise HTTPException(status_code=409, detail="Il distretto selezionato non è attivo")

    updated = particella.num_distretto != distretto.num_distretto or particella.nome_distretto != distretto.nome_distretto
    if updated:
        from datetime import date

        db.add(
            CatParticellaHistory(
                particella_id=particella.id,
                comune_id=particella.comune_id,
                national_code=particella.national_code,
                cod_comune_capacitas=particella.cod_comune_capacitas,
                codice_catastale=particella.codice_catastale,
                foglio=particella.foglio,
                particella=particella.particella,
                subalterno=particella.subalterno,
                superficie_mq=particella.superficie_mq,
                superficie_grafica_mq=particella.superficie_grafica_mq,
                num_distretto=particella.num_distretto,
                geometry=particella.geometry,
                valid_from=particella.valid_from,
                valid_to=date.today(),
                change_reason=(payload.note or "correzione_distretto_da_indici_ruolo_esclusi")[:255],
            )
        )
        particella.num_distretto = distretto.num_distretto
        particella.nome_distretto = distretto.nome_distretto
        db.commit()
    return CatIndiceRuoloAssignDistrettoResponse(
        cat_particella_id=particella.id,
        num_distretto=distretto.num_distretto,
        nome_distretto=distretto.nome_distretto,
        updated=updated,
    )
