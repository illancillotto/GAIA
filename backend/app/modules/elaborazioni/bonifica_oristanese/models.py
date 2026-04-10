from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BonificaOristaneseCredentialCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    login_identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1)
    remember_me: bool = False
    active: bool = True


class BonificaOristaneseCredentialUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    login_identifier: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=1)
    remember_me: bool | None = None
    active: bool | None = None


class BonificaOristaneseCredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    login_identifier: str
    remember_me: bool
    active: bool
    last_used_at: datetime | None
    last_authenticated_url: str | None
    last_error: str | None
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime


class BonificaOristaneseCredentialTestResult(BaseModel):
    ok: bool
    authenticated_url: str | None = None
    cookies: str | None = None
    error: str | None = None
