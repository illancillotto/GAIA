from __future__ import annotations

import logging
import os
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import (
    CatCapacitasTerrenoRow,
    CatComune,
    CatConsorzioUnit,
    CatParticella,
    CatUtenzaIrrigua,
)
from app.modules.catasto.routes.anagrafica.exports import (
    _classify_live_search_hits,
    _collect_live_search_hits,
)
from app.modules.catasto.routes.anagrafica.intestatari import (
    _best_occupancy_for_unit,
    _load_cert_status_from_context,
    _load_intestatari_from_cert_context,
    _resolve_particella_cert_context,
)
from app.modules.catasto.routes.anagrafica.matching import (
    _build_match,
    _load_consorzio_presence_by_particella_ids,
)
from app.modules.catasto.routes.anagrafica.normalization import (
    _alternate_live_lookup_comune,
    _norm_str,
    _normalize_ccs,
    _normalize_cf,
    _normalize_com,
    _normalize_fra,
    _normalize_pvc,
    _safe_int,
)
from app.modules.elaborazioni.capacitas.client import InVoltureClient
from app.modules.elaborazioni.capacitas.models import (
    CapacitasAnagraficaDetail,
    CapacitasIntestatario,
    CapacitasLookupOption,
    CapacitasTerreniSearchRequest,
    CapacitasTerrenoCertificato,
    CapacitasTerrenoRow,
)
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
from app.schemas.catasto_phase1 import (
    CatAnagraficaMatch,
    CatAnagraficaUtenzaSummary,
    CatIntestatarioResponse,
)
from app.services.elaborazioni_capacitas import (
    mark_credential_error,
    mark_credential_used,
    pick_credential,
)
from app.services.elaborazioni_capacitas_terreni import (
    sync_terreni_for_request,
)

router = APIRouter(
    prefix="/catasto/elaborazioni-massive/particelle", tags=["catasto-elaborazioni-massive"]
)
logger = logging.getLogger(__name__)
CATASTO_DISTRETTO_EXPORT_STORAGE_PATH = Path(
    os.getenv("CATASTO_DISTRETTO_EXPORT_STORAGE_PATH", "/data/catasto/exports/distretti")
)


# fmt: off

class _CapacitasLiveResolver:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._manager: CapacitasSessionManager | None = None
        self._client: InVoltureClient | None = None
        self._credential_id: int | None = None
        self._disabled = False
        self._cert_cache: dict[tuple[str, str, str, str, str], CapacitasTerrenoCertificato] = {}
        self._detail_cache: dict[tuple[str, str], CapacitasAnagraficaDetail] = {}
        self._frazione_cache: dict[str, list[CapacitasLookupOption]] = {}
        self._sync_attempted_particelle: set[UUID] = set()
        self.dirty = False

    async def close(self) -> None:
        if self._manager is not None:
            await self._manager.close()
            self._manager = None
            self._client = None

    async def enrich_match(self, p: CatParticella, match: CatAnagraficaMatch) -> CatAnagraficaMatch:
        should_skip_live_sync = self._should_skip_live_sync(match)

        if match.utenza_latest is None and not should_skip_live_sync:
            synced = await self._sync_particella_from_live_terreni(p)
            if synced:
                match = _build_match(
                    self._db,
                    p,
                    presente_in_catasto_consorzio=(p.id in _load_consorzio_presence_by_particella_ids(self._db, {p.id})),
                )
                logger.info(
                    "Capacitas live terreni sync riuscita: particella_id=%s comune=%s sezione=%s foglio=%s particella=%s",
                    p.id,
                    p.nome_comune,
                    p.sezione_catastale,
                    p.foglio,
                    p.particella,
                )

        cert_params = self._resolve_cert_params(p, match)
        if cert_params is None:
            logger.info(
                "Capacitas live contesto certificato mancante: particella_id=%s comune=%s sezione=%s foglio=%s particella=%s cco=%s",
                p.id,
                p.nome_comune,
                p.sezione_catastale,
                p.foglio,
                p.particella,
                match.utenza_latest.cco if match.utenza_latest is not None else None,
            )
            if should_skip_live_sync:
                return match
            synced = await self._sync_particella_from_live_terreni(p)
            if synced:
                match = _build_match(
                    self._db,
                    p,
                    presente_in_catasto_consorzio=(p.id in _load_consorzio_presence_by_particella_ids(self._db, {p.id})),
                )
                logger.info(
                    "Capacitas live terreni sync riuscita dopo contesto mancante: particella_id=%s comune=%s sezione=%s foglio=%s particella=%s",
                    p.id,
                    p.nome_comune,
                    p.sezione_catastale,
                    p.foglio,
                    p.particella,
                )
                cert_params = self._resolve_cert_params(p, match)
        if cert_params is None:
            return match

        match.cert_com = cert_params[1]
        match.cert_pvc = cert_params[2]
        match.cert_fra = cert_params[3]
        match.cert_ccs = cert_params[4]
        certificato = await self._fetch_certificato(*cert_params)
        if certificato is not None:
            match.stato_ruolo = certificato.ruolo_status or match.stato_ruolo
            match.stato_cnc = certificato.utenza_status or match.stato_cnc
        if certificato is None or not certificato.intestatari:
            return match

        resolved: list[CatIntestatarioResponse] = []
        seen: set[str] = set()
        for intestatario in certificato.intestatari:
            item = await self._resolve_intestatario(intestatario)
            if item is None:
                continue
            key = _normalize_cf(item.codice_fiscale) or str(item.id)
            if key in seen:
                continue
            seen.add(key)
            resolved.append(item)

        if resolved:
            match.intestatari = resolved
            match.presente_in_catasto_consorzio = True
        return match

    def _should_skip_live_sync(self, match: CatAnagraficaMatch) -> bool:
        note = (match.note or "").strip().casefold()
        return bool(match.unit_id and note.startswith("presenti dati non aggiornati/storici del sub:"))

    async def find_live_only_matches(
        self,
        *,
        comune: str,
        foglio: str,
        particella: str,
        sub: str | None = None,
    ) -> list[CatAnagraficaMatch]:
        client = await self._ensure_client()
        if client is None:
            return []

        comuni_to_try = [comune]
        alternate = _alternate_live_lookup_comune(comune)
        if alternate and alternate.casefold() not in {item.casefold() for item in comuni_to_try}:
            comuni_to_try.append(alternate)

        matches: list[CatAnagraficaMatch] = []
        seen_keys: set[tuple[str | None, str | None, str | None, str, str, str | None]] = set()

        for lookup_comune in comuni_to_try:
            try:
                hits = await _collect_live_search_hits(
                    client,
                    comune=lookup_comune,
                    sezione=None,
                    foglio=foglio,
                    particella=particella,
                    sub=sub,
                    frazione_cache=self._frazione_cache,
                )
            except Exception:
                continue

            status, _, selected_hits = _classify_live_search_hits(hits)
            if status == "NOT_FOUND":
                continue

            for hit in selected_hits:
                match = self._build_live_only_match_from_row(hit.row, input_comune=comune, lookup_comune=lookup_comune)
                match = await self._hydrate_live_match_from_row(match, hit.row)
                key = (
                    match.cert_com,
                    match.cert_pvc,
                    match.cert_fra,
                    match.foglio,
                    match.particella,
                    match.subalterno,
                )
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                matches.append(match)
        return matches

    def _build_live_matches_from_search_key(
        self,
        *,
        search_key: str,
        input_comune: str,
        lookup_comune: str,
        foglio: str,
        particella: str,
        sub: str | None,
    ) -> list[CatAnagraficaMatch]:
        rows = self._db.execute(
            select(CatCapacitasTerrenoRow)
            .where(
                CatCapacitasTerrenoRow.search_key == search_key,
                CatCapacitasTerrenoRow.foglio == foglio,
                CatCapacitasTerrenoRow.particella == particella,
                func.coalesce(CatCapacitasTerrenoRow.sub, "") == (sub or ""),
            )
            .order_by(desc(CatCapacitasTerrenoRow.collected_at))
        ).scalars().all()
        if not rows:
            return []

        def rank(row: CatCapacitasTerrenoRow) -> tuple[int, int, str]:
            state = (row.row_visual_state or "").strip().casefold()
            return (
                2 if "current" in state else 1 if "black" in state else 0,
                _safe_int(row.anno),
                row.collected_at.isoformat() if row.collected_at else "",
            )

        best_by_sub: dict[str, CatCapacitasTerrenoRow] = {}
        for row in rows:
            key = _norm_str(row.sub) or ""
            current = best_by_sub.get(key)
            if current is None or rank(row) > rank(current):
                best_by_sub[key] = row

        matches: list[CatAnagraficaMatch] = []
        for row in best_by_sub.values():
            matches.append(self._build_live_only_match_from_row(row, input_comune=input_comune, lookup_comune=lookup_comune))
        return matches

    def _build_live_only_match_from_row(
        self,
        row: CatCapacitasTerrenoRow | CapacitasTerrenoRow,
        *,
        input_comune: str,
        lookup_comune: str,
    ) -> CatAnagraficaMatch:
        unit_id = getattr(row, "unit_id", None)
        unit = self._db.get(CatConsorzioUnit, unit_id) if unit_id else None
        particella_record = self._db.get(CatParticella, unit.particella_id) if unit and unit.particella_id else None
        comune_record: CatComune | None = None
        if particella_record is not None and particella_record.comune_id is not None:
            comune_record = self._db.get(CatComune, particella_record.comune_id)
        elif unit is not None and unit.comune_id is not None:
            comune_record = self._db.get(CatComune, unit.comune_id)
        elif row.com and row.com.isdigit():
            comune_record = self._db.execute(
                select(CatComune).where(CatComune.cod_comune_capacitas == int(row.com)).limit(1)
            ).scalars().first()
        elif row.belfiore:
            comune_record = self._db.execute(
                select(CatComune).where(CatComune.codice_catastale == row.belfiore).limit(1)
            ).scalars().first()

        superficie_mq = getattr(row, "superficie_mq", None)
        if superficie_mq is None and getattr(row, "superficie", None) is not None:
            try:
                superficie_mq = float(str(row.superficie))
            except (TypeError, ValueError):
                superficie_mq = None

        cert_com = _normalize_com(row.com)
        cert_pvc = _normalize_pvc(row.pvc)
        cert_fra = _normalize_fra(row.fra)
        cert_ccs = _normalize_ccs(row.ccs)
        intestatari = _load_intestatari_from_cert_context(
            self._db,
            cco=row.cco or "",
            com=cert_com,
            pvc=cert_pvc,
            fra=cert_fra,
            ccs=cert_ccs,
        ) if row.cco else []
        stato_ruolo, stato_cnc = _load_cert_status_from_context(
            self._db,
            cco=row.cco,
            com=cert_com,
            pvc=cert_pvc,
            fra=cert_fra,
            ccs=cert_ccs,
        )
        note = None
        if input_comune.strip().casefold() != lookup_comune.strip().casefold():
            note = f"Dati recuperati da Capacitas cercando il comune alternativo '{lookup_comune}'"
        elif comune_record is None or particella_record is None:
            note = "Dati recuperati da Capacitas live: particella non risolta nel catasto locale"

        return CatAnagraficaMatch(
            particella_id=(particella_record.id if particella_record is not None else unit.id if unit is not None else uuid4()),
            unit_id=unit.id if unit is not None else None,
            comune_id=(particella_record.comune_id if particella_record is not None else comune_record.id if comune_record is not None else None),
            comune=(
                particella_record.nome_comune
                if particella_record is not None
                else comune_record.nome_comune if comune_record is not None else lookup_comune
            ),
            cod_comune_capacitas=(
                particella_record.cod_comune_capacitas
                if particella_record is not None
                else unit.cod_comune_capacitas if unit is not None else _safe_int(row.com) if row.com else None
            ),
            codice_catastale=(
                particella_record.codice_catastale
                if particella_record is not None
                else comune_record.codice_catastale if comune_record is not None else row.belfiore
            ),
            foglio=row.foglio or "",
            particella=row.particella or "",
            subalterno=_norm_str(row.sub),
            num_distretto=particella_record.num_distretto if particella_record is not None else None,
            nome_distretto=particella_record.nome_distretto if particella_record is not None else None,
            superficie_mq=superficie_mq,
            superficie_grafica_mq=particella_record.superficie_grafica_mq if particella_record is not None else None,
            presente_in_catasto_consorzio=bool(unit is not None or particella_record is not None),
            utenza_latest=CatAnagraficaUtenzaSummary(
                id=(unit.id if unit is not None else uuid4()),
                cco=row.cco,
                anno_campagna=_safe_int(row.anno),
                stato="capacitas_live",
                num_distretto=None,
                nome_distretto=None,
                sup_irrigabile_mq=superficie_mq,
                denominazione=None,
                codice_fiscale=None,
                ha_anomalie=None,
            ),
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

    async def _sync_particella_from_live_terreni(self, p: CatParticella) -> bool:
        if p.id in self._sync_attempted_particelle:
            return False
        self._sync_attempted_particelle.add(p.id)

        comune_value = _norm_str(p.nome_comune)
        if not comune_value or not p.foglio or not p.particella:
            return False

        client = await self._ensure_client()
        if client is None:
            return False

        try:
            hits = await _collect_live_search_hits(
                client,
                comune=comune_value,
                sezione=p.sezione_catastale,
                foglio=p.foglio,
                particella=p.particella,
                sub=p.subalterno,
                frazione_cache=self._frazione_cache,
            )
        except Exception as exc:
            logger.info(
                "Capacitas live terreni lookup non risolto: particella_id=%s comune=%s sezione=%s foglio=%s particella=%s err=%s",
                p.id,
                comune_value,
                p.sezione_catastale,
                p.foglio,
                p.particella,
                exc,
            )
            return False

        status, message, selected_hits = _classify_live_search_hits(hits)
        if status == "NOT_FOUND":
            logger.info(
                "Capacitas live terreni nessun risultato: particella_id=%s comune=%s sezione=%s foglio=%s particella=%s",
                p.id,
                comune_value,
                p.sezione_catastale,
                p.foglio,
                p.particella,
            )
            return False
        if status == "MULTIPLE_MATCHES":
            logger.info(
                "Capacitas live terreni match ambiguo: particella_id=%s comune=%s sezione=%s foglio=%s particella=%s msg=%s",
                p.id,
                comune_value,
                p.sezione_catastale,
                p.foglio,
                p.particella,
                message,
            )
            return False

        synced_fraction_ids: set[str] = set()
        for hit in selected_hits:
            if hit.frazione_id in synced_fraction_ids:
                continue
            synced_fraction_ids.add(hit.frazione_id)
            request = CapacitasTerreniSearchRequest(
                frazione_id=hit.frazione_id,
                sezione=p.sezione_catastale or "",
                foglio=p.foglio,
                particella=p.particella,
                sub=p.subalterno or "",
            )
            try:
                await sync_terreni_for_request(
                    self._db,
                    client,
                    request,
                    fetch_certificati=True,
                    fetch_details=False,
                )
                self.dirty = True
            except RuntimeError as exc:
                self._db.rollback()
                normalized = str(exc).casefold()
                if "non trov" not in normalized and "nessun" not in normalized and "no result" not in normalized:
                    logger.info(
                        "Capacitas live terreni sync interrotta: particella_id=%s frazione=%s err=%s",
                        p.id,
                        hit.frazione_id,
                        exc,
                    )
                    return False
            except Exception as exc:
                self._db.rollback()
                logger.warning(
                    "Capacitas live terreni sync fallita: particella_id=%s frazione=%s err=%s",
                    p.id,
                    hit.frazione_id,
                    exc,
                )
                return False
        return bool(synced_fraction_ids)

    async def _hydrate_live_match_from_row(
        self,
        match: CatAnagraficaMatch,
        row: CapacitasTerrenoRow,
    ) -> CatAnagraficaMatch:
        cco = _norm_str(row.cco)
        cert_com = _normalize_com(row.com)
        cert_pvc = _normalize_pvc(row.pvc)
        cert_fra = _normalize_fra(row.fra)
        cert_ccs = _normalize_ccs(row.ccs)
        if not cco or not cert_com or not cert_pvc or cert_fra is None:
            return match

        match.cert_com = cert_com
        match.cert_pvc = cert_pvc
        match.cert_fra = cert_fra
        match.cert_ccs = cert_ccs or "00000"

        certificato = await self._fetch_certificato(cco, cert_com, cert_pvc, cert_fra, match.cert_ccs)
        if certificato is None:
            return match

        match.stato_ruolo = certificato.ruolo_status or match.stato_ruolo
        match.stato_cnc = certificato.utenza_status or match.stato_cnc
        if not certificato.intestatari:
            return match

        resolved: list[CatIntestatarioResponse] = []
        seen: set[str] = set()
        for intestatario in certificato.intestatari:
            item = await self._resolve_intestatario(intestatario)
            if item is None:
                continue
            key = _normalize_cf(item.codice_fiscale) or str(item.id)
            if key in seen:
                continue
            seen.add(key)
            resolved.append(item)

        if resolved:
            match.intestatari = resolved
            match.presente_in_catasto_consorzio = True
        return match

    def _resolve_cert_params(
        self,
        p: CatParticella,
        match: CatAnagraficaMatch,
    ) -> tuple[str, str, str, str, str] | None:
        utenza = match.utenza_latest
        cco = _norm_str(utenza.cco if utenza else None)
        if not cco:
            return None

        if match.cert_com and match.cert_pvc and match.cert_fra:
            return (
                cco,
                match.cert_com,
                match.cert_pvc,
                match.cert_fra,
                match.cert_ccs or "00000",
            )

        latest_utenza = self._db.get(CatUtenzaIrrigua, utenza.id) if utenza is not None else None
        latest_occupancy = None
        if match.unit_id is not None:
            latest_occupancy = _best_occupancy_for_unit(self._db, match.unit_id)
        cert_context = _resolve_particella_cert_context(
            self._db,
            p,
            cco,
            latest_utenza,
            latest_occupancy,
        )
        if not all(cert_context[:3]):
            return None
        return (cco, cert_context[0] or "", cert_context[1] or "", cert_context[2] or "", cert_context[3] or "00000")

    async def _ensure_client(self) -> InVoltureClient | None:
        if self._disabled:
            return None
        if self._client is not None:
            return self._client

        try:
            credential, password = pick_credential(self._db, None)
        except RuntimeError as exc:
            logger.info("Capacitas live resolver disabilitato: %s", exc)
            self._disabled = True
            return None

        self._credential_id = credential.id
        self._manager = CapacitasSessionManager(credential.username, password)
        try:
            await self._manager.login()
            await self._manager.activate_app("involture")
            self._client = InVoltureClient(self._manager)
            mark_credential_used(self._db, credential.id)
            return self._client
        except Exception as exc:
            logger.exception("Errore inizializzazione live resolver Capacitas: cred_id=%d err=%s", credential.id, exc)
            mark_credential_error(self._db, credential.id, str(exc))
            await self.close()
            self._disabled = True
            return None

    async def _fetch_certificato(self, cco: str, com: str, pvc: str, fra: str, ccs: str) -> CapacitasTerrenoCertificato | None:
        key = (cco, com, pvc, fra, ccs)
        cached = self._cert_cache.get(key)
        if cached is not None:
            return cached
        client = await self._ensure_client()
        if client is None:
            return None
        try:
            certificato = await client.fetch_certificato(cco=cco, com=com, pvc=pvc, fra=fra, ccs=ccs)
        except Exception as exc:
            logger.warning("Capacitas live certificato fallito: cco=%s err=%s", cco, exc)
            return None
        self._cert_cache[key] = certificato
        return certificato

    async def _resolve_intestatario(self, intestatario: CapacitasIntestatario) -> CatIntestatarioResponse | None:
        local = self._find_local_intestatario(intestatario)
        if local is not None:
            return local

        detail: CapacitasAnagraficaDetail | None = None
        if intestatario.idxana and intestatario.idxesa:
            cache_key = (intestatario.idxana, intestatario.idxesa)
            detail = self._detail_cache.get(cache_key)
            if detail is None:
                client = await self._ensure_client()
                if client is not None:
                    try:
                        detail = await client.fetch_current_anagrafica_detail(idxana=intestatario.idxana, idxesa=intestatario.idxesa)
                        self._detail_cache[cache_key] = detail
                    except Exception as exc:
                        logger.warning(
                            "Capacitas live dettaglio anagrafica fallito: idxana=%s idxesa=%s err=%s",
                            intestatario.idxana,
                            intestatario.idxesa,
                            exc,
                        )

        return self._upsert_live_intestatario(intestatario, detail)
