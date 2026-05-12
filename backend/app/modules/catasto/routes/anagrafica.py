from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends
from fastapi import HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoElaborazioniMassiveJob
from app.models.catasto_phase1 import (
    CatAnomalia,
    CatCapacitasCertificato,
    CatCapacitasIntestatario,
    CatCapacitasTerrenoRow,
    CatComune,
    CatConsorzioOccupancy,
    CatConsorzioUnit,
    CatParticella,
    CatUtenzaIntestatario,
    CatUtenzaIrrigua,
)
from app.modules.elaborazioni.capacitas.client import InVoltureClient
from app.modules.elaborazioni.capacitas.models import CapacitasAnagraficaDetail, CapacitasIntestatario, CapacitasTerrenoCertificato
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
from app.modules.elaborazioni.capacitas.models import CapacitasTerreniSearchRequest
from app.modules.utenze.models import AnagraficaPerson, AnagraficaSubject, AnagraficaSubjectStatus, AnagraficaSubjectType
from app.modules.utenze.services.person_history_service import snapshot_person_if_changed
from app.schemas.catasto_phase1 import (
    CatAnagraficaBulkSearchRequest,
    CatAnagraficaBulkSearchResponse,
    CatAnagraficaBulkJobCreateRequest,
    CatAnagraficaBulkJobDetail,
    CatAnagraficaBulkJobItem,
    CatAnagraficaBulkJobListResponse,
    CatAnagraficaBulkJobSaveRequest,
    CatAnagraficaBulkJobSummary,
    CatAnagraficaBulkSearchRowResult,
    CatAnagraficaMatch,
    CatAnagraficaUtenzaSummary,
    CatIntestatarioResponse,
)
from app.services.elaborazioni_capacitas import mark_credential_error, mark_credential_used, pick_credential
from app.services.elaborazioni_capacitas_terreni import (
    _resolve_batch_frazione_candidates,
    sync_terreni_for_request,
)

router = APIRouter(prefix="/catasto/elaborazioni-massive/particelle", tags=["catasto-elaborazioni-massive"])
logger = logging.getLogger(__name__)

_FOGLIO_WITH_SEZIONE_RE = r"^\s*(?P<foglio>[^\s]+)\s+sez\.?\s*(?P<sezione>[A-Za-z0-9]+)(?:\s+.*)?$"
_COMUNE_LIVE_SWAP_LOOKUP: dict[str, str] = {
    "arborea": "Terralba",
    "terralba": "Arborea",
    "165": "Terralba",
    "280": "Arborea",
}


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


def _safe_int(value: str | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = value.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _build_denominazione(cognome: str | None, nome: str | None) -> str | None:
    value = " ".join(part for part in [cognome, nome] if part and part.strip()).strip()
    return value or None


def _normalize_cf(value: str | None) -> str | None:
    normalized = _norm_str(value)
    return normalized.upper() if normalized else None


def _normalize_ccs(value: str | None) -> str:
    return _norm_str(value) or "00000"


def _normalize_sezione_value(value: str | None) -> str | None:
    normalized = _norm_str(value)
    if not normalized:
        return None
    lowered = normalized.casefold()
    if lowered.startswith("sez"):
        tail = normalized[3:].lstrip(" .:-")
        return _norm_str(tail) or normalized
    return normalized


def _normalize_bulk_particella_inputs(
    comune: str | None,
    sezione: str | None,
    foglio: str | None,
) -> tuple[str | None, str | None, str | None]:
    comune_norm = _norm_str(comune)
    sezione_norm = _normalize_sezione_value(sezione)
    foglio_norm = _norm_str(foglio)

    if foglio_norm is None:
        return comune_norm, sezione_norm, foglio_norm

    import re

    match = re.match(_FOGLIO_WITH_SEZIONE_RE, foglio_norm, flags=re.IGNORECASE)
    if match:
        foglio_norm = _norm_str(match.group("foglio"))
        if sezione_norm is None:
            sezione_norm = _normalize_sezione_value(match.group("sezione"))

    return comune_norm, sezione_norm, foglio_norm


def _alternate_live_lookup_comune(comune: str | None) -> str | None:
    comune_norm = _norm_str(comune)
    if comune_norm is None:
        return None
    return _COMUNE_LIVE_SWAP_LOOKUP.get(comune_norm.casefold())


def _looks_like_codice_catastale(value: str) -> bool:
    normalized = value.strip().upper()
    return len(normalized) == 4 and normalized[0].isalpha() and normalized[1:].isdigit()


def _query_particelle_candidates(
    db: Session,
    *,
    comune_norm: str,
    sezione_norm: str | None,
    foglio_norm: str,
    particella_norm: str,
    sub_norm: str | None,
) -> list[CatParticella]:
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
    elif _looks_like_codice_catastale(comune_norm):
        codice_catastale_norm = comune_norm.strip().upper()
        query = query.where(
            func.upper(func.coalesce(CatParticella.codice_catastale, CatComune.codice_catastale, "")) == codice_catastale_norm
        )
    else:
        query = query.where(
            func.lower(func.coalesce(CatParticella.nome_comune, CatComune.nome_comune, "")) == comune_norm.lower()
        )

    return db.execute(query.limit(50)).scalars().all()


def _occupancy_rank(occupancy: CatConsorzioOccupancy | None) -> tuple[int, str, str]:
    return (
        1 if bool(occupancy and occupancy.is_current) else 0,
        occupancy.valid_from.isoformat() if occupancy and occupancy.valid_from else "",
        occupancy.updated_at.isoformat() if occupancy and occupancy.updated_at else "",
    )


def _build_summary(results: list[CatAnagraficaBulkSearchRowResult]) -> dict[str, int]:
    s = {"total": len(results), "found": 0, "notFound": 0, "multiple": 0, "invalid": 0, "error": 0}
    for r in results:
        if r.esito == "FOUND":
            s["found"] += 1
        elif r.esito == "NOT_FOUND":
            s["notFound"] += 1
        elif r.esito == "MULTIPLE_MATCHES":
            s["multiple"] += 1
        elif r.esito == "INVALID_ROW":
            s["invalid"] += 1
        elif r.esito == "ERROR":
            s["error"] += 1
    return s


def _split_denominazione(value: str | None, *, fallback_cognome: str | None = None, fallback_nome: str | None = None) -> tuple[str, str]:
    normalized = _norm_str(value)
    if not normalized:
        return fallback_cognome or "N/D", fallback_nome or "N/D"
    parts = normalized.split()
    if len(parts) == 1:
        return parts[0], fallback_nome or "N/D"
    return parts[0], " ".join(parts[1:])


def _compose_address(toponimo: str | None, indirizzo: str | None, civico: str | None, sub: str | None) -> str | None:
    parts = [part for part in [_norm_str(toponimo), _norm_str(indirizzo), _norm_str(civico)] if part]
    value = " ".join(parts).strip()
    sub_norm = _norm_str(sub)
    if sub_norm:
        value = f"{value} {sub_norm}".strip()
    return value or None


def _person_response_from_db(person: AnagraficaPerson, subject: AnagraficaSubject, *, deceduto: bool | None = None) -> CatIntestatarioResponse:
    return CatIntestatarioResponse(
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
        deceduto=deceduto,
    )


def _build_person_payload_from_current_capacitas(
    detail: CapacitasAnagraficaDetail | None,
    intestatario: CapacitasIntestatario,
    normalized_cf: str | None,
) -> dict[str, object | None]:
    cognome, nome = _split_denominazione(
        (detail.cognome + " " + detail.nome).strip() if detail and detail.cognome and detail.nome else detail.denominazione if detail else intestatario.denominazione,
        fallback_cognome=detail.cognome if detail else None,
        fallback_nome=detail.nome if detail else None,
    )
    return {
        "cognome": detail.cognome if detail and detail.cognome else cognome,
        "nome": detail.nome if detail and detail.nome else nome,
        "codice_fiscale": normalized_cf or "",
        "data_nascita": detail.data_nascita if detail else intestatario.data_nascita,
        "comune_nascita": (detail.luogo_nascita if detail else None) or intestatario.luogo_nascita,
        "indirizzo": (
            _compose_address(
                detail.residenza_toponimo if detail else None,
                detail.residenza_indirizzo if detail else None,
                detail.residenza_civico if detail else None,
                detail.residenza_sub if detail else None,
            )
            if detail
            else None
        )
        or intestatario.residenza,
        "comune_residenza": (
            (detail.residenza_localita if detail else None)
            or (detail.residenza_belfiore if detail else None)
            or intestatario.comune_residenza
        ),
        "cap": (detail.residenza_cap if detail else None) or intestatario.cap,
        "email": detail.email if detail else None,
        "telefono": (detail.telefono or detail.cellulare) if detail else None,
        "note": " | ".join(detail.note) if detail and detail.note else None,
    }


class _CapacitasLiveResolver:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._manager: CapacitasSessionManager | None = None
        self._client: InVoltureClient | None = None
        self._credential_id: int | None = None
        self._disabled = False
        self._cert_cache: dict[tuple[str, str, str, str, str], CapacitasTerrenoCertificato] = {}
        self._detail_cache: dict[tuple[str, str], CapacitasAnagraficaDetail] = {}
        self._frazione_cache: dict[str, list[str]] = {}
        self._sync_attempted_particelle: set[UUID] = set()
        self.dirty = False

    async def close(self) -> None:
        if self._manager is not None:
            await self._manager.close()
            self._manager = None
            self._client = None

    async def enrich_match(self, p: CatParticella, match: CatAnagraficaMatch) -> CatAnagraficaMatch:
        if match.utenza_latest is None:
            synced = await self._sync_particella_from_live_terreni(p)
            if synced:
                match = _build_match(
                    self._db,
                    p,
                    presente_in_catasto_consorzio=(p.id in _load_consorzio_presence_by_particella_ids(self._db, {p.id})),
                )

        cert_params = self._resolve_cert_params(p, match)
        if cert_params is None:
            synced = await self._sync_particella_from_live_terreni(p)
            if synced:
                match = _build_match(
                    self._db,
                    p,
                    presente_in_catasto_consorzio=(p.id in _load_consorzio_presence_by_particella_ids(self._db, {p.id})),
                )
                cert_params = self._resolve_cert_params(p, match)
        if cert_params is None:
            return match

        certificato = await self._fetch_certificato(*cert_params)
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
                frazione_candidates = await _resolve_batch_frazione_candidates(
                    client,
                    lookup_comune,
                    None,
                    self._frazione_cache,
                )
            except Exception:
                continue

            for frazione_id in frazione_candidates:
                request = CapacitasTerreniSearchRequest(
                    frazione_id=frazione_id,
                    sezione="",
                    foglio=foglio,
                    particella=particella,
                    sub=sub or "",
                )
                try:
                    result = await sync_terreni_for_request(
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
                    if "non trov" in normalized or "nessun" in normalized or "no result" in normalized:
                        continue
                    return matches
                except Exception:
                    self._db.rollback()
                    return matches

                live_matches = self._build_live_matches_from_search_key(
                    search_key=result.search_key,
                    input_comune=comune,
                    lookup_comune=lookup_comune,
                    foglio=foglio,
                    particella=particella,
                    sub=sub,
                )
                for match in live_matches:
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
        row: CatCapacitasTerrenoRow,
        *,
        input_comune: str,
        lookup_comune: str,
    ) -> CatAnagraficaMatch:
        unit = self._db.get(CatConsorzioUnit, row.unit_id) if row.unit_id else None
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

        cert_com = _norm_str(row.com)
        cert_pvc = _norm_str(row.pvc)
        cert_fra = _norm_str(row.fra)
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
            superficie_mq=row.superficie_mq,
            superficie_grafica_mq=particella_record.superficie_grafica_mq if particella_record is not None else None,
            presente_in_catasto_consorzio=bool(unit is not None or particella_record is not None),
            utenza_latest=CatAnagraficaUtenzaSummary(
                id=(unit.id if unit is not None else uuid4()),
                cco=row.cco,
                anno_campagna=_safe_int(row.anno),
                stato="capacitas_live",
                num_distretto=None,
                nome_distretto=None,
                sup_irrigabile_mq=row.superficie_mq,
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
            frazione_candidates = await _resolve_batch_frazione_candidates(
                client,
                comune_value,
                p.sezione_catastale,
                self._frazione_cache,
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

        attempted_errors: list[str] = []
        for frazione_id in frazione_candidates:
            request = CapacitasTerreniSearchRequest(
                frazione_id=frazione_id,
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
                return True
            except RuntimeError as exc:
                self._db.rollback()
                attempted_errors.append(str(exc))
                normalized = str(exc).casefold()
                if "non trov" not in normalized and "nessun" not in normalized and "no result" not in normalized:
                    logger.info(
                        "Capacitas live terreni sync interrotta: particella_id=%s frazione=%s err=%s",
                        p.id,
                        frazione_id,
                        exc,
                    )
                    return False
            except Exception as exc:
                self._db.rollback()
                logger.warning(
                    "Capacitas live terreni sync fallita: particella_id=%s frazione=%s err=%s",
                    p.id,
                    frazione_id,
                    exc,
                )
                return False

        if attempted_errors:
            logger.info(
                "Capacitas live terreni nessun risultato: particella_id=%s comune=%s sezione=%s foglio=%s particella=%s tentativi=%s",
                p.id,
                comune_value,
                p.sezione_catastale,
                p.foglio,
                p.particella,
                frazione_candidates,
            )
        return False

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

        if utenza is not None:
            occupancy = self._db.execute(
                select(CatConsorzioOccupancy)
                .where(CatConsorzioOccupancy.utenza_id == utenza.id)
                .where(CatConsorzioOccupancy.com.is_not(None))
                .order_by(desc(CatConsorzioOccupancy.updated_at))
                .limit(1)
            ).scalar_one_or_none()
            if occupancy is not None:
                return (cco, occupancy.com or "", occupancy.pvc or "", occupancy.fra or "", occupancy.ccs or "00000")

        certificato = self._db.execute(
            select(CatCapacitasCertificato)
            .where(CatCapacitasCertificato.cco == cco)
            .where(CatCapacitasCertificato.com.is_not(None))
            .order_by(desc(CatCapacitasCertificato.collected_at))
            .limit(1)
        ).scalar_one_or_none()
        if certificato is not None:
            return (cco, certificato.com or "", certificato.pvc or "", certificato.fra or "", certificato.ccs or "00000")

        row = self._db.execute(
            select(CatCapacitasTerrenoRow)
            .join(CatConsorzioUnit, CatConsorzioUnit.id == CatCapacitasTerrenoRow.unit_id)
            .where(CatConsorzioUnit.particella_id == p.id)
            .where(CatCapacitasTerrenoRow.cco == cco)
            .where(CatCapacitasTerrenoRow.com.is_not(None))
            .order_by(desc(CatCapacitasTerrenoRow.collected_at))
            .limit(1)
        ).scalar_one_or_none()
        if row is None:
            return None
        return (cco, row.com or "", row.pvc or "", row.fra or "", row.ccs or "00000")

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

    def _find_local_intestatario(self, intestatario: CapacitasIntestatario) -> CatIntestatarioResponse | None:
        normalized_cf = _normalize_cf(intestatario.codice_fiscale)
        person: AnagraficaPerson | None = None
        subject: AnagraficaSubject | None = None

        if normalized_cf:
            person = self._db.scalar(select(AnagraficaPerson).where(AnagraficaPerson.codice_fiscale == normalized_cf))
            if person is not None:
                subject = self._db.get(AnagraficaSubject, person.subject_id)

        if person is None and intestatario.idxana:
            subject = self._db.scalar(
                select(AnagraficaSubject).where(
                    AnagraficaSubject.source_system == "capacitas",
                    AnagraficaSubject.source_external_id == intestatario.idxana,
                )
            )
            if subject is not None:
                person = self._db.get(AnagraficaPerson, subject.id)

        if person is None or subject is None:
            return None
        return _person_response_from_db(person, subject, deceduto=intestatario.deceduto)

    def _upsert_live_intestatario(
        self,
        intestatario: CapacitasIntestatario,
        detail: CapacitasAnagraficaDetail | None,
    ) -> CatIntestatarioResponse | None:
        normalized_cf = _normalize_cf((detail.codice_fiscale if detail else None) or intestatario.codice_fiscale)
        person: AnagraficaPerson | None = None
        subject: AnagraficaSubject | None = None

        if normalized_cf:
            person = self._db.scalar(select(AnagraficaPerson).where(AnagraficaPerson.codice_fiscale == normalized_cf))
            if person is not None:
                subject = self._db.get(AnagraficaSubject, person.subject_id)

        if person is None and (detail.idxana if detail else intestatario.idxana):
            subject = self._db.scalar(
                select(AnagraficaSubject).where(
                    AnagraficaSubject.source_system == "capacitas",
                    AnagraficaSubject.source_external_id == ((detail.idxana if detail else None) or intestatario.idxana),
                )
            )
            if subject is not None:
                person = self._db.get(AnagraficaPerson, subject.id)

        if person is None and not normalized_cf:
            return None

        person_data = _build_person_payload_from_current_capacitas(detail, intestatario, normalized_cf)
        collected_at = datetime.now(timezone.utc)

        if person is None:
            assert normalized_cf is not None
            subject = AnagraficaSubject(
                subject_type=AnagraficaSubjectType.PERSON.value,
                status=AnagraficaSubjectStatus.ACTIVE.value,
                source_system="capacitas",
                source_external_id=(detail.idxana if detail else None) or intestatario.idxana,
                source_name_raw=(detail.denominazione if detail else None) or intestatario.denominazione or normalized_cf,
                requires_review=False,
            )
            self._db.add(subject)
            self._db.flush()
            person = AnagraficaPerson(subject_id=subject.id, **person_data)
            self._db.add(person)
            self._db.flush()
            self.dirty = True
            return _person_response_from_db(person, subject, deceduto=intestatario.deceduto)

        if subject is None:
            subject = self._db.get(AnagraficaSubject, person.subject_id)
        if subject is None:
            return None

        snapshot_person_if_changed(
            self._db,
            person,
            person_data,
            source_system="capacitas",
            source_ref=(detail.idxana if detail else None) or intestatario.idxana,
            collected_at=collected_at,
        )
        for key, value in person_data.items():
            setattr(person, key, value)
        if ((detail.idxana if detail else None) or intestatario.idxana) and subject.source_external_id is None:
            subject.source_external_id = (detail.idxana if detail else None) or intestatario.idxana
        if not subject.source_name_raw:
            subject.source_name_raw = (detail.denominazione if detail else None) or intestatario.denominazione or normalized_cf
        self._db.flush()
        self.dirty = True
        return _person_response_from_db(person, subject, deceduto=intestatario.deceduto)


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


def _load_intestatari_by_utenza_ids(db: Session, utenza_ids: list[UUID]) -> list[CatIntestatarioResponse]:
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
            else _normalize_cf(row.codice_fiscale)
            or row.idxana
            or str(row.id)
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
    query = select(CatCapacitasCertificato).where(CatCapacitasCertificato.cco == cco)

    com_norm = _norm_str(com)
    pvc_norm = _norm_str(pvc)
    fra_norm = _norm_str(fra)
    ccs_norm = _normalize_ccs(ccs) if any(value is not None for value in (com, pvc, fra, ccs)) else None

    if com_norm is not None:
        query = query.where(CatCapacitasCertificato.com == com_norm)
    if pvc_norm is not None:
        query = query.where(CatCapacitasCertificato.pvc == pvc_norm)
    if fra_norm is not None:
        query = query.where(CatCapacitasCertificato.fra == fra_norm)
    if ccs_norm is not None:
        query = query.where(func.coalesce(CatCapacitasCertificato.ccs, "00000") == ccs_norm)

    return db.execute(query.order_by(desc(CatCapacitasCertificato.collected_at)).limit(1)).scalars().first()


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
    return items


def _context_from_occupancy(occupancy: CatConsorzioOccupancy | None) -> tuple[str | None, str | None, str | None, str | None]:
    if occupancy is None:
        return (None, None, None, None)
    return (
        _norm_str(occupancy.com),
        _norm_str(occupancy.pvc),
        _norm_str(occupancy.fra),
        _normalize_ccs(occupancy.ccs),
    )


def _context_from_values(
    com: str | None,
    pvc: str | None,
    fra: str | None,
    ccs: str | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    return (_norm_str(com), _norm_str(pvc), _norm_str(fra), _normalize_ccs(ccs))


def _collect_local_cert_contexts(db: Session, *, cco: str) -> list[tuple[str, str, str, str]]:
    contexts: set[tuple[str, str, str, str]] = set()

    def _add_context(com: str | None, pvc: str | None, fra: str | None, ccs: str | None) -> None:
        normalized = _context_from_values(com, pvc, fra, ccs)
        if all(normalized[:3]):
            contexts.add(
                (
                    normalized[0] or "",
                    normalized[1] or "",
                    normalized[2] or "",
                    normalized[3] or "00000",
                )
            )

    for cert in db.execute(select(CatCapacitasCertificato).where(CatCapacitasCertificato.cco == cco)).scalars().all():
        _add_context(cert.com, cert.pvc, cert.fra, cert.ccs)
    for occupancy in db.execute(select(CatConsorzioOccupancy).where(CatConsorzioOccupancy.cco == cco)).scalars().all():
        _add_context(occupancy.com, occupancy.pvc, occupancy.fra, occupancy.ccs)
    for row in db.execute(select(CatCapacitasTerrenoRow).where(CatCapacitasTerrenoRow.cco == cco)).scalars().all():
        _add_context(row.com, row.pvc, row.fra, row.ccs)

    return sorted(contexts)


def _is_sentinel_cco(cco: str) -> bool:
    """Returns True for Capacitas placeholder CCOs (e.g. 014099999) that are shared
    across many unrelated sub-units and do not carry reliable intestatario data."""
    return cco.endswith("99999")


def _load_intestatari_from_cco(db: Session, cco: str) -> list[CatIntestatarioResponse]:
    return _load_intestatari_from_cert_context(db, cco=cco)


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

    if latest_occupancy is not None and _norm_str(latest_occupancy.cco) == cco_norm:
        return _context_from_occupancy(latest_occupancy)

    occupancy = (
        db.execute(
            select(CatConsorzioOccupancy)
            .join(CatConsorzioUnit, CatConsorzioUnit.id == CatConsorzioOccupancy.unit_id)
            .where(
                CatConsorzioUnit.particella_id == p.id,
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
        utenza_com = str(latest_utenza.cod_comune_capacitas) if latest_utenza.cod_comune_capacitas is not None else None
        utenza_fra = str(latest_utenza.cod_frazione) if latest_utenza.cod_frazione is not None else None
        cert = _find_certificato_snapshot(db, cco=cco_norm, com=utenza_com, fra=utenza_fra)
        if cert is not None:
            return _context_from_values(cert.com, cert.pvc, cert.fra, cert.ccs)

    if latest_utenza is not None:
        row = (
            db.execute(
                select(CatCapacitasTerrenoRow)
                .join(CatConsorzioUnit, CatConsorzioUnit.id == CatCapacitasTerrenoRow.unit_id)
                .where(
                    CatConsorzioUnit.particella_id == p.id,
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

    unique_contexts = _collect_local_cert_contexts(db, cco=cco_norm)
    if len(unique_contexts) == 1:
        return unique_contexts[0]

    return (None, None, None, None)


def _current_base_match_data(
    db: Session,
    p: CatParticella,
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

    utenza_ids: list[UUID] = [latest_utenza.id] if latest_utenza is not None else []
    intestatari = _load_intestatari_by_utenza_ids(db, utenza_ids) if utenza_ids else []
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

    status_context = _load_cert_status_from_context(
        db,
        cco=cco,
        com=cert_context[0],
        pvc=cert_context[1],
        fra=cert_context[2],
        ccs=cert_context[3],
    )

    return utenza_summary, intestatari, cert_context, status_context


def _build_consorzio_sub_matches(db: Session, p: CatParticella) -> list[CatAnagraficaMatch]:
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
    base_utenza_summary, base_intestatari, base_cert_context, base_status_context = _current_base_match_data(db, p)

    for unit in sub_units:
        occupancy = _best_occupancy_for_unit(db, unit.id)
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
        elif base_utenza_summary is not None and base_intestatari:
            utenza_summary = base_utenza_summary
            intestatari = list(base_intestatari)
            cert_com, cert_pvc, cert_fra, cert_ccs = base_cert_context
            stato_ruolo, stato_cnc = base_status_context
            note = "Presenti dati non aggiornati/storici del sub: intestatario corrente derivato dalla particella base"
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
    base_intestatari: list[CatIntestatarioResponse] = []
    base_cert_context: tuple[str | None, str | None, str | None, str | None] = (None, None, None, None)
    base_status_context: tuple[str | None, str | None] = (None, None)
    if base_particella is not None:
        base_utenza_summary, base_intestatari, base_cert_context, base_status_context = _current_base_match_data(db, base_particella)
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
    elif base_utenza_summary is not None and base_intestatari:
        utenza_summary = base_utenza_summary
        intestatari = list(base_intestatari)
        cert_com, cert_pvc, cert_fra, cert_ccs = base_cert_context
        stato_ruolo, stato_cnc = base_status_context
        note = "Presenti dati non aggiornati/storici del sub: intestatario corrente derivato dalla particella base"
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


def _build_match(db: Session, p: CatParticella, *, presente_in_catasto_consorzio: bool) -> CatAnagraficaMatch:
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
    latest_occupancy = None
    if latest_utenza is None:
        latest_occupancy = (
            db.execute(
                select(CatConsorzioOccupancy)
                .join(CatConsorzioUnit, CatConsorzioUnit.id == CatConsorzioOccupancy.unit_id)
                .where(
                    CatConsorzioUnit.particella_id == p.id,
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

    utenza_ids = [u.id for u in utenze]
    intestatari = _load_intestatari_by_utenza_ids(db, utenza_ids)
    if not intestatari:
        cfs = {u.codice_fiscale.strip().upper() for u in utenze if u.codice_fiscale and u.codice_fiscale.strip()}
        intestatari_by_cf = _load_intestatari_by_cf(db, cfs)
        intestatari = list(intestatari_by_cf.values())

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
    stato_ruolo, stato_cnc = _load_cert_status_from_context(
        db,
        cco=(latest_utenza.cco if latest_utenza is not None else None) or (latest_occupancy.cco if latest_occupancy is not None else None),
        com=cert_com,
        pvc=cert_pvc,
        fra=cert_fra,
        ccs=cert_ccs,
    )

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
            else _normalize_cf(row.codice_fiscale)
            or row.idxana
            or str(row.id)
        )
        if key in seen_by_particella[particella_id]:
            continue
        seen_by_particella[particella_id].add(key)
        items[particella_id].append(_intestatario_response_from_utenza_row(db, row))

    return dict(items)


def _refresh_saved_particelle_matches(
    db: Session,
    results: list[CatAnagraficaBulkSearchRowResult],
) -> list[CatAnagraficaBulkSearchRowResult]:
    particella_ids: set[UUID] = set()
    for row in results:
        if row.match is not None:
            particella_ids.add(row.match.particella_id)
        if row.matches:
            particella_ids.update(match.particella_id for match in row.matches)

    consorzio_unit_ids = _load_consorzio_presence_by_particella_ids(db, particella_ids)
    particelle_con_utenza = _particelle_with_utenza_irrigua(db, particella_ids)
    intestatari_by_particella = _load_intestatari_by_particella_ids(db, particella_ids)

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
                match.intestatari = _load_intestatari_from_cert_context(
                    db,
                    cco=cco,
                    com=cert_com,
                    pvc=cert_pvc,
                    fra=cert_fra,
                    ccs=cert_ccs,
                )
                match.utenza_latest = _utenza_summary_from_occupancy(occupancy) if occupancy else match.utenza_latest
                match.note = None
                match.stato_ruolo, match.stato_cnc = _load_cert_status_from_context(
                    db,
                    cco=cco,
                    com=cert_com,
                    pvc=cert_pvc,
                    fra=cert_fra,
                    ccs=cert_ccs,
                )
            elif base_particella is not None:
                base_utenza_summary, base_intestatari, base_cert_context, base_status_context = _current_base_match_data(db, base_particella)
                if base_utenza_summary is not None and base_intestatari:
                    match.utenza_latest = base_utenza_summary
                    match.intestatari = list(base_intestatari)
                    cert_com, cert_pvc, cert_fra, cert_ccs = base_cert_context
                    match.stato_ruolo, match.stato_cnc = base_status_context
                    match.note = "Presenti dati non aggiornati/storici del sub: intestatario corrente derivato dalla particella base"
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


@router.post("", response_model=CatAnagraficaBulkSearchResponse)
async def bulk_search_anagrafica(
    payload: CatAnagraficaBulkSearchRequest = Body(...),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatAnagraficaBulkSearchResponse:
    results: list[CatAnagraficaBulkSearchRowResult] = []
    live_resolver = _CapacitasLiveResolver(db) if payload.include_capacitas_live else None

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
                    consorzio_present_ids = _load_consorzio_presence_by_particella_ids(
                        db, {p.id for p in particelle if p.id is not None}
                    )
                    matches: list[CatAnagraficaMatch] = []
                    for p in particelle:
                        match = _build_match(db, p, presente_in_catasto_consorzio=(p.id in consorzio_present_ids))
                        if live_resolver is not None:
                            match = await live_resolver.enrich_match(p, match)
                        matches.append(match)

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
                    if live_resolver is not None and live_resolver.dirty:
                        db.commit()
                        live_resolver.dirty = False
                    continue

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
                    continue

                items = _query_particelle_candidates(
                    db,
                    comune_norm=comune_norm,
                    sezione_norm=sezione_norm,
                    foglio_norm=foglio_norm,
                    particella_norm=particella_norm,
                    sub_norm=sub_norm,
                )
                if len(items) == 0:
                    # Fallback: sub explicitly given but not in CatParticella — try CatConsorzioUnit directly
                    sub_match: CatAnagraficaMatch | None = None
                    if sub_norm and foglio_norm and particella_norm and comune_norm:
                        sub_match = _find_consorzio_sub_match(db, foglio_norm, particella_norm, sub_norm, comune_norm)
                    if sub_match is not None and live_resolver is not None:
                        particella_ref = db.get(CatParticella, sub_match.particella_id)
                        if particella_ref is not None:
                            sub_match = await live_resolver.enrich_match(particella_ref, sub_match)
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
                        if len(live_matches) == 1:
                            live_match = live_matches[0]
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
                                    particella_id=live_match.particella_id,
                                    match=live_match,
                                    matches_count=1,
                                )
                            )
                        elif len(live_matches) > 1:
                            results.append(
                                CatAnagraficaBulkSearchRowResult(
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
                            )
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
                        if live_resolver.dirty:
                            db.commit()
                            live_resolver.dirty = False
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
                    continue

                if len(items) > 1:
                    consorzio_present_ids = _load_consorzio_presence_by_particella_ids(
                        db, {p.id for p in items if p.id is not None}
                    )
                    matches: list[CatAnagraficaMatch] = []
                    for item in items:
                        candidate = _build_match(
                            db,
                            item,
                            presente_in_catasto_consorzio=(item.id in consorzio_present_ids),
                        )
                        if live_resolver is not None:
                            candidate = await live_resolver.enrich_match(item, candidate)
                        matches.append(candidate)
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
                    if live_resolver is not None and live_resolver.dirty:
                        db.commit()
                        live_resolver.dirty = False
                    continue

                consorzio_present_ids = _load_consorzio_presence_by_particella_ids(
                    db, {items[0].id} if items[0].id is not None else set()
                )
                match = _build_match(
                    db,
                    items[0],
                    presente_in_catasto_consorzio=(items[0].id in consorzio_present_ids),
                )
                if live_resolver is not None:
                    match = await live_resolver.enrich_match(items[0], match)

                sub_matches: list[CatAnagraficaMatch] | None = None
                if not sub_norm:
                    sub_matches = _build_consorzio_sub_matches(db, items[0]) or None
                    if sub_matches and live_resolver is not None:
                        sub_matches = [await live_resolver.enrich_match(items[0], sub_match) for sub_match in sub_matches]

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
                if live_resolver is not None and live_resolver.dirty:
                    db.commit()
                    live_resolver.dirty = False
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
    finally:
        if live_resolver is not None:
            await live_resolver.close()

    return CatAnagraficaBulkSearchResponse(results=results)


@router.post("/jobs", response_model=CatAnagraficaBulkJobDetail)
async def create_bulk_search_job(
    request: CatAnagraficaBulkJobCreateRequest = Body(...),
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
) -> CatAnagraficaBulkJobDetail:
    payload = request.payload
    # Determine the effective kind exactly like the search endpoint.
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
            return "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"
        return "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"

    kind: Literal["CF_PIVA_PARTICELLE", "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"] = infer_kind()

    response = await bulk_search_anagrafica(payload=payload, db=db, _=user)

    summary = _build_summary(response.results)
    job = CatastoElaborazioniMassiveJob(
        user_id=user.id,
        kind=str(kind),
        source_filename=_norm_str(request.source_filename),
        skipped_rows=max(int(request.skipped_rows or 0), 0),
        payload_json=payload.model_dump(mode="json"),
        results_json={"results": [r.model_dump(mode="json") for r in response.results]},
        summary_json=summary,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return CatAnagraficaBulkJobDetail(
        id=job.id,
        created_at=job.created_at,
        source_filename=job.source_filename,
        kind=job.kind,  # type: ignore[arg-type]
        skipped_rows=job.skipped_rows,
        summary=CatAnagraficaBulkJobSummary(**job.summary_json),
        results=response.results,
    )


@router.post("/jobs/save", response_model=CatAnagraficaBulkJobDetail)
async def save_bulk_search_job(
    request: CatAnagraficaBulkJobSaveRequest = Body(...),
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
) -> CatAnagraficaBulkJobDetail:
    payload = request.payload

    def infer_kind() -> Literal["CF_PIVA_PARTICELLE", "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"]:
        if payload.kind in ("CF_PIVA_PARTICELLE", "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"):
            return payload.kind
        has_particella_keys = any((r.comune or r.foglio or r.particella or r.sub or r.sezione) for r in payload.rows)
        has_tax_keys = any((r.codice_fiscale or r.partita_iva) for r in payload.rows)
        if has_particella_keys and not has_tax_keys:
            return "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"
        if has_tax_keys and not has_particella_keys:
            return "CF_PIVA_PARTICELLE"
        return "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"

    kind = infer_kind()
    summary = _build_summary(request.results)
    job = CatastoElaborazioniMassiveJob(
        user_id=user.id,
        kind=str(kind),
        source_filename=_norm_str(request.source_filename),
        skipped_rows=max(int(request.skipped_rows or 0), 0),
        payload_json=payload.model_dump(mode="json"),
        results_json={"results": [r.model_dump(mode="json") for r in request.results]},
        summary_json=summary,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return CatAnagraficaBulkJobDetail(
        id=job.id,
        created_at=job.created_at,
        source_filename=job.source_filename,
        kind=job.kind,  # type: ignore[arg-type]
        skipped_rows=job.skipped_rows,
        summary=CatAnagraficaBulkJobSummary(**job.summary_json),
        results=request.results,
    )


@router.get("/jobs", response_model=CatAnagraficaBulkJobListResponse)
async def list_bulk_search_jobs(
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
    limit: int = Query(5, ge=1, le=20),
) -> CatAnagraficaBulkJobListResponse:
    rows = (
        db.execute(
            select(CatastoElaborazioniMassiveJob)
            .where(CatastoElaborazioniMassiveJob.user_id == user.id)
            .order_by(desc(CatastoElaborazioniMassiveJob.created_at))
            .limit(limit)
        )
        .scalars()
        .all()
    )

    items: list[CatAnagraficaBulkJobItem] = []
    for job in rows:
        items.append(
            CatAnagraficaBulkJobItem(
                id=job.id,
                created_at=job.created_at,
                source_filename=job.source_filename,
                kind=job.kind,  # type: ignore[arg-type]
                skipped_rows=job.skipped_rows,
                summary=CatAnagraficaBulkJobSummary(**job.summary_json),
            )
        )

    return CatAnagraficaBulkJobListResponse(items=items)


@router.delete("/jobs", response_model=dict[str, int])
async def delete_bulk_search_jobs(
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
) -> dict[str, int]:
    rows = (
        db.execute(
            select(CatastoElaborazioniMassiveJob).where(CatastoElaborazioniMassiveJob.user_id == user.id)
        )
        .scalars()
        .all()
    )
    deleted = len(rows)
    for job in rows:
        db.delete(job)
    db.commit()
    return {"deleted": deleted}


@router.get("/jobs/{job_id}", response_model=CatAnagraficaBulkJobDetail)
async def get_bulk_search_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_active_user),
) -> CatAnagraficaBulkJobDetail:
    job = (
        db.execute(
            select(CatastoElaborazioniMassiveJob)
            .where(CatastoElaborazioniMassiveJob.id == job_id)
            .where(CatastoElaborazioniMassiveJob.user_id == user.id)
            .limit(1)
        )
        .scalars()
        .one_or_none()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trovato")

    raw_results = job.results_json.get("results") if isinstance(job.results_json, dict) else None
    results = [CatAnagraficaBulkSearchRowResult.model_validate(r) for r in (raw_results or [])]

    payload_has_live_results = (
        isinstance(job.payload_json, dict)
        and bool(job.payload_json.get("include_capacitas_live"))
    )
    if job.kind == "COMUNE_FOGLIO_PARTICELLA_INTESTATARI" and not payload_has_live_results:
        results = _refresh_saved_particelle_matches(db, results)
        job.results_json = {"results": [r.model_dump(mode="json") for r in results]}
        job.summary_json = _build_summary(results)
        db.commit()
        db.refresh(job)

    return CatAnagraficaBulkJobDetail(
        id=job.id,
        created_at=job.created_at,
        source_filename=job.source_filename,
        kind=job.kind,  # type: ignore[arg-type]
        skipped_rows=job.skipped_rows,
        summary=CatAnagraficaBulkJobSummary(**job.summary_json),
        results=results,
    )
