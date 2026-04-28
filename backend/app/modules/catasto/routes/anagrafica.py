from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

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
    CatCapacitasTerrenoRow,
    CatComune,
    CatConsorzioOccupancy,
    CatConsorzioUnit,
    CatParticella,
    CatUtenzaIrrigua,
)
from app.modules.elaborazioni.capacitas.client import InVoltureClient
from app.modules.elaborazioni.capacitas.models import CapacitasAnagraficaDetail, CapacitasIntestatario, CapacitasTerrenoCertificato
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
from app.modules.utenze.models import AnagraficaPerson, AnagraficaSubject, AnagraficaSubjectStatus, AnagraficaSubjectType
from app.modules.utenze.services.person_history_service import snapshot_person_if_changed
from app.schemas.catasto_phase1 import (
    CatAnagraficaBulkSearchRequest,
    CatAnagraficaBulkSearchResponse,
    CatAnagraficaBulkJobCreateRequest,
    CatAnagraficaBulkJobDetail,
    CatAnagraficaBulkJobItem,
    CatAnagraficaBulkJobListResponse,
    CatAnagraficaBulkJobSummary,
    CatAnagraficaBulkSearchRowResult,
    CatAnagraficaMatch,
    CatAnagraficaUtenzaSummary,
    CatIntestatarioResponse,
)
from app.services.elaborazioni_capacitas import mark_credential_error, mark_credential_used, pick_credential

router = APIRouter(prefix="/catasto/elaborazioni-massive/particelle", tags=["catasto-elaborazioni-massive"])
logger = logging.getLogger(__name__)


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


def _normalize_cf(value: str | None) -> str | None:
    normalized = _norm_str(value)
    return normalized.upper() if normalized else None


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
        self.dirty = False

    async def close(self) -> None:
        if self._manager is not None:
            await self._manager.close()
            self._manager = None
            self._client = None

    async def enrich_match(self, p: CatParticella, match: CatAnagraficaMatch) -> CatAnagraficaMatch:
        cert_params = self._resolve_cert_params(p, match.utenza_latest)
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
        return match

    def _resolve_cert_params(
        self,
        p: CatParticella,
        utenza: CatAnagraficaUtenzaSummary | None,
    ) -> tuple[str, str, str, str, str] | None:
        cco = _norm_str(utenza.cco if utenza else None)
        if not cco:
            return None

        certificato = self._db.execute(
            select(CatCapacitasCertificato)
            .where(CatCapacitasCertificato.cco == cco)
            .where(CatCapacitasCertificato.com.is_not(None))
            .order_by(desc(CatCapacitasCertificato.collected_at))
            .limit(1)
        ).scalar_one_or_none()
        if certificato is not None:
            return (cco, certificato.com or "", certificato.pvc or "", certificato.fra or "", certificato.ccs or "00000")

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
async def bulk_search_anagrafica(
    payload: CatAnagraficaBulkSearchRequest = Body(...),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatAnagraficaBulkSearchResponse:
    results: list[CatAnagraficaBulkSearchRowResult] = []
    live_resolver = _CapacitasLiveResolver(db)

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
                    matches: list[CatAnagraficaMatch] = []
                    for p in particelle:
                        match = _build_match(db, p)
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
                    if live_resolver.dirty:
                        db.commit()
                        live_resolver.dirty = False
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
                    matches: list[CatAnagraficaMatch] = []
                    for item in items:
                        candidate = _build_match(db, item)
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
                    if live_resolver.dirty:
                        db.commit()
                        live_resolver.dirty = False
                    continue

                match = _build_match(db, items[0])
                match = await live_resolver.enrich_match(items[0], match)
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
                if live_resolver.dirty:
                    db.commit()
                    live_resolver.dirty = False
            except Exception as exc:
                if live_resolver.dirty:
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
        payload_json=payload.model_dump(),
        results_json={"results": [r.model_dump() for r in response.results]},
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
    return CatAnagraficaBulkJobDetail(
        id=job.id,
        created_at=job.created_at,
        source_filename=job.source_filename,
        kind=job.kind,  # type: ignore[arg-type]
        skipped_rows=job.skipped_rows,
        summary=CatAnagraficaBulkJobSummary(**job.summary_json),
        results=results,
    )
