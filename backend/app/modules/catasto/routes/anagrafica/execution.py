from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import (
    CatParticella,
    CatUtenzaIrrigua,
)
from app.modules.catasto.routes.anagrafica.authoritative import _CapacitasAuthoritativeResolver
from app.modules.catasto.routes.anagrafica.matching import (
    _build_consorzio_sub_matches,
    _build_match,
    _find_consorzio_sub_match,
    _load_consorzio_presence_by_particella_ids,
)
from app.modules.catasto.routes.anagrafica.normalization import (
    _infer_bulk_kind,
    _norm_str,
    _normalize_bulk_particella_inputs,
    _normalize_bulk_payload,
    _query_particelle_candidates,
)
from app.modules.catasto.routes.anagrafica.resolvers import _CapacitasLiveResolver
from app.schemas.catasto_phase1 import (
    CatAnagraficaBulkSearchRequest,
    CatAnagraficaBulkSearchResponse,
    CatAnagraficaBulkSearchRow,
    CatAnagraficaBulkSearchRowResult,
    CatAnagraficaMatch,
)

router = APIRouter(
    prefix="/catasto/elaborazioni-massive/particelle", tags=["catasto-elaborazioni-massive"]
)
logger = logging.getLogger(__name__)
CATASTO_DISTRETTO_EXPORT_STORAGE_PATH = Path(
    os.getenv("CATASTO_DISTRETTO_EXPORT_STORAGE_PATH", "/data/catasto/exports/distretti")
)


async def _build_tax_matches(
    db: Session,
    particelle: list[CatParticella],
    consorzio_present_ids: set,
    live_resolver: _CapacitasLiveResolver | _CapacitasAuthoritativeResolver | None,
) -> list[CatAnagraficaMatch]:
    matches: list[CatAnagraficaMatch] = []
    for particella in particelle:
        match = _build_match(
            db,
            particella,
            presente_in_catasto_consorzio=(particella.id in consorzio_present_ids),
        )
        if live_resolver is not None:
            match = await live_resolver.enrich_match(particella, match)
        matches.append(match)
    return matches


async def _build_candidate_matches(
    db: Session,
    items: list[CatParticella],
    consorzio_present_ids: set,
    live_resolver: _CapacitasLiveResolver | _CapacitasAuthoritativeResolver | None,
    *,
    live_authoritative: bool,
) -> list[CatAnagraficaMatch]:
    matches: list[CatAnagraficaMatch] = []
    for item in items:
        candidate = _build_match(
            db,
            item,
            presente_in_catasto_consorzio=(item.id in consorzio_present_ids),
            live_authoritative=live_authoritative,
        )
        if live_resolver is not None:
            candidate = await live_resolver.enrich_match(item, candidate)
        matches.append(candidate)
    return matches


def _commit_live_changes(
    db: Session,
    live_resolver: _CapacitasLiveResolver | _CapacitasAuthoritativeResolver | None,
) -> None:
    if live_resolver is not None and live_resolver.dirty:
        db.commit()
        live_resolver.dirty = False


def _build_live_search_result(
    row: CatAnagraficaBulkSearchRow,
    live_matches: list[CatAnagraficaMatch],
) -> CatAnagraficaBulkSearchRowResult:
    if len(live_matches) == 1:
        live_match = live_matches[0]
        return CatAnagraficaBulkSearchRowResult(
            row_index=row.row_index,
            comune_input=row.comune,
            sezione_input=row.sezione,
            foglio_input=row.foglio,
            particella_input=row.particella,
            sub_input=row.sub,
            esito="FOUND",
            message="OK",
            particella_id=live_match.particella_id,
            match=live_match,
            matches_count=1,
        )
    if len(live_matches) > 1:
        return CatAnagraficaBulkSearchRowResult(
            row_index=row.row_index,
            comune_input=row.comune,
            sezione_input=row.sezione,
            foglio_input=row.foglio,
            particella_input=row.particella,
            sub_input=row.sub,
            esito="MULTIPLE_MATCHES",
            message=f"Trovati {len(live_matches)} esiti live Capacitas. Verifica il comune/frazione corretti.",
            matches_count=len(live_matches),
            matches=live_matches,
        )
    return CatAnagraficaBulkSearchRowResult(
        row_index=row.row_index,
        comune_input=row.comune,
        sezione_input=row.sezione,
        foglio_input=row.foglio,
        particella_input=row.particella,
        sub_input=row.sub,
        esito="NOT_FOUND",
        message="Nessuna particella trovata.",
    )


async def _enrich_sub_matches(
    live_resolver: _CapacitasLiveResolver | _CapacitasAuthoritativeResolver | None,
    particella: CatParticella,
    sub_matches: list[CatAnagraficaMatch] | None,
) -> list[CatAnagraficaMatch] | None:
    if not sub_matches or live_resolver is None:
        return sub_matches
    return [await live_resolver.enrich_match(particella, sub_match) for sub_match in sub_matches]


async def _resolve_sub_match(
    db: Session,
    lookup: tuple[str, str, str, str],
    live_resolver: _CapacitasLiveResolver | _CapacitasAuthoritativeResolver | None,
    *,
    live_authoritative: bool,
) -> CatAnagraficaMatch | None:
    comune_norm, foglio_norm, particella_norm, sub_norm = lookup
    sub_match: CatAnagraficaMatch | None = None
    if sub_norm and foglio_norm and particella_norm and comune_norm:
        sub_match = _find_consorzio_sub_match(
            db,
            foglio_norm,
            particella_norm,
            sub_norm,
            comune_norm,
            live_authoritative=live_authoritative,
        )
    if sub_match is None or live_resolver is None:
        return sub_match
    particella_ref = db.get(CatParticella, sub_match.particella_id)
    if particella_ref is not None:
        sub_match = await live_resolver.enrich_match(particella_ref, sub_match)
    return sub_match


# fmt: off

async def execute_bulk_search_payload(
    payload: CatAnagraficaBulkSearchRequest,
    db: Session,
    *,
    on_row_processed: Callable[[int, int, CatAnagraficaBulkSearchRow, list[CatAnagraficaBulkSearchRowResult]], Awaitable[None]] | None = None,
) -> CatAnagraficaBulkSearchResponse:
    payload = _normalize_bulk_payload(payload)
    kind = _infer_bulk_kind(payload)
    total_rows = len(payload.rows)
    results: list[CatAnagraficaBulkSearchRowResult] = []
    live_resolver = (
        (_CapacitasAuthoritativeResolver(db) if kind == "COMUNE_FOGLIO_PARTICELLA_INTESTATARI" else _CapacitasLiveResolver(db))
        if payload.include_capacitas_live
        else None
    )
    live_authoritative = kind == "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"

    try:
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
                    else:
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
                        else:
                            particelle = (
                                db.execute(
                                    select(CatParticella)
                                    .where(CatParticella.id.in_(particella_ids), CatParticella.is_current.is_(True))
                                    .limit(200)
                                )
                                .scalars()
                                .all()
                            )
                            consorzio_present_ids = _load_consorzio_presence_by_particella_ids(
                                db, {p.id for p in particelle if p.id is not None}
                            )
                            matches = await _build_tax_matches(
                                db,
                                particelle,
                                consorzio_present_ids,
                                live_resolver,
                            )

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
                    _commit_live_changes(db, live_resolver)
                else:
                    comune_norm, sezione_norm, foglio_norm = _normalize_bulk_particella_inputs(
                        row.comune,
                        row.sezione,
                        row.foglio,
                    )
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
                    else:
                        items = _query_particelle_candidates(
                            db,
                            comune_norm=comune_norm,
                            sezione_norm=sezione_norm,
                            foglio_norm=foglio_norm,
                            particella_norm=particella_norm,
                            sub_norm=sub_norm,
                        )
                        if len(items) == 0:
                            sub_match = await _resolve_sub_match(
                                db,
                                (comune_norm, foglio_norm, particella_norm, sub_norm),
                                live_resolver,
                                live_authoritative=live_authoritative,
                            )
                            if sub_match is not None:
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
                                        particella_id=sub_match.particella_id,
                                        match=sub_match,
                                        matches_count=1,
                                    )
                                )
                            elif live_resolver is not None:
                                live_matches = await live_resolver.find_live_only_matches(
                                    comune=comune_norm,
                                    foglio=foglio_norm,
                                    particella=particella_norm,
                                    sub=sub_norm,
                                )
                                results.append(_build_live_search_result(row, live_matches))
                                _commit_live_changes(db, live_resolver)
                            else:
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
                        elif len(items) > 1:
                            consorzio_present_ids = _load_consorzio_presence_by_particella_ids(
                                db, {p.id for p in items if p.id is not None}
                            )
                            matches = await _build_candidate_matches(
                                db,
                                items,
                                consorzio_present_ids,
                                live_resolver,
                                live_authoritative=live_authoritative,
                            )
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
                                    matches_count=len(items),
                                    matches=matches,
                                )
                            )
                            _commit_live_changes(db, live_resolver)
                        else:
                            consorzio_present_ids = _load_consorzio_presence_by_particella_ids(
                                db, {items[0].id} if items[0].id is not None else set()
                            )
                            match = _build_match(
                                db,
                                items[0],
                                presente_in_catasto_consorzio=(items[0].id in consorzio_present_ids),
                                live_authoritative=live_authoritative,
                            )
                            if live_resolver is not None:
                                match = await live_resolver.enrich_match(items[0], match)

                            sub_matches: list[CatAnagraficaMatch] | None = None
                            if not sub_norm:
                                sub_matches = _build_consorzio_sub_matches(
                                    db,
                                    items[0],
                                    live_authoritative=live_authoritative,
                                ) or None
                                sub_matches = await _enrich_sub_matches(
                                    live_resolver,
                                    items[0],
                                    sub_matches,
                                )

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
                                    matches=sub_matches,
                                    matches_count=(len(sub_matches) if sub_matches else 1),
                                )
                            )
                            _commit_live_changes(db, live_resolver)
            except Exception as exc:
                if live_resolver is not None and live_resolver.dirty:
                    db.rollback()
                    live_resolver.dirty = False
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
            if on_row_processed is not None:
                await on_row_processed(len(results), total_rows, row, results)
    finally:
        if live_resolver is not None:
            await live_resolver.close()

    return CatAnagraficaBulkSearchResponse(results=results)
