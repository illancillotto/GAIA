"""Record past shipments atomically; never dispatch or authorize a shipment."""

from uuid import uuid4

from sqlalchemy import select

from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeEvidence,
    NoticeNotification,
)
from app.modules.ruolo.services.notice_register import (
    RegisterConflict,
    _audit,
    _document,
    _snapshot,
)


def _reject_duplicate(db, document_id, payload):
    channels = ("posta", "raccomandata") if payload.channel == "posta" else (payload.channel,)
    identity = (
        NoticeAttempt.tracking_code == payload.tracking_code
        if payload.tracking_code
        else NoticeAttempt.sent_at == payload.sent_at
    )
    existing = db.scalar(
        select(NoticeAttempt.id)
        .where(
            NoticeAttempt.document_id == document_id,
            NoticeAttempt.channel.in_(channels),
            identity,
        )
        .limit(1)
    )
    if existing is not None:
        raise RegisterConflict("Tentativo gia presente: controllare gli eventi del documento")


def record_attempt(db, document_id, payload, change):
    document = _document(db, document_id, change)
    _reject_duplicate(db, document.id, payload)
    notification = db.get(NoticeNotification, document.id)
    before = _snapshot(notification) if notification else None
    attempt = NoticeAttempt(
        id=uuid4(),
        document_id=document.id,
        source_system="manual",
        source_key=str(uuid4()),
        channel=payload.channel,
        tracking_code=payload.tracking_code,
        sent_at=payload.sent_at,
    )
    db.add(attempt)
    db.flush()
    evidence = NoticeEvidence(
        id=uuid4(),
        document_id=document.id,
        attempt_id=attempt.id,
        source_system="manual",
        source_key=str(attempt.id),
        kind="invio_registrato",
        occurred_on=payload.sent_at.date(),
        reference=payload.evidence_reference,
        original_json=payload.model_dump(mode="json"),
    )
    db.add(evidence)
    if notification is None:
        notification = NoticeNotification(document_id=document.id)
        db.add(notification)
    notification.state, notification.notified_on, notification.evidence_id = (
        "da_verificare",
        None,
        None,
    )
    db.flush()
    _audit(
        db,
        document,
        change,
        {
            "action": "record_attempt",
            "before_json": {"notification": before},
            "after_json": {
                "attempt": _snapshot(attempt),
                "evidence": _snapshot(evidence),
                "notification": _snapshot(notification),
            },
        },
    )
    return attempt
