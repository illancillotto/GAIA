from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import re

from sqlalchemy import select
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
from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
from app.modules.elaborazioni.capacitas.models import (
    CapacitasAnagraficaDetail,
    CapacitasStoricoAnagraficaRow,
    CapacitasTerreniBatchItem,
    CapacitasTerreniBatchItemResult,
    CapacitasTerreniBatchRequest,
    CapacitasTerreniBatchResponse,
    CapacitasTerreniJobCreateRequest,
    CapacitasTerreniJobOut,
    CapacitasTerreniSearchRequest,
    CapacitasTerreniSyncResponse,
    CapacitasIntestatario,
    CapacitasTerrenoCertificato,
    CapacitasTerrenoDetail,
    CapacitasTerrenoRow,
)

_COMUNE_SWAP_CODES: dict[int, int] = {
    165: 280,  # Arborea -> Terralba
    280: 165,  # Terralba -> Arborea
}


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


async def sync_terreni_for_request(
    db: Session,
    client: InVoltureClient,
    request: CapacitasTerreniSearchRequest,
    *,
    fetch_certificati: bool = True,
    fetch_details: bool = True,
) -> CapacitasTerreniSyncResponse:
    result = await client.search_terreni(request)
    collected_at = datetime.now(timezone.utc)
    search_key = build_search_key(request)
    counters = SyncCounters()
    certificato_cache: dict[tuple[str, str, str, str, str], CapacitasTerrenoCertificato] = {}
    storico_cache: dict[str, list[CapacitasStoricoAnagraficaRow]] = {}
    anagrafica_detail_cache: dict[str, CapacitasAnagraficaDetail] = {}

    for row in result.rows:
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
            certificato = certificato_cache.get(cache_key)
            if certificato is None:
                certificato = await client.fetch_certificato(
                    cco=row.cco,
                    com=row.com,
                    pvc=row.pvc,
                    fra=row.fra or "",
                    ccs=row.ccs or "",
                )
                certificato_cache[cache_key] = certificato
                counters.certificati += 1
                certificato_snapshot = CatCapacitasCertificato(
                    cco=certificato.cco or row.cco,
                    fra=certificato.fra or row.fra,
                    ccs=certificato.ccs or row.ccs,
                    pvc=certificato.pvc or row.pvc,
                    com=certificato.com or row.com,
                    partita_code=certificato.partita_code,
                    utenza_code=certificato.utenza_code,
                    utenza_status=certificato.utenza_status,
                    ruolo_status=certificato.ruolo_status or certificato.partita_status,
                    raw_html=certificato.raw_html,
                    parsed_json=certificato.model_dump(exclude_none=True, mode="json"),
                    collected_at=collected_at,
                )
                db.add(certificato_snapshot)
                db.flush()
                await _persist_capacitas_intestatari(
                    db,
                    client,
                    certificato_snapshot,
                    certificato,
                    collected_at,
                    storico_cache=storico_cache,
                    anagrafica_detail_cache=anagrafica_detail_cache,
                )

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


async def sync_terreni_batch(
    db: Session,
    client: InVoltureClient,
    request: CapacitasTerreniBatchRequest,
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
            else await _resolve_batch_frazione_candidates(client, item.comune, frazione_cache)
        )
        search_key = ""
        try:
            result = await _sync_batch_item_with_candidates(db, client, request, item, frazione_candidates)
            search_key = result.search_key
            item_results.append(
                CapacitasTerreniBatchItemResult(
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
            )
            totals["processed_items"] += 1
            totals["total_rows"] += result.total_rows
            totals["imported_rows"] += result.imported_rows
            totals["imported_certificati"] += result.imported_certificati
            totals["imported_details"] += result.imported_details
            totals["linked_units"] += result.linked_units
            totals["linked_occupancies"] += result.linked_occupancies
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
            item_results.append(
                CapacitasTerreniBatchItemResult(
                    label=item.label,
                    search_key=search_key,
                    ok=False,
                    error=str(exc),
                )
            )
            totals["processed_items"] += 1
            totals["failed_items"] += 1
            if not request.continue_on_error:
                break

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
    storico_cache: dict[str, list[CapacitasStoricoAnagraficaRow]],
    anagrafica_detail_cache: dict[str, CapacitasAnagraficaDetail],
) -> None:
    utenze = []
    if certificato.cco:
        utenze = list(
            db.scalars(select(CatUtenzaIrrigua).where(CatUtenzaIrrigua.cco == certificato.cco)).all()
        )
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


async def _sync_batch_item_with_candidates(
    db: Session,
    client: InVoltureClient,
    batch_request: CapacitasTerreniBatchRequest,
    item: CapacitasTerreniBatchItem,
    frazione_candidates: list[str],
) -> CapacitasTerreniSyncResponse:
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
    cache: dict[str, list[str]],
) -> list[str]:
    comune_value = (comune or "").strip()
    if not comune_value:
        raise RuntimeError("Riga batch non valida: serve 'comune' oppure 'frazione_id'.")

    cache_key = _normalize_lookup_label(comune_value)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    options = await client.search_frazioni(comune_value)
    if not options:
        raise RuntimeError(f"Nessuna frazione Capacitas trovata per comune '{comune_value}'.")
    if len(options) == 1:
        cache[cache_key] = [options[0].id]
        return cache[cache_key]

    exact_matches = [option for option in options if _normalize_lookup_label(option.display) == cache_key]
    if exact_matches:
        cache[cache_key] = [option.id for option in exact_matches]
        return cache[cache_key]

    # Match on the comune part (right of *, or label minus numeric prefix).
    # Handles "03 CABRAS" (no *) and "11 ORISTANO*ORISTANO" alike.
    comune_matches = [
        option for option in options if _normalize_lookup_label(_extract_lookup_comune(option.display)) == cache_key
    ]
    if comune_matches:
        cache[cache_key] = [option.id for option in comune_matches]
        return cache[cache_key]

    # Fallback: match on the frazione part (left of *, or label minus numeric prefix).
    # Covers the reverse lookup when the user inputs a frazione name rather than the comune.
    frazione_matches = [
        option for option in options if _normalize_lookup_label(_extract_lookup_frazione(option.display)) == cache_key
    ]
    if frazione_matches:
        cache[cache_key] = [option.id for option in frazione_matches]
        return cache[cache_key]

    raise RuntimeError(
        f"Comune '{comune_value}' ambiguo in Capacitas: trovate {len(options)} frazioni. Usa un nome piu specifico oppure risolvi prima il lookup manuale."
    )


def _find_or_create_unit(db: Session, row: CapacitasTerrenoRow) -> CatConsorzioUnit | None:
    if not row.foglio or not row.particella:
        return None

    source_comune = _find_source_comune(db, row)
    comune, particella, resolution_mode = _resolve_real_comune_and_particella(db, row, source_comune)
    unit = db.scalar(
        select(CatConsorzioUnit).where(
            CatConsorzioUnit.foglio == row.foglio,
            CatConsorzioUnit.particella == row.particella,
            CatConsorzioUnit.subalterno == row.sub,
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
        subalterno=row.sub,
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
    job = CapacitasTerreniSyncJob(
        requested_by_user_id=requested_by_user_id,
        credential_id=credential_id,
        status="pending",
        mode="batch",
        payload_json=payload.model_dump(exclude_none=True, mode="json"),
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


async def run_terreni_sync_job(
    db: Session,
    client: InVoltureClient,
    job: CapacitasTerreniSyncJob,
) -> CapacitasTerreniSyncJob:
    payload = CapacitasTerreniBatchRequest.model_validate(job.payload_json or {})
    job.status = "processing"
    job.started_at = datetime.now(timezone.utc)
    job.error_detail = None
    db.commit()
    db.refresh(job)

    try:
        result = await sync_terreni_batch(db, client, payload)
        job.status = "succeeded" if result.failed_items == 0 else "completed_with_errors"
        job.result_json = result.model_dump(exclude_none=True, mode="json")
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
    if existing is not None:
        return False

    utenza = None
    if anno:
        utenza = db.scalar(
            select(CatUtenzaIrrigua).where(
                CatUtenzaIrrigua.cco == row.cco,
                CatUtenzaIrrigua.anno_campagna == anno,
            )
        )

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


def _find_source_comune(db: Session, row: CapacitasTerrenoRow) -> CatComune | None:
    if row.belfiore:
        comune = db.scalar(select(CatComune).where(CatComune.codice_catastale == row.belfiore))
        if comune is not None:
            return comune
    if row.com and row.com.isdigit():
        return db.scalar(select(CatComune).where(CatComune.cod_comune_capacitas == int(row.com)))
    return None


def _find_particella(db: Session, comune: CatComune | None, row: CapacitasTerrenoRow) -> CatParticella | None:
    stmt = select(CatParticella).where(
        CatParticella.foglio == row.foglio,
        CatParticella.particella == row.particella,
        CatParticella.subalterno == row.sub,
        CatParticella.is_current.is_(True),
    )
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
