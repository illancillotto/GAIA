from __future__ import annotations

import json
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, exists, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import (
    CatAnomalia,
    CatCapacitasCertificato,
    CatComune,
    CatConsorzioUnit,
    CatParticella,
    CatParticellaHistory,
    CatUtenzaIntestatario,
    CatUtenzaIrrigua,
)
from app.modules.elaborazioni.capacitas.client import InVoltureClient
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
from app.services.elaborazioni_capacitas import mark_credential_error, mark_credential_used, pick_credential
from app.services.elaborazioni_capacitas_particelle_sync import sync_single_particella
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaPersonSnapshot
from app.schemas.catasto_phase1 import (
    CatAnomaliaResponse,
    CatParticellaCapacitasSyncInput,
    CatParticellaCapacitasSyncResponse,
    CatConsorzioOccupancyResponse,
    CatConsorzioUnitSummaryResponse,
    CatParticellaDetailResponse,
    CatParticellaConsorzioResponse,
    CatParticellaHistoryResponse,
    CatParticellaResponse,
    CatUtenzaIntestatarioResponse,
    CatUtenzaIrriguaResponse,
)
from app.modules.utenze.schemas import AnagraficaPersonResponse, AnagraficaPersonSnapshotResponse
from app.modules.ruolo.models import RuoloParticella

router = APIRouter(prefix="/catasto/particelle", tags=["catasto-particelle"])


def _normalize_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.replace(" ", "").strip().upper()
    return normalized or None


_ZERO_SHARE_TITLE_RE = re.compile(r"\b0\s*/\s*0\b")


def _is_visible_owner_title(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip()
    if not normalized:
        return True
    return _ZERO_SHARE_TITLE_RE.search(normalized) is None


def _build_subject_display_name(
    person: AnagraficaPerson | None = None,
    company: AnagraficaCompany | None = None,
) -> str | None:
    if person is not None:
        value = " ".join(part for part in [person.cognome, person.nome] if part and part.strip()).strip()
        return value or person.codice_fiscale
    if company is not None:
        return company.ragione_sociale or company.partita_iva or company.codice_fiscale
    return None


def _resolve_subject_preview_by_identifier_map(
    db: Session,
    utenze: list[CatUtenzaIrrigua],
) -> dict[str, tuple[UUID, str] | None]:
    identifiers = {
        normalized
        for utenza in utenze
        for normalized in [_normalize_identifier(utenza.codice_fiscale)]
        if normalized is not None
    }
    if not identifiers:
        return {}

    subject_map: dict[str, set[tuple[UUID, str]]] = {identifier: set() for identifier in identifiers}

    person_rows = db.execute(
        select(AnagraficaPerson)
        .where(func.upper(func.replace(AnagraficaPerson.codice_fiscale, " ", "")).in_(identifiers))
    ).scalars().all()
    for person in person_rows:
        identifier = _normalize_identifier(person.codice_fiscale)
        if identifier is None:
            continue
        subject_map.setdefault(identifier, set()).add(
            (person.subject_id, _build_subject_display_name(person=person) or str(person.subject_id))
        )

    company_rows = db.execute(
        select(AnagraficaCompany).where(
            or_(
                func.upper(func.replace(func.coalesce(AnagraficaCompany.partita_iva, ""), " ", "")).in_(identifiers),
                func.upper(func.replace(func.coalesce(AnagraficaCompany.codice_fiscale, ""), " ", "")).in_(identifiers),
            )
        )
    ).scalars().all()
    for company in company_rows:
        for raw_identifier in [company.partita_iva, company.codice_fiscale]:
            identifier = _normalize_identifier(raw_identifier)
            if identifier is None or identifier not in identifiers:
                continue
            subject_map.setdefault(identifier, set()).add(
                (company.subject_id, _build_subject_display_name(company=company) or str(company.subject_id))
            )

    resolved: dict[str, tuple[UUID, str] | None] = {}
    for identifier, matches in subject_map.items():
        resolved[identifier] = next(iter(matches)) if len(matches) == 1 else None
    return resolved


def _with_ruolo_year_filter(query, anno_tributario: int):
    return query.where(
        exists(
            select(RuoloParticella.id).where(
                RuoloParticella.catasto_parcel_id == CatParticella.id,
                RuoloParticella.anno_tributario == anno_tributario,
            )
        )
    )


def _with_anagrafica_filter(query):
    return query.where(
        exists(select(CatUtenzaIrrigua.id).where(CatUtenzaIrrigua.particella_id == CatParticella.id))
    )


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
    search: str | None = Query(
        None,
        description="Ricerca parziale unificata su CF/P.IVA/intestatario (case-insensitive).",
    ),
    cf: str | None = Query(None),
    intestatario: str | None = Query(None, description="Ricerca parziale sulla denominazione utenza (case-insensitive)."),
    ha_anomalie: bool | None = Query(None),
    solo_con_anagrafica: bool = Query(
        False,
        description="Se true, mostra solo particelle con almeno una anagrafica collegata; per ricerche puntuali foglio/particella la riga resta visibile anche se senza anagrafica.",
    ),
    solo_a_ruolo: bool = Query(False, description="Se true, mostra solo particelle collegate ad almeno una riga ruolo."),
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
    if anno is not None or search or cf or intestatario or ha_anomalie is not None:
        utenze_filters: list = [CatUtenzaIrrigua.particella_id == CatParticella.id]
        if anno is not None:
            utenze_filters.append(CatUtenzaIrrigua.anno_campagna == anno)
        if search:
            search_term = f"%{search.strip()}%"
            utenze_filters.append(
                or_(
                    CatUtenzaIrrigua.codice_fiscale.ilike(search_term),
                    CatUtenzaIrrigua.denominazione.ilike(search_term),
                    exists(
                        select(CatUtenzaIntestatario.id).where(
                            CatUtenzaIntestatario.utenza_id == CatUtenzaIrrigua.id,
                            or_(
                                CatUtenzaIntestatario.codice_fiscale.ilike(search_term),
                                CatUtenzaIntestatario.partita_iva.ilike(search_term),
                                CatUtenzaIntestatario.denominazione.ilike(search_term),
                            ),
                        )
                    ),
                )
            )
        if cf:
            cf_norm = cf.strip().upper()
            utenze_filters.append(
                or_(
                    CatUtenzaIrrigua.codice_fiscale == cf_norm,
                    exists(
                        select(CatUtenzaIntestatario.id).where(
                            CatUtenzaIntestatario.utenza_id == CatUtenzaIrrigua.id,
                            or_(
                                CatUtenzaIntestatario.codice_fiscale == cf_norm,
                                CatUtenzaIntestatario.partita_iva == cf_norm,
                            ),
                        )
                    ),
                )
            )
        if intestatario:
            intestatario_term = f"%{intestatario.strip()}%"
            utenze_filters.append(
                or_(
                    CatUtenzaIrrigua.denominazione.ilike(intestatario_term),
                    exists(
                        select(CatUtenzaIntestatario.id).where(
                            CatUtenzaIntestatario.utenza_id == CatUtenzaIrrigua.id,
                            CatUtenzaIntestatario.denominazione.ilike(intestatario_term),
                        )
                    ),
                )
            )
        if ha_anomalie is True:
            utenze_filters.append(
                exists(select(CatAnomalia.id).where(CatAnomalia.utenza_id == CatUtenzaIrrigua.id))
            )
        if ha_anomalie is False:
            utenze_filters.append(
                ~exists(select(CatAnomalia.id).where(CatAnomalia.utenza_id == CatUtenzaIrrigua.id))
            )
        query = query.where(exists(select(CatUtenzaIrrigua.id).where(*utenze_filters)))

    def _load_items(source_query):
        if not solo_a_ruolo:
            return list(db.execute(source_query.limit(limit)).scalars().all())

        latest_ruolo_year = db.scalar(select(func.max(RuoloParticella.anno_tributario)))
        if latest_ruolo_year is None:
            return []

        items = list(
            db.execute(_with_ruolo_year_filter(source_query, int(latest_ruolo_year)).limit(limit)).scalars().all()
        )
        if not items:
            fallback_year = int(latest_ruolo_year) - 1
            items = list(db.execute(_with_ruolo_year_filter(source_query, fallback_year).limit(limit)).scalars().all())
        return items

    direct_particella_lookup = bool((foglio or "").strip() and (particella or "").strip())
    effective_query = _with_anagrafica_filter(query) if solo_con_anagrafica else query
    items = _load_items(effective_query)
    if not items and solo_con_anagrafica and direct_particella_lookup:
        items = _load_items(query)

    if not items:
        return []

    particella_ids = [p.id for p in items]
    anagrafica_ids = set(
        db.execute(select(CatUtenzaIrrigua.particella_id).where(CatUtenzaIrrigua.particella_id.in_(particella_ids))).scalars().all()
    )
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
        r.ha_anagrafica = p.id in anagrafica_ids
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


@router.post("/{particella_id}/capacitas-sync", response_model=CatParticellaCapacitasSyncResponse)
async def sync_particella_capacitas(
    particella_id: UUID,
    body: CatParticellaCapacitasSyncInput,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_active_user),
) -> CatParticellaCapacitasSyncResponse:
    item = db.get(CatParticella, particella_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Particella not found")

    try:
        credential, password = pick_credential(db, body.credential_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    manager = CapacitasSessionManager(credential.username, password)
    try:
        await manager.login()
        await manager.activate_app("involture")
        client = InVoltureClient(manager)
        job, item_result, refreshed = await sync_single_particella(
            db,
            client,
            particella_id=particella_id,
            requested_by_user_id=current_user.id,
            credential_id=credential.id,
            fetch_certificati=body.fetch_certificati,
            fetch_details=body.fetch_details,
        )
        mark_credential_used(db, credential.id)
        payload = CatParticellaDetailResponse.model_validate(refreshed)
        payload.fuori_distretto = refreshed.fuori_distretto
        return CatParticellaCapacitasSyncResponse(
            particella=payload,
            status=str(item_result.get("status") or refreshed.capacitas_last_sync_status or "failed"),
            message=str(item_result.get("message") or "Sync completata."),
            job_id=job.id,
        )
    except Exception as exc:
        db.rollback()
        mark_credential_error(db, credential.id, str(exc))
        raise HTTPException(status_code=502, detail=f"Errore sync particella Capacitas: {exc}") from exc
    finally:
        await manager.close()


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
        utenza_ids = [occ.utenza_id for occ in unit.occupancies if occ.utenza_id]
        intestatari_proprietari: list[CatUtenzaIntestatarioResponse] = []
        if utenza_ids:
            intestatari_rows = (
                db.execute(
                    select(CatUtenzaIntestatario)
                    .where(CatUtenzaIntestatario.utenza_id.in_(utenza_ids))
                    .order_by(desc(CatUtenzaIntestatario.data_agg), CatUtenzaIntestatario.denominazione.asc())
                )
                .scalars()
                .all()
            )
            for row in intestatari_rows:
                if not _is_visible_owner_title(row.titoli):
                    continue
                person = db.get(AnagraficaPerson, row.subject_id) if row.subject_id else None
                person_snapshots = []
                if row.subject_id:
                    person_snapshots = (
                        db.execute(
                            select(AnagraficaPersonSnapshot)
                            .where(AnagraficaPersonSnapshot.subject_id == row.subject_id)
                            .order_by(desc(AnagraficaPersonSnapshot.collected_at))
                            .limit(10)
                        )
                        .scalars()
                        .all()
                    )
                base_owner = CatUtenzaIntestatarioResponse.model_validate(row).model_dump(
                    exclude={"person", "person_snapshots"}
                )
                intestatari_proprietari.append(
                    CatUtenzaIntestatarioResponse(
                        **base_owner,
                        person=(
                            AnagraficaPersonResponse.model_validate(
                                {
                                    "subject_id": str(person.subject_id),
                                    "cognome": person.cognome,
                                    "nome": person.nome,
                                    "codice_fiscale": person.codice_fiscale,
                                    "data_nascita": person.data_nascita,
                                    "comune_nascita": person.comune_nascita,
                                    "indirizzo": person.indirizzo,
                                    "comune_residenza": person.comune_residenza,
                                    "cap": person.cap,
                                    "email": person.email,
                                    "telefono": person.telefono,
                                    "note": person.note,
                                    "created_at": person.created_at,
                                    "updated_at": person.updated_at,
                                }
                            )
                            if person
                            else None
                        ),
                        person_snapshots=[
                            AnagraficaPersonSnapshotResponse.model_validate(
                                {
                                    "id": str(snapshot.id),
                                    "subject_id": str(snapshot.subject_id),
                                    "is_capacitas_history": snapshot.is_capacitas_history,
                                    "source_system": snapshot.source_system,
                                    "source_ref": snapshot.source_ref,
                                    "cognome": snapshot.cognome,
                                    "nome": snapshot.nome,
                                    "codice_fiscale": snapshot.codice_fiscale,
                                    "data_nascita": snapshot.data_nascita,
                                    "comune_nascita": snapshot.comune_nascita,
                                    "indirizzo": snapshot.indirizzo,
                                    "comune_residenza": snapshot.comune_residenza,
                                    "cap": snapshot.cap,
                                    "email": snapshot.email,
                                    "telefono": snapshot.telefono,
                                    "note": snapshot.note,
                                    "valid_from": snapshot.valid_from,
                                    "collected_at": snapshot.collected_at,
                                }
                            )
                            for snapshot in person_snapshots
                        ],
                    )
                )
        base_payload = CatConsorzioUnitSummaryResponse.model_validate(unit).model_dump(
            exclude={"comune_label", "source_comune_resolved_label", "occupancies", "intestatari_proprietari"}
        )
        payload_units.append(
            CatConsorzioUnitSummaryResponse(
                **base_payload,
                comune_label=comune_record.nome_comune if comune_record else None,
                source_comune_resolved_label=source_comune_record.nome_comune if source_comune_record else None,
                occupancies=[CatConsorzioOccupancyResponse.model_validate(occ) for occ in unit.occupancies],
                intestatari_proprietari=intestatari_proprietari,
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
    utenze = list(
        db.execute(select(CatUtenzaIrrigua).where(*filters).order_by(desc(CatUtenzaIrrigua.anno_campagna))).scalars().all()
    )
    subject_preview_map = _resolve_subject_preview_by_identifier_map(db, utenze)
    response_items: list[CatUtenzaIrriguaResponse] = []
    for utenza in utenze:
        preview = subject_preview_map.get(_normalize_identifier(utenza.codice_fiscale))
        response_items.append(
            CatUtenzaIrriguaResponse.model_validate(utenza).model_copy(
                update={
                    "subject_id": preview[0] if preview is not None else None,
                    "subject_display_name": preview[1] if preview is not None else None,
                }
            )
        )
    return response_items


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
