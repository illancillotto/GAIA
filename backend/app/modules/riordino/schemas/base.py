"""Shared Pydantic models for Riordino responses."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class RiordinoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedResponse(RiordinoSchema):
    id: uuid.UUID
    created_at: datetime


class PaginatedResponse(RiordinoSchema):
    total: int
    page: int
    per_page: int
    total_pages: int
