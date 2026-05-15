"""Routes per consultazione avvisi, particelle e statistiche."""
from __future__ import annotations

import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_module
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoParcel
from app.modules.ruolo import repositories as repo
from app.modules.ruolo.models import RuoloAvviso, RuoloPartita, RuoloParticella
from app.modules.ruolo.schemas import (
    CatastoParcelResponse,
    RuoloAvvisoDetailResponse,
    RuoloAvvisoListItemResponse,
    RuoloAvvisoListResponse,
    RuoloParticellaResponse,
    RuoloPartitaResponse,
    RuoloStatsByAnnoResponse,
    RuoloStatsComuneItem,
    RuoloStatsComuneResponse,
    RuoloStatsResponse,
)

router = APIRouter(tags=["ruolo-query"])


def _avviso_to_list_item(avviso: RuoloAvviso, display_name: str | None, is_linked: bool) -> RuoloAvvisoListItemResponse:
    return RuoloAvvisoListItemResponse(
        id=str(avviso.id),
        codice_cnc=avviso.codice_cnc,
        anno_tributario=avviso.anno_tributario,
        subject_id=str(avviso.subject_id) if avviso.subject_id else None,
        codice_fiscale_raw=avviso.codice_fiscale_raw,
        nominativo_raw=avviso.nominativo_raw,
        codice_utenza=avviso.codice_utenza,
        importo_totale_0648=avviso.importo_totale_0648,
        importo_totale_0985=avviso.importo_totale_0985,
        importo_totale_0668=avviso.importo_totale_0668,
        importo_totale_euro=avviso.importo_totale_euro,
        display_name=display_name,
        is_linked=is_linked,
        created_at=avviso.created_at,
        updated_at=avviso.updated_at,
    )


def _particella_to_response(p: RuoloParticella) -> RuoloParticellaResponse:
    return RuoloParticellaResponse(
        id=str(p.id),
        partita_id=str(p.partita_id),
        anno_tributario=p.anno_tributario,
        domanda_irrigua=p.domanda_irrigua,
        distretto=p.distretto,
        foglio=p.foglio,
        particella=p.particella,
        subalterno=p.subalterno,
        sup_catastale_are=p.sup_catastale_are,
        sup_catastale_ha=p.sup_catastale_ha,
        sup_irrigata_ha=p.sup_irrigata_ha,
        coltura=p.coltura,
        importo_manut=p.importo_manut,
        importo_irrig=p.importo_irrig,
        importo_ist=p.importo_ist,
        catasto_parcel_id=str(p.catasto_parcel_id) if p.catasto_parcel_id else None,
        created_at=p.created_at,
    )


def _partita_to_response(db: Session, partita: RuoloPartita) -> RuoloPartitaResponse:
    particelle = repo.get_partita_particelle(db, partita.id)
    return RuoloPartitaResponse(
        id=str(partita.id),
        avviso_id=str(partita.avviso_id),
        codice_partita=partita.codice_partita,
        comune_nome=partita.comune_nome,
        comune_codice=partita.comune_codice,
        contribuente_cf=partita.contribuente_cf,
        co_intestati_raw=partita.co_intestati_raw,
        importo_0648=partita.importo_0648,
        importo_0985=partita.importo_0985,
        importo_0668=partita.importo_0668,
        particelle=[_particella_to_response(p) for p in particelle],
        created_at=partita.created_at,
    )


# ---------------------------------------------------------------------------
# Avvisi
# ---------------------------------------------------------------------------

@router.get("/avvisi", response_model=RuoloAvvisoListResponse)
def list_avvisi(
    anno: int | None = None,
    subject_id: str | None = None,
    q: str | None = Query(default=None, min_length=1),
    codice_fiscale: str | None = None,
    comune: str | None = None,
    codice_utenza: str | None = None,
    unlinked: bool = False,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_module("ruolo")),
) -> RuoloAvvisoListResponse:
    results, total = repo.list_avvisi(
        db,
        anno=anno,
        subject_id=subject_id,
        q=q,
        codice_fiscale=codice_fiscale,
        comune=comune,
        codice_utenza=codice_utenza,
        unlinked=unlinked,
        page=page,
        page_size=page_size,
    )
    items = [
        _avviso_to_list_item(r["avviso"], r["display_name"], r["is_linked"])
        for r in results
    ]
    return RuoloAvvisoListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/avvisi/export")
def export_avvisi_csv(
    anno: int | None = None,
    subject_id: str | None = None,
    q: str | None = Query(default=None, min_length=1),
    codice_fiscale: str | None = None,
    comune: str | None = None,
    codice_utenza: str | None = None,
    unlinked: bool = False,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_module("ruolo")),
) -> Response:
    """Export CSV degli avvisi con gli stessi filtri della lista."""
    results, _ = repo.list_avvisi(
        db,
        anno=anno,
        subject_id=subject_id,
        q=q,
        codice_fiscale=codice_fiscale,
        comune=comune,
        codice_utenza=codice_utenza,
        unlinked=unlinked,
        page=1,
        page_size=100_000,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "CF/PIVA", "Nominativo", "Anno", "Codice CNC", "Codice Utenza",
        "Importo 0648", "Importo 0985", "Importo 0668", "Importo Totale",
        "Soggetto Collegato",
    ])
    for r in results:
        avviso = r["avviso"]
        writer.writerow([
            avviso.codice_fiscale_raw,
            avviso.nominativo_raw,
            avviso.anno_tributario,
            avviso.codice_cnc,
            avviso.codice_utenza,
            avviso.importo_totale_0648,
            avviso.importo_totale_0985,
            avviso.importo_totale_0668,
            avviso.importo_totale_euro,
            "Si" if r["is_linked"] else "No",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="avvisi_ruolo.csv"'},
    )


@router.get("/avvisi/{avviso_id}", response_model=RuoloAvvisoDetailResponse)
def get_avviso(
    avviso_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_module("ruolo")),
) -> RuoloAvvisoDetailResponse:
    avviso = repo.get_avviso(db, avviso_id)
    if avviso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avviso non trovato")

    partite_db = repo.get_avviso_partite(db, avviso_id)
    partite = [_partita_to_response(db, p) for p in partite_db]
    display_name = repo._get_subject_display_name(db, avviso.subject_id)

    return RuoloAvvisoDetailResponse(
        id=str(avviso.id),
        import_job_id=str(avviso.import_job_id),
        codice_cnc=avviso.codice_cnc,
        anno_tributario=avviso.anno_tributario,
        subject_id=str(avviso.subject_id) if avviso.subject_id else None,
        codice_fiscale_raw=avviso.codice_fiscale_raw,
        nominativo_raw=avviso.nominativo_raw,
        domicilio_raw=avviso.domicilio_raw,
        residenza_raw=avviso.residenza_raw,
        n2_extra_raw=avviso.n2_extra_raw,
        codice_utenza=avviso.codice_utenza,
        importo_totale_0648=avviso.importo_totale_0648,
        importo_totale_0985=avviso.importo_totale_0985,
        importo_totale_0668=avviso.importo_totale_0668,
        importo_totale_euro=avviso.importo_totale_euro,
        importo_totale_lire=avviso.importo_totale_lire,
        n4_campo_sconosciuto=avviso.n4_campo_sconosciuto,
        partite=partite,
        display_name=display_name,
        created_at=avviso.created_at,
        updated_at=avviso.updated_at,
    )


@router.get("/soggetti/{subject_id}/avvisi", response_model=list[RuoloAvvisoListItemResponse])
def get_avvisi_by_subject(
    subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_module("ruolo")),
) -> list[RuoloAvvisoListItemResponse]:
    avvisi = repo.list_avvisi_by_subject(db, subject_id)
    display_name = repo._get_subject_display_name(db, subject_id)
    return [
        _avviso_to_list_item(a, display_name, True)
        for a in avvisi
    ]


# ---------------------------------------------------------------------------
# Particelle
# ---------------------------------------------------------------------------

@router.get("/particelle", response_model=list[RuoloParticellaResponse])
def search_particelle(
    anno: int | None = None,
    foglio: str | None = None,
    particella: str | None = None,
    comune: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_module("ruolo")),
) -> list[RuoloParticellaResponse]:
    items, _ = repo.search_particelle(
        db, anno=anno, foglio=foglio, particella=particella, comune=comune,
        page=page, page_size=page_size,
    )
    return [_particella_to_response(p) for p in items]


# ---------------------------------------------------------------------------
# Statistiche
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=RuoloStatsResponse)
def get_stats(
    anno: int | None = None,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_module("ruolo")),
) -> RuoloStatsResponse:
    data = repo.get_stats(db, anno=anno)
    items = [
        RuoloStatsByAnnoResponse(
            anno_tributario=d["anno_tributario"],
            total_avvisi=d["total_avvisi"],
            avvisi_collegati=d["avvisi_collegati"],
            avvisi_non_collegati=d["avvisi_non_collegati"],
            totale_0648=d["totale_0648"],
            totale_0985=d["totale_0985"],
            totale_0668=d["totale_0668"],
            totale_euro=d["totale_euro"],
        )
        for d in data
    ]
    return RuoloStatsResponse(items=items)


@router.get("/stats/comuni", response_model=RuoloStatsComuneResponse)
def get_stats_comuni(
    anno: int,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_module("ruolo")),
) -> RuoloStatsComuneResponse:
    data = repo.get_stats_comuni(db, anno=anno)
    items = [
        RuoloStatsComuneItem(
            comune_nome=d["comune_nome"],
            anno_tributario=d["anno_tributario"],
            totale_0648=d["totale_0648"],
            totale_0985=d["totale_0985"],
            totale_0668=d["totale_0668"],
            totale_euro=d["totale_euro"],
            num_avvisi=d["num_avvisi"],
        )
        for d in data
    ]
    return RuoloStatsComuneResponse(anno_tributario=anno, items=items)


# ---------------------------------------------------------------------------
# Catasto Parcels (prefisso /catasto in router esterno)
# ---------------------------------------------------------------------------

catasto_router = APIRouter(tags=["catasto-parcels"])


@catasto_router.get("/parcels", response_model=list[CatastoParcelResponse])
def list_catasto_parcels(
    comune_codice: str | None = None,
    foglio: str | None = None,
    particella: str | None = None,
    active_only: bool = False,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_module("ruolo")),
) -> list[CatastoParcelResponse]:
    items, _ = repo.list_catasto_parcels(
        db,
        comune_codice=comune_codice,
        foglio=foglio,
        particella=particella,
        active_only=active_only,
        page=page,
        page_size=page_size,
    )
    return [CatastoParcelResponse.model_validate(p) for p in items]


@catasto_router.get("/parcels/{parcel_id}/history", response_model=list[CatastoParcelResponse])
def get_parcel_history(
    parcel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_module("ruolo")),
) -> list[CatastoParcelResponse]:
    parcel = db.get(CatastoParcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcella non trovata")
    history = repo.get_catasto_parcel_history(
        db,
        comune_codice=parcel.comune_codice,
        foglio=parcel.foglio,
        particella=parcel.particella,
        subalterno=parcel.subalterno,
    )
    return [CatastoParcelResponse.model_validate(p) for p in history]
