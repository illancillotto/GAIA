from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import (
    CatCapacitasCertificato,
    CatCapacitasTerrenoDetail,
    CatCapacitasTerrenoRow,
    CatComune,
    CatConsorzioOccupancy,
    CatConsorzioUnit,
    CatConsorzioUnitSegment,
    CatParticella,
    CatUtenzaIrrigua,
)
from app.models.capacitas import CapacitasTerreniSyncJob
from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
from app.modules.elaborazioni.capacitas.models import (
    CapacitasTerreniBatchItem,
    CapacitasTerreniBatchItemResult,
    CapacitasTerreniBatchRequest,
    CapacitasTerreniBatchResponse,
    CapacitasTerreniJobCreateRequest,
    CapacitasTerreniJobOut,
    CapacitasTerreniSearchRequest,
    CapacitasTerreniSyncResponse,
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
            raw_payload_json=row.model_dump(by_alias=True, exclude_none=True),
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
                db.add(
                    CatCapacitasCertificato(
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
                        parsed_json=certificato.model_dump(exclude_none=True),
                        collected_at=collected_at,
                    )
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
                    parsed_json=detail.model_dump(exclude_none=True),
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


def _extract_lookup_suffix(value: str) -> str:
    if "*" not in value:
        return value
    return value.split("*")[-1].strip()


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

    suffix_matches = [
        option for option in options if _normalize_lookup_label(_extract_lookup_suffix(option.display)) == cache_key
    ]
    if suffix_matches:
        cache[cache_key] = [option.id for option in suffix_matches]
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
        payload_json=payload.model_dump(exclude_none=True),
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
        job.result_json = result.model_dump(exclude_none=True)
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
