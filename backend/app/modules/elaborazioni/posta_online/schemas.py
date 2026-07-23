from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PostaOnlineCredentialCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1)
    active: bool = True
    allowed_hours_start: int = Field(default=0, ge=0, le=23)
    allowed_hours_end: int = Field(default=23, ge=0, le=23)
    min_delay_ms: int = Field(default=3500, ge=1000, le=60000)
    max_delay_ms: int = Field(default=9000, ge=1000, le=120000)

    @model_validator(mode="after")
    def validate_delay_range(self) -> "PostaOnlineCredentialCreate":
        if self.max_delay_ms < self.min_delay_ms:
            raise ValueError("max_delay_ms non puo essere minore di min_delay_ms")
        return self


class PostaOnlineCredentialUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    username: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=1)
    active: bool | None = None
    allowed_hours_start: int | None = Field(default=None, ge=0, le=23)
    allowed_hours_end: int | None = Field(default=None, ge=0, le=23)
    min_delay_ms: int | None = Field(default=None, ge=1000, le=60000)
    max_delay_ms: int | None = Field(default=None, ge=1000, le=120000)

    @model_validator(mode="after")
    def validate_delay_range(self) -> "PostaOnlineCredentialUpdate":
        if self.min_delay_ms is not None and self.max_delay_ms is not None and self.max_delay_ms < self.min_delay_ms:
            raise ValueError("max_delay_ms non puo essere minore di min_delay_ms")
        return self


class PostaOnlineCredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    username: str
    active: bool
    allowed_hours_start: int
    allowed_hours_end: int
    min_delay_ms: int
    max_delay_ms: int
    last_used_at: datetime | None = None
    last_error: str | None = None
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime


class PostaOnlineCredentialTestJobCreateRequest(BaseModel):
    min_delay_ms: int | None = Field(default=None, ge=1000, le=60000)
    max_delay_ms: int | None = Field(default=None, ge=1000, le=120000)

    @model_validator(mode="after")
    def validate_delay_range(self) -> "PostaOnlineCredentialTestJobCreateRequest":
        if self.min_delay_ms is not None and self.max_delay_ms is not None and self.max_delay_ms < self.min_delay_ms:
            raise ValueError("max_delay_ms non puo essere minore di min_delay_ms")
        return self


class PostaOnlineRegisteredMailSyncJobCreateRequest(BaseModel):
    credential_id: int | None = None
    annualita: list[int] = Field(default_factory=lambda: [2022, 2023])
    include_contacts: bool = True
    include_details: bool = True
    max_pages: int | None = Field(default=None, ge=1, le=200)
    max_details: int | None = Field(default=None, ge=1, le=10000)
    min_delay_ms: int | None = Field(default=None, ge=1000, le=60000)
    max_delay_ms: int | None = Field(default=None, ge=1000, le=120000)
    continue_on_error: bool = True

    @model_validator(mode="after")
    def validate_payload(self) -> "PostaOnlineRegisteredMailSyncJobCreateRequest":
        years = sorted({int(year) for year in self.annualita if year in {2022, 2023}})
        if not years:
            raise ValueError("annualita deve includere almeno 2022 o 2023")
        self.annualita = years
        if self.min_delay_ms is not None and self.max_delay_ms is not None and self.max_delay_ms < self.min_delay_ms:
            raise ValueError("max_delay_ms non puo essere minore di min_delay_ms")
        return self


class PostaOnlineRegisteredMailSyncJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    credential_id: int | None = None
    requested_by_user_id: int | None = None
    status: str
    mode: str
    payload_json: dict[str, Any] | list[Any] | None = None
    result_json: dict[str, Any] | list[Any] | None = None
    error_detail: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
