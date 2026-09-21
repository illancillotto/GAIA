"""Read-only register projections. Search results never establish a link."""

from uuid import UUID

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.notice_register_api_schemas import (
    CandidateFilters,
    CandidateResult,
    CandidateView,
    DocumentDetail,
    DocumentSummary,
    DocumentView,
    NotificationView,
    Pagination,
    PositionView,
    RecoveryView,
    RegisterFilters,
)
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeAudit,
    NoticeDocument,
    NoticeEvidence,
    NoticeNotification,
    NoticePosition,
    NoticeRecovery,
)


def _position_counts():
    tax_code_differs = and_(
        func.trim(NoticeDocument.tax_code) != "",
        func.trim(RuoloAvviso.codice_fiscale_raw) != "",
        func.upper(func.trim(NoticeDocument.tax_code))
        != func.upper(func.trim(RuoloAvviso.codice_fiscale_raw)),
    )
    conflicting = and_(
        NoticePosition.avviso_id.is_not(None),
        or_(
            RuoloAvviso.id.is_(None),
            RuoloAvviso.anno_tributario != NoticePosition.tax_year,
            tax_code_differs,
        ),
    )
    return (
        select(
            NoticePosition.document_id,
            func.count().label("position_count"),
            func.sum(case((NoticePosition.avviso_id.is_(None), 1), else_=0)).label(
                "unlinked_count"
            ),
            func.sum(case((conflicting, 1), else_=0)).label("conflicting_count"),
            func.sum(
                case(
                    (
                        or_(
                            NoticeRecovery.position_id.is_(None),
                            NoticeRecovery.state == "da_verificare",
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("recovery_review_count"),
        )
        .join(NoticeDocument, NoticeDocument.id == NoticePosition.document_id)
        .outerjoin(RuoloAvviso, RuoloAvviso.id == NoticePosition.avviso_id)
        .outerjoin(NoticeRecovery, NoticeRecovery.position_id == NoticePosition.id)
        .group_by(NoticePosition.document_id)
        .subquery()
    )


def _summary_query():
    counts = _position_counts()
    return (
        select(
            NoticeDocument,
            func.coalesce(NoticeNotification.state, "da_verificare").label("notification_state"),
            *(
                func.coalesce(counts.c[name], 0).label(name)
                for name in (
                    "position_count",
                    "unlinked_count",
                    "conflicting_count",
                    "recovery_review_count",
                )
            ),
        )
        .outerjoin(NoticeNotification, NoticeNotification.document_id == NoticeDocument.id)
        .outerjoin(
            counts,
            counts.c.document_id == NoticeDocument.id,
        )
    )


def _search_documents(q: str):
    position_matches = (
        select(NoticePosition.id)
        .where(
            NoticePosition.document_id == NoticeDocument.id,
            NoticePosition.source_reference.icontains(q, autoescape=True),
        )
        .exists()
    )
    tracking_matches = (
        select(NoticeAttempt.id)
        .where(
            NoticeAttempt.document_id == NoticeDocument.id,
            NoticeAttempt.tracking_code.icontains(q, autoescape=True),
        )
        .exists()
    )
    return or_(
        NoticeDocument.document_number.icontains(q, autoescape=True),
        NoticeDocument.tax_code.icontains(q, autoescape=True),
        position_matches,
        tracking_matches,
    )


def _filter_query(query, filters: RegisterFilters):
    columns = query.selected_columns
    if filters.view == "riconciliati":
        query = query.where(NoticeDocument.reconciled_into_id.is_not(None))
    else:
        query = query.where(NoticeDocument.reconciled_into_id.is_(None))
    if filters.reconciliation_candidates:
        query = query.where(NoticeDocument.source_system != "poste_db", columns.position_count > 0)
    if filters.q is not None:
        query = query.where(_search_documents(filters.q))
    if (
        filters.tax_year is not None
        or filters.recovery_state is not None
        or filters.view == "affidamenti"
    ):
        query = query.where(_matching_position(filters))
    if filters.notification_state is not None:
        query = query.where(columns.notification_state == filters.notification_state)
    if filters.view == "anomalie":
        query = query.where(
            or_(
                columns.position_count == 0,
                columns.unlinked_count > 0,
                columns.conflicting_count > 0,
                columns.recovery_review_count > 0,
                columns.notification_state == "da_verificare",
            )
        )
    return query


def _matching_position(filters: RegisterFilters):
    query = (
        select(NoticePosition.id)
        .outerjoin(
            NoticeRecovery,
            NoticeRecovery.position_id == NoticePosition.id,
        )
        .where(
            NoticePosition.document_id == NoticeDocument.id,
        )
    )
    state = func.coalesce(NoticeRecovery.state, "da_verificare")
    if filters.tax_year is not None:
        query = query.where(NoticePosition.tax_year == filters.tax_year)
    if filters.recovery_state is not None:
        query = query.where(state == filters.recovery_state)
    if filters.view == "affidamenti":
        query = query.where(state == "affidato")
    return query.exists()


def _summary(row) -> DocumentSummary:
    document, state, count, unlinked, conflicting, recovery_review = row
    anomalies = [
        key
        for key, detected in (
            ("posizioni_assenti", count == 0),
            ("collegamenti_mancanti", unlinked > 0),
            ("collegamenti_discordanti", conflicting > 0),
            ("notifica_da_verificare", state == "da_verificare"),
            ("step_da_verificare", recovery_review > 0),
        )
        if detected
    ]
    if document.reconciled_into_id is not None:
        anomalies = []
    return DocumentSummary(
        **DocumentView.model_validate(document).model_dump(),
        notification_state=state,
        position_count=count,
        unlinked_count=unlinked,
        conflicting_count=conflicting,
        recovery_review_count=recovery_review,
        anomalies=anomalies,
    )


def _page(db: Session, query, pagination: Pagination) -> tuple[list, int]:
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = list(
        db.execute(
            query.offset((pagination.page - 1) * pagination.page_size).limit(pagination.page_size)
        )
    )
    return rows, total


def list_documents(db: Session, filters: RegisterFilters) -> dict:
    query = _filter_query(_summary_query(), filters).order_by(
        NoticeDocument.created_at.desc(),
        NoticeDocument.id,
    )
    rows, total = _page(db, query, filters)
    return {
        "items": [_summary(row) for row in rows],
        "total": total,
        "page": filters.page,
        "page_size": filters.page_size,
    }


def document_detail(db: Session, document: NoticeDocument) -> DocumentDetail:
    summary = _summary(db.execute(_summary_query().where(NoticeDocument.id == document.id)).one())
    notification = db.get(NoticeNotification, document.id)
    rows = db.execute(
        select(NoticePosition, RuoloAvviso, NoticeRecovery)
        .outerjoin(
            RuoloAvviso,
            RuoloAvviso.id == NoticePosition.avviso_id,
        )
        .outerjoin(NoticeRecovery, NoticeRecovery.position_id == NoticePosition.id)
        .where(
            NoticePosition.document_id == document.id,
        )
        .order_by(NoticePosition.tax_year, NoticePosition.source_reference, NoticePosition.id)
    )
    return DocumentDetail(
        **summary.model_dump(),
        original_json=document.original_json,
        notification=NotificationView.model_validate(notification) if notification else None,
        positions=[
            PositionView(
                id=p.id,
                source_namespace=p.source_namespace,
                source_reference=p.source_reference,
                tax_year=p.tax_year,
                avviso_id=p.avviso_id,
                avviso=CandidateView.model_validate(a) if a else None,
                recovery=RecoveryView.model_validate(r) if r else None,
            )
            for p, a, r in rows
        ],
    )


def _candidate_search(q: str):
    text_match = or_(
        *(
            column.icontains(q, autoescape=True)
            for column in (
                RuoloAvviso.codice_cnc,
                RuoloAvviso.codice_fiscale_raw,
                RuoloAvviso.nominativo_raw,
            )
        )
    )
    try:
        identifier = UUID(q)
    except ValueError:
        return text_match
    return or_(text_match, RuoloAvviso.id == identifier)


def search_candidates(db: Session, position: NoticePosition, filters: CandidateFilters) -> dict:
    linked = (
        select(NoticePosition.id)
        .where(
            NoticePosition.document_id == position.document_id,
            NoticePosition.avviso_id == RuoloAvviso.id,
        )
        .exists()
    )
    query = (
        select(RuoloAvviso, linked)
        .where(
            RuoloAvviso.anno_tributario == position.tax_year,
            _candidate_search(filters.q),
        )
        .order_by(RuoloAvviso.codice_cnc, RuoloAvviso.id)
    )
    rows, total = _page(db, query, filters)
    return {
        "items": [
            CandidateResult(
                **CandidateView.model_validate(avviso).model_dump(),
                already_linked=already_linked,
            )
            for avviso, already_linked in rows
        ],
        "total": total,
        "page": filters.page,
        "page_size": filters.page_size,
    }


def document_events(db: Session, document_id, kind: str, pagination: Pagination) -> dict:
    model, order = {
        "evidenze": (NoticeEvidence, NoticeEvidence.id),
        "invii": (NoticeAttempt, NoticeAttempt.id),
        "storico": (NoticeAudit, NoticeAudit.version.desc()),
    }[kind]
    rows, total = _page(
        db, select(model).where(model.document_id == document_id).order_by(order), pagination
    )
    return {
        "items": [row[0] for row in rows],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }
