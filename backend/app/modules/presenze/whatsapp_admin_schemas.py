from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WhatsAppReminderDayResponse(BaseModel):
    work_date: date
    problem: str
    detail: str


class WhatsAppMessageResponse(BaseModel):
    id: UUID
    collaborator_id: UUID
    collaborator_name: str
    application_user_id: int | None
    user_label: str
    username: str | None
    phone_e164: str
    text_body: str
    days: list[WhatsAppReminderDayResponse]
    status: str
    provider: str
    provider_message_id: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    delivered_at: datetime | None
    read_at: datetime | None


class WhatsAppMessageListResponse(BaseModel):
    items: list[WhatsAppMessageResponse]
    total: int
    page: int
    page_size: int


class WhatsAppMessageQuery(BaseModel):
    status: str | None = Field(default=None, max_length=32)
    q: str | None = Field(default=None, max_length=120)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)


class WhatsAppDashboardSummaryResponse(BaseModel):
    provider_enabled: bool
    provider: str | None
    session_status: str
    session_detail: str | None
    cron: str
    next_run_at: datetime | None
    send_window: str
    max_per_run: int
    sent_total: int
    delivered_total: int
    read_total: int
    failed_total: int
    uncertain_total: int
    opted_out_total: int


class WhatsAppPreviewItemResponse(BaseModel):
    collaborator_id: UUID
    collaborator_name: str
    application_user_id: int | None
    phone_e164: str | None
    days: list[WhatsAppReminderDayResponse]
    message_text: str | None
    ready: bool
    reason: str | None


class WhatsAppPreviewResponse(BaseModel):
    ready: list[WhatsAppPreviewItemResponse]
    skipped: list[WhatsAppPreviewItemResponse]
    generated_at: datetime


class WhatsAppOptOutResponse(BaseModel):
    application_user_id: int
    user_label: str
    username: str | None
    collaborator_name: str | None
    phone_e164: str | None
    source: str
    created_at: datetime


class WhatsAppPhoneUpdate(BaseModel):
    phone: str = Field(max_length=50)


class WhatsAppPhoneResponse(BaseModel):
    application_user_id: int
    phone: str | None


class WhatsAppReconcileRequest(BaseModel):
    sent: bool
    evidence: str = Field(min_length=1, max_length=2000)
    provider_message_id: str | None = Field(default=None, max_length=255)


class WhatsAppConfigResponse(BaseModel):
    provider: str
    waha_url: str
    waha_session: str
    api_key_configured: bool
    hmac_key_configured: bool
    reminder_cron: str
    lookback_days: int
    include_missing_punches: bool
    max_per_run: int
    min_delay_seconds: int
    max_delay_seconds: int
    send_start_hour: int
    send_end_hour: int
    updated_at: datetime | None
    updated_by_user_id: int | None


class WhatsAppConfigUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    provider: str = Field(pattern="^(|dry_run|waha)$")
    waha_url: str = Field(
        min_length=1,
        max_length=500,
        pattern=r"^https?://[^\s/]+(?:/[^\s]*)?$",
    )
    waha_session: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    waha_api_key: str | None = Field(default=None, max_length=500)
    waha_hmac_key: str | None = Field(default=None, max_length=500)
    clear_api_key: bool = False
    clear_hmac_key: bool = False
    reminder_cron: str = Field(min_length=9, max_length=100)
    lookback_days: int = Field(ge=1, le=31)
    include_missing_punches: bool
    max_per_run: int = Field(ge=1, le=100)
    min_delay_seconds: int = Field(ge=0, le=3600)
    max_delay_seconds: int = Field(ge=0, le=3600)
    send_start_hour: int = Field(ge=0, le=23)
    send_end_hour: int = Field(ge=1, le=24)

    @model_validator(mode="after")
    def validate_ranges(self) -> WhatsAppConfigUpdate:
        if self.max_delay_seconds < self.min_delay_seconds:
            raise ValueError("La pausa massima deve essere maggiore o uguale alla minima")
        if self.send_end_hour <= self.send_start_hour:
            raise ValueError("La fine della fascia deve essere successiva all'inizio")
        return self


class WhatsAppSessionResponse(BaseModel):
    name: str
    status: str
    phone: str | None
    display_name: str | None


class WhatsAppQrResponse(BaseModel):
    image_data_url: str
