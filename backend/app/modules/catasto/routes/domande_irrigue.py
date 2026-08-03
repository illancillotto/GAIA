from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatAnomalia
from app.modules.catasto.models.domande_irrigue import CatDomandaIrrigua, CatDomandaIrriguaParticella
from app.modules.catasto.services.domande_irrigue import DIR_ANOMALIA_TYPES
from app.modules.ruolo.models import RuoloParticella

router = APIRouter(prefix="/catasto/domande-irrigue", tags=["catasto-domande-irrigue"])


class CatDomandaIrriguaParticellaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    domanda_id: UUID
    external_id: str | None
    unit_id: UUID | None
    segment_id: UUID | None
    particella_id: UUID | None
    utenza_id: UUID | None
    occupancy_id: UUID | None
    localita: str | None
    comizio: str | None
    foglio: str | None
    particella: str | None
    sub: str | None
    sup_cat_mq: Decimal | None
    sup_irr_mq: Decimal | None
    coltura: str | None
    part_pvc: str | None
    part_com: str | None
    part_cco: str | None
    part_fra: str | None
    part_ccs: str | None
    ruolo_bon: Decimal | None
    ruolo_irr: Decimal | None
    ruolo_var: Decimal | None
    note: str | None


class CatDomandaIrriguaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str | None
    anno: int
    domanda_numero: str | None
    cco: str | None
    com: str | None
    pvc: str | None
    fra: str | None
    ccs: str | None
    idxana: str | None
    source_row_id: str | None
    source_denominazione: str | None
    source_patrimonio: str | None
    patrimonio_has_domanda_hint: bool
    comune: str | None
    subject_id: UUID | None
    utenza_id: UUID | None
    occupancy_id: UUID | None
    stato: str | None
    stato_codice: str | None
    tipo: str | None
    tipo_codice: str | None
    tipo_scheda_codice: str | None
    tipo_scheda: str | None
    autorinnovo: bool
    ruolo_irr: Decimal | None
    tot_sup_cat_mq: Decimal | None
    tot_sup_irr_mq: Decimal | None
    tot_sup_servita_mq: Decimal | None
    tot_sup_richiesta_mq: Decimal | None
    tot_sup_malus_mq: Decimal | None
    tot_sup_bonus_mq: Decimal | None
    data_ins: datetime | None
    data_agg: datetime | None
    data_rett: datetime | None
    data_sosp: datetime | None
    data_chius: datetime | None
    note: str | None
    particelle: list[CatDomandaIrriguaParticellaResponse] = Field(default_factory=list)


class CatDomandeIrrigueListResponse(BaseModel):
    items: list[CatDomandaIrriguaResponse]
    total: int
    limit: int
    offset: int


class CatDomandeIrrigueBucketResponse(BaseModel):
    key: str
    count: int


class CatDomandeIrrigueSummaryResponse(BaseModel):
    total_domande: int
    total_particelle: int
    linked_utenze: int
    linked_occupancies: int
    linked_particelle: int
    open_anomalies: int
    by_anno: list[CatDomandeIrrigueBucketResponse]
    by_stato: list[CatDomandeIrrigueBucketResponse]


class CatDomandeIrrigueRuoloReconciliationItem(BaseModel):
    ruolo_particella_id: UUID
    anno_tributario: int
    domanda_irrigua: str | None
    foglio: str
    particella: str
    subalterno: str | None
    coltura_ruolo: str | None
    sup_irrigata_ha: Decimal | None
    domanda_id: UUID | None
    domanda_numero: str | None
    domanda_particella_id: UUID | None
    coltura_domanda: str | None
    sup_irr_mq: Decimal | None
    match_status: str
    issue: str | None = None


class CatDomandeIrrigueRuoloReconciliationResponse(BaseModel):
    total_ruolo_rows: int
    matched_rows: int
    missing_rows: int
    crop_mismatch_rows: int
    surface_mismatch_rows: int
    items: list[CatDomandeIrrigueRuoloReconciliationItem]


@router.get("", response_model=CatDomandeIrrigueListResponse)
def list_domande_irrigue(
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
    anno: int | None = Query(default=None),
    stato: str | None = Query(default=None),
    subject_id: UUID | None = None,
    utenza_id: UUID | None = None,
    cco: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> CatDomandeIrrigueListResponse:
    query = _apply_domande_filters(
        select(CatDomandaIrrigua),
        anno=anno,
        stato=stato,
        subject_id=subject_id,
        utenza_id=utenza_id,
        cco=cco,
        search=search,
    )
    total = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    rows = db.scalars(
        query.options(selectinload(CatDomandaIrrigua.particelle))
        .order_by(CatDomandaIrrigua.anno.desc(), CatDomandaIrrigua.data_ins.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return CatDomandeIrrigueListResponse(
        items=[_serialize_domanda(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=CatDomandeIrrigueSummaryResponse)
def get_domande_irrigue_summary(
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
    anno: int | None = Query(default=None),
) -> CatDomandeIrrigueSummaryResponse:
    domanda_query = select(CatDomandaIrrigua)
    particella_query = select(CatDomandaIrriguaParticella).join(CatDomandaIrrigua)
    if anno is not None:
        domanda_query = domanda_query.where(CatDomandaIrrigua.anno == anno)
        particella_query = particella_query.where(CatDomandaIrrigua.anno == anno)

    return CatDomandeIrrigueSummaryResponse(
        total_domande=int(db.scalar(select(func.count()).select_from(domanda_query.subquery())) or 0),
        total_particelle=int(db.scalar(select(func.count()).select_from(particella_query.subquery())) or 0),
        linked_utenze=_count_distinct(db, domanda_query, CatDomandaIrrigua.utenza_id),
        linked_occupancies=_count_distinct(db, domanda_query, CatDomandaIrrigua.occupancy_id),
        linked_particelle=_count_distinct(db, particella_query, CatDomandaIrriguaParticella.particella_id),
        open_anomalies=_count_open_domande_anomalies(db, anno),
        by_anno=_bucket_rows(db, domanda_query, CatDomandaIrrigua.anno),
        by_stato=_bucket_rows(db, domanda_query, CatDomandaIrrigua.stato),
    )


@router.get("/reconciliation/ruolo", response_model=CatDomandeIrrigueRuoloReconciliationResponse)
def reconcile_domande_irrigue_ruolo(
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
    anno: int | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> CatDomandeIrrigueRuoloReconciliationResponse:
    query = select(RuoloParticella).where(RuoloParticella.domanda_irrigua.is_not(None))
    if anno is not None:
        query = query.where(RuoloParticella.anno_tributario == anno)
    total = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    ruolo_rows = db.scalars(query.order_by(RuoloParticella.anno_tributario.desc()).limit(limit)).all()
    items = [_build_reconciliation_item(db, row) for row in ruolo_rows]
    return CatDomandeIrrigueRuoloReconciliationResponse(
        total_ruolo_rows=total,
        matched_rows=sum(1 for item in items if item.match_status == "matched"),
        missing_rows=sum(1 for item in items if item.match_status == "missing"),
        crop_mismatch_rows=sum(1 for item in items if item.issue == "coltura_mismatch"),
        surface_mismatch_rows=sum(1 for item in items if item.issue == "superficie_mismatch"),
        items=items,
    )


@router.get("/{domanda_id}", response_model=CatDomandaIrriguaResponse)
def get_domanda_irrigua(
    domanda_id: UUID,
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatDomandaIrriguaResponse:
    domanda = db.scalars(
        select(CatDomandaIrrigua)
        .options(selectinload(CatDomandaIrrigua.particelle))
        .where(CatDomandaIrrigua.id == domanda_id)
    ).one_or_none()
    if domanda is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domanda irrigua non trovata")
    return _serialize_domanda(domanda)


def _apply_domande_filters(
    query,
    *,
    anno: int | None,
    stato: str | None,
    subject_id: UUID | None,
    utenza_id: UUID | None,
    cco: str | None,
    search: str | None,
):
    if anno is not None:
        query = query.where(CatDomandaIrrigua.anno == anno)
    if stato:
        query = query.where(CatDomandaIrrigua.stato.ilike(stato.strip()))
    if subject_id is not None:
        query = query.where(CatDomandaIrrigua.subject_id == subject_id)
    if utenza_id is not None:
        query = query.where(CatDomandaIrrigua.utenza_id == utenza_id)
    if cco:
        query = query.where(CatDomandaIrrigua.cco == cco.strip())
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                CatDomandaIrrigua.domanda_numero.ilike(term),
                CatDomandaIrrigua.source_denominazione.ilike(term),
                CatDomandaIrrigua.comune.ilike(term),
                CatDomandaIrrigua.cco.ilike(term),
            )
        )
    return query


def _serialize_domanda(domanda: CatDomandaIrrigua) -> CatDomandaIrriguaResponse:
    return CatDomandaIrriguaResponse.model_validate(domanda)


def _count_distinct(db: Session, base_query, column) -> int:
    subquery = base_query.with_only_columns(column.label("value")).where(column.is_not(None)).subquery()
    return int(db.scalar(select(func.count(func.distinct(subquery.c.value)))) or 0)


def _count_open_domande_anomalies(db: Session, anno: int | None) -> int:
    query = select(func.count(CatAnomalia.id)).where(CatAnomalia.tipo.in_(DIR_ANOMALIA_TYPES), CatAnomalia.status == "aperta")
    if anno is not None:
        query = query.where(CatAnomalia.anno_campagna == anno)
    return int(db.scalar(query) or 0)


def _bucket_rows(db: Session, base_query, column) -> list[CatDomandeIrrigueBucketResponse]:
    subquery = base_query.with_only_columns(column.label("bucket")).subquery()
    bucket = func.coalesce(cast(subquery.c.bucket, String), "N/D")
    rows = db.execute(
        select(bucket, func.count())
        .select_from(subquery)
        .group_by(bucket)
        .order_by(func.count().desc())
    ).all()
    return [CatDomandeIrrigueBucketResponse(key=str(key), count=int(count)) for key, count in rows]


def _build_reconciliation_item(db: Session, row: RuoloParticella) -> CatDomandeIrrigueRuoloReconciliationItem:
    match = _find_domanda_particella_for_ruolo(db, row)
    if match is None:
        return CatDomandeIrrigueRuoloReconciliationItem(
            ruolo_particella_id=row.id,
            anno_tributario=row.anno_tributario,
            domanda_irrigua=row.domanda_irrigua,
            foglio=row.foglio,
            particella=row.particella,
            subalterno=row.subalterno,
            coltura_ruolo=row.coltura,
            sup_irrigata_ha=_decimal_or_none(row.sup_irrigata_ha),
            domanda_id=None,
            domanda_numero=None,
            domanda_particella_id=None,
            coltura_domanda=None,
            sup_irr_mq=None,
            match_status="missing",
            issue="domanda_non_trovata",
        )
    detail, domanda = match
    issue = _reconciliation_issue(row, detail)
    return CatDomandeIrrigueRuoloReconciliationItem(
        ruolo_particella_id=row.id,
        anno_tributario=row.anno_tributario,
        domanda_irrigua=row.domanda_irrigua,
        foglio=row.foglio,
        particella=row.particella,
        subalterno=row.subalterno,
        coltura_ruolo=row.coltura,
        sup_irrigata_ha=_decimal_or_none(row.sup_irrigata_ha),
        domanda_id=domanda.id,
        domanda_numero=domanda.domanda_numero,
        domanda_particella_id=detail.id,
        coltura_domanda=detail.coltura,
        sup_irr_mq=detail.sup_irr_mq,
        match_status="matched" if issue is None else "mismatch",
        issue=issue,
    )


def _find_domanda_particella_for_ruolo(
    db: Session,
    row: RuoloParticella,
) -> tuple[CatDomandaIrriguaParticella, CatDomandaIrrigua] | None:
    domanda_key = (row.domanda_irrigua or "").strip()
    if not domanda_key:
        return None
    normalized_key = domanda_key.lstrip("0") or "0"
    query = (
        select(CatDomandaIrriguaParticella, CatDomandaIrrigua)
        .join(CatDomandaIrrigua, CatDomandaIrriguaParticella.domanda_id == CatDomandaIrrigua.id)
        .where(
            CatDomandaIrrigua.anno == row.anno_tributario,
            or_(
                CatDomandaIrrigua.domanda_numero == domanda_key,
                func.ltrim(CatDomandaIrrigua.domanda_numero, "0") == normalized_key,
            ),
        )
    )
    if row.cat_particella_id is not None:
        query = query.where(CatDomandaIrriguaParticella.particella_id == row.cat_particella_id)
    else:
        query = query.where(
            CatDomandaIrriguaParticella.foglio == row.foglio,
            CatDomandaIrriguaParticella.particella == row.particella,
            func.coalesce(CatDomandaIrriguaParticella.sub, "") == (row.subalterno or ""),
        )
    return db.execute(query.limit(1)).first()


def _reconciliation_issue(row: RuoloParticella, detail: CatDomandaIrriguaParticella) -> str | None:
    ruolo_crop = _normalize_label(row.coltura)
    domanda_crop = _normalize_label(detail.coltura)
    if ruolo_crop and domanda_crop and ruolo_crop != domanda_crop:
        return "coltura_mismatch"
    ruolo_mq = _decimal_or_none(row.sup_irrigata_ha)
    if ruolo_mq is not None:
        ruolo_mq *= Decimal("10000")
    domanda_mq = _decimal_or_none(detail.sup_irr_mq)
    if ruolo_mq is not None and domanda_mq is not None and abs(ruolo_mq - domanda_mq) > Decimal("1"):
        return "superficie_mismatch"
    return None


def _decimal_or_none(value) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _normalize_label(value: str | None) -> str:
    return " ".join((value or "").strip().casefold().split())
