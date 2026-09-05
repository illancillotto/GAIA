from __future__ import annotations

import logging
import os
from collections import defaultdict
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import (
    CatAnomalia,
    CatComune,
    CatConsorzioOccupancy,
    CatConsorzioUnit,
    CatParticella,
    CatUtenzaIntestatario,
    CatUtenzaIrrigua,
)
from app.modules.catasto.routes.anagrafica.intestatari import (
    _best_occupancy_for_unit,
    _context_from_occupancy,
    _intestatario_response_from_utenza_record,
    _intestatario_response_from_utenza_row,
    _is_sentinel_cco,
    _load_cert_status_from_context,
    _load_intestatari_by_cf,
    _load_intestatari_by_utenza_ids,
    _load_intestatari_from_cert_context,
    _particella_unit_match_clause,
    _resolve_particella_cert_context,
    _utenza_summary_from_occupancy,
    _utenza_summary_from_record,
)
from app.modules.catasto.routes.anagrafica.normalization import (
    _looks_like_int,
    _norm_str,
    _normalize_cf,
)
from app.modules.catasto.routes.anagrafica.uploads import _load_riordino_fields_for_particella
from app.schemas.catasto_phase1 import (
    CatAnagraficaBulkSearchRowResult,
    CatAnagraficaMatch,
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

def _current_base_match_data(
    db: Session,
    p: CatParticella,
    *,
    live_authoritative: bool = False,
) -> tuple[
    CatAnagraficaUtenzaSummary | None,
    list[CatIntestatarioResponse],
    tuple[str | None, str | None, str | None, str | None],
    tuple[str | None, str | None],
]:
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

    current_occupancy = (
        db.execute(
            select(CatConsorzioOccupancy)
            .join(CatConsorzioUnit, CatConsorzioUnit.id == CatConsorzioOccupancy.unit_id)
            .where(
                CatConsorzioUnit.particella_id == p.id,
                CatConsorzioOccupancy.cco.is_not(None),
                CatConsorzioOccupancy.is_current.is_(True),
            )
            .order_by(desc(CatConsorzioOccupancy.valid_from), desc(CatConsorzioOccupancy.updated_at))
            .limit(1)
        )
        .scalars()
        .first()
    )

    utenza_summary = _utenza_summary_from_record(latest_utenza) or _utenza_summary_from_occupancy(current_occupancy)
    cco = (latest_utenza.cco if latest_utenza is not None else None) or (current_occupancy.cco if current_occupancy is not None else None)
    cert_context = _resolve_particella_cert_context(db, p, cco, latest_utenza, current_occupancy)

    intestatari: list[CatIntestatarioResponse] = []
    if not live_authoritative:
        utenza_ids: list[UUID] = [latest_utenza.id] if latest_utenza is not None else []
        intestatari = _load_intestatari_by_utenza_ids(db, utenza_ids) if utenza_ids else []
        if not intestatari and latest_utenza is not None and latest_utenza.codice_fiscale:
            intestatari_by_cf = _load_intestatari_by_cf(db, {_normalize_cf(latest_utenza.codice_fiscale) or ""})
            intestatari = [item for item in intestatari_by_cf.values()]
        if not intestatari and cco and not _is_sentinel_cco(cco):
            cert_com, cert_pvc, cert_fra, cert_ccs = cert_context
            intestatari = _load_intestatari_from_cert_context(
                db,
                cco=cco,
                com=cert_com,
                pvc=cert_pvc,
                fra=cert_fra,
                ccs=cert_ccs,
            )
        if not intestatari and latest_utenza is not None:
            fallback_owner = _intestatario_response_from_utenza_record(latest_utenza)
            if fallback_owner is not None:
                intestatari = [fallback_owner]

    status_context = (
        _load_cert_status_from_context(
            db,
            cco=cco if all(cert_context[:3]) else None,
            com=cert_context[0],
            pvc=cert_context[1],
            fra=cert_context[2],
            ccs=cert_context[3],
        )
        if not live_authoritative
        else (None, None)
    )

    return utenza_summary, intestatari, cert_context, status_context


def _build_consorzio_sub_matches(db: Session, p: CatParticella, *, live_authoritative: bool = False) -> list[CatAnagraficaMatch]:
    """Returns one CatAnagraficaMatch per sub-level CatConsorzioUnit for the given particella.

    Sub-level units are those with subalterno IS NOT NULL linked to the same
    foglio/particella/comune as the particella but stored separately (particella_id=None).
    """
    if p.cod_comune_capacitas is None:
        return []

    sub_units = db.execute(
        select(CatConsorzioUnit)
        .where(
            CatConsorzioUnit.foglio == p.foglio,
            CatConsorzioUnit.particella == p.particella,
            CatConsorzioUnit.cod_comune_capacitas == p.cod_comune_capacitas,
            CatConsorzioUnit.subalterno.is_not(None),
            CatConsorzioUnit.is_active.is_(True),
        )
        .order_by(CatConsorzioUnit.subalterno)
    ).scalars().all()

    if not sub_units:
        return []

    comune_record = db.get(CatComune, p.comune_id) if p.comune_id else None
    matches: list[CatAnagraficaMatch] = []
    base_utenza_summary, _base_intestatari, base_cert_context, base_status_context = _current_base_match_data(
        db,
        p,
        live_authoritative=live_authoritative,
    )

    for unit in sub_units:
        occupancy = _best_occupancy_for_unit(db, unit.id)
        riordino_code, riordino_maglia, riordino_lotto = _load_riordino_fields_for_particella(db, p, unit.id)
        cco = occupancy.cco if occupancy else None
        is_stale = bool(occupancy and not occupancy.is_current)
        cert_com, cert_pvc, cert_fra, cert_ccs = _context_from_occupancy(occupancy)
        stato_ruolo, stato_cnc = _load_cert_status_from_context(
            db, cco=cco, com=cert_com, pvc=cert_pvc, fra=cert_fra, ccs=cert_ccs
        )
        intestatari: list[CatIntestatarioResponse] = []
        utenza_summary = _utenza_summary_from_occupancy(occupancy) if occupancy else None
        if cco and _is_sentinel_cco(cco):
            note = "CCO provvisorio Capacitas: dati intestatario non disponibili"
        elif cco and not is_stale:
            intestatari = _load_intestatari_from_cert_context(
                db,
                cco=cco,
                com=cert_com,
                pvc=cert_pvc,
                fra=cert_fra,
                ccs=cert_ccs,
            )
            note = None
        elif base_utenza_summary is not None:
            utenza_summary = base_utenza_summary
            cert_com, cert_pvc, cert_fra, cert_ccs = base_cert_context
            stato_ruolo, stato_cnc = base_status_context
            intestatari = []
            note = "Presenti dati non aggiornati/storici del sub: intestatario corrente non disponibile"
        else:
            note = "Presenti dati non aggiornati/storici del sub: intestatario corrente non disponibile"

        matches.append(
            CatAnagraficaMatch(
                particella_id=p.id,
                unit_id=unit.id,
                comune=p.nome_comune or (comune_record.nome_comune if comune_record else None),
                comune_id=p.comune_id,
                cod_comune_capacitas=p.cod_comune_capacitas,
                codice_catastale=p.codice_catastale or (comune_record.codice_catastale if comune_record else None),
                foglio=p.foglio,
                particella=p.particella,
                subalterno=unit.subalterno,
                num_distretto=p.num_distretto,
                nome_distretto=p.nome_distretto,
                riordino_code=riordino_code,
                riordino_maglia=riordino_maglia,
                riordino_lotto=riordino_lotto,
                superficie_mq=p.superficie_mq,
                superficie_grafica_mq=p.superficie_grafica_mq,
                presente_in_catasto_consorzio=True,
                utenza_latest=utenza_summary,
                cert_com=cert_com,
                cert_pvc=cert_pvc,
                cert_fra=cert_fra,
                cert_ccs=cert_ccs,
                stato_ruolo=stato_ruolo,
                stato_cnc=stato_cnc,
                intestatari=intestatari,
                anomalie_count=0,
                anomalie_top=[],
                note=note,
            )
        )

    return matches


def _find_consorzio_sub_match(
    db: Session,
    foglio: str,
    particella: str,
    sub: str,
    comune_norm: str,
    *,
    live_authoritative: bool = False,
) -> CatAnagraficaMatch | None:
    """Fallback: looks up a sub-level CatConsorzioUnit directly when CatParticella has no entry for that sub.

    Used when the user explicitly specifies a sub (e.g. A, B) that only exists in CatConsorzioUnit
    (particella_id=None) and not in CatParticella.
    """
    sub_value = sub.strip()
    unit_query = select(CatConsorzioUnit).where(
        CatConsorzioUnit.foglio == foglio,
        CatConsorzioUnit.particella == particella,
        CatConsorzioUnit.subalterno == sub_value,
        CatConsorzioUnit.is_active.is_(True),
    )
    if _looks_like_int(comune_norm):
        unit_query = unit_query.where(CatConsorzioUnit.cod_comune_capacitas == int(comune_norm))
    else:
        unit_query = unit_query.where(
            func.lower(func.coalesce(CatConsorzioUnit.source_comune_label, "")) == comune_norm.lower()
        )

    unit = db.execute(unit_query.limit(1)).scalars().first()
    if unit is None:
        return None
    occupancy = _best_occupancy_for_unit(db, unit.id)

    cco = occupancy.cco if occupancy else None
    is_stale = bool(occupancy and not occupancy.is_current)
    cert_com, cert_pvc, cert_fra, cert_ccs = _context_from_occupancy(occupancy)
    stato_ruolo, stato_cnc = _load_cert_status_from_context(
        db, cco=cco, com=cert_com, pvc=cert_pvc, fra=cert_fra, ccs=cert_ccs
    )
    intestatari: list[CatIntestatarioResponse] = []
    utenza_summary = _utenza_summary_from_occupancy(occupancy) if occupancy else None

    # Resolve comune info from the unit's comune reference
    comune_record = db.get(CatComune, unit.comune_id) if unit.comune_id else None
    source_comune = db.get(CatComune, unit.source_comune_id) if unit.source_comune_id else None
    resolved_comune = comune_record or source_comune

    # Try to find the base CatParticella (sub=None) to reuse its particella_id and geometry data
    base_particella: CatParticella | None = None
    if unit.particella_id is None:
        p_query = select(CatParticella).where(
            CatParticella.foglio == foglio,
            CatParticella.particella == particella,
            CatParticella.is_current.is_(True),
            func.coalesce(CatParticella.subalterno, "") == "",
        )
        if resolved_comune is not None:
            p_query = p_query.where(CatParticella.comune_id == resolved_comune.id)
        base_particella = db.execute(p_query.limit(1)).scalars().first()
    else:
        base_particella = db.get(CatParticella, unit.particella_id)

    particella_id = base_particella.id if base_particella else unit.id  # type: ignore[arg-type]
    base_utenza_summary: CatAnagraficaUtenzaSummary | None = None
    base_cert_context: tuple[str | None, str | None, str | None, str | None] = (None, None, None, None)
    base_status_context: tuple[str | None, str | None] = (None, None)
    if base_particella is not None:
        base_utenza_summary, _base_intestatari, base_cert_context, base_status_context = _current_base_match_data(
            db,
            base_particella,
            live_authoritative=live_authoritative,
        )
    riordino_code, riordino_maglia, riordino_lotto = _load_riordino_fields_for_particella(
        db,
        base_particella,
        unit.id,
    )
    if cco and _is_sentinel_cco(cco):
        note = "CCO provvisorio Capacitas: dati intestatario non disponibili"
    elif cco and not is_stale:
        intestatari = _load_intestatari_from_cert_context(
            db,
            cco=cco,
            com=cert_com,
            pvc=cert_pvc,
            fra=cert_fra,
            ccs=cert_ccs,
        )
        note = None
    elif base_utenza_summary is not None:
        utenza_summary = base_utenza_summary
        cert_com, cert_pvc, cert_fra, cert_ccs = base_cert_context
        stato_ruolo, stato_cnc = base_status_context
        intestatari = []
        note = "Presenti dati non aggiornati/storici del sub: intestatario corrente non disponibile"
    else:
        note = "Presenti dati non aggiornati/storici del sub: intestatario corrente non disponibile"
    return CatAnagraficaMatch(
        particella_id=particella_id,
        unit_id=unit.id,
        comune=resolved_comune.nome_comune if resolved_comune else unit.source_comune_label,
        comune_id=resolved_comune.id if resolved_comune else None,
        cod_comune_capacitas=unit.cod_comune_capacitas,
        codice_catastale=resolved_comune.codice_catastale if resolved_comune else None,
        foglio=unit.foglio or foglio,
        particella=unit.particella or particella,
        subalterno=unit.subalterno,
        num_distretto=base_particella.num_distretto if base_particella else None,
        nome_distretto=base_particella.nome_distretto if base_particella else None,
        riordino_code=riordino_code,
        riordino_maglia=riordino_maglia,
        riordino_lotto=riordino_lotto,
        superficie_mq=base_particella.superficie_mq if base_particella else None,
        superficie_grafica_mq=base_particella.superficie_grafica_mq if base_particella else None,
        presente_in_catasto_consorzio=True,
        utenza_latest=utenza_summary,
        cert_com=cert_com,
        cert_pvc=cert_pvc,
        cert_fra=cert_fra,
        cert_ccs=cert_ccs,
        stato_ruolo=stato_ruolo,
        stato_cnc=stato_cnc,
        intestatari=intestatari,
        anomalie_count=0,
        anomalie_top=[],
        note=note,
    )


def _load_consorzio_presence_by_particella_ids(db: Session, particella_ids: set[UUID]) -> set[UUID]:
    if not particella_ids:
        return set()
    rows = db.execute(
        select(CatConsorzioUnit.particella_id)
        .where(
            CatConsorzioUnit.particella_id.in_(sorted(particella_ids)),
            CatConsorzioUnit.is_active.is_(True),
        )
        .distinct()
    ).scalars().all()
    return {pid for pid in rows if pid is not None}


def _particelle_with_utenza_irrigua(db: Session, particella_ids: set[UUID]) -> set[UUID]:
    """Particelle che hanno almeno una utenza di campagna (dati consortili operativi)."""
    if not particella_ids:
        return set()
    rows = (
        db.execute(
            select(CatUtenzaIrrigua.particella_id)
            .where(
                CatUtenzaIrrigua.particella_id.in_(particella_ids),
                CatUtenzaIrrigua.particella_id.is_not(None),
            )
            .distinct()
        )
        .scalars()
        .all()
    )
    return {pid for pid in rows if pid is not None}


def _build_match(
    db: Session,
    p: CatParticella,
    *,
    presente_in_catasto_consorzio: bool,
    live_authoritative: bool = False,
) -> CatAnagraficaMatch:
    comune_record = db.get(CatComune, p.comune_id) if p.comune_id else None
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
    latest_occupancy = (
        db.execute(
            select(CatConsorzioOccupancy)
            .join(CatConsorzioUnit, CatConsorzioUnit.id == CatConsorzioOccupancy.unit_id)
            .where(
                _particella_unit_match_clause(p),
                CatConsorzioOccupancy.cco.is_not(None),
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

    utenze = db.execute(
        select(CatUtenzaIrrigua)
        .where(CatUtenzaIrrigua.particella_id == p.id)
        .order_by(desc(CatUtenzaIrrigua.anno_campagna))
        .limit(25)
    ).scalars().all()

    intestatari: list[CatIntestatarioResponse] = []
    if not live_authoritative:
        utenza_ids = [u.id for u in utenze]
        intestatari = _load_intestatari_by_utenza_ids(db, utenza_ids)
        if not intestatari:
            cfs = {u.codice_fiscale.strip().upper() for u in utenze if u.codice_fiscale and u.codice_fiscale.strip()}
            intestatari_by_cf = _load_intestatari_by_cf(db, cfs)
            intestatari = list(intestatari_by_cf.values())
        if not intestatari and latest_utenza is not None:
            fallback_owner = _intestatario_response_from_utenza_record(latest_utenza)
            if fallback_owner is not None:
                intestatari = [fallback_owner]

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

    # Oltre all'anagrafe unità consortili (CatConsorzioUnit), conta come "presente"
    # anche una utenza di campagna o intestatari già noti: altrimenti l'export mostra
    # "non presente" pur avendo CF/particella/intestatari da database o live Capacitas.
    presente_eff = (
        presente_in_catasto_consorzio
        or (latest_utenza is not None)
        or bool(intestatari)
    )
    cert_com, cert_pvc, cert_fra, cert_ccs = _resolve_particella_cert_context(
        db,
        p,
        (latest_utenza.cco if latest_utenza is not None else None) or (latest_occupancy.cco if latest_occupancy is not None else None),
        latest_utenza,
        latest_occupancy,
    )
    status_cco = (
        (latest_utenza.cco if latest_utenza is not None else None) or (latest_occupancy.cco if latest_occupancy is not None else None)
    ) if all([cert_com, cert_pvc, cert_fra]) else None
    stato_ruolo, stato_cnc = (
        _load_cert_status_from_context(
            db,
            cco=status_cco,
            com=cert_com,
            pvc=cert_pvc,
            fra=cert_fra,
            ccs=cert_ccs,
        )
        if not live_authoritative
        else (None, None)
    )
    riordino_code, riordino_maglia, riordino_lotto = _load_riordino_fields_for_particella(db, p)

    return CatAnagraficaMatch(
        particella_id=p.id,
        unit_id=None,
        comune=p.nome_comune or (comune_record.nome_comune if comune_record else None),
        comune_id=p.comune_id,
        cod_comune_capacitas=p.cod_comune_capacitas,
        codice_catastale=p.codice_catastale or (comune_record.codice_catastale if comune_record else None),
        foglio=p.foglio,
        particella=p.particella,
        subalterno=p.subalterno,
        num_distretto=p.num_distretto,
        nome_distretto=p.nome_distretto,
        riordino_code=riordino_code,
        riordino_maglia=riordino_maglia,
        riordino_lotto=riordino_lotto,
        superficie_mq=p.superficie_mq,
        superficie_grafica_mq=p.superficie_grafica_mq,
        presente_in_catasto_consorzio=presente_eff,
        utenza_latest=_utenza_summary_from_record(latest_utenza) or _utenza_summary_from_occupancy(latest_occupancy),
        cert_com=cert_com,
        cert_pvc=cert_pvc,
        cert_fra=cert_fra,
        cert_ccs=cert_ccs,
        stato_ruolo=stato_ruolo,
        stato_cnc=stato_cnc,
        intestatari=intestatari,
        anomalie_count=int(anomalie_count or 0),
        anomalie_top=[{"tipo": t, "count": int(c or 0)} for (t, c) in anomalie_types],
    )


def _load_intestatari_by_particella_ids(
    db: Session,
    particella_ids: set[UUID],
) -> dict[UUID, list[CatIntestatarioResponse]]:
    if not particella_ids:
        return {}

    utenze = db.execute(
        select(CatUtenzaIrrigua.id, CatUtenzaIrrigua.particella_id)
        .where(CatUtenzaIrrigua.particella_id.in_(particella_ids))
        .order_by(CatUtenzaIrrigua.particella_id, desc(CatUtenzaIrrigua.anno_campagna))
    ).all()

    utenza_to_particella: dict[UUID, UUID] = {}
    counts_by_particella: dict[UUID, int] = defaultdict(int)
    for utenza_id, particella_id in utenze:
        if particella_id is None or counts_by_particella[particella_id] >= 25:
            continue
        counts_by_particella[particella_id] += 1
        utenza_to_particella[utenza_id] = particella_id

    if not utenza_to_particella:
        return {}

    rows = (
        db.execute(
            select(CatUtenzaIntestatario)
            .where(CatUtenzaIntestatario.utenza_id.in_(list(utenza_to_particella.keys())))
            .order_by(
                desc(CatUtenzaIntestatario.anno_riferimento),
                desc(CatUtenzaIntestatario.data_agg),
                CatUtenzaIntestatario.denominazione.asc(),
            )
        )
        .scalars()
        .all()
    )

    items: dict[UUID, list[CatIntestatarioResponse]] = defaultdict(list)
    seen_by_particella: dict[UUID, set[str]] = defaultdict(set)
    for row in rows:
        particella_id = utenza_to_particella.get(row.utenza_id)
        if particella_id is None:
            continue
        key = (
            str(row.subject_id)
            if row.subject_id
            else _normalize_cf(row.codice_fiscale) or row.idxana or str(row.id)
        )
        if key in seen_by_particella[particella_id]:
            continue
        seen_by_particella[particella_id].add(key)
        items[particella_id].append(_intestatario_response_from_utenza_row(db, row))

    return dict(items)


def _refresh_saved_particelle_matches(
    db: Session,
    results: list[CatAnagraficaBulkSearchRowResult],
    *,
    live_authoritative: bool = False,
) -> list[CatAnagraficaBulkSearchRowResult]:
    particella_ids: set[UUID] = set()
    for row in results:
        if row.match is not None:
            particella_ids.add(row.match.particella_id)
        if row.matches:
            particella_ids.update(match.particella_id for match in row.matches)

    consorzio_unit_ids = _load_consorzio_presence_by_particella_ids(db, particella_ids)
    particelle_con_utenza = _particelle_with_utenza_irrigua(db, particella_ids)
    intestatari_by_particella = (
        {} if live_authoritative else _load_intestatari_by_particella_ids(db, particella_ids)
    )

    def refresh_match(match: CatAnagraficaMatch | None) -> CatAnagraficaMatch | None:
        if match is None:
            return None
        if match.unit_id is not None:
            unit = db.get(CatConsorzioUnit, match.unit_id)
            if unit is None:
                return match
            occupancy = _best_occupancy_for_unit(db, unit.id)
            cco = occupancy.cco if occupancy else None
            is_stale = bool(occupancy and not occupancy.is_current)
            cert_com, cert_pvc, cert_fra, cert_ccs = _context_from_occupancy(occupancy)
            base_particella = db.get(CatParticella, match.particella_id)
            if cco and not is_stale:
                match.intestatari = (
                    []
                    if live_authoritative
                    else _load_intestatari_from_cert_context(
                        db,
                        cco=cco,
                        com=cert_com,
                        pvc=cert_pvc,
                        fra=cert_fra,
                        ccs=cert_ccs,
                    )
                )
                match.utenza_latest = _utenza_summary_from_occupancy(occupancy) if occupancy else match.utenza_latest
                match.note = None
                match.stato_ruolo, match.stato_cnc = (
                    (None, None)
                    if live_authoritative
                    else _load_cert_status_from_context(
                        db,
                        cco=cco,
                        com=cert_com,
                        pvc=cert_pvc,
                        fra=cert_fra,
                        ccs=cert_ccs,
                    )
                )
            elif base_particella is not None:
                base_utenza_summary, _base_intestatari, base_cert_context, base_status_context = _current_base_match_data(
                    db,
                    base_particella,
                    live_authoritative=live_authoritative,
                )
                if base_utenza_summary is not None:
                    match.utenza_latest = base_utenza_summary
                    match.intestatari = []
                    cert_com, cert_pvc, cert_fra, cert_ccs = base_cert_context
                    match.stato_ruolo, match.stato_cnc = base_status_context
                    match.note = "Presenti dati non aggiornati/storici del sub: intestatario corrente non disponibile"
                else:
                    match.intestatari = []
                    match.stato_ruolo = None
                    match.stato_cnc = None
                    match.note = "Presenti dati non aggiornati/storici del sub: intestatario corrente non disponibile"
            else:
                match.stato_ruolo = None
                match.stato_cnc = None
            match.cert_com = cert_com
            match.cert_pvc = cert_pvc
            match.cert_fra = cert_fra
            match.cert_ccs = cert_ccs
            match.presente_in_catasto_consorzio = True
            return match
        intestatari = intestatari_by_particella.get(match.particella_id)
        if intestatari:
            match.intestatari = intestatari
        pid = match.particella_id
        particella = db.get(CatParticella, pid)
        if particella is not None:
            latest_utenza = (
                db.execute(
                    select(CatUtenzaIrrigua)
                    .where(CatUtenzaIrrigua.particella_id == pid)
                    .order_by(desc(CatUtenzaIrrigua.anno_campagna))
                    .limit(1)
                )
                .scalars()
                .first()
            )
            latest_occupancy = (
                db.execute(
                    select(CatConsorzioOccupancy)
                    .join(CatConsorzioUnit, CatConsorzioUnit.id == CatConsorzioOccupancy.unit_id)
                    .where(
                        _particella_unit_match_clause(particella),
                        CatConsorzioOccupancy.cco.is_not(None),
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
            cco = (
                (latest_utenza.cco if latest_utenza is not None else None)
                or (latest_occupancy.cco if latest_occupancy is not None else None)
                or (match.utenza_latest.cco if match.utenza_latest is not None else None)
            )
            cert_com, cert_pvc, cert_fra, cert_ccs = _resolve_particella_cert_context(
                db,
                particella,
                cco,
                latest_utenza,
                latest_occupancy,
            )
            match.cert_com = cert_com
            match.cert_pvc = cert_pvc
            match.cert_fra = cert_fra
            match.cert_ccs = cert_ccs
            match.stato_ruolo, match.stato_cnc = (
                (None, None)
                if live_authoritative
                else _load_cert_status_from_context(
                    db,
                    cco=cco if all([cert_com, cert_pvc, cert_fra]) else None,
                    com=cert_com,
                    pvc=cert_pvc,
                    fra=cert_fra,
                    ccs=cert_ccs,
                )
            )
            refreshed_utenza = _utenza_summary_from_record(latest_utenza) or _utenza_summary_from_occupancy(latest_occupancy)
            if refreshed_utenza is not None:
                match.utenza_latest = refreshed_utenza
        match.presente_in_catasto_consorzio = (
            pid in consorzio_unit_ids
            or pid in particelle_con_utenza
            or bool(match.intestatari)
        )
        return match

    for row in results:
        if row.match is not None:
            row.match = refresh_match(row.match)
        if row.matches:
            row.matches = [refreshed for match in row.matches if (refreshed := refresh_match(match)) is not None]
    return results


def _match_needs_live_context_refresh(match: CatAnagraficaMatch | None) -> bool:
    if match is None or match.utenza_latest is None:
        return False
    if not _norm_str(match.utenza_latest.cco):
        return False
    return not all((_norm_str(match.cert_com), _norm_str(match.cert_pvc), _norm_str(match.cert_fra)))


def _results_need_live_refresh(results: list[CatAnagraficaBulkSearchRowResult]) -> bool:
    for row in results:
        if _match_needs_live_context_refresh(row.match):
            return True
        for sub_match in row.matches or []:
            if _match_needs_live_context_refresh(sub_match):
                return True
    return False
