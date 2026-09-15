from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from apscheduler.triggers.cron import CronTrigger
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.presenze.whatsapp_admin_schemas import WhatsAppConfigUpdate
from app.modules.presenze.whatsapp_models import PresenzeWhatsAppConfig
from app.services.elaborazioni_credentials import get_credential_fernet


@dataclass(frozen=True)
class WhatsAppRuntimeConfig:
    provider: str
    waha_url: str
    waha_session: str
    waha_api_key: str
    waha_hmac_key: str
    reminder_cron: str
    lookback_days: int
    include_missing_punches: bool
    max_per_run: int
    min_delay_seconds: int
    max_delay_seconds: int
    send_start_hour: int
    send_end_hour: int
    updated_at: datetime | None = None
    updated_by_user_id: int | None = None


def environment_whatsapp_config() -> WhatsAppRuntimeConfig:
    return WhatsAppRuntimeConfig(
        provider=settings.presenze_whatsapp_provider.strip().lower(),
        waha_url=settings.presenze_whatsapp_waha_url.strip(),
        waha_session=settings.presenze_whatsapp_waha_session.strip() or "default",
        waha_api_key=settings.presenze_whatsapp_waha_api_key,
        waha_hmac_key=settings.presenze_whatsapp_waha_hmac_key,
        reminder_cron=settings.presenze_whatsapp_reminder_cron,
        lookback_days=settings.presenze_whatsapp_lookback_days,
        include_missing_punches=settings.presenze_whatsapp_include_missing_punches,
        max_per_run=settings.presenze_whatsapp_max_per_run,
        min_delay_seconds=settings.presenze_whatsapp_min_delay_seconds,
        max_delay_seconds=settings.presenze_whatsapp_max_delay_seconds,
        send_start_hour=settings.presenze_whatsapp_send_start_hour,
        send_end_hour=settings.presenze_whatsapp_send_end_hour,
    )


def _decrypt(value: str | None) -> str:
    if not value:
        return ""
    return get_credential_fernet().decrypt(value.encode()).decode()


def _encrypt(value: str) -> str:
    return get_credential_fernet().encrypt(value.encode()).decode()


def load_whatsapp_config(db: Session) -> WhatsAppRuntimeConfig:
    row = db.get(PresenzeWhatsAppConfig, 1)
    if row is None:
        return environment_whatsapp_config()
    return WhatsAppRuntimeConfig(
        provider=row.provider,
        waha_url=row.waha_url,
        waha_session=row.waha_session,
        waha_api_key=_decrypt(row.waha_api_key_encrypted),
        waha_hmac_key=_decrypt(row.waha_hmac_key_encrypted),
        reminder_cron=row.reminder_cron,
        lookback_days=row.lookback_days,
        include_missing_punches=row.include_missing_punches,
        max_per_run=row.max_per_run,
        min_delay_seconds=row.min_delay_seconds,
        max_delay_seconds=row.max_delay_seconds,
        send_start_hour=row.send_start_hour,
        send_end_hour=row.send_end_hour,
        updated_at=row.updated_at,
        updated_by_user_id=row.updated_by_user_id,
    )


def serialize_whatsapp_config(config: WhatsAppRuntimeConfig) -> dict[str, object]:
    return {
        "provider": config.provider,
        "waha_url": config.waha_url,
        "waha_session": config.waha_session,
        "api_key_configured": bool(config.waha_api_key),
        "hmac_key_configured": bool(config.waha_hmac_key),
        "reminder_cron": config.reminder_cron,
        "lookback_days": config.lookback_days,
        "include_missing_punches": config.include_missing_punches,
        "max_per_run": config.max_per_run,
        "min_delay_seconds": config.min_delay_seconds,
        "max_delay_seconds": config.max_delay_seconds,
        "send_start_hour": config.send_start_hour,
        "send_end_hour": config.send_end_hour,
        "updated_at": config.updated_at,
        "updated_by_user_id": config.updated_by_user_id,
    }


def _validated_secrets(
    current: WhatsAppRuntimeConfig, payload: WhatsAppConfigUpdate
) -> tuple[str, str]:
    api_key = "" if payload.clear_api_key else (payload.waha_api_key or current.waha_api_key)
    hmac_key = "" if payload.clear_hmac_key else (payload.waha_hmac_key or current.waha_hmac_key)
    if payload.provider == "waha" and (not api_key or not hmac_key):
        raise HTTPException(
            status_code=409,
            detail="Per attivare WAHA sono obbligatorie API key e chiave webhook HMAC",
        )
    return api_key, hmac_key


def _validate_cron(expression: str) -> None:
    try:
        CronTrigger.from_crontab(expression, timezone="Europe/Rome")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Espressione cron non valida") from exc


def update_whatsapp_config(
    db: Session, payload: WhatsAppConfigUpdate, *, user_id: int
) -> WhatsAppRuntimeConfig:
    _validate_cron(payload.reminder_cron)
    current = load_whatsapp_config(db)
    api_key, hmac_key = _validated_secrets(current, payload)
    row = db.get(PresenzeWhatsAppConfig, 1) or PresenzeWhatsAppConfig(id=1)
    row.provider = payload.provider
    row.waha_url = payload.waha_url.strip().rstrip("/")
    row.waha_session = payload.waha_session.strip()
    row.waha_api_key_encrypted = _encrypt(api_key) if api_key else None
    row.waha_hmac_key_encrypted = _encrypt(hmac_key) if hmac_key else None
    row.reminder_cron = payload.reminder_cron.strip()
    row.lookback_days = payload.lookback_days
    row.include_missing_punches = payload.include_missing_punches
    row.max_per_run = payload.max_per_run
    row.min_delay_seconds = payload.min_delay_seconds
    row.max_delay_seconds = payload.max_delay_seconds
    row.send_start_hour = payload.send_start_hour
    row.send_end_hour = payload.send_end_hour
    row.updated_at = datetime.now(UTC)
    row.updated_by_user_id = user_id
    db.add(row)
    db.commit()
    return load_whatsapp_config(db)
