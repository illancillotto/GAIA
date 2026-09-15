from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.organizational import OperatorProfile
from app.modules.presenze.models import PresenzeCollaborator
from app.modules.presenze.services.punch_reminder_job import (
    load_notified_days,
    load_opted_out_user_ids,
    load_reminder_contacts,
    load_reminder_inputs,
)
from app.modules.presenze.services.punch_reminder_pending import blocked_days
from app.modules.presenze.services.punch_reminders import (
    ReminderPolicy,
    build_punch_reminder_text,
    select_punch_reminders,
)
from app.modules.presenze.whatsapp_models import (
    PresenzeWhatsAppMessage,
    PresenzeWhatsAppOptOut,
)


def dashboard_summary(db: Session, now: datetime | None = None) -> dict[str, object]:
    current = now or datetime.now(UTC)
    statuses = dict(
        db.execute(
            select(PresenzeWhatsAppMessage.status, func.count(PresenzeWhatsAppMessage.id)).group_by(
                PresenzeWhatsAppMessage.status
            )
        ).all()
    )
    provider = settings.presenze_whatsapp_provider.strip()
    session_status, session_detail = _session_status(provider)
    trigger = CronTrigger.from_crontab(
        settings.presenze_whatsapp_reminder_cron, timezone="Europe/Rome"
    )
    return {
        "provider_enabled": bool(provider),
        "provider": provider or None,
        "session_status": session_status,
        "session_detail": session_detail,
        "cron": settings.presenze_whatsapp_reminder_cron,
        "next_run_at": trigger.get_next_fire_time(None, current) if provider else None,
        "send_window": (
            f"{settings.presenze_whatsapp_send_start_hour:02d}:00-"
            f"{settings.presenze_whatsapp_send_end_hour:02d}:00"
        ),
        "max_per_run": settings.presenze_whatsapp_max_per_run,
        "sent_total": sum(statuses.get(key, 0) for key in ("SENT", "DELIVERED", "READ")),
        "delivered_total": statuses.get("DELIVERED", 0) + statuses.get("READ", 0),
        "read_total": statuses.get("READ", 0),
        "failed_total": statuses.get("FAILED", 0) + statuses.get("NOT_ON_WHATSAPP", 0),
        "uncertain_total": statuses.get("SENDING", 0) + statuses.get("UNKNOWN", 0),
        "opted_out_total": db.scalar(select(func.count(PresenzeWhatsAppOptOut.application_user_id)))
        or 0,
    }


def list_messages(
    db: Session, *, status: str | None, query: str | None, page: int, page_size: int
) -> dict[str, object]:
    stmt = (
        select(PresenzeWhatsAppMessage, PresenzeCollaborator, ApplicationUser)
        .join(
            PresenzeCollaborator, PresenzeCollaborator.id == PresenzeWhatsAppMessage.collaborator_id
        )
        .outerjoin(
            ApplicationUser, ApplicationUser.id == PresenzeWhatsAppMessage.application_user_id
        )
    )
    if status:
        stmt = stmt.where(PresenzeWhatsAppMessage.status == status)
    if query and query.strip():
        term = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                PresenzeCollaborator.name.ilike(term),
                ApplicationUser.username.ilike(term),
                ApplicationUser.full_name.ilike(term),
                PresenzeWhatsAppMessage.phone_e164.ilike(term),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(PresenzeWhatsAppMessage.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            _message_payload(message, collaborator, user) for message, collaborator, user in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def build_preview(db: Session, now: datetime | None = None) -> dict[str, object]:
    current = now or datetime.now(UTC)
    today = current.astimezone(ZoneInfo("Europe/Rome")).date()
    first_day = today - timedelta(days=max(1, settings.presenze_whatsapp_lookback_days))
    items = load_reminder_inputs(db, first_day, today)
    policy = ReminderPolicy(
        today=today,
        include_missing_punches=settings.presenze_whatsapp_include_missing_punches,
        notified=load_notified_days(db, first_day) | blocked_days(db),
        opted_out_user_ids=load_opted_out_user_ids(db),
    )
    selection = select_punch_reminders(
        items, load_reminder_contacts(db, {item.application_user_id for item in items}), policy
    )
    return {
        "ready": [
            {
                "collaborator_id": item.collaborator_id,
                "collaborator_name": item.collaborator_name,
                "application_user_id": item.application_user_id,
                "phone_e164": item.phone_e164,
                "days": list(item.days),
                "message_text": build_punch_reminder_text(item),
                "ready": True,
                "reason": None,
            }
            for item in selection.reminders
        ],
        "skipped": [
            {
                "collaborator_id": item.collaborator_id,
                "collaborator_name": item.collaborator_name,
                "application_user_id": item.application_user_id,
                "phone_e164": None,
                "days": list(item.days),
                "message_text": None,
                "ready": False,
                "reason": item.reason,
            }
            for item in selection.skipped
        ],
        "generated_at": current,
    }


def list_opt_outs(db: Session) -> list[dict[str, object]]:
    rows = db.execute(
        select(PresenzeWhatsAppOptOut, ApplicationUser, PresenzeCollaborator)
        .join(ApplicationUser, ApplicationUser.id == PresenzeWhatsAppOptOut.application_user_id)
        .outerjoin(
            PresenzeCollaborator,
            PresenzeCollaborator.application_user_id == PresenzeWhatsAppOptOut.application_user_id,
        )
        .order_by(PresenzeWhatsAppOptOut.created_at.desc())
    ).all()
    return [
        {
            "application_user_id": item.application_user_id,
            "user_label": _user_label(user),
            "username": user.username,
            "collaborator_name": collaborator.name if collaborator else None,
            "phone_e164": item.phone_e164,
            "source": item.source,
            "created_at": item.created_at,
        }
        for item, user, collaborator in rows
    ]


def update_phone(db: Session, user_id: int, phone: str) -> dict[str, object] | None:
    user = db.get(ApplicationUser, user_id)
    if user is None:
        return None
    profile = db.scalar(select(OperatorProfile).where(OperatorProfile.user_id == user_id))
    if profile is None:
        profile = OperatorProfile(user_id=user_id)
        db.add(profile)
    profile.phone = phone.strip() or None
    db.commit()
    return {"application_user_id": user_id, "phone": profile.phone}


def remove_opt_out(db: Session, user_id: int) -> bool:
    item = db.get(PresenzeWhatsAppOptOut, user_id)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


def _message_payload(
    message: PresenzeWhatsAppMessage,
    collaborator: PresenzeCollaborator,
    user: ApplicationUser | None,
) -> dict[str, object]:
    return {
        "id": message.id,
        "collaborator_id": collaborator.id,
        "collaborator_name": collaborator.name,
        "application_user_id": message.application_user_id,
        "user_label": _user_label(user) if user else collaborator.name,
        "username": user.username if user else None,
        "phone_e164": message.phone_e164,
        "text_body": message.text_body,
        "days": message.days_json,
        "status": message.status,
        "provider": message.provider,
        "provider_message_id": message.provider_message_id,
        "error_code": message.error_code,
        "error_message": message.error_message,
        "created_at": message.created_at,
        "updated_at": message.updated_at,
        "delivered_at": message.delivered_at,
        "read_at": message.read_at,
    }


def _user_label(user: ApplicationUser) -> str:
    return (user.full_name or "").strip() or user.username


def _session_status(provider: str) -> tuple[str, str | None]:
    normalized = provider.lower()
    if not normalized:
        return "disabled", None
    if normalized == "dry_run":
        return "dry_run", "Nessun messaggio viene inviato"
    if normalized != "waha":
        return "unsupported", f"Provider {provider} non supportato"
    if not settings.presenze_whatsapp_waha_url or not settings.presenze_whatsapp_waha_api_key:
        return "misconfigured", "URL o API key WAHA assente"
    return _configured_waha_status()


def _configured_waha_status() -> tuple[str, str | None]:
    try:
        response = httpx.get(
            f"{settings.presenze_whatsapp_waha_url.rstrip('/')}/api/sessions/"
            f"{settings.presenze_whatsapp_waha_session or 'default'}",
            headers={
                "accept": "application/json",
                "x-api-key": settings.presenze_whatsapp_waha_api_key,
            },
            timeout=3.0,
        )
    except httpx.HTTPError as exc:
        return "unavailable", str(exc)
    if not response.is_success:
        return "unavailable", f"WAHA HTTP {response.status_code}"
    return _parse_waha_status(response)


def _parse_waha_status(response: httpx.Response) -> tuple[str, str | None]:
    try:
        body = response.json()
    except ValueError:
        return "invalid_response", "Risposta WAHA non valida"
    status = body.get("status") if isinstance(body, dict) else None
    if not isinstance(status, str) or not status.strip():
        return "invalid_response", "Stato sessione WAHA assente"
    return status.strip().lower(), None
