from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import re
from typing import Awaitable, Callable, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import (
    CatCapacitasCertificato,
    CatCapacitasIntestatario,
    CatCapacitasTerrenoDetail,
    CatCapacitasTerrenoRow,
    CatComune,
    CatConsorzioOccupancy,
    CatConsorzioUnit,
    CatConsorzioUnitSegment,
    CatParticella,
    CatUtenzaIntestatario,
    CatUtenzaIrrigua,
)
from app.modules.utenze.models import AnagraficaPerson, AnagraficaSubject, AnagraficaSubjectStatus, AnagraficaSubjectType
from app.modules.utenze.services.person_history_service import persist_person_source_snapshot, snapshot_person_if_changed
from app.models.capacitas import CapacitasTerreniSyncJob
from app.modules.elaborazioni.capacitas.apps.involture.client import CapacitasSessionExpiredError, InVoltureClient
from app.modules.elaborazioni.capacitas.models import (
    CapacitasAnagraficaDetail,
    CapacitasStoricoAnagraficaRow,
    CapacitasTerreniBatchItem,
    CapacitasTerreniBatchItemResult,
    CapacitasTerreniBatchRequest,
    CapacitasTerreniBatchResponse,
    CapacitasTerreniJobOut,
    CapacitasTerreniSearchRequest,
    CapacitasTerreniSyncResponse,
    CapacitasIntestatario,
    CapacitasTerrenoCertificato,
    CapacitasTerrenoDetail,
    CapacitasTerrenoRow,
)


TerreniItemProgressCallback = Callable[[CapacitasTerreniBatchItemResult], Awaitable[None]]


class CapacitasFrazioneAmbiguaError(RuntimeError):
    """Raised when multiple frazioni return results for the same foglio/particella."""

    def __init__(self, message: str, candidates: list[dict]) -> None:
        super().__init__(message)
        self.candidates = candidates


_COMUNE_SWAP_CODES: dict[int, int] = {
    165: 280,  # Arborea -> Terralba
    280: 165,  # Terralba -> Arborea
}

BASE_TERRENI_THROTTLE_MS = 300
DOUBLE_SPEED_MULTIPLIER = 2
MAX_TERRENI_PARALLEL_WORKERS = 2
TERRENI_STALE_JOB_MINUTES = 30
AUTO_RESUME_TERRENI_MODES = {"batch"}
UTC = timezone.utc


@dataclass(slots=True)
class SyncCounters:
    rows: int = 0
    certificati: int = 0
    details: int = 0
    units: set[str] | None = None
    occupancies: int = 0

    def __post_init__(self) -> None:
        if self.units is None:
            self.units = set()


@dataclass(slots=True)
class TerreniSyncPolicy:
    throttle_ms: int
    speed_multiplier: int
    parallel_workers: int


def compute_terreni_sync_policy(
    *,
    double_speed: bool = False,
    parallel_workers: int = 1,
    throttle_ms: int | None = None,
) -> TerreniSyncPolicy:
    speed_multiplier = DOUBLE_SPEED_MULTIPLIER if double_speed else 1
    effective_throttle_ms = max(
        0,
        throttle_ms if throttle_ms is not None else round(BASE_TERRENI_THROTTLE_MS / speed_multiplier),
    )
    worker_count = max(1, min(MAX_TERRENI_PARALLEL_WORKERS, parallel_workers))
    return TerreniSyncPolicy(
        throttle_ms=effective_throttle_ms,
        speed_multiplier=speed_multiplier,
        parallel_workers=worker_count,
    )


async def sync_terreni_for_request(
    db: Session,
    client: InVoltureClient,
    request: CapacitasTerreniSearchRequest,
    *,
    fetch_certificati: bool = True,
    fetch_details: bool = True,
    throttle_ms: int = 0,
) -> CapacitasTerreniSyncResponse:
    effective_request = request
    result = await client.search_terreni(effective_request)
    if not result.rows and request.sezione.strip():
        effective_request = request.model_copy(update={"sezione": ""})
        result = await client.search_terreni(effective_request)
    if not result.rows:
        raise RuntimeError(
            f"Particella {request.foglio}/{request.particella}"
            f"{('/' + request.sub) if request.sub else ''} non trovata"
        )
    collected_at = datetime.now(timezone.utc)
    search_key = build_search_key(effective_request)
    counters = SyncCounters()
    certificato_cache: dict[tuple[str, str, str, str, str], tuple[CapacitasTerrenoCertificato, CatCapacitasCertificato]] = {}
    storico_cache: dict[str, list[CapacitasStoricoAnagraficaRow]] = {}
    anagrafica_detail_cache: dict[str, CapacitasAnagraficaDetail] = {}

    for index, row in enumerate(result.rows, start=1):
        unit = _find_or_create_unit(db, row)
        if unit is not None:
            counters.units.add(str(unit.id))

        detail: CapacitasTerrenoDetail | None = None
        if fetch_details and row.external_row_id:
            detail = await client.fetch_terreno_detail(external_row_id=row.external_row_id)
            counters.details += 1

        segment = _find_or_create_segment(db, unit, detail)
        occupancy_created = _find_or_create_occupancy(db, unit, segment, row)
        counters.occupancies += 1 if occupancy_created else 0

        row_snapshot = CatCapacitasTerrenoRow(
            unit_id=unit.id if unit else None,
            search_key=search_key,
            external_row_id=row.external_row_id,
            cco=row.cco,
            fra=row.fra,
            ccs=row.ccs,
            pvc=row.pvc,
            com=row.com,
            belfiore=row.belfiore,
            foglio=row.foglio,
            particella=row.particella,
            sub=row.sub,
            anno=_to_int(row.anno),
            voltura=row.voltura,
            opcode=row.opcode,
            data_reg=row.data_reg,
            superficie_mq=_to_decimal(row.superficie),
            bac_descr=row.bac_descr,
            row_visual_state=row.row_visual_state,
            raw_payload_json=row.model_dump(by_alias=True, exclude_none=True, mode="json"),
            collected_at=collected_at,
        )
        db.add(row_snapshot)
        db.flush()
        counters.rows += 1

        if fetch_certificati and row.cco and row.com and row.pvc and row.fra is not None and row.ccs is not None:
            cache_key = (row.cco, row.com, row.pvc, row.fra or "", row.ccs or "")
            if cache_key not in certificato_cache:
                target_utenza = _find_utenza_for_terreno_row(db, row)
                certificato_cache[cache_key] = await sync_certificato_snapshot(
                    db,
                    client,
                    cco=row.cco,
                    com=row.com,
                    pvc=row.pvc,
                    fra=row.fra or "",
                    ccs=row.ccs or "",
                    collected_at=collected_at,
                    target_utenze=[target_utenza] if target_utenza is not None else None,
                    storico_cache=storico_cache,
                    anagrafica_detail_cache=anagrafica_detail_cache,
                )
                counters.certificati += 1

        if detail is not None:
            db.add(
                CatCapacitasTerrenoDetail(
                    terreno_row_id=row_snapshot.id,
                    external_row_id=detail.external_row_id or row.external_row_id,
                    foglio=detail.foglio,
                    particella=detail.particella,
                    sub=detail.sub,
                    riordino_code=detail.riordino_code,
                    riordino_maglia=detail.riordino_maglia,
                    riordino_lotto=detail.riordino_lotto,
                    irridist=detail.irridist,
                    raw_html=detail.raw_html,
                    parsed_json=detail.model_dump(exclude_none=True, mode="json"),
                    collected_at=collected_at,
                )
            )

        if index < len(result.rows) and throttle_ms > 0:
            await asyncio.sleep(throttle_ms / 1000)

    db.commit()
    return CapacitasTerreniSyncResponse(
        total_rows=result.total,
        imported_rows=counters.rows,
        imported_certificati=counters.certificati,
        imported_details=counters.details,
        linked_units=len(counters.units or set()),
        linked_occupancies=counters.occupancies,
        search_key=search_key,
    )


async def sync_certificato_snapshot(
    db: Session,
    client: InVoltureClient,
    *,
    cco: str,
    com: str,
    pvc: str,
    fra: str,
    ccs: str,
    collected_at: datetime | None = None,
    target_utenze: list[CatUtenzaIrrigua] | None = None,
    persist_snapshot_intestatari: bool = True,
    storico_cache: dict[str, list[CapacitasStoricoAnagraficaRow]] | None = None,
    anagrafica_detail_cache: dict[str, CapacitasAnagraficaDetail] | None = None,
) -> tuple[CapacitasTerrenoCertificato, CatCapacitasCertificato]:
    effective_collected_at = collected_at or datetime.now(timezone.utc)
    effective_storico_cache = storico_cache if storico_cache is not None else {}
    effective_anagrafica_detail_cache = anagrafica_detail_cache if anagrafica_detail_cache is not None else {}

    certificato = await client.fetch_certificato(
        cco=cco,
        com=com,
        pvc=pvc,
        fra=fra,
        ccs=ccs,
    )
    certificato_snapshot = CatCapacitasCertificato(
        cco=certificato.cco or cco,
        fra=certificato.fra or fra,
        ccs=certificato.ccs or ccs,
        pvc=certificato.pvc or pvc,
        com=certificato.com or com,
        partita_code=certificato.partita_code,
        utenza_code=certificato.utenza_code,
        utenza_status=certificato.utenza_status,
        ruolo_status=certificato.ruolo_status or certificato.partita_status,
        raw_html=certificato.raw_html,
        parsed_json=certificato.model_dump(exclude_none=True, mode="json"),
        collected_at=effective_collected_at,
    )
    db.add(certificato_snapshot)
    db.flush()

    await _persist_capacitas_intestatari(
        db,
        client,
        certificato_snapshot,
        certificato,
        effective_collected_at,
        target_utenze=target_utenze,
        persist_snapshot_intestatari=persist_snapshot_intestatari,
        storico_cache=effective_storico_cache,
        anagrafica_detail_cache=effective_anagrafica_detail_cache,
    )
    return certificato, certificato_snapshot


async def refetch_certificati_senza_intestatari(
    db: Session,
    client: InVoltureClient,
    *,
    limit: int = 50,
    throttle_ms: int = 0,
    storico_cache: dict[str, list[CapacitasStoricoAnagraficaRow]] | None = None,
    anagrafica_detail_cache: dict[str, CapacitasAnagraficaDetail] | None = None,
) -> int:
    """Re-fetcha i certificati salvati con 0 intestatari (bug session-state Capacitas).

    Va chiamato in una sessione Capacitas fresca, prima di qualsiasi search_terreni,
    altrimenti si riproduce lo stesso bug di stato sessione.
    Ritorna il numero di certificati ri-fetchati con successo.
    """
    certs_with_intestatari = select(CatCapacitasIntestatario.certificato_id).distinct().scalar_subquery()
    empty_certs = list(
        db.scalars(
            select(CatCapacitasCertificato)
            .where(CatCapacitasCertificato.id.notin_(certs_with_intestatari))
            .where(CatCapacitasCertificato.com.isnot(None))
            .where(CatCapacitasCertificato.pvc.isnot(None))
            .order_by(CatCapacitasCertificato.collected_at.desc())
            .limit(limit)
        ).all()
    )
    if not empty_certs:
        return 0

    effective_storico_cache = storico_cache if storico_cache is not None else {}
    effective_anagrafica_cache = anagrafica_detail_cache if anagrafica_detail_cache is not None else {}
    collected_at = datetime.now(timezone.utc)
    refetched = 0

    for index, cert in enumerate(empty_certs):
        try:
            target_utenze_for_context = _find_utenze_for_cert_context(
                db,
                cco=cert.cco,
                com=cert.com,
                fra=cert.fra,
            )
            target_utenza = target_utenze_for_context[0] if target_utenze_for_context else None
            target_utenze = [target_utenza] if target_utenza is not None else None
            await sync_certificato_snapshot(
                db,
                client,
                cco=cert.cco,
                com=cert.com or "",
                pvc=cert.pvc or "",
                fra=cert.fra or "",
                ccs=cert.ccs or "",
                collected_at=collected_at,
                target_utenze=target_utenze,
                storico_cache=effective_storico_cache,
                anagrafica_detail_cache=effective_anagrafica_cache,
            )
            db.commit()
            refetched += 1
        except Exception:
            db.rollback()

        if index < len(empty_certs) - 1 and throttle_ms > 0:
            await asyncio.sleep(throttle_ms / 1000)

    return refetched


async def sync_terreni_batch(
    db: Session,
    client: InVoltureClient,
    request: CapacitasTerreniBatchRequest,
    *,
    policy: TerreniSyncPolicy | None = None,
    progress_callback: TerreniItemProgressCallback | None = None,
) -> CapacitasTerreniBatchResponse:
    item_results: list[CapacitasTerreniBatchItemResult] = []
    totals = {
        "processed_items": 0,
        "failed_items": 0,
        "total_rows": 0,
        "imported_rows": 0,
        "imported_certificati": 0,
        "imported_details": 0,
        "linked_units": 0,
        "linked_occupancies": 0,
    }
    frazione_cache: dict[str, list[str]] = {}

    for item in request.items:
        frazione_candidates = (
            [item.frazione_id]
            if item.frazione_id
            else await _resolve_batch_frazione_candidates(client, item.comune, item.sezione, frazione_cache)
        )
        search_key = ""
        try:
            result = await _sync_batch_item_with_candidates(
                db,
                client,
                request,
                item,
                frazione_candidates,
                throttle_ms=policy.throttle_ms if policy is not None else 0,
            )
            search_key = result.search_key
            item_result = CapacitasTerreniBatchItemResult(
                label=item.label,
                search_key=result.search_key,
                ok=True,
                total_rows=result.total_rows,
                imported_rows=result.imported_rows,
                imported_certificati=result.imported_certificati,
                imported_details=result.imported_details,
                linked_units=result.linked_units,
                linked_occupancies=result.linked_occupancies,
            )
            item_results.append(item_result)
            totals["processed_items"] += 1
            totals["total_rows"] += result.total_rows
            totals["imported_rows"] += result.imported_rows
            totals["imported_certificati"] += result.imported_certificati
            totals["imported_details"] += result.imported_details
            totals["linked_units"] += result.linked_units
            totals["linked_occupancies"] += result.linked_occupancies
            if progress_callback is not None:
                await progress_callback(item_result)
        except Exception as exc:
            db.rollback()
            if not search_key:
                search_key = build_search_key(
                    CapacitasTerreniSearchRequest(
                        frazione_id=frazione_candidates[0] if frazione_candidates else "",
                        sezione=item.sezione,
                        foglio=item.foglio,
                        particella=item.particella,
                        sub=item.sub,
                        qualita=item.qualita,
                        caratura=item.caratura,
                        caratura_val=item.caratura_val,
                        in_essere=item.in_essere,
                        in_dom_irr=item.in_dom_irr,
                        limita_risultati=item.limita_risultati,
                        credential_id=item.credential_id if item.credential_id is not None else request.credential_id,
                    )
                )
            item_result = CapacitasTerreniBatchItemResult(
                label=item.label,
                search_key=search_key,
                ok=False,
                error=str(exc),
            )
            item_results.append(item_result)
            totals["processed_items"] += 1
            totals["failed_items"] += 1
            if progress_callback is not None:
                await progress_callback(item_result)
            if isinstance(exc, CapacitasSessionExpiredError) or not request.continue_on_error:
                break

        if totals["processed_items"] < len(request.items) and policy is not None and policy.throttle_ms > 0:
            await asyncio.sleep(policy.throttle_ms / 1000)

    return CapacitasTerreniBatchResponse(items=item_results, **totals)


def build_search_key(request: CapacitasTerreniSearchRequest) -> str:
    return "|".join(
        [
            request.frazione_id.strip(),
            request.sezione.strip(),
            request.foglio.strip(),
            request.particella.strip(),
            request.sub.strip(),
        ]
    )


def _normalize_lookup_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


async def _persist_capacitas_intestatari(
    db: Session,
    client: InVoltureClient,
    certificato_snapshot: CatCapacitasCertificato,
    certificato: CapacitasTerrenoCertificato,
    collected_at: datetime,
    *,
    target_utenze: list[CatUtenzaIrrigua] | None = None,
    persist_snapshot_intestatari: bool = True,
    storico_cache: dict[str, list[CapacitasStoricoAnagraficaRow]],
    anagrafica_detail_cache: dict[str, CapacitasAnagraficaDetail],
) -> None:
    utenze = target_utenze or []
    if target_utenze is None and certificato.cco:
        candidate_utenze = _find_utenze_for_cert_context(
            db,
            cco=certificato.cco,
            com=certificato.com,
            fra=certificato.fra,
        )
        # Without a single resolved target, avoid spraying annual owner links
        # across every utenza that happens to share the same certificate context.
        utenze = candidate_utenze if len(candidate_utenze) == 1 else []
    for intestatario in certificato.intestatari:
        history_rows: list[CapacitasStoricoAnagraficaRow] = []
        if intestatario.idxana:
            history_rows = storico_cache.get(intestatario.idxana, [])
            if not history_rows:
                try:
                    history_rows = await client.fetch_anagrafica_history(idxana=intestatario.idxana)
                except Exception:
                    history_rows = []
                storico_cache[intestatario.idxana] = history_rows

        subject = (
            _find_existing_subject_from_intestatario(db, intestatario)
            if history_rows
            else _match_or_create_subject_from_intestatario(db, intestatario, collected_at)
        )
        resolved_subject = await _persist_utenza_intestatari_from_history(
            db,
            client,
            utenze,
            intestatario,
            collected_at,
            storico_cache=storico_cache,
            anagrafica_detail_cache=anagrafica_detail_cache,
            fallback_subject=subject,
            prefetched_history_rows=history_rows,
        )
        subject = resolved_subject or subject
        if persist_snapshot_intestatari:
            db.add(
                CatCapacitasIntestatario(
                    certificato_id=certificato_snapshot.id,
                    subject_id=subject.id if subject else None,
                    idxana=intestatario.idxana,
                    idxesa=intestatario.idxesa,
                    codice_fiscale=intestatario.codice_fiscale,
                    denominazione=intestatario.denominazione,
                    data_nascita=intestatario.data_nascita,
                    luogo_nascita=intestatario.luogo_nascita,
                    residenza=intestatario.residenza,
                    comune_residenza=intestatario.comune_residenza,
                    cap=intestatario.cap,
                    titoli=intestatario.titoli,
                    deceduto=intestatario.deceduto,
                    raw_payload_json=intestatario.model_dump(exclude_none=True, mode="json"),
                    collected_at=collected_at,
                )
            )


async def _persist_utenza_intestatari_from_history(
    db: Session,
    client: InVoltureClient,
    utenze: list[CatUtenzaIrrigua],
    intestatario: CapacitasIntestatario,
    collected_at: datetime,
    *,
    storico_cache: dict[str, list[CapacitasStoricoAnagraficaRow]],
    anagrafica_detail_cache: dict[str, CapacitasAnagraficaDetail],
    fallback_subject: AnagraficaSubject | None,
    prefetched_history_rows: list[CapacitasStoricoAnagraficaRow] | None = None,
) -> AnagraficaSubject | None:
    if not utenze:
        return fallback_subject

    history_rows: list[CapacitasStoricoAnagraficaRow] = prefetched_history_rows or []
    if not history_rows and intestatario.idxana:
        history_rows = storico_cache.get(intestatario.idxana, [])
        if not history_rows:
            try:
                history_rows = await client.fetch_anagrafica_history(idxana=intestatario.idxana)
            except Exception:
                history_rows = []
            storico_cache[intestatario.idxana] = history_rows

    resolved_subject = fallback_subject
    for utenza in utenze:
        matched_rows = [row for row in history_rows if _to_int(row.anno) == utenza.anno_campagna]
        if matched_rows:
            for history_row in matched_rows:
                subject = await _match_or_create_subject_from_history_row(
                    db,
                    client,
                    history_row,
                    intestatario,
                    anagrafica_detail_cache=anagrafica_detail_cache,
                )
                resolved_subject = subject or resolved_subject
                _upsert_utenza_intestatario_link(
                    db,
                    utenza,
                    history_row=history_row,
                    intestatario=intestatario,
                    subject=subject,
                    collected_at=collected_at,
                )
        else:
            _upsert_utenza_intestatario_link(
                db,
                utenza,
                history_row=None,
                intestatario=intestatario,
                subject=fallback_subject,
                collected_at=collected_at,
            )
    return resolved_subject


def _find_existing_subject_from_intestatario(
    db: Session,
    intestatario: CapacitasIntestatario,
) -> AnagraficaSubject | None:
    normalized_cf = _normalize_cf(intestatario.codice_fiscale)
    if normalized_cf:
        person = db.scalar(select(AnagraficaPerson).where(AnagraficaPerson.codice_fiscale == normalized_cf))
        if person is not None:
            return db.get(AnagraficaSubject, person.subject_id)

    if intestatario.idxana:
        return db.scalar(
            select(AnagraficaSubject).where(
                AnagraficaSubject.source_system == "capacitas",
                AnagraficaSubject.source_external_id == intestatario.idxana,
            )
        )

    return None


async def _match_or_create_subject_from_history_row(
    db: Session,
    client: InVoltureClient,
    history_row: CapacitasStoricoAnagraficaRow,
    intestatario: CapacitasIntestatario,
    *,
    anagrafica_detail_cache: dict[str, CapacitasAnagraficaDetail],
) -> AnagraficaSubject | None:
    detail = anagrafica_detail_cache.get(history_row.history_id)
    if detail is None:
        detail = await client.fetch_anagrafica_detail(history_id=history_row.history_id)
        anagrafica_detail_cache[history_row.history_id] = detail

    normalized_cf = _normalize_cf(detail.codice_fiscale or history_row.codice_fiscale or intestatario.codice_fiscale)
    person: AnagraficaPerson | None = None
    if normalized_cf:
        person = db.scalar(select(AnagraficaPerson).where(AnagraficaPerson.codice_fiscale == normalized_cf))
    if person is None and (history_row.idxana or intestatario.idxana):
        subject = db.scalar(
            select(AnagraficaSubject).where(
                AnagraficaSubject.source_system == "capacitas",
                AnagraficaSubject.source_external_id == (history_row.idxana or intestatario.idxana),
            )
        )
        if subject is not None:
            person = db.get(AnagraficaPerson, subject.id)

    if person is None and not normalized_cf:
        return None

    person_data = _build_person_payload_from_history(detail, history_row, intestatario, normalized_cf)
    collected_at = _parse_datetime_value(history_row.data_agg) or datetime.now(timezone.utc)

    if person is None:
        assert normalized_cf is not None
        subject = AnagraficaSubject(
            subject_type=AnagraficaSubjectType.PERSON.value,
            status=AnagraficaSubjectStatus.ACTIVE.value,
            source_system="capacitas",
            source_external_id=history_row.idxana or intestatario.idxana,
            source_name_raw=detail.denominazione or history_row.denominazione or intestatario.denominazione or normalized_cf,
            requires_review=False,
        )
        db.add(subject)
        db.flush()
        person = AnagraficaPerson(subject_id=subject.id, **person_data)
        db.add(person)
        _persist_capacitas_history_person_snapshot(
            db,
            person,
            person_data,
            history_row,
            collected_at=collected_at,
        )
        return subject

    subject = db.get(AnagraficaSubject, person.subject_id)
    if subject is None:
        return None

    _persist_capacitas_history_person_snapshot(
        db,
        person,
        person_data,
        history_row,
        collected_at=collected_at,
    )
    snapshot_person_if_changed(
        db,
        person,
        person_data,
        source_system="capacitas",
        source_ref=history_row.idxana or intestatario.idxana,
        collected_at=collected_at,
    )
    for key, value in person_data.items():
        setattr(person, key, value)

    if history_row.idxana or intestatario.idxana:
        subject.source_external_id = history_row.idxana or intestatario.idxana
    if not subject.source_name_raw:
        subject.source_name_raw = detail.denominazione or history_row.denominazione or intestatario.denominazione
    return subject


def _build_residenza_from_detail(detail: CapacitasAnagraficaDetail, intestatario: CapacitasIntestatario) -> tuple[str | None, str | None, str | None]:
    indirizzo = _compose_address(
        detail.residenza_toponimo,
        detail.residenza_indirizzo,
        detail.residenza_civico,
        detail.residenza_sub,
    )
    comune = detail.residenza_belfiore or intestatario.comune_residenza
    cap = detail.residenza_cap or intestatario.cap
    residenza = indirizzo
    if comune:
        residenza = f"{(cap + ' ') if cap else ''}{comune} - {indirizzo or ''}".strip(" -")
    return residenza or intestatario.residenza, comune, cap


def _persist_capacitas_history_person_snapshot(
    db: Session,
    person: AnagraficaPerson,
    person_data: dict[str, object | None],
    history_row: CapacitasStoricoAnagraficaRow,
    *,
    collected_at: datetime,
) -> None:
    persist_person_source_snapshot(
        db,
        person,
        person_data,
        source_system="capacitas",
        source_ref=history_row.history_id,
        collected_at=collected_at,
        valid_from=collected_at,
        is_capacitas_history=True,
    )


def _build_person_payload_from_history(
    detail: CapacitasAnagraficaDetail,
    history_row: CapacitasStoricoAnagraficaRow,
    intestatario: CapacitasIntestatario,
    normalized_cf: str | None,
) -> dict[str, object | None]:
    cognome = detail.cognome or _split_denominazione(detail.denominazione or history_row.denominazione or intestatario.denominazione)[0]
    nome = detail.nome or _split_denominazione(detail.denominazione or history_row.denominazione or intestatario.denominazione)[1]
    comune_nascita = history_row.luogo_nascita or detail.luogo_nascita or intestatario.luogo_nascita
    residenza, comune_residenza, cap = _build_residenza_from_detail(detail, intestatario)
    indirizzo = _compose_address(
        detail.residenza_toponimo,
        detail.residenza_indirizzo,
        detail.residenza_civico,
        detail.residenza_sub,
    ) or residenza or intestatario.residenza
    note_parts = [part for part in detail.note if part]
    return {
        "cognome": cognome,
        "nome": nome,
        "codice_fiscale": normalized_cf or "",
        "data_nascita": detail.data_nascita or _parse_date_ddmmyyyy(history_row.data_nascita) or intestatario.data_nascita,
        "comune_nascita": comune_nascita,
        "indirizzo": indirizzo,
        "comune_residenza": comune_residenza,
        "cap": cap,
        "email": detail.email,
        "telefono": detail.telefono or detail.cellulare,
        "note": " | ".join(note_parts) if note_parts else None,
    }


def _upsert_utenza_intestatario_link(
    db: Session,
    utenza: CatUtenzaIrrigua,
    *,
    history_row: CapacitasStoricoAnagraficaRow | None,
    intestatario: CapacitasIntestatario,
    subject: AnagraficaSubject | None,
    collected_at: datetime,
) -> None:
    existing = db.scalar(
        select(CatUtenzaIntestatario).where(
            CatUtenzaIntestatario.utenza_id == utenza.id,
            CatUtenzaIntestatario.history_id == (history_row.history_id if history_row else None),
            CatUtenzaIntestatario.idxana == (history_row.idxana if history_row and history_row.idxana else intestatario.idxana),
        )
    )
    if existing is not None:
        return

    residenza = intestatario.residenza
    comune_residenza = intestatario.comune_residenza
    cap = intestatario.cap
    if history_row is not None:
        # When available, use the historic detail-backed view already normalized in GAIA.
        detail_residenza = None
        if subject is not None:
            person = db.get(AnagraficaPerson, subject.id)
            if person is not None:
                detail_residenza = person.indirizzo
                comune_residenza = person.comune_residenza or comune_residenza
                cap = person.cap or cap
        if detail_residenza:
            residenza = detail_residenza

    db.add(
        CatUtenzaIntestatario(
            utenza_id=utenza.id,
            subject_id=subject.id if subject else None,
            idxana=history_row.idxana if history_row and history_row.idxana else intestatario.idxana,
            idxesa=intestatario.idxesa,
            history_id=history_row.history_id if history_row else None,
            anno_riferimento=_to_int(history_row.anno) if history_row else utenza.anno_campagna,
            data_agg=_parse_datetime_value(history_row.data_agg) if history_row else collected_at,
            at=history_row.at if history_row else None,
            site=history_row.site if history_row else None,
            voltura=history_row.voltura if history_row else None,
            op=history_row.op if history_row else None,
            sn=history_row.sn if history_row else None,
            codice_fiscale=history_row.codice_fiscale if history_row and history_row.codice_fiscale else intestatario.codice_fiscale,
            partita_iva=history_row.partita_iva if history_row else None,
            denominazione=history_row.denominazione if history_row and history_row.denominazione else intestatario.denominazione,
            data_nascita=_parse_date_ddmmyyyy(history_row.data_nascita) if history_row else intestatario.data_nascita,
            luogo_nascita=history_row.luogo_nascita if history_row else intestatario.luogo_nascita,
            sesso=history_row.sesso if history_row else None,
            residenza=residenza,
            comune_residenza=comune_residenza,
            cap=cap,
            titoli=intestatario.titoli,
            deceduto=intestatario.deceduto,
            collected_at=collected_at,
            raw_payload_json=(
                history_row.model_dump(by_alias=True, exclude_none=True, mode="json")
                if history_row
                else intestatario.model_dump(exclude_none=True, mode="json")
            ),
        )
    )


def _match_or_create_subject_from_intestatario(
    db: Session,
    intestatario: CapacitasIntestatario,
    collected_at: datetime,
) -> AnagraficaSubject | None:
    normalized_cf = _normalize_cf(intestatario.codice_fiscale)
    person: AnagraficaPerson | None = None

    if normalized_cf:
        person = db.scalar(select(AnagraficaPerson).where(AnagraficaPerson.codice_fiscale == normalized_cf))
    if person is None and intestatario.idxana:
        subject = db.scalar(
            select(AnagraficaSubject).where(
                AnagraficaSubject.source_system == "capacitas",
                AnagraficaSubject.source_external_id == intestatario.idxana,
            )
        )
        if subject is not None:
            person = db.get(AnagraficaPerson, subject.id)

    if person is None and not normalized_cf:
        return None

    if person is None:
        assert normalized_cf is not None
        subject = AnagraficaSubject(
            subject_type=AnagraficaSubjectType.PERSON.value,
            status=AnagraficaSubjectStatus.ACTIVE.value,
            source_system="capacitas",
            source_external_id=intestatario.idxana,
            source_name_raw=intestatario.denominazione or normalized_cf or "Capacitas intestatario",
            requires_review=False,
        )
        db.add(subject)
        db.flush()
        cognome, nome = _split_denominazione(intestatario.denominazione)
        person = AnagraficaPerson(
            subject_id=subject.id,
            cognome=cognome,
            nome=nome,
            codice_fiscale=normalized_cf,
            data_nascita=intestatario.data_nascita,
            comune_nascita=intestatario.luogo_nascita,
            indirizzo=intestatario.residenza,
            comune_residenza=intestatario.comune_residenza,
            cap=intestatario.cap,
        )
        db.add(person)
        return subject

    subject = db.get(AnagraficaSubject, person.subject_id)
    if subject is None:
        return None

    cognome, nome = _split_denominazione(intestatario.denominazione, fallback_cognome=person.cognome, fallback_nome=person.nome)
    merged_data = {
        "cognome": cognome,
        "nome": nome,
        "codice_fiscale": normalized_cf or person.codice_fiscale,
        "data_nascita": intestatario.data_nascita or person.data_nascita,
        "comune_nascita": intestatario.luogo_nascita or person.comune_nascita,
        "indirizzo": intestatario.residenza or person.indirizzo,
        "comune_residenza": intestatario.comune_residenza or person.comune_residenza,
        "cap": intestatario.cap or person.cap,
        "email": person.email,
        "telefono": person.telefono,
        "note": person.note,
    }
    snapshot_person_if_changed(
        db,
        person,
        merged_data,
        source_system="capacitas",
        source_ref=intestatario.idxana,
        collected_at=collected_at,
    )
    person.cognome = merged_data["cognome"]
    person.nome = merged_data["nome"]
    person.codice_fiscale = merged_data["codice_fiscale"]
    person.data_nascita = merged_data["data_nascita"]
    person.comune_nascita = merged_data["comune_nascita"]
    person.indirizzo = merged_data["indirizzo"]
    person.comune_residenza = merged_data["comune_residenza"]
    person.cap = merged_data["cap"]

    if subject.source_system == "capacitas" and intestatario.idxana:
        subject.source_external_id = intestatario.idxana
    elif subject.source_external_id is None and intestatario.idxana:
        subject.source_external_id = intestatario.idxana

    if not subject.source_name_raw and intestatario.denominazione:
        subject.source_name_raw = intestatario.denominazione
    return subject


def _normalize_cf(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"\s+", "", value).upper()
    return normalized or None


def _parse_date_ddmmyyyy(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def _parse_datetime_value(value: str | None) -> datetime | None:
    if not value:
        return None
    for pattern in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(value.strip(), pattern).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _compose_address(toponimo: str | None, indirizzo: str | None, civico: str | None, sub: str | None) -> str | None:
    parts = [part.strip() for part in [toponimo, indirizzo, civico] if part and part.strip()]
    value = " ".join(parts).strip()
    if sub and sub.strip():
        value = f"{value}/{sub.strip()}" if value else sub.strip()
    return value or None


def _split_denominazione(
    denominazione: str | None,
    *,
    fallback_cognome: str | None = None,
    fallback_nome: str | None = None,
) -> tuple[str, str]:
    cleaned = (denominazione or "").strip()
    if not cleaned:
        return fallback_cognome or "Sconosciuto", fallback_nome or "Capacitas"
    parts = cleaned.split()
    if len(parts) == 1:
        return parts[0], fallback_nome or parts[0]
    return parts[0], " ".join(parts[1:])


def _strip_numeric_prefix(value: str) -> str:
    """Strip leading numeric code like '03 ' or '11 ' from Capacitas display labels."""
    return re.sub(r"^\d+\s+", "", value).strip()


def _extract_lookup_comune(value: str) -> str:
    """Return the comune (right-hand) part of a Capacitas label.

    For 'NN FRAZIONE*COMUNE' returns 'COMUNE'; for 'NN NOME' (no asterisk)
    returns 'NOME' after stripping the numeric prefix.
    """
    if "*" in value:
        return value.split("*")[-1].strip()
    return _strip_numeric_prefix(value)


def _extract_lookup_frazione(value: str) -> str:
    """Return the frazione (left-hand) part of a Capacitas label.

    For 'NN FRAZIONE*COMUNE' returns 'FRAZIONE' (numeric prefix stripped);
    for 'NN NOME' (no asterisk) returns 'NOME' after stripping the prefix.
    """
    if "*" in value:
        return _strip_numeric_prefix(value.split("*")[0])
    return _strip_numeric_prefix(value)


def _extract_lookup_suffix(value: str) -> str:
    """Legacy alias kept for call-sites; delegates to _extract_lookup_comune."""
    return _extract_lookup_comune(value)


_SECTION_FRAZIONE_HINTS: dict[tuple[str, str], list[str]] = {
    ("oristano", "a"): ["11"],
    ("oristano", "b"): ["04"],
    ("oristano", "c"): ["05"],
    ("oristano", "d"): ["09"],
    ("oristano", "e"): ["18"],
    ("cabras", "a"): ["03"],
    ("cabras", "b"): ["20"],
    ("simaxis", "a"): ["19", "10"],
    ("simaxis", "b"): ["15"],
}

_SECTION_LOOKUP_COMUNE_OVERRIDES: dict[tuple[str, str], tuple[str, list[str]]] = {
    ("terralba", "b"): ("Arborea", ["31"]),
}


def _apply_section_frazione_hints(
    comune: str | None,
    sezione: str | None,
    candidate_ids: list[str],
    *,
    preferred_ids_override: list[str] | None = None,
) -> list[str]:
    comune_key = _normalize_lookup_label((comune or "").strip())
    sezione_key = (sezione or "").strip().casefold()
    normalized_candidates = [candidate.strip() for candidate in candidate_ids if candidate and candidate.strip()]
    if not comune_key or not sezione_key or not normalized_candidates:
        return normalized_candidates

    preferred_ids = preferred_ids_override or _SECTION_FRAZIONE_HINTS.get((comune_key, sezione_key))
    if not preferred_ids:
        return normalized_candidates

    preferred_present = [candidate_id for candidate_id in preferred_ids if candidate_id in normalized_candidates]
    if not preferred_present:
        return normalized_candidates

    remainder = [candidate_id for candidate_id in normalized_candidates if candidate_id not in preferred_present]
    return preferred_present + remainder


async def _probe_frazioni_for_item(
    client: InVoltureClient,
    item: CapacitasTerreniBatchItem,
    frazione_candidates: list[str],
) -> list[dict]:
    """Lightweight probe: search (no DB write) each fraction and return those with results."""
    hits: list[dict] = []
    for frazione_id in frazione_candidates:
        search_req = CapacitasTerreniSearchRequest(
            frazione_id=frazione_id,
            sezione=item.sezione,
            foglio=item.foglio,
            particella=item.particella,
            sub=item.sub,
        )
        try:
            result = await client.search_terreni(search_req)
            rows = result.rows if result else []
            if rows:
                hits.append({
                    "frazione_id": frazione_id,
                    "n_rows": len(rows),
                    "ccos": sorted({r.cco for r in rows if r.cco}),
                    "stati": sorted({r.row_visual_state for r in rows if r.row_visual_state}),
                })
        except Exception:
            pass
    return hits


async def _sync_batch_item_with_candidates(
    db: Session,
    client: InVoltureClient,
    batch_request: CapacitasTerreniBatchRequest,
    item: CapacitasTerreniBatchItem,
    frazione_candidates: list[str],
    *,
    throttle_ms: int = 0,
) -> CapacitasTerreniSyncResponse:
    # When frazione is explicit (single candidate) skip ambiguity check entirely.
    if len(frazione_candidates) > 1:
        hits = await _probe_frazioni_for_item(client, item, frazione_candidates)
        if len(hits) > 1:
            comune_value = (item.comune or "").strip() or "n/d"
            raise CapacitasFrazioneAmbiguaError(
                f"Particella {item.foglio}/{item.particella} trovata in {len(hits)} frazioni distinte "
                f"per comune '{comune_value}': richiede risoluzione manuale.",
                candidates=hits,
            )
        if len(hits) == 1:
            # Exactly one fraction has results — restrict to that one.
            frazione_candidates = [hits[0]["frazione_id"]]

    attempted_errors: list[str] = []

    for frazione_id in frazione_candidates:
        sync_request = CapacitasTerreniSearchRequest(
            frazione_id=frazione_id,
            sezione=item.sezione,
            foglio=item.foglio,
            particella=item.particella,
            sub=item.sub,
            qualita=item.qualita,
            caratura=item.caratura,
            caratura_val=item.caratura_val,
            in_essere=item.in_essere,
            in_dom_irr=item.in_dom_irr,
            limita_risultati=item.limita_risultati,
            credential_id=item.credential_id if item.credential_id is not None else batch_request.credential_id,
        )
        try:
            return await sync_terreni_for_request(
                db,
                client,
                sync_request,
                fetch_certificati=item.fetch_certificati if item.fetch_certificati is not None else batch_request.fetch_certificati,
                fetch_details=item.fetch_details if item.fetch_details is not None else batch_request.fetch_details,
                throttle_ms=throttle_ms,
            )
        except RuntimeError as exc:
            db.rollback()
            message = str(exc)
            attempted_errors.append(message)
            if len(frazione_candidates) == 1 or not _is_retryable_missing_result_error(message):
                raise
        except Exception:
            db.rollback()
            raise

    comune_value = (item.comune or "").strip() or "n/d"
    raise RuntimeError(
        f"Particella {item.foglio}/{item.particella}"
        f"{('/' + item.sub) if item.sub else ''} non trovata in nessuna delle {len(frazione_candidates)} "
        f"frazioni candidate per comune '{comune_value}'. Ultimo esito: {attempted_errors[-1] if attempted_errors else 'n/d'}"
    )


def _is_retryable_missing_result_error(message: str) -> bool:
    normalized = message.casefold()
    return "non trov" in normalized or "nessun" in normalized or "no result" in normalized


async def _resolve_batch_frazione_candidates(
    client: InVoltureClient,
    comune: str | None,
    sezione: str | None,
    cache: dict[str, list[str]],
) -> list[str]:
    comune_value = (comune or "").strip()
    if not comune_value:
        raise RuntimeError("Riga batch non valida: serve 'comune' oppure 'frazione_id'.")

    override = _SECTION_LOOKUP_COMUNE_OVERRIDES.get((_normalize_lookup_label(comune_value), (sezione or "").strip().casefold()))
    lookup_comune_value = override[0] if override is not None else comune_value
    preferred_ids_override = override[1] if override is not None else None
    cache_key = f"{_normalize_lookup_label(comune_value)}|{(sezione or '').strip().casefold()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    options = await client.search_frazioni(lookup_comune_value)
    if not options:
        raise RuntimeError(f"Nessuna frazione Capacitas trovata per comune '{lookup_comune_value}'.")
    if len(options) == 1:
        cache[cache_key] = _apply_section_frazione_hints(
            comune_value,
            sezione,
            [options[0].id],
            preferred_ids_override=preferred_ids_override,
        )
        return cache[cache_key]

    lookup_comune_key = _normalize_lookup_label(lookup_comune_value)
    exact_matches = [option for option in options if _normalize_lookup_label(option.display) == lookup_comune_key]
    if exact_matches:
        cache[cache_key] = _apply_section_frazione_hints(
            comune_value,
            sezione,
            [option.id for option in exact_matches],
            preferred_ids_override=preferred_ids_override,
        )
        return cache[cache_key]

    # Match on the comune part (right of *, or label minus numeric prefix).
    # Handles "03 CABRAS" (no *) and "11 ORISTANO*ORISTANO" alike.
    comune_matches = [
        option for option in options if _normalize_lookup_label(_extract_lookup_comune(option.display)) == lookup_comune_key
    ]
    if comune_matches:
        cache[cache_key] = _apply_section_frazione_hints(
            comune_value,
            sezione,
            [option.id for option in comune_matches],
            preferred_ids_override=preferred_ids_override,
        )
        return cache[cache_key]

    # Fallback: match on the frazione part (left of *, or label minus numeric prefix).
    # Covers the reverse lookup when the user inputs a frazione name rather than the comune.
    frazione_matches = [
        option for option in options if _normalize_lookup_label(_extract_lookup_frazione(option.display)) == lookup_comune_key
    ]
    if frazione_matches:
        cache[cache_key] = _apply_section_frazione_hints(
            comune_value,
            sezione,
            [option.id for option in frazione_matches],
            preferred_ids_override=preferred_ids_override,
        )
        return cache[cache_key]

    raise RuntimeError(
        f"Comune '{lookup_comune_value}' ambiguo in Capacitas: trovate {len(options)} frazioni. Usa un nome piu specifico oppure risolvi prima il lookup manuale."
    )


def _find_or_create_unit(db: Session, row: CapacitasTerrenoRow) -> CatConsorzioUnit | None:
    if not row.foglio or not row.particella:
        return None

    normalized_sub = (row.sub or "").strip() or None
    source_comune = _find_source_comune(db, row)
    comune, particella, resolution_mode = _resolve_real_comune_and_particella(db, row, source_comune)
    unit = db.scalar(
        select(CatConsorzioUnit).where(
            CatConsorzioUnit.foglio == row.foglio,
            CatConsorzioUnit.particella == row.particella,
            CatConsorzioUnit.subalterno == normalized_sub,
            CatConsorzioUnit.sezione_catastale == row.sez,
        )
    )
    if unit is not None:
        if unit.particella_id is None and particella is not None:
            unit.particella_id = particella.id
        if unit.comune_id is None and comune is not None:
            unit.comune_id = comune.id
        if unit.cod_comune_capacitas is None and comune is not None:
            unit.cod_comune_capacitas = comune.cod_comune_capacitas
        if unit.source_comune_id is None and source_comune is not None:
            unit.source_comune_id = source_comune.id
        if unit.source_cod_comune_capacitas is None and source_comune is not None:
            unit.source_cod_comune_capacitas = source_comune.cod_comune_capacitas
        if unit.source_codice_catastale is None:
            unit.source_codice_catastale = row.belfiore
        if unit.source_comune_label is None and source_comune is not None:
            unit.source_comune_label = source_comune.nome_comune
        if unit.comune_resolution_mode is None:
            unit.comune_resolution_mode = resolution_mode
        unit.source_last_seen = date.today()
        return unit

    unit = CatConsorzioUnit(
        particella_id=particella.id if particella else None,
        comune_id=comune.id if comune else None,
        cod_comune_capacitas=comune.cod_comune_capacitas if comune else None,
        source_comune_id=source_comune.id if source_comune else None,
        source_cod_comune_capacitas=source_comune.cod_comune_capacitas if source_comune else None,
        source_codice_catastale=row.belfiore,
        source_comune_label=source_comune.nome_comune if source_comune else None,
        comune_resolution_mode=resolution_mode,
        sezione_catastale=row.sez,
        foglio=row.foglio,
        particella=row.particella,
        subalterno=normalized_sub,
        descrizione=f"Capacitas {row.foglio}/{row.particella}" + (f"/{row.sub}" if row.sub else ""),
        source_first_seen=date.today(),
        source_last_seen=date.today(),
        is_active=True,
    )
    db.add(unit)
    db.flush()
    return unit


def create_terreni_sync_job(
    db: Session,
    *,
    requested_by_user_id: int | None,
    credential_id: int | None,
    payload: CapacitasTerreniBatchRequest,
) -> CapacitasTerreniSyncJob:
    payload_json = payload.model_dump(exclude_none=True, mode="json")
    payload_json.setdefault("auto_resume", False)
    job = CapacitasTerreniSyncJob(
        requested_by_user_id=requested_by_user_id,
        credential_id=credential_id,
        status="pending",
        mode="batch",
        payload_json=payload_json,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_terreni_sync_jobs(db: Session) -> list[CapacitasTerreniSyncJob]:
    return list(db.scalars(select(CapacitasTerreniSyncJob).order_by(CapacitasTerreniSyncJob.id.desc())).all())


def get_terreni_sync_job(db: Session, job_id: int) -> CapacitasTerreniSyncJob | None:
    return db.get(CapacitasTerreniSyncJob, job_id)


def delete_terreni_sync_job(db: Session, job: CapacitasTerreniSyncJob) -> None:
    db.delete(job)
    db.commit()


def serialize_terreni_sync_job(job: CapacitasTerreniSyncJob) -> CapacitasTerreniJobOut:
    return CapacitasTerreniJobOut.model_validate(job)


def _normalize_job_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _mark_stale_terreni_job(
    job: CapacitasTerreniSyncJob,
    *,
    completed_at: datetime,
    detail: str,
) -> None:
    job.status = "failed"
    job.completed_at = completed_at
    job.error_detail = f"{job.error_detail}\n{detail}".strip() if job.error_detail else detail
    if isinstance(job.result_json, dict):
        result_json = dict(job.result_json)
        result_json["current_label"] = None
        result_json["completed_at"] = completed_at.isoformat()
        job.result_json = result_json


def expire_stale_terreni_sync_jobs(db: Session) -> None:
    now = datetime.now(UTC)
    stale_cutoff = now - timedelta(minutes=TERRENI_STALE_JOB_MINUTES)
    jobs = db.scalars(
        select(CapacitasTerreniSyncJob).where(
            CapacitasTerreniSyncJob.status == "processing",
            CapacitasTerreniSyncJob.completed_at.is_(None),
        )
    ).all()
    if not jobs:
        return

    changed = False
    for job in jobs:
        started_at = _normalize_job_datetime(job.started_at)
        updated_at = _normalize_job_datetime(job.updated_at)
        reference_at = updated_at or started_at

        if reference_at is not None and reference_at < stale_cutoff:
            _mark_stale_terreni_job(
                job,
                completed_at=now,
                detail=(
                    "Job marcato come failed: worker Capacitas senza avanzamento oltre la soglia di "
                    f"{TERRENI_STALE_JOB_MINUTES} minuti."
                ),
            )
            changed = True

    if changed:
        db.commit()


def prepare_terreni_sync_jobs_for_recovery(db: Session) -> list[int]:
    now = datetime.now(UTC)
    jobs = db.scalars(
        select(CapacitasTerreniSyncJob).where(
            CapacitasTerreniSyncJob.status.in_(("pending", "processing", "queued_resume")),
            CapacitasTerreniSyncJob.completed_at.is_(None),
        )
    ).all()
    if not jobs:
        return []

    recovered_ids: list[int] = []
    changed = False
    for job in jobs:
        payload_json = dict(job.payload_json or {})
        auto_resume = bool(payload_json.get("auto_resume", False))
        if not auto_resume or job.mode not in AUTO_RESUME_TERRENI_MODES:
            continue

        result_json = dict(job.result_json or {})
        result_json["resume_reason"] = "backend_restart"
        result_json["last_resume_at"] = now.isoformat()
        result_json["resume_count"] = int(result_json.get("resume_count", 0)) + 1
        result_json["current_label"] = None
        job.result_json = result_json
        job.error_detail = None
        job.completed_at = None
        job.status = "queued_resume"
        recovered_ids.append(job.id)
        changed = True

    if changed:
        db.commit()
    return recovered_ids


def _build_initial_terreni_job_result(
    payload: CapacitasTerreniBatchRequest,
    *,
    policy: TerreniSyncPolicy,
    parallel_workers: int,
) -> dict[str, object]:
    return {
        "items": [],
        "processed_items": 0,
        "failed_items": 0,
        "total_rows": 0,
        "imported_rows": 0,
        "imported_certificati": 0,
        "imported_details": 0,
        "linked_units": 0,
        "linked_occupancies": 0,
        "total_items": len(payload.items),
        "current_label": None,
        "speed_multiplier": policy.speed_multiplier,
        "parallel_workers": parallel_workers,
        "throttle_ms": policy.throttle_ms,
    }


def _record_terreni_job_item_progress(
    db: Session,
    *,
    job_id: int,
    item_result: CapacitasTerreniBatchItemResult,
) -> None:
    job = db.scalar(
        select(CapacitasTerreniSyncJob)
        .where(CapacitasTerreniSyncJob.id == job_id)
        .with_for_update()
    )
    if job is None:
        return

    current_result = dict(job.result_json or {})
    items = current_result.get("items")
    if not isinstance(items, list):
        items = []
        current_result["items"] = items

    item_payload = item_result.model_dump(exclude_none=True, mode="json")
    items.append(item_payload)
    current_result["processed_items"] = int(current_result.get("processed_items", 0)) + 1
    current_result["failed_items"] = int(current_result.get("failed_items", 0)) + (0 if item_result.ok else 1)
    current_result["total_rows"] = int(current_result.get("total_rows", 0)) + item_result.total_rows
    current_result["imported_rows"] = int(current_result.get("imported_rows", 0)) + item_result.imported_rows
    current_result["imported_certificati"] = int(current_result.get("imported_certificati", 0)) + item_result.imported_certificati
    current_result["imported_details"] = int(current_result.get("imported_details", 0)) + item_result.imported_details
    current_result["linked_units"] = int(current_result.get("linked_units", 0)) + item_result.linked_units
    current_result["linked_occupancies"] = int(current_result.get("linked_occupancies", 0)) + item_result.linked_occupancies
    total_items = int(current_result.get("total_items", 0) or 0)
    if total_items > 0:
        current_result["progress_percent"] = min(
            100,
            round((int(current_result["processed_items"]) / total_items) * 100, 2),
        )
    current_result["current_label"] = None if int(current_result["processed_items"]) >= total_items else item_result.label or item_result.search_key

    job.result_json = current_result
    db.commit()


def _merge_terreni_batch_responses(responses: Sequence[CapacitasTerreniBatchResponse]) -> CapacitasTerreniBatchResponse:
    items: list[CapacitasTerreniBatchItemResult] = []
    totals = {
        "processed_items": 0,
        "failed_items": 0,
        "total_rows": 0,
        "imported_rows": 0,
        "imported_certificati": 0,
        "imported_details": 0,
        "linked_units": 0,
        "linked_occupancies": 0,
    }

    for response in responses:
        items.extend(response.items)
        totals["processed_items"] += response.processed_items
        totals["failed_items"] += response.failed_items
        totals["total_rows"] += response.total_rows
        totals["imported_rows"] += response.imported_rows
        totals["imported_certificati"] += response.imported_certificati
        totals["imported_details"] += response.imported_details
        totals["linked_units"] += response.linked_units
        totals["linked_occupancies"] += response.linked_occupancies

    return CapacitasTerreniBatchResponse(items=items, **totals)


async def _run_terreni_sync_parallel(
    *,
    session_factory: Callable[[], Session],
    clients: Sequence[InVoltureClient],
    payload: CapacitasTerreniBatchRequest,
    policy: TerreniSyncPolicy,
    progress_callback: TerreniItemProgressCallback | None = None,
) -> CapacitasTerreniBatchResponse:
    item_groups = [payload.items[index::len(clients)] for index in range(len(clients))]

    async def worker(client: InVoltureClient, items: list[CapacitasTerreniBatchItem]) -> CapacitasTerreniBatchResponse:
        worker_db = session_factory()
        try:
            return await sync_terreni_batch(
                worker_db,
                client,
                CapacitasTerreniBatchRequest(
                    items=items,
                    continue_on_error=payload.continue_on_error,
                    credential_id=payload.credential_id,
                    fetch_certificati=payload.fetch_certificati,
                    fetch_details=payload.fetch_details,
                    double_speed=payload.double_speed,
                    parallel_workers=payload.parallel_workers,
                    throttle_ms=payload.throttle_ms,
                ),
                policy=policy,
                progress_callback=progress_callback,
            )
        finally:
            worker_db.close()

    responses = await asyncio.gather(
        *(worker(client, items) for client, items in zip(clients, item_groups, strict=False) if items)
    )
    return _merge_terreni_batch_responses(responses)


async def run_terreni_sync_job(
    db: Session,
    client: InVoltureClient,
    job: CapacitasTerreniSyncJob,
    *,
    session_factory: Callable[[], Session] | None = None,
    clients: Sequence[InVoltureClient] | None = None,
) -> CapacitasTerreniSyncJob:
    payload = CapacitasTerreniBatchRequest.model_validate(job.payload_json or {})
    job.status = "processing"
    job.started_at = datetime.now(timezone.utc)
    job.error_detail = None
    policy = compute_terreni_sync_policy(
        double_speed=payload.double_speed,
        parallel_workers=payload.parallel_workers,
        throttle_ms=payload.throttle_ms,
    )
    client_pool = list(clients or [client])
    parallel_workers = min(policy.parallel_workers, len(client_pool), max(1, len(payload.items)))
    job.result_json = _build_initial_terreni_job_result(payload, policy=policy, parallel_workers=parallel_workers)
    db.commit()
    db.refresh(job)

    async def record_progress(item_result: CapacitasTerreniBatchItemResult) -> None:
        if session_factory is None:
            _record_terreni_job_item_progress(db, job_id=job.id, item_result=item_result)
            return

        progress_db = session_factory()
        try:
            _record_terreni_job_item_progress(progress_db, job_id=job.id, item_result=item_result)
        finally:
            progress_db.close()

    try:
        if parallel_workers > 1 and session_factory is not None:
            result = await _run_terreni_sync_parallel(
                session_factory=session_factory,
                clients=client_pool[:parallel_workers],
                payload=payload,
                policy=policy,
                progress_callback=record_progress,
            )
        else:
            result = await sync_terreni_batch(db, client, payload, policy=policy, progress_callback=record_progress)
        job.status = "succeeded" if result.failed_items == 0 else "completed_with_errors"
        final_result = result.model_dump(exclude_none=True, mode="json")
        final_result["speed_multiplier"] = policy.speed_multiplier
        final_result["parallel_workers"] = parallel_workers
        final_result["throttle_ms"] = policy.throttle_ms
        job.result_json = final_result
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        return job
    except Exception as exc:
        db.rollback()
        job = db.get(CapacitasTerreniSyncJob, job.id)
        assert job is not None
        job.status = "failed"
        job.error_detail = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        raise


def _find_or_create_segment(
    db: Session,
    unit: CatConsorzioUnit | None,
    detail: CapacitasTerrenoDetail | None,
) -> CatConsorzioUnitSegment | None:
    if unit is None or detail is None:
        return None

    riordino_code = detail.riordino_code
    riordino_maglia = detail.riordino_maglia
    riordino_lotto = detail.riordino_lotto
    if not any([riordino_code, riordino_maglia, riordino_lotto]):
        return None

    segment = db.scalar(
        select(CatConsorzioUnitSegment).where(
            CatConsorzioUnitSegment.unit_id == unit.id,
            CatConsorzioUnitSegment.riordino_code == riordino_code,
            CatConsorzioUnitSegment.riordino_maglia == riordino_maglia,
            CatConsorzioUnitSegment.riordino_lotto == riordino_lotto,
            CatConsorzioUnitSegment.is_current.is_(True),
        )
    )
    if segment is not None:
        return segment

    segment = CatConsorzioUnitSegment(
        unit_id=unit.id,
        label="Segmento riordino",
        segment_type="riordino",
        riordino_code=riordino_code,
        riordino_maglia=riordino_maglia,
        riordino_lotto=riordino_lotto,
        current_status="attiva",
        valid_from=date.today(),
        is_current=True,
    )
    db.add(segment)
    db.flush()
    return segment


def _find_or_create_occupancy(
    db: Session,
    unit: CatConsorzioUnit | None,
    segment: CatConsorzioUnitSegment | None,
    row: CapacitasTerrenoRow,
) -> bool:
    if unit is None or not row.cco:
        return False

    anno = _to_int(row.anno)
    valid_from = date(anno, 1, 1) if anno else None
    valid_to = date(anno, 12, 31) if anno else None
    existing = db.scalar(
        select(CatConsorzioOccupancy).where(
            CatConsorzioOccupancy.unit_id == unit.id,
            CatConsorzioOccupancy.segment_id == (segment.id if segment else None),
            CatConsorzioOccupancy.cco == row.cco,
            CatConsorzioOccupancy.valid_from == valid_from,
            CatConsorzioOccupancy.valid_to == valid_to,
            CatConsorzioOccupancy.source_type == "capacitas_terreni",
        )
    )
    utenza = _find_utenza_for_terreno_row(db, row) if anno else None

    if existing is not None:
        if existing.utenza_id is None and utenza is not None:
            existing.utenza_id = utenza.id
        return False

    db.add(
        CatConsorzioOccupancy(
            unit_id=unit.id,
            segment_id=segment.id if segment else None,
            utenza_id=utenza.id if utenza else None,
            cco=row.cco,
            fra=row.fra,
            ccs=row.ccs,
            pvc=row.pvc,
            com=row.com,
            source_type="capacitas_terreni",
            relationship_type="utilizzatore_reale",
            valid_from=valid_from,
            valid_to=valid_to,
            is_current=row.row_visual_state == "current_black",
            confidence=Decimal("0.90"),
            notes="Occupazione derivata da ricerca terreni Capacitas",
        )
    )
    return True


def _same_optional_text(left: str | None, right: str | None) -> bool:
    return (left or "").strip() == (right or "").strip()


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _find_utenze_for_cert_context(
    db: Session,
    *,
    cco: str,
    com: str | None,
    fra: str | None,
) -> list[CatUtenzaIrrigua]:
    query = select(CatUtenzaIrrigua).where(CatUtenzaIrrigua.cco == cco)

    comune_code = _parse_optional_int(com)
    frazione_code = _parse_optional_int(fra)
    if comune_code is not None:
        query = query.where(CatUtenzaIrrigua.cod_comune_capacitas == comune_code)
    if frazione_code is not None:
        query = query.where(CatUtenzaIrrigua.cod_frazione == frazione_code)

    return list(
        db.scalars(
            query.order_by(CatUtenzaIrrigua.anno_campagna.desc(), CatUtenzaIrrigua.id.desc())
        ).all()
    )


def _find_utenza_for_terreno_row(db: Session, row: CapacitasTerrenoRow) -> CatUtenzaIrrigua | None:
    if not row.cco:
        return None

    anno = _to_int(row.anno)
    row_com = _to_int(row.com)
    row_fra = _to_int(row.fra)

    def _matches_geo(candidate: CatUtenzaIrrigua) -> bool:
        if row_com is not None and candidate.cod_comune_capacitas != row_com:
            return False
        if row_fra is not None and candidate.cod_frazione != row_fra:
            return False
        if row.foglio and not _same_optional_text(candidate.foglio, row.foglio):
            return False
        if row.particella and not _same_optional_text(candidate.particella, row.particella):
            return False
        if row.sub is not None and not _same_optional_text(candidate.subalterno, row.sub):
            return False
        return True

    if anno is not None:
        exact = list(
            db.scalars(
                select(CatUtenzaIrrigua).where(
                    CatUtenzaIrrigua.cco == row.cco,
                    CatUtenzaIrrigua.anno_campagna == anno,
                )
            ).all()
        )
        match = next((c for c in exact if _matches_geo(c)), None)
        if match is not None:
            return match

    # Fallback: anno non corrisponde (es. row.anno=2024, utenza.anno_campagna=2025).
    # Usa l'utenza piu recente per questo CCO con le stesse coordinate geografiche.
    all_for_cco = list(
        db.scalars(
            select(CatUtenzaIrrigua)
            .where(CatUtenzaIrrigua.cco == row.cco)
            .order_by(CatUtenzaIrrigua.anno_campagna.desc())
        ).all()
    )
    return next((c for c in all_for_cco if _matches_geo(c)), None)


def _find_source_comune(db: Session, row: CapacitasTerrenoRow) -> CatComune | None:
    if row.belfiore:
        comune = db.scalar(select(CatComune).where(CatComune.codice_catastale == row.belfiore))
        if comune is not None:
            return comune
    if row.com and row.com.isdigit():
        return db.scalar(select(CatComune).where(CatComune.cod_comune_capacitas == int(row.com)))
    return None


def _find_particella(db: Session, comune: CatComune | None, row: CapacitasTerrenoRow) -> CatParticella | None:
    normalized_sub = (row.sub or "").strip() or None
    stmt = select(CatParticella).where(
        CatParticella.foglio == row.foglio,
        CatParticella.particella == row.particella,
        CatParticella.is_current.is_(True),
    )
    if normalized_sub is None:
        stmt = stmt.where(func.coalesce(CatParticella.subalterno, "") == "")
    else:
        stmt = stmt.where(CatParticella.subalterno == normalized_sub)
    if comune is not None:
        stmt = stmt.where(CatParticella.comune_id == comune.id)
    elif row.belfiore:
        stmt = stmt.where(CatParticella.codice_catastale == row.belfiore)
    return db.scalar(stmt)


def _resolve_real_comune_and_particella(
    db: Session,
    row: CapacitasTerrenoRow,
    source_comune: CatComune | None,
) -> tuple[CatComune | None, CatParticella | None, str]:
    particella = _find_particella(db, source_comune, row)
    if particella is not None:
        if source_comune is not None and particella.comune_id == source_comune.id:
            return source_comune, particella, "source_match"
        resolved = db.get(CatComune, particella.comune_id) if particella.comune_id else source_comune
        return resolved, particella, "resolved_from_particella"

    if source_comune is None or source_comune.cod_comune_capacitas not in _COMUNE_SWAP_CODES:
        return source_comune, None, "source_only"

    alternate_code = _COMUNE_SWAP_CODES[source_comune.cod_comune_capacitas]
    alternate_comune = db.scalar(select(CatComune).where(CatComune.cod_comune_capacitas == alternate_code))
    if alternate_comune is None:
        return source_comune, None, "source_only"

    swapped_particella = _find_particella(db, alternate_comune, row)
    if swapped_particella is not None:
        return alternate_comune, swapped_particella, "swapped_arborea_terralba"

    return source_comune, None, "source_only"


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _to_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    cleaned = value.strip().replace(".", "").replace(",", ".")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None
