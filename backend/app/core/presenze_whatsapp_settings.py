from pydantic import Field

from app.core.capacitas_autosync_settings import CapacitasAutoSyncSettings


class PresenzeWhatsAppSettings(CapacitasAutoSyncSettings):
    """Promemoria WhatsApp timbrature via gateway WAHA; disattivi con provider vuoto."""

    presenze_whatsapp_provider: str = Field(
        default="",
        alias="PRESENZE_WHATSAPP_PROVIDER",
    )
    presenze_whatsapp_waha_url: str = Field(
        default="http://waha:3000",
        alias="PRESENZE_WHATSAPP_WAHA_URL",
    )
    presenze_whatsapp_waha_api_key: str = Field(
        default="",
        alias="PRESENZE_WHATSAPP_WAHA_API_KEY",
    )
    presenze_whatsapp_waha_session: str = Field(
        default="default",
        alias="PRESENZE_WHATSAPP_WAHA_SESSION",
    )
    presenze_whatsapp_waha_hmac_key: str = Field(
        default="",
        alias="PRESENZE_WHATSAPP_WAHA_HMAC_KEY",
    )
    presenze_whatsapp_reminder_cron: str = Field(
        default="30 9 * * 1-5",
        alias="PRESENZE_WHATSAPP_REMINDER_CRON",
    )
    presenze_whatsapp_lookback_days: int = Field(
        default=3,
        alias="PRESENZE_WHATSAPP_LOOKBACK_DAYS",
    )
    presenze_whatsapp_include_missing_punches: bool = Field(
        default=False,
        alias="PRESENZE_WHATSAPP_INCLUDE_MISSING_PUNCHES",
    )
    presenze_whatsapp_max_per_run: int = Field(
        default=40,
        alias="PRESENZE_WHATSAPP_MAX_PER_RUN",
    )
    presenze_whatsapp_min_delay_seconds: int = Field(
        default=25,
        alias="PRESENZE_WHATSAPP_MIN_DELAY_SECONDS",
    )
    presenze_whatsapp_max_delay_seconds: int = Field(
        default=75,
        alias="PRESENZE_WHATSAPP_MAX_DELAY_SECONDS",
    )
    presenze_whatsapp_send_start_hour: int = Field(
        default=8,
        alias="PRESENZE_WHATSAPP_SEND_START_HOUR",
    )
    presenze_whatsapp_send_end_hour: int = Field(
        default=19,
        alias="PRESENZE_WHATSAPP_SEND_END_HOUR",
    )
