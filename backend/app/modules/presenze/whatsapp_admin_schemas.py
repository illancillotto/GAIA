from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


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
