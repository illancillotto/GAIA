"""Audited register commands. The caller owns authorization and commit/rollback.

All mutations serialize on the document and reject stale operator versions.
No command creates debt, infers a notification, or enables an outgoing shipment.
"""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeAudit,
    NoticeDocument,
    NoticeEvidence,
    NoticeNotification,
    NoticePosition,
    NoticeRecovery,
)
from app.modules.ruolo.notice_register_schemas import (
    DocumentDetails,
    EvidenceInput,
    HistoricalDocument,
    NotificationDecision,
    OperatorChange,
    PositionInput,
    RecoveryDecision,
)


class RegisterConflict(ValueError):
    """The operator must reload before applying a stale change."""


class RegisterNotFound(ValueError):
    """A document or a position in the requested document does not exist."""


def _snapshot(record: object) -> dict:
    result = {}
    for column in inspect(type(record)).columns:
        value = getattr(record, column.key)
        if isinstance(value, date | datetime | Decimal | uuid.UUID):
            value = str(value)
        result[column.key] = deepcopy(value)
    return result


def _document(
    db: Session, document_id: uuid.UUID, change: OperatorChange, *, allow_reconciled: bool = False
) -> NoticeDocument:
    document = db.scalar(
        select(NoticeDocument)
        .where(NoticeDocument.id == document_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if document is None:
        raise RegisterNotFound("Documento non trovato")
    if document.reconciled_into_id is not None and not allow_reconciled:
        raise RegisterConflict("Scheda gia riconciliata: aprire il documento di destinazione")
    if document.version != change.expected_version:
        raise RegisterConflict("Registro modificato da un altro operatore: ricaricare")
    return document


def _audit(db: Session, document: NoticeDocument, change: OperatorChange, event: dict) -> None:
    document.version += 1
    db.add(
        NoticeAudit(
            document_id=document.id,
            version=document.version,
            actor_id=change.actor_id,
            reason=change.reason,
            **event,
        )
    )
    db.flush()


def create_historical_document(
    db: Session,
    payload: HistoricalDocument,
    change: OperatorChange,
) -> NoticeDocument:
    if change.expected_version != 1:
        raise RegisterConflict("Un nuovo documento deve partire dalla versione 1")
    document = NoticeDocument(
        id=uuid.uuid4(),
        source_system="manual",
        source_key=str(uuid.uuid4()),
        **payload.model_dump(exclude={"positions"}),
        original_json=payload.model_dump(mode="json"),
        version=1,
    )
    db.add(document)
    db.flush()
    db.add(NoticeNotification(document_id=document.id, state="da_verificare"))
    positions = []
    for item in payload.positions:
        position = NoticePosition(id=uuid.uuid4(), document_id=document.id, **item.model_dump())
        db.add(position)
        db.flush()
        db.add(NoticeRecovery(position_id=position.id, state="da_verificare"))
        positions.append(_snapshot(position))
    db.add(
        NoticeAudit(
            document_id=document.id,
            version=1,
            actor_id=change.actor_id,
            reason=change.reason,
            action="create_document",
            before_json={},
            after_json={"document": _snapshot(document), "positions": positions},
        )
    )
    db.flush()
    return document


def revise_document(
    db: Session,
    document_id: uuid.UUID,
    payload: DocumentDetails,
    change: OperatorChange,
) -> NoticeDocument:
    document = _document(db, document_id, change)
    if all(getattr(document, field) == value for field, value in payload.model_dump().items()):
        return document
    notification = db.get(NoticeNotification, document_id)
    before = {**_snapshot(document), "notification": _snapshot(notification)}
    for field, value in payload.model_dump().items():
        setattr(document, field, value)
    _reset_notification(notification)
    _audit(
        db,
        document,
        change,
        {
            "action": "revise_document",
            "before_json": before,
            "after_json": {
                **_snapshot(document),
                "version": document.version + 1,
                "notification": _snapshot(notification),
            },
        },
    )
    return document


def _position(db: Session, document_id: uuid.UUID, position_id: uuid.UUID) -> NoticePosition:
    position = db.get(NoticePosition, position_id)
    if position is None or position.document_id != document_id:
        raise RegisterNotFound("Posizione non appartenente al documento")
    return position


def _validate_link(db: Session, position: NoticePosition, avviso_id: uuid.UUID | None) -> None:
    if avviso_id is None:
        return
    avviso = db.get(RuoloAvviso, avviso_id)
    if avviso is None or avviso.anno_tributario != position.tax_year:
        raise ValueError("Avviso inesistente o annualita non corrispondente")
    existing = db.scalar(
        select(NoticePosition.id).where(
            NoticePosition.document_id == position.document_id,
            NoticePosition.avviso_id == avviso_id,
            NoticePosition.id != position.id,
        )
    )
    if existing is not None:
        raise ValueError("Avviso gia collegato al documento")


def _reset_notification(notification: NoticeNotification) -> None:
    notification.state = "da_verificare"
    notification.notified_on = notification.evidence_id = None


def _scope_snapshot(db: Session, position: NoticePosition) -> dict:
    return {
        "position": _snapshot(position),
        "notification": _snapshot(db.get(NoticeNotification, position.document_id)),
        "recovery": _snapshot(db.get(NoticeRecovery, position.id)),
    }


def _reset_position_review(db: Session, position: NoticePosition) -> None:
    _reset_notification(db.get(NoticeNotification, position.document_id))
    recovery = db.get(NoticeRecovery, position.id)
    recovery.state = "da_verificare"
    recovery.case_reference = recovery.verified_on = recovery.evidence_reference = (
        recovery.amount
    ) = None


def add_position(
    db: Session,
    document_id: uuid.UUID,
    payload: PositionInput,
    change: OperatorChange,
) -> NoticePosition:
    document = _document(db, document_id, change)
    notification = db.get(NoticeNotification, document_id)
    before = {"notification": _snapshot(notification)}
    position = NoticePosition(id=uuid.uuid4(), document_id=document_id, **payload.model_dump())
    db.add(position)
    db.flush()
    db.add(NoticeRecovery(position_id=position.id, state="da_verificare"))
    db.flush()
    _reset_notification(notification)
    _audit(
        db,
        document,
        change,
        {
            "action": "add_position",
            "before_json": before,
            "after_json": _scope_snapshot(db, position),
        },
    )
    return position


def revise_position(
    db: Session,
    document_id: uuid.UUID,
    position_id: uuid.UUID,
    payload: PositionInput,
    change: OperatorChange,
) -> NoticePosition:
    document = _document(db, document_id, change)
    position = _position(db, document_id, position_id)
    if all(getattr(position, field) == value for field, value in payload.model_dump().items()):
        return position
    before = _scope_snapshot(db, position)
    for field, value in payload.model_dump().items():
        setattr(position, field, value)
    position.avviso_id = None
    _reset_position_review(db, position)
    _audit(
        db,
        document,
        change,
        {
            "action": "revise_position",
            "before_json": before,
            "after_json": _scope_snapshot(db, position),
        },
    )
    return position


def link_position(
    db: Session,
    document_id: uuid.UUID,
    position_id: uuid.UUID,
    avviso_id: uuid.UUID | None,
    change: OperatorChange,
) -> NoticePosition:
    document = _document(db, document_id, change)
    position = _position(db, document_id, position_id)
    _validate_link(db, position, avviso_id)
    if position.avviso_id == avviso_id:
        return position
    before = _scope_snapshot(db, position)
    position.avviso_id = avviso_id
    # A corrected scope must be reviewed again; retain the former proof in audit.
    _reset_position_review(db, position)
    _audit(
        db,
        document,
        change,
        {
            "action": "link_position",
            "before_json": before,
            "after_json": _scope_snapshot(db, position),
        },
    )
    return position


def record_evidence(
    db: Session,
    document_id: uuid.UUID,
    payload: EvidenceInput,
    change: OperatorChange,
) -> NoticeEvidence:
    document = _document(db, document_id, change)
    if payload.attempt_id is not None:
        attempt = db.get(NoticeAttempt, payload.attempt_id)
        if attempt is None or attempt.document_id != document_id:
            raise ValueError("Tentativo non appartenente al documento")
    evidence = NoticeEvidence(id=uuid.uuid4(), document_id=document_id, **payload.model_dump())
    db.add(evidence)
    _audit(
        db,
        document,
        change,
        {
            "action": "record_evidence",
            "before_json": {},
            "after_json": _snapshot(evidence),
        },
    )
    return evidence


def assess_notification(
    db: Session,
    document_id: uuid.UUID,
    payload: NotificationDecision,
    change: OperatorChange,
) -> NoticeNotification:
    document = _document(db, document_id, change)
    if payload.evidence_id is not None:
        evidence = db.get(NoticeEvidence, payload.evidence_id)
        if evidence is None or evidence.document_id != document_id:
            raise ValueError("Evidenza non appartenente al documento")
    notification = db.get(NoticeNotification, document_id)
    before = _snapshot(notification)
    for field, value in payload.model_dump().items():
        setattr(notification, field, value)
    _audit(
        db,
        document,
        change,
        {
            "action": "assess_notification",
            "before_json": before,
            "after_json": _snapshot(notification),
        },
    )
    return notification


def assess_recovery(
    db: Session,
    document_id: uuid.UUID,
    position_id: uuid.UUID,
    payload: RecoveryDecision,
    change: OperatorChange,
) -> NoticeRecovery:
    document = _document(db, document_id, change)
    _position(db, document_id, position_id)
    recovery = db.get(NoticeRecovery, position_id)
    before = _snapshot(recovery)
    for field, value in payload.model_dump().items():
        setattr(recovery, field, value)
    _audit(
        db,
        document,
        change,
        {
            "action": "assess_recovery",
            "before_json": before,
            "after_json": _snapshot(recovery),
        },
    )
    return recovery
