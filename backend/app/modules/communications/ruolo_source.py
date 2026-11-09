"""Ruolo owns business rules and source documents; transports never import them."""

from pathlib import Path
from uuid import UUID

from sqlalchemy import String, cast, exists, func, or_, select

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import (
    RuoloAvviso,
    RuoloTributiNoticeNumber,
    RuoloTributiReminderBatch,
    RuoloTributiReminderBatchItem,
)
from app.modules.ruolo.notice_register_models import (
    NoticeDocument,
    NoticeNotification,
    NoticePosition,
)
from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem
from app.modules.ruolo.services.notice_communication_fields import (
    template_variables as template_variables,
)
from app.modules.ruolo.services.notice_eligibility import eligibility
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson
from app.modules.utenze.services.electronic_contacts import contact_columns, contact_values
from app.services.nas_connector import NasConnectorError

from .models import CommunicationMessage
from .policy import Conflict, Missing, digest, sha256


def source_item(db, identity):
    item = db.scalar(
        select(RuoloTributiReminderBatchItem)
        .where(RuoloTributiReminderBatchItem.id == identity)
        .execution_options(populate_existing=True)
    )
    if item is None:
        raise Missing("Sollecito non trovato")
    return item


def contacts(db, item):
    return contact_values(db, item.subject_id)


def read_pdf(item) -> bytes:
    """Read only: missing or regenerated files never cause an implicit generation."""
    path = item.generated_document_path
    if not path or Path(path).suffix.lower() != ".pdf":
        raise Conflict("PDF definitivo assente")
    try:
        if repo.is_remote_reminder_document_path(path):
            return repo.read_remote_reminder_document(Path(path))
        if Path(path).stat().st_size > 32 * 1024 * 1024:
            raise Conflict("PDF oltre 32 MiB")
        return Path(path).read_bytes()
    except (OSError, NasConnectorError) as exc:
        raise Conflict("PDF sorgente non disponibile") from exc


def _document(db, item):
    document = db.scalar(
        select(NoticeDocument)
        .where(
            NoticeDocument.source_system == "gaia_batch_item",
            NoticeDocument.source_key == str(item.id),
        )
        .execution_options(populate_existing=True)
    )
    number = str((item.payload_json or {}).get("notice_number") or "")
    reservation = db.scalar(
        select(RuoloTributiNoticeNumber).where(RuoloTributiNoticeNumber.notice_number == number)
    )
    if (
        document is None
        or document.reconciled_into_id
        or document.document_number != number
        or reservation is None
        or reservation.status != "generated"
    ):
        raise Conflict("Identità canonica o numero definitivo non verificati")
    return document


def _positions(db, item):
    results = []
    for value in item.avviso_ids_json or []:
        current = repo.get_tributi_avviso(db, UUID(value))
        if current is None or current["avviso"].anno_tributario != 2021:
            raise Conflict("Posizione mancante o annualità diversa da 2021")
        reasons = eligibility(db, current)["reasons"]
        if not current.get("reminder_enabled"):
            reasons.append("sollecito_non_abilitato")
        if reasons:
            raise Conflict("Sollecito non eleggibile: " + ", ".join(sorted(set(reasons))))
        avviso = current["avviso"]
        results.append(
            {
                "avviso": {
                    column.name: getattr(avviso, column.name) for column in avviso.__table__.columns
                },
                "current": {
                    key: current.get(key)
                    for key in (
                        "payment_status",
                        "saldo_amount",
                        "due_amount",
                        "paid_amount",
                        "workflow_status",
                        "calculation_policy",
                        "mailing_delivery",
                        "reminder_enabled",
                    )
                },
            }
        )
    if not results:
        raise Conflict("Sollecito senza posizioni canoniche")
    return results


def inspect(db, identity, *, own_message_id=None):
    item = source_item(db, identity)
    if item.status != "generated" or item.years_json != [2021]:
        raise Conflict("Sono ammessi solo PDF definitivi dell'annualità 2021")
    document = _document(db, item)
    poste = db.scalar(
        select(PosteDispatchItem.id)
        .where(
            or_(
                PosteDispatchItem.batch_item_id == item.id,
                PosteDispatchItem.notice_number == document.document_number,
            ),
            PosteDispatchItem.active_key.is_not(None),
        )
        .limit(1)
    )
    duplicate = db.scalar(
        select(CommunicationMessage.id)
        .where(
            CommunicationMessage.active_key == document.document_number,
            CommunicationMessage.id != own_message_id if own_message_id else True,
        )
        .limit(1)
    )
    if poste or duplicate:
        raise Conflict("Avviso già prenotato o spedito da un canale GAIA")
    business = _positions(db, item)
    content = read_pdf(item)
    fingerprint = digest(
        {
            "document": [document.id, document.version, document.document_number],
            "item": {column.name: getattr(item, column.name) for column in item.__table__.columns},
            "positions": business,
            "contacts": contacts(db, item),
            "pdf": sha256(content),
        }
    )
    return item, document, content, fingerprint


def list_candidates(db, *, channel, filters, page, page_size):
    item = RuoloTributiReminderBatchItem
    person, company = AnagraficaPerson, AnagraficaCompany
    year = func.replace(cast(item.years_json, String), " ", "") == "[2021]"
    query = (
        select(item, RuoloTributiReminderBatch.title, *contact_columns(item.subject_id).values())
        .join(RuoloTributiReminderBatch, item.batch_id == RuoloTributiReminderBatch.id)
        .outerjoin(person, person.subject_id == item.subject_id)
        .outerjoin(company, company.subject_id == item.subject_id)
        .where(year)
    )
    query = _candidate_filters(query, filters, channel)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(item.created_at.desc(), item.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [_candidate_row(db, *row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def _candidate_filters(query, filters, channel):
    item = RuoloTributiReminderBatchItem
    if filters.get("q"):
        term = "%" + filters["q"].replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.where(
            or_(
                item.display_name.ilike(term, escape="\\"),
                item.codice_fiscale.ilike(term, escape="\\"),
                cast(item.payload_json["notice_number"], String).ilike(term),
            )
        )
    if filters.get("batch_id"):
        query = query.where(item.batch_id == filters["batch_id"])
    query = _contact_filters(query, filters, channel)
    query = _business_filters(query, filters)
    for name, comparison in (
        ("date_from", item.created_at.__ge__),
        ("date_to", item.created_at.__le__),
    ):
        if filters.get(name):
            query = query.where(comparison(filters[name]))
    if filters.get("state") or filters.get("account_id"):
        conditions = [CommunicationMessage.source_entity_id == item.id]
        for key, column in (
            ("state", CommunicationMessage.state),
            ("account_id", CommunicationMessage.account_id),
        ):
            if filters.get(key):
                conditions.append(column == filters[key])
        query = query.where(exists().where(*conditions))
    return query


def _contact_filters(query, filters, channel):
    columns = contact_columns(RuoloTributiReminderBatchItem.subject_id)
    fields = (
        ("has_contact", columns[channel]),
        ("has_pec", columns["pec"]),
        ("has_email", columns["email"]),
    )
    for key, column in fields:
        if filters.get(key) is not None:
            present = column.is_not(None) & (func.trim(column) != "")
            query = query.where(present if filters[key] else ~present)
    return query


def _business_filters(query, filters):
    item = RuoloTributiReminderBatchItem
    if filters.get("document_state"):
        query = query.where(item.status == filters["document_state"])
    # Explicit Registro links; never infer an avviso from CF, year or number.
    position = (
        select(NoticePosition.avviso_id)
        .join(NoticeDocument)
        .where(
            NoticeDocument.source_system == "gaia_batch_item",
            func.replace(NoticeDocument.source_key, "-", "")
            == func.replace(cast(item.id, String), "-", ""),
        )
    )
    if filters.get("payment_state"):
        accounting, _, payment_status = repo._base_tributi_query()
        accounting = accounting.with_only_columns(RuoloAvviso.id).where(
            payment_status == filters["payment_state"]
        )
        query = query.where(position.where(NoticePosition.avviso_id.in_(accounting)).exists())
    if filters.get("notification_state"):
        notices = (
            select(NoticePosition.avviso_id)
            .join(NoticeNotification, NoticeNotification.document_id == NoticePosition.document_id)
            .where(NoticeNotification.state == filters["notification_state"])
        )
        query = query.where(position.where(NoticePosition.avviso_id.in_(notices)).exists())
    return query


def _candidate_row(db, item, title, email, pec):
    message = db.scalar(
        select(CommunicationMessage)
        .where(CommunicationMessage.source_entity_id == item.id)
        .order_by(CommunicationMessage.created_at.desc())
        .limit(1)
    )
    payment_state, notification_state = _current_states(db, item)
    return {
        "id": item.id,
        "batch_id": item.batch_id,
        "batch_title": title,
        "notice_number": (item.payload_json or {}).get("notice_number"),
        "display_name": item.display_name,
        "tax_code": item.codice_fiscale,
        "year": 2021,
        "amount": (item.payload_json or {}).get("notice_total_amount") or item.saldo_amount,
        "email": email,
        "pec": pec,
        "document_state": item.status,
        "payment_state": payment_state,
        "notification_state": notification_state,
        "communication_state": message.state if message else None,
        "message_id": message.id if message else None,
        "last_event_at": message.updated_at if message else None,
    }


def _current_states(db, item):
    ids = [UUID(value) for value in item.avviso_ids_json or []]
    summaries = [repo.get_tributi_avviso(db, identity) for identity in ids]
    payment = sorted({value["payment_status"] if value else "da_verificare" for value in summaries})
    notifications = sorted(
        set(
            db.scalars(
                select(NoticeNotification.state)
                .join(NoticePosition, NoticePosition.document_id == NoticeNotification.document_id)
                .where(NoticePosition.avviso_id.in_(ids))
            )
        )
    )
    return ", ".join(payment) or "da_verificare", ", ".join(notifications) or "da_verificare"
