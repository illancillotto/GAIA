"""Read-only selection and confirmation snapshot for a single daily anomaly."""

import hashlib
import json
from datetime import UTC, date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyRecord
from app.modules.presenze.services.parser import extract_detail_payload
from app.modules.presenze.services.punch_reminder_job import (
    _punches_by_record,
    load_notified_days,
    load_opted_out_user_ids,
    load_reminder_contacts,
    reminder_input,
)
from app.modules.presenze.services.punch_reminder_pending import blocked_days
from app.modules.presenze.services.punch_reminders import (
    PunchReminder,
    ReminderDay,
    ReminderPolicy,
    _contact_outcome,
    reminder_day,
)
from app.modules.presenze.services.whatsapp_config import load_whatsapp_config


def manual_candidate(db: Session, record_id: UUID) -> PunchReminder:
    record = db.get(PresenzeDailyRecord, record_id)
    if record is None:
        raise HTTPException(404, "Giornata non trovata")
    collaborator = db.get(PresenzeCollaborator, record.collaborator_id)
    if collaborator is None or not collaborator.is_active:
        raise HTTPException(409, "Collaboratore non attivo")
    punches = _punches_by_record(db, [record.id]).get(record.id, ())
    item = reminder_input(record, collaborator, punches)
    today = datetime.now(UTC).astimezone(ZoneInfo("Europe/Rome")).date()
    if item.work_date >= today or item.validated or item.justified_absence:
        raise HTTPException(409, "Giornata non chiusa, validata o assenza gia giustificata")
    key = (collaborator.id, record.work_date)
    if key in load_notified_days(db, date.min) | blocked_days(db):
        raise HTTPException(409, "Giornata gia notificata o invio con esito da verificare")
    policy = ReminderPolicy(
        today=today, include_missing_punches=True, opted_out_user_ids=load_opted_out_user_ids(db)
    )
    contacts = load_reminder_contacts(db, {item.application_user_id})
    reason, phone = _contact_outcome(
        item.application_user_id, contacts.get(item.application_user_id), policy
    )
    if reason:
        if reason in {"operator_profile_missing", "phone_missing", "phone_invalid"}:
            raise HTTPException(
                409,
                {
                    "message": "Numero WhatsApp mancante o non valido. Aggiungi il numero del collaboratore.",
                    "code": reason,
                    "application_user_id": item.application_user_id,
                    "collaborator_name": collaborator.name,
                },
            )
        raise HTTPException(409, f"Destinatario non disponibile: {reason}")
    structural = reminder_day(item, include_missing_punches=True)
    reasons = anomaly_reasons(record.raw_payload_json)
    if structural:
        reasons.insert(0, structural.detail)
    if not reasons:
        raise HTTPException(409, "Nessuna anomalia comunicabile: verificare il dettaglio INAZ")
    day = ReminderDay(record.work_date, "manual_anomaly", "; ".join(dict.fromkeys(reasons)))
    return PunchReminder(
        collaborator.id, collaborator.name, item.application_user_id, phone, (day,)
    )


def anomaly_reasons(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return []
    anomalies = extract_detail_payload(payload).get("anomalies", [])
    reasons = []
    for anomaly in anomalies:
        for key in ("anomaliagiornata", "Anomalia giornata", "col_1"):
            value = anomaly.get(key)
            if value:
                reasons.append(str(value).strip())
                break
    return reasons


def manual_text(reminder: PunchReminder, reason: str) -> str:
    return (
        f"Ciao {reminder.collaborator_name}, per la giornata del "
        f"{reminder.days[0].work_date:%d/%m/%Y} risulta questa anomalia:\n"
        f"{reason.strip()}\n\n"
        "Accedi a INAZ, apri la giornata indicata e verifica le timbrature e i giustificativi. "
        "Inserisci la richiesta di correzione appropriata in base alle ore effettivamente "
        "lavorate o all'assenza. Se non riesci, contatta il tuo responsabile.\n"
        "Avviso GAIA. Rispondi STOP per non ricevere piu questi avvisi."
    )


def manual_preview(db: Session, record_id: UUID) -> dict[str, object]:
    reminder = manual_candidate(db, record_id)
    config = load_whatsapp_config(db)
    if config.provider not in {"waha", "dry_run"}:
        raise HTTPException(409, "Provider WhatsApp disattivato")
    result = {
        "record_id": str(record_id),
        "collaborator_name": reminder.collaborator_name,
        "application_user_id": reminder.application_user_id,
        "phone_e164": reminder.phone_e164,
        "work_date": reminder.days[0].work_date.isoformat(),
        "reason": reminder.days[0].detail,
        "text": manual_text(reminder, reminder.days[0].detail),
        "provider": config.provider,
    }
    result["fingerprint"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result
