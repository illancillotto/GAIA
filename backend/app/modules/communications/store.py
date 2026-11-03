"""Atomic outbox lookups, transitions and append-only audit events."""

from sqlalchemy import select

from .models import CommunicationAttachment, CommunicationEvent, CommunicationMessage
from .policy import TRANSITIONS, Conflict, Missing


def event(db, aggregate_id, kind, *, actor_id=None, **detail):
    db.add(
        CommunicationEvent(aggregate_id=aggregate_id, kind=kind, actor_id=actor_id, detail=detail)
    )


def message(db, identity, *, expected_version=None):
    result = db.scalar(
        select(CommunicationMessage)
        .where(CommunicationMessage.id == identity)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if result is None:
        raise Missing("Comunicazione non trovata")
    if expected_version is not None and expected_version != result.version:
        raise Conflict("Versione obsoleta: ricaricare la comunicazione")
    return result


def attachments(db, identity):
    return list(
        db.scalars(
            select(CommunicationAttachment)
            .where(CommunicationAttachment.message_id == identity)
            .order_by(CommunicationAttachment.primary_document.desc(), CommunicationAttachment.id)
        )
    )


def transition(db, item, target, *, actor_id=None, **detail):
    if target not in TRANSITIONS[item.state]:
        raise Conflict(f"Transizione {item.state} -> {target} non consentita")
    before, item.state = item.state, target
    event(db, item.id, "state_changed", actor_id=actor_id, before=before, after=target, **detail)


def public_model(value, *, omit=()):
    return {
        column.name: getattr(value, column.name)
        for column in value.__table__.columns
        if column.name not in omit
    }


def detail(db, item):
    result = public_model(item)
    result["attachments"] = [public_model(a, omit=("content",)) for a in attachments(db, item.id)]
    return result
