from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatAnomalia, CatComune, CatParticella, CatUtenzaIrrigua
from app.modules.utenze.models import AnagraficaPerson, AnagraficaSubject
from app.schemas.catasto_phase1 import (
    CatAnagraficaBulkSearchRequest,
    CatAnagraficaBulkSearchResponse,
    CatAnagraficaBulkSearchRowResult,
    CatAnagraficaMatch,
    CatAnagraficaUtenzaSummary,
    CatIntestatarioResponse,
)

router = APIRouter(prefix="/catasto/elaborazioni-massive/particelle", tags=["catasto-elaborazioni-massive"])


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


def _build_denominazione(cognome: str | None, nome: str | None) -> str | None:
    value = " ".join(part for part in [cognome, nome] if part and part.strip()).strip()
    return value or None


def _load_intestatari_by_cf(db: Session, cfs: set[str]) -> dict[str, CatIntestatarioResponse]:
    if not cfs:
        return {}
    rows = (
        db.execute(
            select(AnagraficaPerson, AnagraficaSubject)
            .join(AnagraficaSubject, AnagraficaSubject.id == AnagraficaPerson.subject_id)
            .where(AnagraficaPerson.codice_fiscale.in_(sorted(cfs)))
        )
        .all()
    )
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
            ragione_sociale=None,
            source=subject.source_system,
            last_verified_at=person.updated_at,
            deceduto=None,
        )
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


def _build_match(db: Session, p: CatParticella) -> CatAnagraficaMatch:
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

    utenze = db.execute(
        select(CatUtenzaIrrigua)
        .where(CatUtenzaIrrigua.particella_id == p.id)
        .order_by(desc(CatUtenzaIrrigua.anno_campagna))
        .limit(25)
    ).scalars().all()

    cfs = {u.codice_fiscale.strip().upper() for u in utenze if u.codice_fiscale and u.codice_fiscale.strip()}
    intestatari_by_cf = _load_intestatari_by_cf(db, cfs)
    intestatari: list[CatIntestatarioResponse] = list(intestatari_by_cf.values())

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
        comune=p.nome_comune or (comune_record.nome_comune if comune_record else None),
        comune_id=p.comune_id,
        cod_comune_capacitas=p.cod_comune_capacitas,
        codice_catastale=p.codice_catastale or (comune_record.codice_catastale if comune_record else None),
        foglio=p.foglio,
        particella=p.particella,
        subalterno=p.subalterno,
        num_distretto=p.num_distretto,
        nome_distretto=p.nome_distretto,
        superficie_mq=p.superficie_mq,
        superficie_grafica_mq=p.superficie_grafica_mq,
        utenza_latest=_utenza_summary_from_record(latest_utenza),
        intestatari=intestatari,
        anomalie_count=int(anomalie_count or 0),
        anomalie_top=[{"tipo": t, "count": int(c or 0)} for (t, c) in anomalie_types],
    )


@router.post("", response_model=CatAnagraficaBulkSearchResponse)
def bulk_search_anagrafica(
    payload: CatAnagraficaBulkSearchRequest = Body(...),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatAnagraficaBulkSearchResponse:
    results: list[CatAnagraficaBulkSearchRowResult] = []

    def infer_kind() -> Literal["CF_PIVA_PARTICELLE", "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"]:
        if payload.kind in ("CF_PIVA_PARTICELLE", "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"):
            return payload.kind
        has_particella_keys = any((r.comune or r.foglio or r.particella or r.sub or r.sezione) for r in payload.rows)
        has_tax_keys = any((r.codice_fiscale or r.partita_iva) for r in payload.rows)
        if has_particella_keys and not has_tax_keys:
            return "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"
        if has_tax_keys and not has_particella_keys:
            return "CF_PIVA_PARTICELLE"
        if has_tax_keys and has_particella_keys:
            # Prefer the cadastral flow; rows that contain only CF/P.IVA will be marked invalid.
            return "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"
        return "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"

    kind: Literal["CF_PIVA_PARTICELLE", "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"] = infer_kind()

    for row in payload.rows:
        try:
            if kind == "CF_PIVA_PARTICELLE":
                cf_norm = _norm_str(row.codice_fiscale)
                piva_norm = _norm_str(row.partita_iva)
                tax_key = (cf_norm or piva_norm or "").upper()

                if not tax_key:
                    results.append(
                        CatAnagraficaBulkSearchRowResult(
                            row_index=row.row_index,
                            codice_fiscale_input=row.codice_fiscale,
                            partita_iva_input=row.partita_iva,
                            esito="INVALID_ROW",
                            message="Campo obbligatorio mancante (codice_fiscale o partita_iva).",
                        )
                    )
                    continue

                utenze = (
                    db.execute(
                        select(CatUtenzaIrrigua.particella_id)
                        .where(
                            CatUtenzaIrrigua.particella_id.is_not(None),
                            func.upper(func.coalesce(CatUtenzaIrrigua.codice_fiscale, "")) == tax_key,
                        )
                        .order_by(desc(CatUtenzaIrrigua.anno_campagna))
                        .limit(200)
                    )
                    .scalars()
                    .all()
                )
                particella_ids = list(dict.fromkeys([pid for pid in utenze if pid is not None]))
                if not particella_ids:
                    results.append(
                        CatAnagraficaBulkSearchRowResult(
                            row_index=row.row_index,
                            codice_fiscale_input=row.codice_fiscale,
                            partita_iva_input=row.partita_iva,
                            esito="NOT_FOUND",
                            message="Nessuna particella associata trovata.",
                            matches_count=0,
                            matches=[],
                        )
                    )
                    continue

                particelle = (
                    db.execute(
                        select(CatParticella)
                        .where(CatParticella.id.in_(particella_ids), CatParticella.is_current.is_(True))
                        .limit(200)
                    )
                    .scalars()
                    .all()
                )
                matches = [_build_match(db, p) for p in particelle]
                results.append(
                    CatAnagraficaBulkSearchRowResult(
                        row_index=row.row_index,
                        codice_fiscale_input=row.codice_fiscale,
                        partita_iva_input=row.partita_iva,
                        esito="FOUND" if matches else "NOT_FOUND",
                        message="OK" if matches else "Nessuna particella associata trovata.",
                        matches_count=len(matches),
                        matches=matches,
                        match=matches[0] if matches else None,
                        particella_id=matches[0].particella_id if matches else None,
                    )
                )
                continue

            comune_norm = _norm_str(row.comune)
            sezione_norm = _norm_str(row.sezione)
            foglio_norm = _norm_str(row.foglio)
            particella_norm = _norm_str(row.particella)
            sub_norm = _norm_str(row.sub)

            if not comune_norm or not foglio_norm or not particella_norm:
                results.append(
                    CatAnagraficaBulkSearchRowResult(
                        row_index=row.row_index,
                        comune_input=row.comune,
                        sezione_input=row.sezione,
                        foglio_input=row.foglio,
                        particella_input=row.particella,
                        sub_input=row.sub,
                        esito="INVALID_ROW",
                        message="Campi obbligatori mancanti (comune/foglio/particella).",
                    )
                )
                continue

            query = (
                select(CatParticella)
                .outerjoin(CatComune, CatComune.id == CatParticella.comune_id)
                .where(
                    CatParticella.is_current.is_(True),
                    CatParticella.foglio == foglio_norm,
                    CatParticella.particella == particella_norm,
                )
                .order_by(CatParticella.cod_comune_capacitas, CatParticella.foglio, CatParticella.particella)
            )

            if sezione_norm:
                query = query.where(CatParticella.sezione_catastale == sezione_norm)
            if sub_norm:
                query = query.where(CatParticella.subalterno == sub_norm)

            if _looks_like_int(comune_norm):
                query = query.where(CatParticella.cod_comune_capacitas == int(comune_norm))
            else:
                query = query.where(
                    func.lower(func.coalesce(CatParticella.nome_comune, CatComune.nome_comune, "")) == comune_norm.lower()
                )

            items = db.execute(query.limit(50)).scalars().all()
            if len(items) == 0:
                results.append(
                    CatAnagraficaBulkSearchRowResult(
                        row_index=row.row_index,
                        comune_input=row.comune,
                        sezione_input=row.sezione,
                        foglio_input=row.foglio,
                        particella_input=row.particella,
                        sub_input=row.sub,
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
                        sezione_input=row.sezione,
                        foglio_input=row.foglio,
                        particella_input=row.particella,
                        sub_input=row.sub,
                        esito="MULTIPLE_MATCHES",
                        message=f"Trovate {len(items)} particelle. Specifica meglio comune/sezione/sub.",
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
                    sezione_input=row.sezione,
                    foglio_input=row.foglio,
                    particella_input=row.particella,
                    sub_input=row.sub,
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
                    sezione_input=row.sezione,
                    foglio_input=row.foglio,
                    particella_input=row.particella,
                    sub_input=row.sub,
                    codice_fiscale_input=row.codice_fiscale,
                    partita_iva_input=row.partita_iva,
                    esito="ERROR",
                    message=str(exc),
                )
            )

    return CatAnagraficaBulkSearchResponse(results=results)
