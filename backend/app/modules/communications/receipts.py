"""Archive first, correlate by technical identity, project technical evidence only."""

from email import policy
from email.parser import BytesParser

from sqlalchemy import select

from app.modules.ruolo.notice_register_models import NoticeAttempt, NoticeEvidence

from . import store
from .models import CommunicationMessage, CommunicationReceipt
from .policy import now, sha256
from .receipt_parser import parse


def ingest(db, account, raw, *, parser=parse):
    fingerprint = sha256(raw)
    duplicate = db.scalar(
        select(CommunicationReceipt).where(
            CommunicationReceipt.account_id == account.id,
            CommunicationReceipt.sha256 == fingerprint,
        )
    )
    if duplicate:
        return duplicate
    parsed = parser(raw, account.channel)
    message = _correlate(db, account, parsed)
    provider_id = str(BytesParser(policy=policy.default).parsebytes(raw).get("Message-ID") or "")[
        :200
    ]
    receipt = CommunicationReceipt(
        message_id=message.id if message else None,
        account_id=account.id,
        kind=parsed.kind,
        provider_id=provider_id,
        correlated_id=parsed.correlated_id,
        occurred_at=parsed.occurred_at,
        sha256=fingerprint,
        original=raw,
        classification="matched" if message else "unmatched",
    )
    db.add(receipt)
    db.flush()
    store.event(
        db,
        message.id if message else account.id,
        "receipt_archived",
        receipt_id=str(receipt.id),
        receipt_kind=parsed.kind,
        classification=receipt.classification,
    )
    if message:
        _apply(db, message, receipt)
    return receipt


def _correlate(db, account, parsed):
    if not parsed.correlated_id or (account.channel == "pec" and not parsed.verified):
        return None
    message = db.scalar(
        select(CommunicationMessage)
        .where(
            CommunicationMessage.account_id == account.id,
            CommunicationMessage.technical_id == parsed.correlated_id,
        )
        .with_for_update()
    )
    if message is None or message.recipient.lower() != parsed.recipient:
        return None
    return message


def _apply(db, message, receipt):
    target = receipt.kind
    if target in {"accepted", "delivered", "not_delivered"}:
        # Never downgrade delivery with a duplicate, late acceptance or error.
        from .policy import TRANSITIONS

        if target in TRANSITIONS[message.state]:
            store.transition(db, message, target, receipt_id=str(receipt.id))
    _register_evidence(db, message, receipt)


def register_attempt(db, message):
    existing = db.scalar(
        select(NoticeAttempt).where(
            NoticeAttempt.source_system == "gaia_communications",
            NoticeAttempt.source_key == str(message.id),
        )
    )
    if existing:
        return existing
    attempt = NoticeAttempt(
        document_id=message.document_id,
        source_system="gaia_communications",
        source_key=str(message.id),
        channel=message.channel,
        tracking_code=str(message.id),
        sent_at=now(),
    )
    db.add(attempt)
    db.flush()
    return attempt


def _register_evidence(db, message, receipt):
    attempt = register_attempt(db, message)
    # Append evidence without modifying any legal evaluation or imported inCASS row.
    db.add(
        NoticeEvidence(
            document_id=message.document_id,
            attempt_id=attempt.id,
            source_system="gaia_communications",
            source_key=str(receipt.id),
            kind=f"{message.channel}_{receipt.kind}",
            occurred_on=receipt.occurred_at.date() if receipt.occurred_at else None,
            reference=f"communications/receipts/{receipt.id}",
            original_json={
                "receipt_id": str(receipt.id),
                "sha256": receipt.sha256,
                "technical_id": receipt.correlated_id,
                "legal_effect": "requires_review",
            },
        )
    )
