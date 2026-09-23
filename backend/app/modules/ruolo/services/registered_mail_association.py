from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.ruolo.enums import (
    RuoloTributiPaymentRecordStatus,
    RuoloTributiRegisteredMailMatchStatus,
    RuoloTributiRegisteredMailRecoveryStatus,
)
from app.modules.ruolo.models import RuoloAvviso, RuoloTributiPayment, RuoloTributiRegisteredMail
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeAudit,
    NoticeDocument,
    NoticeNotification,
    NoticePosition,
    NoticeRecovery,
)

MANUAL_ASSOCIATION_KEY = "manual_association"


def associated_avviso_ids(mail: RuoloTributiRegisteredMail | None) -> set[uuid.UUID]:
    """Return all active links, including the legacy primary link."""
    if mail is None:
        return set()
    result = {mail.avviso_id} if mail.avviso_id is not None else set()
    association = manual_association(mail)
    values = association.get("avviso_ids", []) if association else []
    if isinstance(values, list):
        for value in values:
            try:
                result.add(uuid.UUID(str(value)))
            except (TypeError, ValueError):
                continue
    return result


def get_registered_mail(db: Session, mail_id: uuid.UUID) -> RuoloTributiRegisteredMail | None:
    return db.scalar(
        select(RuoloTributiRegisteredMail)
        .where(RuoloTributiRegisteredMail.id == mail_id)
        .with_for_update()
    )


def set_manual_association(
    db: Session,
    *,
    mail: RuoloTributiRegisteredMail,
    avviso: RuoloAvviso | None,
    updated_by: int,
    avvisi: list[RuoloAvviso] | None = None,
) -> RuoloTributiRegisteredMail:
    selected = avvisi if avvisi is not None else ([avviso] if avviso is not None else [])
    previous = manual_association(mail) or {}
    previous_ids = previous.get("avviso_ids")
    was_cumulative = isinstance(previous_ids, list) and len(previous_ids) > 1
    if len(selected) > 1:
        _validate_selected_avvisi(selected)
        _sync_cumulative_register(db, mail=mail, avvisi=selected, updated_by=updated_by)
    elif was_cumulative:
        _clear_cumulative_register(db, mail=mail, updated_by=updated_by)
    primary = selected[0] if selected else None
    payload = dict(mail.raw_payload_json or {})
    payload[MANUAL_ASSOCIATION_KEY] = {
        "active": True,
        "avviso_id": str(primary.id) if primary is not None else None,
        "avviso_ids": [str(item.id) for item in selected],
        "updated_by": updated_by,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    mail.raw_payload_json = payload
    mail.avviso_id = primary.id if primary is not None else None
    mail.subject_id = primary.subject_id if primary is not None else None
    mail.match_status = (
        RuoloTributiRegisteredMailMatchStatus.MATCHED.value
        if primary is not None
        else RuoloTributiRegisteredMailMatchStatus.UNMATCHED.value
    )
    mail.match_score = 100 if primary is not None else None
    mail.match_reason = (
        "Associazione manuale impostata dall'operatore"
        if primary is not None
        else "Associazione manuale rimossa dall'operatore"
    )
    mail.anomaly_key = None if primary is not None else "manual_unlinked"
    mail.recovery_status = _recovery_status(db, primary, avvisi=selected)
    db.flush()
    return mail


def _validate_selected_avvisi(avvisi: list[RuoloAvviso]) -> None:
    if len({item.id for item in avvisi}) != len(avvisi):
        raise ValueError("Avvisi duplicati")
    subjects = {item.subject_id for item in avvisi}
    if None in subjects or len(subjects) != 1:
        raise ValueError("Gli avvisi devono appartenere allo stesso contribuente")
    if len({item.anno_tributario for item in avvisi}) != len(avvisi):
        raise ValueError("E' consentito un solo avviso per annualita")


def _sync_cumulative_register(
    db: Session,
    *,
    mail: RuoloTributiRegisteredMail,
    avvisi: list[RuoloAvviso],
    updated_by: int,
) -> None:
    attempt = db.scalar(
        select(NoticeAttempt).where(NoticeAttempt.registered_mail_id == mail.id).with_for_update()
    )
    document = db.get(NoticeDocument, attempt.document_id) if attempt is not None else None
    if document is not None and (
        document.reconciled_into_id is not None or document.source_system != "posta_online"
    ):
        raise ValueError("Documento esistente: usare il Registro per aggiornare le posizioni")
    created = document is None
    if document is None:
        document = NoticeDocument(
            source_system="posta_online",
            source_key=f"{mail.source_shipment_id}:{mail.recipient_index}",
            document_number=mail.source_shipment_id,
            tax_code=avvisi[0].codice_fiscale_raw,
            original_json={
                "registered_mail_id": str(mail.id),
                "source_shipment_id": mail.source_shipment_id,
                "recipient_index": mail.recipient_index,
                "avviso_ids": [str(item.id) for item in avvisi],
                "registered_mail_cost_amount": (
                    float(mail.price_amount) if mail.price_amount is not None else None
                ),
            },
            version=1,
        )
        db.add(document)
        db.flush()
        db.add(NoticeNotification(document_id=document.id, state="da_verificare"))
        attempt = NoticeAttempt(
            document_id=document.id,
            source_system="posta_online",
            source_key=f"{mail.source_shipment_id}:{mail.recipient_index}",
            channel="raccomandata",
            tracking_code=mail.tracking_number,
            sent_at=mail.sent_at,
            registered_mail_id=mail.id,
        )
        db.add(attempt)
        db.flush()
        db.add(
            NoticeAudit(
                document_id=document.id,
                version=1,
                actor_id=updated_by,
                action="create_registered_mail_document",
                reason="Documento cumulativo raccomandata confermato dall'operatore",
                before_json={},
                after_json={"avviso_ids": [str(item.id) for item in avvisi]},
            )
        )
    else:
        document.original_json = {
            **(document.original_json or {}),
            "avviso_ids": [str(item.id) for item in avvisi],
            "registered_mail_cost_amount": (
                float(mail.price_amount) if mail.price_amount is not None else None
            ),
        }
        current = list(
            db.scalars(
                select(NoticePosition).where(NoticePosition.document_id == document.id)
            ).all()
        )
        for position in current:
            if position.avviso_id not in {item.id for item in avvisi}:
                position.avviso_id = None

    existing_by_year = {
        position.tax_year: position
        for position in db.scalars(
            select(NoticePosition).where(NoticePosition.document_id == document.id)
        )
    }
    for avviso in avvisi:
        position = existing_by_year.get(avviso.anno_tributario)
        if position is None:
            position = NoticePosition(
                document_id=document.id,
                source_namespace="posta_online",
                source_reference=str(avviso.id),
                tax_year=avviso.anno_tributario,
                avviso_id=avviso.id,
            )
            db.add(position)
            db.flush()
            db.add(NoticeRecovery(position_id=position.id, state="da_verificare"))
        else:
            position.avviso_id = avviso.id
            position.source_reference = str(avviso.id)
    if not created:
        db.add(
            NoticeAudit(
                document_id=document.id,
                version=document.version + 1,
                actor_id=updated_by,
                action="manual_registered_mail_association",
                reason="Associazione cumulativa raccomandata confermata dall'operatore",
                before_json={},
                after_json={"avviso_ids": [str(item.id) for item in avvisi]},
            )
        )
        document.version += 1
    db.flush()


def _clear_cumulative_register(
    db: Session,
    *,
    mail: RuoloTributiRegisteredMail,
    updated_by: int,
) -> None:
    attempt = db.scalar(
        select(NoticeAttempt).where(NoticeAttempt.registered_mail_id == mail.id).with_for_update()
    )
    if attempt is None:
        return
    document = db.get(NoticeDocument, attempt.document_id)
    if document is None:
        return
    positions = list(
        db.scalars(select(NoticePosition).where(NoticePosition.document_id == document.id))
    )
    if not any(position.avviso_id is not None for position in positions):
        return
    for position in positions:
        position.avviso_id = None
    document.original_json = {**(document.original_json or {}), "avviso_ids": []}
    document.version += 1
    db.add(
        NoticeAudit(
            document_id=document.id,
            version=document.version,
            actor_id=updated_by,
            action="manual_registered_mail_unlink",
            reason="Associazione cumulativa raccomandata rimossa dall'operatore",
            before_json={},
            after_json={"avviso_ids": []},
        )
    )
    db.flush()


def resolve_import_match(
    db: Session,
    mail: RuoloTributiRegisteredMail | None,
    automatic_match: dict[str, Any],
) -> dict[str, Any]:
    association = manual_association(mail)
    return manual_match(db, association) or automatic_match


def preserve_manual_association(
    payload: dict[str, Any],
    mail: RuoloTributiRegisteredMail | None,
) -> dict[str, Any]:
    association = manual_association(mail)
    if association is not None:
        payload[MANUAL_ASSOCIATION_KEY] = association
    return payload


def manual_association(mail: RuoloTributiRegisteredMail | None) -> dict[str, Any] | None:
    if mail is None or not isinstance(mail.raw_payload_json, dict):
        return None
    value = mail.raw_payload_json.get(MANUAL_ASSOCIATION_KEY)
    return dict(value) if isinstance(value, dict) and value.get("active") is True else None


def manual_match(db: Session, association: dict[str, Any] | None) -> dict[str, Any] | None:
    if association is None:
        return None
    raw_avviso_id = association.get("avviso_id")
    if raw_avviso_id is None:
        return _unmatched("Associazione manuale rimossa dall'operatore", "manual_unlinked")
    try:
        avviso = db.get(RuoloAvviso, uuid.UUID(str(raw_avviso_id)))
    except ValueError:
        avviso = None
    if avviso is None:
        return _unmatched(
            "Avviso dell'associazione manuale non disponibile", "manual_target_missing"
        )
    return {
        "match_status": RuoloTributiRegisteredMailMatchStatus.MATCHED.value,
        "match_score": 100,
        "match_reason": "Associazione manuale impostata dall'operatore",
        "avviso": avviso,
        "candidates": [avviso],
    }


def _unmatched(reason: str, anomaly_key: str) -> dict[str, Any]:
    return {
        "match_status": RuoloTributiRegisteredMailMatchStatus.UNMATCHED.value,
        "match_score": None,
        "match_reason": reason,
        "anomaly_key": anomaly_key,
        "candidates": [],
    }


def _recovery_status(
    db: Session,
    avviso: RuoloAvviso | None,
    *,
    avvisi: list[RuoloAvviso] | None = None,
) -> str:
    selected = avvisi or ([avviso] if avviso is not None else [])
    if not selected:
        return RuoloTributiRegisteredMailRecoveryStatus.PENDING.value
    paid_amount = db.scalar(
        select(func.coalesce(func.sum(RuoloTributiPayment.amount), 0)).where(
            RuoloTributiPayment.avviso_id.in_([item.id for item in selected]),
            RuoloTributiPayment.status == RuoloTributiPaymentRecordStatus.VALID.value,
        )
    )
    if Decimal(str(paid_amount or 0)) > Decimal("0"):
        return RuoloTributiRegisteredMailRecoveryStatus.READY_ON_PAYMENT.value
    return RuoloTributiRegisteredMailRecoveryStatus.PENDING.value
