"""Read-only queries over the STEP archive."""

from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.elaborazioni.step import storage
from app.modules.elaborazioni.step.models import (
    StepContribuente,
    StepDocumento,
    StepPagamento,
    StepRuoloLink,
    StepTributo,
)
from app.modules.elaborazioni.step.ruolo_link import LINK_STATUSES
from app.modules.elaborazioni.step.schemas import (
    StepAvvisoLinkOut,
    StepContribuenteDetail,
    StepContribuenteRow,
    StepContribuentiPage,
    StepDocumentoOut,
    StepLinkAnomaliesPage,
    StepLinkAnomalyOut,
    StepOverviewOut,
    StepPagamentoOut,
    StepRuoloLinkOut,
    StepTributoOut,
)


def _count(db: Session, model) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def list_import_archives() -> list[str]:
    root = storage.import_root()
    if not root.is_dir():
        return []
    return sorted(
        path.name for path in root.iterdir() if path.is_file() and path.suffix.lower() == ".zip"
    )


def overview(db: Session) -> StepOverviewOut:
    links = dict.fromkeys(LINK_STATUSES, 0)
    for status, count in db.execute(
        select(StepRuoloLink.status, func.count()).group_by(StepRuoloLink.status)
    ).all():
        links[status] = int(count)
    return StepOverviewOut(
        contribuenti=_count(db, StepContribuente),
        documenti=_count(db, StepDocumento),
        tributi=_count(db, StepTributo),
        pagamenti=_count(db, StepPagamento),
        pdf_scaricati=int(
            db.scalar(
                select(func.count())
                .select_from(StepDocumento)
                .where(StepDocumento.pdf_status == "downloaded")
            )
            or 0
        ),
        residuo_totale=db.scalar(select(func.coalesce(func.sum(StepContribuente.residuo), 0)))
        or Decimal("0"),
        ultimo_aggiornamento=db.scalar(select(func.max(StepContribuente.last_seen_at))),
        links=links,
        import_archives=list_import_archives(),
    )


def list_contribuenti(
    db: Session,
    *,
    q: str | None,
    only_residuo: bool,
    page: int,
    page_size: int,
) -> StepContribuentiPage:
    query = select(StepContribuente)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                StepContribuente.codice_fiscale.ilike(pattern),
                StepContribuente.denominazione.ilike(pattern),
            )
        )
    if only_residuo:
        query = query.where(StepContribuente.residuo > 0)
    total = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    rows = db.scalars(
        query.order_by(StepContribuente.denominazione.asc(), StepContribuente.codice_fiscale.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return StepContribuentiPage(
        items=[StepContribuenteRow.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def _documento_out(db: Session, documento: StepDocumento) -> StepDocumentoOut:
    tributi = db.scalars(
        select(StepTributo)
        .where(StepTributo.documento_id == documento.id)
        .order_by(StepTributo.position)
    ).all()
    links = db.scalars(
        select(StepRuoloLink)
        .where(StepRuoloLink.documento_id == documento.id)
        .order_by(StepRuoloLink.reference_key)
    ).all()
    out = StepDocumentoOut.model_validate(documento)
    out.tributi = [StepTributoOut.model_validate(row) for row in tributi]
    out.links = [StepRuoloLinkOut.model_validate(row) for row in links]
    return out


def contribuente_detail(db: Session, contribuente_id: uuid.UUID) -> StepContribuenteDetail | None:
    contribuente = db.get(StepContribuente, contribuente_id)
    if contribuente is None:
        return None
    documenti = db.scalars(
        select(StepDocumento)
        .where(StepDocumento.contribuente_id == contribuente_id)
        .order_by(StepDocumento.num_doc)
    ).all()
    pagamenti = db.scalars(
        select(StepPagamento)
        .where(StepPagamento.contribuente_id == contribuente_id)
        .order_by(StepPagamento.position)
    ).all()
    detail = StepContribuenteDetail.model_validate(contribuente)
    detail.documenti = [_documento_out(db, documento) for documento in documenti]
    detail.pagamenti = [StepPagamentoOut.model_validate(row) for row in pagamenti]
    return detail


def link_anomalies(
    db: Session, *, status: str | None, page: int, page_size: int
) -> StepLinkAnomaliesPage:
    statuses = [status] if status else [item for item in LINK_STATUSES if item != "linked"]
    base = (
        select(StepRuoloLink, StepDocumento, StepContribuente)
        .join(StepDocumento, StepDocumento.id == StepRuoloLink.documento_id)
        .join(StepContribuente, StepContribuente.id == StepDocumento.contribuente_id)
        .where(StepRuoloLink.status.in_(statuses))
    )
    total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = db.execute(
        base.order_by(StepContribuente.denominazione, StepRuoloLink.reference_key)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        StepLinkAnomalyOut(
            **StepRuoloLinkOut.model_validate(link).model_dump(),
            contribuente_id=contribuente.id,
            codice_fiscale=contribuente.codice_fiscale,
            denominazione=contribuente.denominazione,
            num_doc=documento.num_doc,
        )
        for link, documento, contribuente in rows
    ]
    return StepLinkAnomaliesPage(items=items, total=total, page=page, page_size=page_size)


def links_for_avviso(db: Session, avviso_id: uuid.UUID) -> list[StepAvvisoLinkOut]:
    rows = db.execute(
        select(StepRuoloLink, StepDocumento, StepContribuente)
        .join(StepDocumento, StepDocumento.id == StepRuoloLink.documento_id)
        .join(StepContribuente, StepContribuente.id == StepDocumento.contribuente_id)
        .where(StepRuoloLink.ruolo_avviso_id == avviso_id)
        .order_by(StepDocumento.num_doc)
    ).all()
    return [
        StepAvvisoLinkOut(
            contribuente_id=contribuente.id,
            codice_fiscale=contribuente.codice_fiscale,
            denominazione=contribuente.denominazione,
            documento_id=documento.id,
            num_doc=documento.num_doc,
            data_notifica=documento.data_notifica,
            pdf_status=documento.pdf_status,
            link=StepRuoloLinkOut.model_validate(link),
        )
        for link, documento, contribuente in rows
    ]


def documento_pdf(db: Session, documento_id: uuid.UUID) -> tuple[StepDocumento, Path] | None:
    documento = db.get(StepDocumento, documento_id)
    if documento is None or documento.pdf_status != "downloaded" or not documento.pdf_path:
        return None
    try:
        return documento, storage.resolve_stored_pdf(documento.pdf_path)
    except FileNotFoundError:
        return None
