"""Load list-only states once per page, using the canonical accounting calculation."""

from uuid import UUID

from sqlalchemy import select

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.notice_register_models import NoticeNotification, NoticePosition

from .models import CommunicationMessage


def page_states(db, items):
    identities = {item.id for item in items}
    avviso_ids = {UUID(value) for item in items for value in item.avviso_ids_json or []}
    if not identities:
        return {}, {}, {}
    query, _, _ = repo._base_tributi_query()
    rows = db.execute(query.where(RuoloAvviso.id.in_(avviso_ids))).all()
    cores = repo._precompute_tributi_effective_cores(db, rows=rows)
    payment = {identity: value["payment_status"] for identity, value in cores.items()}
    notifications = {}
    for identity, state in db.execute(
        select(NoticePosition.avviso_id, NoticeNotification.state)
        .join(NoticeNotification, NoticeNotification.document_id == NoticePosition.document_id)
        .where(NoticePosition.avviso_id.in_(avviso_ids))
    ):
        notifications.setdefault(identity, set()).add(state)
    messages = {}
    for message in db.scalars(
        select(CommunicationMessage)
        .where(CommunicationMessage.source_entity_id.in_(identities))
        .order_by(CommunicationMessage.created_at.desc(), CommunicationMessage.id.desc())
    ):
        messages.setdefault(message.source_entity_id, message)
    return payment, notifications, messages


def item_states(item, payment, notifications):
    ids = [UUID(value) for value in item.avviso_ids_json or []]
    payments = {payment.get(identity, "da_verificare") for identity in ids}
    states = {state for identity in ids for state in notifications.get(identity, ())}
    return ", ".join(sorted(payments)) or "da_verificare", ", ".join(
        sorted(states)
    ) or "da_verificare"
