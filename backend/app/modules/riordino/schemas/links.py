"""Parcel and party link schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.riordino.schemas.base import TimestampedResponse


class ParcelLinkCreate(BaseModel):
    foglio: str
    particella: str
    subalterno: str | None = None
    quality_class: str | None = None
    title_holder_name: str | None = None
    title_holder_subject_id: uuid.UUID | None = None
    source: str | None = None
    notes: str | None = None


class ParcelLinkResponse(TimestampedResponse):
    practice_id: uuid.UUID
    foglio: str
    particella: str
    subalterno: str | None = None
    quality_class: str | None = None
    title_holder_name: str | None = None
    title_holder_subject_id: uuid.UUID | None = None
    source: str | None = None
    notes: str | None = None
    updated_at: datetime


class PartyLinkCreate(BaseModel):
    subject_id: uuid.UUID
    role: str
    notes: str | None = None


class PartyLinkResponse(TimestampedResponse):
    practice_id: uuid.UUID
    subject_id: uuid.UUID
    role: str
    notes: str | None = None
