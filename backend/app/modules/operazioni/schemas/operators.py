from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WCOperatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    wc_id: int
    username: str | None
    email: str | None
    first_name: str | None
    last_name: str | None
    tax: str | None
    role: str | None
    enabled: bool
    gaia_user_id: int | None
    wc_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WCOperatorListResponse(BaseModel):
    items: list[WCOperatorResponse]
    total: int


class GaiaUserMin(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool


class UnlinkedOperatorItem(BaseModel):
    id: UUID
    wc_id: int
    username: str | None
    email: str | None
    first_name: str | None
    last_name: str | None
    role: str | None
    enabled: bool
    suggested_gaia_user: GaiaUserMin | None


class UnlinkedOperatorsResponse(BaseModel):
    items: list[UnlinkedOperatorItem]
    total: int


class LinkGaiaRequest(BaseModel):
    gaia_user_id: int


class AutoLinkResult(BaseModel):
    linked: int
    already_linked: int
    skipped: int
