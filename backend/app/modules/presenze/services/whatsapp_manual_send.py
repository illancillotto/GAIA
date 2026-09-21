"""Confirmed manual delivery, serialized with scheduled reminders."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.presenze.services.punch_reminder_dispatch import (
    DispatchOutcome,
    is_within_send_window,
)
from app.modules.presenze.services.punch_reminder_job import _advisory_lock, record_dispatch_outcome
from app.modules.presenze.services.whatsapp_config import load_whatsapp_config
from app.modules.presenze.services.whatsapp_manual_preview import (
    manual_candidate,
    manual_preview,
    manual_text,
)
from app.modules.presenze.services.whatsapp_waha import WhatsAppSendError, build_whatsapp_sender
from app.modules.presenze.whatsapp_models import PresenzeWhatsAppMessage


class ManualSendRequest(BaseModel):
    fingerprint: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=5, max_length=1500)
    allow_outside_window: bool = False


def send_manual(
    db: Session, record_id: UUID, payload: ManualSendRequest, actor_id: int
) -> dict[str, str]:
    with _advisory_lock(db) as acquired:
        if not acquired:
            raise HTTPException(409, "Un invio WhatsApp e gia in corso; riprova piu tardi")
        db.rollback()
        preview = manual_preview(db, record_id)
        if preview["fingerprint"] != payload.fingerprint:
            raise HTTPException(409, "Dati cambiati: riapri l'anteprima prima di inviare")
        if len(payload.reason.strip()) < 5:
            raise HTTPException(422, "Specifica il motivo dell'anomalia")
        config = load_whatsapp_config(db)
        now = datetime.now(UTC)
        if not (payload.allow_outside_window or is_within_send_window(now, config.send_start_hour, config.send_end_hour)):
            raise HTTPException(
                409, "Invio consentito solo nella fascia oraria configurata, lun-ven"
            )
        recent = db.scalar(
            select(PresenzeWhatsAppMessage.id)
            .where(
                PresenzeWhatsAppMessage.created_at
                > now - timedelta(seconds=config.min_delay_seconds)
            )
            .limit(1)
        )
        if recent is not None:
            raise HTTPException(429, "Attendi la pausa configurata prima di un altro invio")
        try:
            sender = build_whatsapp_sender(config)
        except ValueError as exc:
            raise HTTPException(
                409, "Configurazione WhatsApp incompleta: contatta un amministratore"
            ) from exc
        if sender is None:
            raise HTTPException(409, "Provider WhatsApp non disponibile")
        reminder = manual_candidate(db, record_id)
        outcome = DispatchOutcome(reminder, manual_text(reminder, payload.reason), "SENDING")
        return _deliver(db, sender, outcome, (record_id, actor_id, payload.fingerprint))


def _deliver(db, sender, outcome: DispatchOutcome, audit: tuple[UUID, int, str]) -> dict[str, str]:
    try:
        if not sender.check_number(outcome.reminder.phone_e164):
            raise HTTPException(409, "Il numero del collaboratore non risulta su WhatsApp")
    except WhatsAppSendError as exc:
        raise HTTPException(
            502, "Impossibile verificare il numero WhatsApp; nessun invio eseguito"
        ) from exc
    # Network preflight can take time: never send to a contact changed meanwhile.
    db.rollback()
    if manual_preview(db, audit[0])["fingerprint"] != audit[2]:
        raise HTTPException(409, "Dati cambiati durante la verifica; riapri l'anteprima")
    message = record_dispatch_outcome(db, sender.provider, outcome)
    message.days_json = [
        {**day, "source": "manual", "requested_by_user_id": audit[1], "record_id": str(audit[0])}
        for day in message.days_json
    ]
    db.commit()
    outcome = replace(outcome, attempt_id=message.id)
    try:
        sent = sender.send_text(outcome.reminder.phone_e164, outcome.text)
        outcome = replace(outcome, status=sent.status, provider_message_id=sent.provider_message_id)
    except WhatsAppSendError as exc:
        outcome = replace(
            outcome,
            status="UNKNOWN" if exc.uncertain else "FAILED",
            error_code=exc.code,
            error_message=str(exc),
        )
    record_dispatch_outcome(db, sender.provider, outcome)
    return {"message_id": str(message.id), "status": outcome.status}
