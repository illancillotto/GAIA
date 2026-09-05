from __future__ import annotations

import logging
import os
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import (
    CatCapacitasCertificato,
    CatCapacitasIntestatario,
    CatCapacitasTerrenoRow,
    CatConsorzioOccupancy,
    CatConsorzioUnit,
    CatParticella,
    CatUtenzaIntestatario,
    CatUtenzaIrrigua,
)
from app.modules.catasto.routes.anagrafica.normalization import (
    _build_denominazione,
    _norm_str,
    _normalize_ccs,
    _normalize_cf,
    _normalize_com,
    _normalize_fra,
    _normalize_pvc,
)
from app.modules.catasto.routes.anagrafica.persons import (
    _person_response_from_db,
    _split_denominazione,
)
from app.modules.utenze.models import (
    AnagraficaPerson,
    AnagraficaSubject,
)
from app.schemas.catasto_phase1 import (
    CatAnagraficaUtenzaSummary,
    CatIntestatarioResponse,
)

router = APIRouter(
    prefix="/catasto/elaborazioni-massive/particelle", tags=["catasto-elaborazioni-massive"]
)
logger = logging.getLogger(__name__)
CATASTO_DISTRETTO_EXPORT_STORAGE_PATH = Path(
    os.getenv("CATASTO_DISTRETTO_EXPORT_STORAGE_PATH", "/data/catasto/exports/distretti")
)


# fmt: off

def _load_intestatari_by_cf(db: Session, cfs: set[str]) -> dict[str, CatIntestatarioResponse]:
    if not cfs:
        return {}
    rows = db.execute(
        select(AnagraficaPerson, AnagraficaSubject)
        .join(AnagraficaSubject, AnagraficaSubject.id == AnagraficaPerson.subject_id)
        .where(AnagraficaPerson.codice_fiscale.in_(sorted(cfs)))
    ).all()
    items: dict[str, CatIntestatarioResponse] = {}
    for person, subject in rows:
        if not person.codice_fiscale:
            continue
        items[person.codice_fiscale] = CatIntestatarioResponse(
            id=person.subject_id,
            codice_fiscale=person.codice_fiscale,
            denominazione=_build_denominazione(person.cognome, person.nome),
            tipo="PF",
            cognome=person.cognome,
            nome=person.nome,
            data_nascita=person.data_nascita,
            luogo_nascita=person.comune_nascita,
            indirizzo=person.indirizzo,
            comune_residenza=person.comune_residenza,
            cap=person.cap,
            email=person.email,
            telefono=person.telefono,
            ragione_sociale=None,
            source=subject.source_system,
            last_verified_at=person.updated_at,
            deceduto=None,
        )
    return items


def _intestatario_response_from_utenza_row(
    db: Session,
    row: CatUtenzaIntestatario,
) -> CatIntestatarioResponse:
    if row.subject_id is not None:
        subject = db.get(AnagraficaSubject, row.subject_id)
        person = db.get(AnagraficaPerson, row.subject_id)
        if subject is not None and person is not None:
            return _person_response_from_db(person, subject, deceduto=row.deceduto)

    cognome, nome = _split_denominazione(row.denominazione)
    codice_fiscale = _normalize_cf(row.codice_fiscale) or ""
    return CatIntestatarioResponse(
        id=row.subject_id or row.id,
        codice_fiscale=codice_fiscale,
        denominazione=row.denominazione,
        tipo="PF" if len(codice_fiscale) == 16 else "PG" if codice_fiscale else None,
        cognome=cognome if codice_fiscale else None,
        nome=nome if codice_fiscale else None,
        data_nascita=row.data_nascita,
        luogo_nascita=row.luogo_nascita,
        indirizzo=row.residenza,
        comune_residenza=row.comune_residenza,
        cap=row.cap,
        email=None,
        telefono=None,
        ragione_sociale=row.denominazione if codice_fiscale and len(codice_fiscale) != 16 else None,
        source="capacitas",
        last_verified_at=row.data_agg or row.collected_at,
        deceduto=row.deceduto,
    )


def _intestatario_response_from_utenza_record(row: CatUtenzaIrrigua) -> CatIntestatarioResponse | None:
    codice_fiscale = _normalize_cf(row.codice_fiscale) or ""
    denominazione = _norm_str(row.denominazione)
    if not codice_fiscale and not denominazione:
        return None

    cognome: str | None = None
    nome: str | None = None
    ragione_sociale: str | None = None
    tipo: str | None = None
    if codice_fiscale:
        if len(codice_fiscale) == 16:
            tipo = "PF"
            cognome, nome = _split_denominazione(denominazione)
        else:
            tipo = "PG"
            ragione_sociale = denominazione

    return CatIntestatarioResponse(
        id=row.id,
        codice_fiscale=codice_fiscale,
        denominazione=denominazione,
        tipo=tipo,
        cognome=cognome,
        nome=nome,
        data_nascita=None,
        luogo_nascita=None,
        indirizzo=None,
        comune_residenza=None,
        cap=None,
        email=None,
        telefono=None,
        ragione_sociale=ragione_sociale,
        source="capacitas_import",
        last_verified_at=row.created_at,
        deceduto=None,
    )


def _load_intestatari_by_utenza_ids(
    db: Session, utenza_ids: list[UUID]
) -> list[CatIntestatarioResponse]:
    if not utenza_ids:
        return []

    rows = (
        db.execute(
            select(CatUtenzaIntestatario)
            .where(CatUtenzaIntestatario.utenza_id.in_(utenza_ids))
            .order_by(
                desc(CatUtenzaIntestatario.anno_riferimento),
                desc(CatUtenzaIntestatario.data_agg),
                CatUtenzaIntestatario.denominazione.asc(),
            )
        )
        .scalars()
        .all()
    )

    items: list[CatIntestatarioResponse] = []
    seen: set[str] = set()
    for row in rows:
        key = (
            str(row.subject_id)
            if row.subject_id
            else _normalize_cf(row.codice_fiscale) or row.idxana or str(row.id)
        )
        if key in seen:
            continue
        seen.add(key)
        items.append(_intestatario_response_from_utenza_row(db, row))
    return items


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


def _utenza_summary_from_occupancy(occupancy: CatConsorzioOccupancy | None) -> CatAnagraficaUtenzaSummary | None:
    if occupancy is None or not occupancy.cco:
        return None
    return CatAnagraficaUtenzaSummary(
        id=occupancy.utenza_id or occupancy.id,
        cco=occupancy.cco,
        anno_campagna=occupancy.valid_from.year if occupancy.valid_from else None,
        stato="capacitas_terreni",
        num_distretto=None,
        nome_distretto=None,
        sup_irrigabile_mq=None,
        denominazione=None,
        codice_fiscale=None,
        ha_anomalie=None,
    )


def _intestatario_response_from_capacitas_row(row: CatCapacitasIntestatario) -> CatIntestatarioResponse:
    cognome, nome = _split_denominazione(row.denominazione)
    codice_fiscale = _normalize_cf(row.codice_fiscale) or ""
    return CatIntestatarioResponse(
        id=row.subject_id or row.id,
        codice_fiscale=codice_fiscale,
        denominazione=row.denominazione,
        tipo="PF" if len(codice_fiscale) == 16 else "PG" if codice_fiscale else None,
        cognome=cognome if codice_fiscale else None,
        nome=nome if codice_fiscale else None,
        data_nascita=row.data_nascita,
        luogo_nascita=row.luogo_nascita,
        indirizzo=row.residenza,
        comune_residenza=row.comune_residenza,
        cap=row.cap,
        email=None,
        telefono=None,
        ragione_sociale=row.denominazione if codice_fiscale and len(codice_fiscale) != 16 else None,
        source="capacitas",
        last_verified_at=row.collected_at,
        deceduto=row.deceduto,
    )


def _find_certificato_snapshot(
    db: Session,
    *,
    cco: str,
    com: str | None = None,
    pvc: str | None = None,
    fra: str | None = None,
    ccs: str | None = None,
) -> CatCapacitasCertificato | None:
    if all(value is None for value in (com, pvc, fra, ccs)):
        return None

    query = select(CatCapacitasCertificato).where(CatCapacitasCertificato.cco == cco)

    com_norm = _normalize_com(com)
    pvc_norm = _normalize_pvc(pvc)
    fra_norm = _normalize_fra(fra)
    ccs_norm = _normalize_ccs(ccs) if any(value is not None for value in (com, pvc, fra, ccs)) else None

    if com_norm is not None:
        query = query.where(CatCapacitasCertificato.com == com_norm)
    if pvc_norm is not None:
        query = query.where(CatCapacitasCertificato.pvc == pvc_norm)
    if fra_norm is not None:
        query = query.where(CatCapacitasCertificato.fra == fra_norm)
    query = query.where(func.coalesce(CatCapacitasCertificato.ccs, "00000") == ccs_norm)

    snapshots = db.execute(query.order_by(desc(CatCapacitasCertificato.collected_at))).scalars().all()
    if not snapshots:
        return None
    valid = [snap for snap in snapshots if _is_usable_certificato_snapshot(snap)]
    return valid[0] if valid else snapshots[0]


def _is_usable_certificato_snapshot(snapshot: CatCapacitasCertificato) -> bool:
    payload = snapshot.parsed_json or {}
    if not isinstance(payload, dict):
        return False
    raw_text = str(payload.get("raw_text") or "").casefold()
    if "deadlock" in raw_text or "ripetere la transazione" in raw_text:
        return False
    if payload.get("partita_code") or payload.get("utenza_code"):
        return True
    if payload.get("intestatari") or payload.get("terreni"):
        return True
    return False


def _load_intestatari_from_cert_context(
    db: Session,
    *,
    cco: str,
    com: str | None = None,
    pvc: str | None = None,
    fra: str | None = None,
    ccs: str | None = None,
) -> list[CatIntestatarioResponse]:
    if _is_sentinel_cco(cco):
        return []
    cert = _find_certificato_snapshot(db, cco=cco, com=com, pvc=pvc, fra=fra, ccs=ccs)
    if cert is None:
        return []
    rows = db.execute(
        select(CatCapacitasIntestatario)
        .where(CatCapacitasIntestatario.certificato_id == cert.id)
        .order_by(CatCapacitasIntestatario.denominazione)
    ).scalars().all()
    seen: set[str] = set()
    items: list[CatIntestatarioResponse] = []
    for row in rows:
        key = _normalize_cf(row.codice_fiscale) or row.idxana or str(row.id)
        if key in seen:
            continue
        seen.add(key)
        items.append(_intestatario_response_from_capacitas_row(row))
    if items:
        return items

    payload = cert.parsed_json or {}
    raw_intestatari = payload.get("intestatari") if isinstance(payload, dict) else None
    if not isinstance(raw_intestatari, list):
        return []
    for raw in raw_intestatari:
        if not isinstance(raw, dict):
            continue
        codice_fiscale = _normalize_cf(raw.get("codice_fiscale")) or "UNKNOWN"
        key = codice_fiscale or str(raw.get("idxana") or raw.get("denominazione") or uuid4())
        if key in seen:
            continue
        seen.add(key)
        items.append(
            CatIntestatarioResponse(
                id=uuid4(),
                codice_fiscale=codice_fiscale,
                denominazione=_norm_str(raw.get("denominazione")),
                tipo=_norm_str(raw.get("tipo")),
                cognome=_norm_str(raw.get("cognome")),
                nome=_norm_str(raw.get("nome")),
                data_nascita=None,
                luogo_nascita=_norm_str(raw.get("luogo_nascita")),
                indirizzo=_norm_str(raw.get("indirizzo")),
                comune_residenza=_norm_str(raw.get("comune_residenza")),
                cap=_norm_str(raw.get("cap")),
                email=_norm_str(raw.get("email")),
                telefono=_norm_str(raw.get("telefono")),
                ragione_sociale=_norm_str(raw.get("ragione_sociale")),
                source="capacitas_certificato_snapshot",
                last_verified_at=cert.collected_at,
                deceduto=None,
            )
        )
    return items


def _context_from_occupancy(occupancy: CatConsorzioOccupancy | None) -> tuple[str | None, str | None, str | None, str | None]:
    if occupancy is None:
        return (None, None, None, None)
    return (
        _normalize_com(occupancy.com),
        _normalize_pvc(occupancy.pvc),
        _normalize_fra(occupancy.fra),
        _normalize_ccs(occupancy.ccs),
    )


def _context_from_values(
    com: str | None,
    pvc: str | None,
    fra: str | None,
    ccs: str | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    return (_normalize_com(com), _normalize_pvc(pvc), _normalize_fra(fra), _normalize_ccs(ccs))


def _is_sentinel_cco(cco: str) -> bool:
    """Returns True for Capacitas placeholder CCOs (e.g. 014099999) that are shared
    across many unrelated sub-units and do not carry reliable intestatario data."""
    return cco.endswith("99999")


def _load_cert_status_from_context(
    db: Session,
    *,
    cco: str | None,
    com: str | None = None,
    pvc: str | None = None,
    fra: str | None = None,
    ccs: str | None = None,
) -> tuple[str | None, str | None]:
    cco_norm = _norm_str(cco)
    if not cco_norm:
        return (None, None)
    cert = _find_certificato_snapshot(db, cco=cco_norm, com=com, pvc=pvc, fra=fra, ccs=ccs)
    if cert is None:
        return (None, None)
    return (cert.ruolo_status, cert.utenza_status)


def _best_occupancy_for_unit(db: Session, unit_id: UUID) -> CatConsorzioOccupancy | None:
    """Returns the best occupancy for a unit: current first, then most recent."""
    return db.execute(
        select(CatConsorzioOccupancy)
        .where(CatConsorzioOccupancy.unit_id == unit_id, CatConsorzioOccupancy.cco.is_not(None))
        .order_by(
            desc(CatConsorzioOccupancy.is_current),
            desc(CatConsorzioOccupancy.valid_from),
            desc(CatConsorzioOccupancy.updated_at),
        )
        .limit(1)
    ).scalars().first()


def _particella_unit_match_clause(p: CatParticella):
    return or_(
        CatConsorzioUnit.particella_id == p.id,
        and_(
            CatConsorzioUnit.foglio == p.foglio,
            CatConsorzioUnit.particella == p.particella,
            CatConsorzioUnit.cod_comune_capacitas == p.cod_comune_capacitas,
        ),
    )


def _resolve_particella_cert_context(
    db: Session,
    p: CatParticella,
    cco: str | None,
    latest_utenza: CatUtenzaIrrigua | None,
    latest_occupancy: CatConsorzioOccupancy | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    cco_norm = _norm_str(cco)
    if not cco_norm:
        return (None, None, None, None)
    latest_utenza_com = _normalize_com(latest_utenza.cod_comune_capacitas) if latest_utenza and latest_utenza.cod_comune_capacitas is not None else None
    latest_utenza_fra = _normalize_fra(latest_utenza.cod_frazione) if latest_utenza and latest_utenza.cod_frazione is not None else None

    if latest_occupancy is not None and _norm_str(latest_occupancy.cco) == cco_norm:
        return _context_from_occupancy(latest_occupancy)

    occupancy = (
        db.execute(
            select(CatConsorzioOccupancy)
            .join(CatConsorzioUnit, CatConsorzioUnit.id == CatConsorzioOccupancy.unit_id)
            .where(
                _particella_unit_match_clause(p),
                CatConsorzioOccupancy.cco == cco_norm,
                CatConsorzioOccupancy.com.is_not(None),
            )
            .order_by(
                desc(CatConsorzioOccupancy.is_current),
                desc(CatConsorzioOccupancy.valid_from),
                desc(CatConsorzioOccupancy.updated_at),
            )
            .limit(1)
        )
        .scalars()
        .first()
    )
    if occupancy is not None:
        return _context_from_occupancy(occupancy)

    if latest_utenza is not None:
        cert = _find_certificato_snapshot(db, cco=cco_norm, com=latest_utenza_com, fra=latest_utenza_fra)
        if cert is not None:
            return _context_from_values(cert.com, cert.pvc, cert.fra, cert.ccs)

    if latest_utenza is not None:
        row = (
            db.execute(
                select(CatCapacitasTerrenoRow)
                .join(CatConsorzioUnit, CatConsorzioUnit.id == CatCapacitasTerrenoRow.unit_id)
                .where(
                    _particella_unit_match_clause(p),
                    CatCapacitasTerrenoRow.cco == cco_norm,
                    CatCapacitasTerrenoRow.com.is_not(None),
                )
                .order_by(desc(CatCapacitasTerrenoRow.collected_at))
                .limit(1)
            )
            .scalars()
            .first()
        )
        if row is not None:
            return _context_from_values(row.com, row.pvc, row.fra, row.ccs)

    # Non fidarsi mai di un contesto certificato derivato da solo CCO:
    # il CCO puo essere riusato su comuni/frazioni diversi e produrre link/stati errati.
    return (None, None, None, None)
