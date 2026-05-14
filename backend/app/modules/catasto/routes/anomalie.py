from __future__ import annotations

from dataclasses import asdict
import re
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_admin_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatAnomalia, CatComune, CatParticella, CatUtenzaIrrigua
from app.modules.catasto.services.ade_status_scan import (
    create_ade_status_scan_batch,
    get_ade_status_scan_summary,
    list_ade_status_scan_candidates,
)
from app.modules.catasto.services.import_capacitas import ANOMALIA_TYPES
from app.modules.catasto.services.validation import validate_codice_fiscale
from app.services.elaborazioni_credentials import ElaborazioneCredentialNotFoundError
from app.schemas.catasto_phase1 import (
    CatAdeStatusScanCandidateListResponse,
    CatAdeStatusScanCandidateResponse,
    CatAdeStatusScanRunInput,
    CatAdeStatusScanRunResponse,
    CatAdeStatusScanSummaryResponse,
    CatAnomaliaComuneCandidateResponse,
    CatAnomaliaComuneWizardApplyInput,
    CatAnomaliaComuneWizardApplyResponse,
    CatAnomaliaComuneWizardItemResponse,
    CatAnomaliaComuneWizardListResponse,
    CatAnomaliaCfWizardApplyInput,
    CatAnomaliaCfWizardApplyResponse,
    CatAnomaliaCfWizardItemResponse,
    CatAnomaliaCfWizardListResponse,
    CatAnomaliaListResponse,
    CatAnomaliaParticellaCandidateResponse,
    CatAnomaliaParticellaWizardApplyInput,
    CatAnomaliaParticellaWizardApplyResponse,
    CatAnomaliaParticellaWizardItemResponse,
    CatAnomaliaParticellaWizardListResponse,
    CatAnomaliaResponse,
    CatAnomaliaSummaryBucketResponse,
    CatAnomaliaSummaryResponse,
    CatAnomaliaUpdateInput,
)

router = APIRouter(prefix="/catasto/anomalie", tags=["catasto-anomalie"])

CF_WIZARD_TYPES = {"VAL-02-cf_invalido", "VAL-03-cf_mancante"}
COMUNE_WIZARD_TYPES = {"VAL-04-comune_invalido"}
PARTICELLA_WIZARD_TYPES = {"VAL-05-particella_assente"}
SEVERITY_RANK = {"error": 3, "warning": 2, "info": 1}


def _apply_anomalie_filters(
    query,
    *,
    tipo: str | None,
    status_filter: str | None,
    severita: str | None,
    anno: int | None,
    distretto: str | None,
):
    if tipo:
        query = query.where(CatAnomalia.tipo == tipo)
    if status_filter:
        query = query.where(CatAnomalia.status == status_filter)
    if severita:
        query = query.where(CatAnomalia.severita == severita)
    if anno is not None:
        query = query.where(CatAnomalia.anno_campagna == anno)
    if distretto:
        if distretto.isdigit():
            query = query.join(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id).where(
                CatUtenzaIrrigua.num_distretto == int(distretto)
            )
        else:
            query = query.where(False)
    return query


def _normalize_lookup_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def _extract_source_comune_code(anomalia: CatAnomalia, utenza: CatUtenzaIrrigua) -> int | None:
    dati_json = anomalia.dati_json if isinstance(anomalia.dati_json, dict) else {}
    raw_value = dati_json.get("cod_istat")
    if raw_value is None:
        raw_value = utenza.cod_comune_capacitas
    try:
        return int(raw_value) if raw_value is not None else None
    except (TypeError, ValueError):
        return utenza.cod_comune_capacitas


def _build_comune_candidates(
    db: Session,
    anomalia: CatAnomalia,
    utenza: CatUtenzaIrrigua,
) -> list[CatAnomaliaComuneCandidateResponse]:
    source_code = _extract_source_comune_code(anomalia, utenza)
    source_name = _normalize_lookup_text(utenza.nome_comune)

    rows = db.execute(select(CatComune).order_by(CatComune.nome_comune.asc()).limit(500)).scalars().all()
    candidates: list[CatAnomaliaComuneCandidateResponse] = []
    for row in rows:
        score = 0
        if source_code is not None and row.cod_comune_capacitas == source_code:
            score += 8
        if source_code is not None and row.codice_comune_formato_numerico == source_code:
            score += 6
        if source_code is not None and row.codice_comune_numerico_2017_2025 == source_code:
            score += 6

        row_name = _normalize_lookup_text(row.nome_comune)
        row_legacy_name = _normalize_lookup_text(row.nome_comune_legacy)
        if source_name and source_name == row_name:
            score += 8
        elif source_name and source_name == row_legacy_name:
            score += 7
        elif source_name and (source_name in row_name or row_name in source_name):
            score += 4
        elif source_name and row_legacy_name and (source_name in row_legacy_name or row_legacy_name in source_name):
            score += 3

        if score <= 0:
            continue

        candidates.append(
            CatAnomaliaComuneCandidateResponse(
                id=row.id,
                nome_comune=row.nome_comune,
                nome_comune_legacy=row.nome_comune_legacy,
                codice_catastale=row.codice_catastale,
                cod_comune_capacitas=row.cod_comune_capacitas,
                codice_comune_formato_numerico=row.codice_comune_formato_numerico,
                codice_comune_numerico_2017_2025=row.codice_comune_numerico_2017_2025,
                sigla_provincia=row.sigla_provincia,
                match_score=score,
            )
        )

    return sorted(
        candidates,
        key=lambda item: (-item.match_score, item.nome_comune.lower(), item.cod_comune_capacitas),
    )


def _build_particella_candidates(db: Session, utenza: CatUtenzaIrrigua) -> list[CatAnomaliaParticellaCandidateResponse]:
    if not (utenza.foglio and utenza.particella):
        return []

    query = select(CatParticella).where(
        CatParticella.is_current.is_(True),
        CatParticella.foglio == utenza.foglio,
        CatParticella.particella == utenza.particella,
    )
    if utenza.cod_comune_capacitas is not None:
        query = query.where(CatParticella.cod_comune_capacitas == utenza.cod_comune_capacitas)
    elif utenza.nome_comune:
        query = query.where(CatParticella.nome_comune.ilike(utenza.nome_comune.strip()))

    rows = db.execute(query.limit(25)).scalars().all()
    if not rows:
        return []

    particella_ids = [row.id for row in rows]
    anagrafica_ids = set(
        db.execute(select(CatUtenzaIrrigua.particella_id).where(CatUtenzaIrrigua.particella_id.in_(particella_ids))).scalars().all()
    )

    candidates: list[CatAnomaliaParticellaCandidateResponse] = []
    for row in rows:
        score = 0
        if utenza.cod_comune_capacitas is not None and row.cod_comune_capacitas == utenza.cod_comune_capacitas:
            score += 5
        if (utenza.sezione_catastale or "").strip().upper() == (row.sezione_catastale or "").strip().upper():
            score += 3
        if (utenza.subalterno or "").strip().upper() == (row.subalterno or "").strip().upper():
            score += 2
        if not utenza.subalterno and row.subalterno is None:
            score += 1
        candidates.append(
            CatAnomaliaParticellaCandidateResponse(
                id=row.id,
                cod_comune_capacitas=row.cod_comune_capacitas,
                codice_catastale=row.codice_catastale,
                nome_comune=row.nome_comune,
                sezione_catastale=row.sezione_catastale,
                foglio=row.foglio,
                particella=row.particella,
                subalterno=row.subalterno,
                num_distretto=row.num_distretto,
                nome_distretto=row.nome_distretto,
                ha_anagrafica=row.id in anagrafica_ids,
                match_score=score,
            )
        )

    return sorted(
        candidates,
        key=lambda item: (-item.match_score, item.nome_comune or "", item.sezione_catastale or "", item.subalterno or ""),
    )


@router.get("/", response_model=CatAnomaliaListResponse)
def list_anomalie(
    tipo: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    severita: str | None = Query(None),
    anno: int | None = Query(None),
    distretto: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatAnomaliaListResponse:
    query = select(CatAnomalia).order_by(desc(CatAnomalia.created_at))
    count_query = select(func.count()).select_from(CatAnomalia)
    query = _apply_anomalie_filters(
        query,
        tipo=tipo,
        status_filter=status_filter,
        severita=severita,
        anno=anno,
        distretto=distretto,
    )
    count_query = _apply_anomalie_filters(
        count_query,
        tipo=tipo,
        status_filter=status_filter,
        severita=severita,
        anno=anno,
        distretto=distretto,
    )

    total = db.execute(count_query).scalar_one()
    items = db.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return CatAnomaliaListResponse(
        items=[CatAnomaliaResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=CatAnomaliaSummaryResponse)
def anomalie_summary(
    status_filter: str | None = Query(None, alias="status"),
    severita: str | None = Query(None),
    anno: int | None = Query(None),
    distretto: str | None = Query(None),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatAnomaliaSummaryResponse:
    summary_query = (
        select(
            CatAnomalia.tipo,
            func.max(CatAnomalia.descrizione),
            CatAnomalia.severita,
            func.count(),
        )
        .select_from(CatAnomalia)
        .group_by(CatAnomalia.tipo, CatAnomalia.severita)
    )
    summary_query = _apply_anomalie_filters(
        summary_query,
        tipo=None,
        status_filter=status_filter,
        severita=severita,
        anno=anno,
        distretto=distretto,
    )
    rows = db.execute(summary_query).all()

    buckets_map: dict[str, CatAnomaliaSummaryBucketResponse] = {}
    for tipo_value, descrizione, severita_value, count in rows:
        current = buckets_map.get(str(tipo_value))
        next_rank = SEVERITY_RANK.get(str(severita_value), 0)
        current_rank = SEVERITY_RANK.get(current.severita, 0) if current else -1
        label = str(descrizione or ANOMALIA_TYPES.get(str(tipo_value), str(tipo_value)))

        if current is None:
            buckets_map[str(tipo_value)] = CatAnomaliaSummaryBucketResponse(
                tipo=str(tipo_value),
                label=label,
                severita=str(severita_value),
                count=int(count or 0),
            )
            continue

        current.count += int(count or 0)
        if next_rank > current_rank:
            current.severita = str(severita_value)
        if not current.label and label:
            current.label = label

    buckets = sorted(
        buckets_map.values(),
        key=lambda item: (-SEVERITY_RANK.get(item.severita, 0), -item.count, item.label.lower()),
    )
    return CatAnomaliaSummaryResponse(total=sum(item.count for item in buckets), buckets=buckets)


@router.get("/ade-scan/summary", response_model=CatAdeStatusScanSummaryResponse)
def ade_status_scan_summary(
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatAdeStatusScanSummaryResponse:
    return CatAdeStatusScanSummaryResponse(**get_ade_status_scan_summary(db))


@router.get("/ade-scan/candidates", response_model=CatAdeStatusScanCandidateListResponse)
def ade_status_scan_candidates(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatAdeStatusScanCandidateListResponse:
    items = list_ade_status_scan_candidates(db, limit=limit)
    return CatAdeStatusScanCandidateListResponse(
        items=[CatAdeStatusScanCandidateResponse(**asdict(item)) for item in items],
        total=len(items),
    )


@router.post("/ade-scan/run", response_model=CatAdeStatusScanRunResponse)
def run_ade_status_scan(
    payload: CatAdeStatusScanRunInput,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_active_user),
) -> CatAdeStatusScanRunResponse:
    try:
        result = create_ade_status_scan_batch(db, user_id=current_user.id, limit=max(1, min(payload.limit, 500)))
    except ElaborazioneCredentialNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return CatAdeStatusScanRunResponse(**result)


@router.get("/wizard/cf/items", response_model=CatAnomaliaCfWizardListResponse)
def list_cf_wizard_items(
    status_filter: str = Query("aperta", alias="status"),
    anno: int | None = Query(None),
    distretto: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatAnomaliaCfWizardListResponse:
    query = (
        select(CatAnomalia, CatUtenzaIrrigua)
        .join(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id)
        .where(CatAnomalia.tipo.in_(sorted(CF_WIZARD_TYPES)))
        .order_by(desc(CatAnomalia.created_at))
    )
    count_query = (
        select(func.count())
        .select_from(CatAnomalia)
        .join(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id)
        .where(CatAnomalia.tipo.in_(sorted(CF_WIZARD_TYPES)))
    )
    query = _apply_anomalie_filters(
        query,
        tipo=None,
        status_filter=status_filter,
        severita=None,
        anno=anno,
        distretto=distretto,
    )
    count_query = _apply_anomalie_filters(
        count_query,
        tipo=None,
        status_filter=status_filter,
        severita=None,
        anno=anno,
        distretto=distretto,
    )

    rows = db.execute(query.limit(limit)).all()
    total = db.execute(count_query).scalar_one()
    items: list[CatAnomaliaCfWizardItemResponse] = []
    for anomalia, utenza in rows:
        validation = validate_codice_fiscale(utenza.codice_fiscale_raw or utenza.codice_fiscale)
        suggested = validation.get("cf_normalizzato")
        suggested_cf = str(suggested) if isinstance(suggested, str) and bool(validation.get("is_valid")) else None
        items.append(
            CatAnomaliaCfWizardItemResponse(
                anomalia_id=anomalia.id,
                utenza_id=utenza.id,
                particella_id=anomalia.particella_id,
                anno_campagna=anomalia.anno_campagna,
                tipo=anomalia.tipo,
                severita=anomalia.severita,
                descrizione=anomalia.descrizione,
                status=anomalia.status,
                denominazione=utenza.denominazione,
                codice_fiscale=utenza.codice_fiscale,
                codice_fiscale_raw=utenza.codice_fiscale_raw,
                num_distretto=utenza.num_distretto,
                nome_comune=utenza.nome_comune,
                sezione_catastale=utenza.sezione_catastale,
                foglio=utenza.foglio,
                particella=utenza.particella,
                subalterno=utenza.subalterno,
                error_code=str(validation.get("error_code")) if validation.get("error_code") else None,
                suggested_codice_fiscale=suggested_cf,
                created_at=anomalia.created_at,
            )
        )

    return CatAnomaliaCfWizardListResponse(items=items, total=int(total or 0))


@router.get("/wizard/comune/items", response_model=CatAnomaliaComuneWizardListResponse)
def list_comune_wizard_items(
    status_filter: str = Query("aperta", alias="status"),
    anno: int | None = Query(None),
    distretto: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatAnomaliaComuneWizardListResponse:
    query = (
        select(CatAnomalia, CatUtenzaIrrigua)
        .join(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id)
        .where(CatAnomalia.tipo.in_(sorted(COMUNE_WIZARD_TYPES)))
        .order_by(desc(CatAnomalia.created_at))
    )
    count_query = (
        select(func.count())
        .select_from(CatAnomalia)
        .join(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id)
        .where(CatAnomalia.tipo.in_(sorted(COMUNE_WIZARD_TYPES)))
    )
    query = _apply_anomalie_filters(
        query,
        tipo=None,
        status_filter=status_filter,
        severita=None,
        anno=anno,
        distretto=distretto,
    )
    count_query = _apply_anomalie_filters(
        count_query,
        tipo=None,
        status_filter=status_filter,
        severita=None,
        anno=anno,
        distretto=distretto,
    )

    rows = db.execute(query.limit(limit)).all()
    total = db.execute(count_query).scalar_one()
    items: list[CatAnomaliaComuneWizardItemResponse] = []
    for anomalia, utenza in rows:
        items.append(
            CatAnomaliaComuneWizardItemResponse(
                anomalia_id=anomalia.id,
                utenza_id=utenza.id,
                anno_campagna=anomalia.anno_campagna,
                tipo=anomalia.tipo,
                severita=anomalia.severita,
                descrizione=anomalia.descrizione,
                status=anomalia.status,
                denominazione=utenza.denominazione,
                nome_comune=utenza.nome_comune,
                cod_comune_capacitas=utenza.cod_comune_capacitas,
                source_cod_comune_capacitas=_extract_source_comune_code(anomalia, utenza),
                num_distretto=utenza.num_distretto,
                sezione_catastale=utenza.sezione_catastale,
                foglio=utenza.foglio,
                particella=utenza.particella,
                subalterno=utenza.subalterno,
                candidates=_build_comune_candidates(db, anomalia, utenza)[:10],
                created_at=anomalia.created_at,
            )
        )

    return CatAnomaliaComuneWizardListResponse(items=items, total=int(total or 0))


@router.get("/wizard/particella/items", response_model=CatAnomaliaParticellaWizardListResponse)
def list_particella_wizard_items(
    status_filter: str = Query("aperta", alias="status"),
    anno: int | None = Query(None),
    distretto: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatAnomaliaParticellaWizardListResponse:
    query = (
        select(CatAnomalia, CatUtenzaIrrigua)
        .join(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id)
        .where(CatAnomalia.tipo.in_(sorted(PARTICELLA_WIZARD_TYPES)))
        .order_by(desc(CatAnomalia.created_at))
    )
    count_query = (
        select(func.count())
        .select_from(CatAnomalia)
        .join(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id)
        .where(CatAnomalia.tipo.in_(sorted(PARTICELLA_WIZARD_TYPES)))
    )
    query = _apply_anomalie_filters(
        query,
        tipo=None,
        status_filter=status_filter,
        severita=None,
        anno=anno,
        distretto=distretto,
    )
    count_query = _apply_anomalie_filters(
        count_query,
        tipo=None,
        status_filter=status_filter,
        severita=None,
        anno=anno,
        distretto=distretto,
    )

    rows = db.execute(query.limit(limit)).all()
    total = db.execute(count_query).scalar_one()
    items: list[CatAnomaliaParticellaWizardItemResponse] = []
    for anomalia, utenza in rows:
        items.append(
            CatAnomaliaParticellaWizardItemResponse(
                anomalia_id=anomalia.id,
                utenza_id=utenza.id,
                anno_campagna=anomalia.anno_campagna,
                tipo=anomalia.tipo,
                severita=anomalia.severita,
                descrizione=anomalia.descrizione,
                status=anomalia.status,
                denominazione=utenza.denominazione,
                nome_comune=utenza.nome_comune,
                sezione_catastale=utenza.sezione_catastale,
                foglio=utenza.foglio,
                particella=utenza.particella,
                subalterno=utenza.subalterno,
                cod_comune_capacitas=utenza.cod_comune_capacitas,
                num_distretto=utenza.num_distretto,
                candidates=_build_particella_candidates(db, utenza)[:10],
                created_at=anomalia.created_at,
            )
        )

    return CatAnomaliaParticellaWizardListResponse(items=items, total=int(total or 0))


@router.post("/wizard/cf/apply", response_model=CatAnomaliaCfWizardApplyResponse)
def apply_cf_wizard(
    payload: CatAnomaliaCfWizardApplyInput,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_admin_user),
) -> CatAnomaliaCfWizardApplyResponse:
    if not payload.items:
        raise HTTPException(status_code=422, detail="No wizard items provided")

    seen_ids: set[UUID] = set()
    updated_utenze: set[UUID] = set()
    closed_anomalies = 0

    for item in payload.items:
        if item.anomalia_id in seen_ids:
            raise HTTPException(status_code=422, detail="Duplicate anomaly ids are not allowed in wizard apply")
        seen_ids.add(item.anomalia_id)

        anomalia = db.get(CatAnomalia, item.anomalia_id)
        if anomalia is None:
            raise HTTPException(status_code=404, detail=f"Anomalia {item.anomalia_id} not found")
        if anomalia.tipo not in CF_WIZARD_TYPES:
            raise HTTPException(status_code=409, detail=f"Anomalia {item.anomalia_id} is not supported by CF wizard")
        if anomalia.utenza_id is None:
            raise HTTPException(status_code=409, detail=f"Anomalia {item.anomalia_id} has no utenza linked")

        validation = validate_codice_fiscale(item.codice_fiscale)
        normalized_cf = validation.get("cf_normalizzato")
        if not bool(validation.get("is_valid")) or not isinstance(normalized_cf, str):
            raise HTTPException(
                status_code=422,
                detail=f"Codice fiscale non valido per anomalia {item.anomalia_id}: {validation.get('error_code') or 'CHECKSUM_ERRATO'}",
            )

        utenza = db.get(CatUtenzaIrrigua, anomalia.utenza_id)
        if utenza is None:
            raise HTTPException(status_code=404, detail=f"Utenza {anomalia.utenza_id} not found")

        utenza.codice_fiscale = normalized_cf
        utenza.codice_fiscale_raw = normalized_cf
        utenza.anomalia_cf_invalido = False
        utenza.anomalia_cf_mancante = False
        db.add(utenza)
        updated_utenze.add(utenza.id)

        related = db.execute(
            select(CatAnomalia).where(
                CatAnomalia.utenza_id == utenza.id,
                CatAnomalia.tipo.in_(sorted(CF_WIZARD_TYPES)),
                CatAnomalia.status == "aperta",
            )
        ).scalars().all()
        note = item.note_operatore.strip() if item.note_operatore and item.note_operatore.strip() else "Correzione CF tramite wizard anomalie"
        for related_anomalia in related:
            related_anomalia.status = "chiusa"
            related_anomalia.note_operatore = note
            related_anomalia.assigned_to = current_user.id
            db.add(related_anomalia)
            closed_anomalies += 1

    db.commit()
    return CatAnomaliaCfWizardApplyResponse(
        applied_count=len(payload.items),
        updated_utenze=len(updated_utenze),
        closed_anomalies=closed_anomalies,
    )


@router.post("/wizard/comune/apply", response_model=CatAnomaliaComuneWizardApplyResponse)
def apply_comune_wizard(
    payload: CatAnomaliaComuneWizardApplyInput,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_admin_user),
) -> CatAnomaliaComuneWizardApplyResponse:
    if not payload.items:
        raise HTTPException(status_code=422, detail="No wizard items provided")

    seen_ids: set[UUID] = set()
    updated_utenze: set[UUID] = set()
    closed_anomalies = 0

    for item in payload.items:
        if item.anomalia_id in seen_ids:
            raise HTTPException(status_code=422, detail="Duplicate anomaly ids are not allowed in wizard apply")
        seen_ids.add(item.anomalia_id)

        anomalia = db.get(CatAnomalia, item.anomalia_id)
        if anomalia is None:
            raise HTTPException(status_code=404, detail=f"Anomalia {item.anomalia_id} not found")
        if anomalia.tipo not in COMUNE_WIZARD_TYPES:
            raise HTTPException(status_code=409, detail=f"Anomalia {item.anomalia_id} is not supported by comune wizard")
        if anomalia.utenza_id is None:
            raise HTTPException(status_code=409, detail=f"Anomalia {item.anomalia_id} has no utenza linked")

        utenza = db.get(CatUtenzaIrrigua, anomalia.utenza_id)
        if utenza is None:
            raise HTTPException(status_code=404, detail=f"Utenza {anomalia.utenza_id} not found")
        comune = db.get(CatComune, item.comune_id)
        if comune is None:
            raise HTTPException(status_code=404, detail=f"Comune {item.comune_id} not found")

        allowed_candidate_ids = {candidate.id for candidate in _build_comune_candidates(db, anomalia, utenza)}
        if item.comune_id not in allowed_candidate_ids:
            raise HTTPException(status_code=409, detail=f"Comune {item.comune_id} is not a valid candidate for anomalia {item.anomalia_id}")

        utenza.comune_id = comune.id
        utenza.cod_comune_capacitas = comune.cod_comune_capacitas
        utenza.nome_comune = comune.nome_comune
        utenza.anomalia_comune_invalido = False
        db.add(utenza)
        updated_utenze.add(utenza.id)

        related = db.execute(
            select(CatAnomalia).where(
                CatAnomalia.utenza_id == utenza.id,
                CatAnomalia.tipo.in_(sorted(COMUNE_WIZARD_TYPES)),
                CatAnomalia.status == "aperta",
            )
        ).scalars().all()
        note = item.note_operatore.strip() if item.note_operatore and item.note_operatore.strip() else "Correzione comune tramite wizard anomalie"
        for related_anomalia in related:
            related_anomalia.status = "chiusa"
            related_anomalia.note_operatore = note
            related_anomalia.assigned_to = current_user.id
            db.add(related_anomalia)
            closed_anomalies += 1

    db.commit()
    return CatAnomaliaComuneWizardApplyResponse(
        applied_count=len(payload.items),
        updated_utenze=len(updated_utenze),
        closed_anomalies=closed_anomalies,
    )


@router.post("/wizard/particella/apply", response_model=CatAnomaliaParticellaWizardApplyResponse)
def apply_particella_wizard(
    payload: CatAnomaliaParticellaWizardApplyInput,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_admin_user),
) -> CatAnomaliaParticellaWizardApplyResponse:
    if not payload.items:
        raise HTTPException(status_code=422, detail="No wizard items provided")

    seen_ids: set[UUID] = set()
    updated_utenze: set[UUID] = set()
    closed_anomalies = 0

    for item in payload.items:
        if item.anomalia_id in seen_ids:
            raise HTTPException(status_code=422, detail="Duplicate anomaly ids are not allowed in wizard apply")
        seen_ids.add(item.anomalia_id)

        anomalia = db.get(CatAnomalia, item.anomalia_id)
        if anomalia is None:
            raise HTTPException(status_code=404, detail=f"Anomalia {item.anomalia_id} not found")
        if anomalia.tipo not in PARTICELLA_WIZARD_TYPES:
            raise HTTPException(status_code=409, detail=f"Anomalia {item.anomalia_id} is not supported by particella wizard")
        if anomalia.utenza_id is None:
            raise HTTPException(status_code=409, detail=f"Anomalia {item.anomalia_id} has no utenza linked")

        utenza = db.get(CatUtenzaIrrigua, anomalia.utenza_id)
        if utenza is None:
            raise HTTPException(status_code=404, detail=f"Utenza {anomalia.utenza_id} not found")
        particella = db.get(CatParticella, item.particella_id)
        if particella is None:
            raise HTTPException(status_code=404, detail=f"Particella {item.particella_id} not found")
        if not particella.is_current:
            raise HTTPException(status_code=409, detail=f"Particella {item.particella_id} is not current")

        allowed_candidate_ids = {candidate.id for candidate in _build_particella_candidates(db, utenza)}
        if item.particella_id not in allowed_candidate_ids:
            raise HTTPException(status_code=409, detail=f"Particella {item.particella_id} is not a valid candidate for anomalia {item.anomalia_id}")

        utenza.particella_id = particella.id
        utenza.cod_comune_capacitas = particella.cod_comune_capacitas
        utenza.nome_comune = particella.nome_comune
        utenza.sezione_catastale = particella.sezione_catastale
        utenza.foglio = particella.foglio
        utenza.particella = particella.particella
        utenza.subalterno = particella.subalterno
        utenza.anomalia_particella_assente = False
        db.add(utenza)
        updated_utenze.add(utenza.id)

        related = db.execute(
            select(CatAnomalia).where(
                CatAnomalia.utenza_id == utenza.id,
                CatAnomalia.tipo.in_(sorted(PARTICELLA_WIZARD_TYPES)),
                CatAnomalia.status == "aperta",
            )
        ).scalars().all()
        note = item.note_operatore.strip() if item.note_operatore and item.note_operatore.strip() else "Collegamento particella tramite wizard anomalie"
        for related_anomalia in related:
            related_anomalia.particella_id = particella.id
            related_anomalia.status = "chiusa"
            related_anomalia.note_operatore = note
            related_anomalia.assigned_to = current_user.id
            db.add(related_anomalia)
            closed_anomalies += 1

    db.commit()
    return CatAnomaliaParticellaWizardApplyResponse(
        applied_count=len(payload.items),
        updated_utenze=len(updated_utenze),
        closed_anomalies=closed_anomalies,
    )


@router.patch("/{anomalia_id}", response_model=CatAnomaliaResponse)
def update_anomalia(
    anomalia_id: UUID,
    payload: CatAnomaliaUpdateInput,
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_admin_user),
):
    item = db.get(CatAnomalia, anomalia_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Anomalia not found")

    if payload.status is not None:
        item.status = payload.status
    if payload.note_operatore is not None:
        item.note_operatore = payload.note_operatore
    if payload.assigned_to is not None:
        item.assigned_to = payload.assigned_to

    db.add(item)
    db.commit()
    db.refresh(item)
    return CatAnomaliaResponse.model_validate(item)
