from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

AssetCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Z0-9][A-Z0-9_-]{0,63}$"),
]
AssetType = Annotated[
    str, StringConstraints(strip_whitespace=True, to_lower=True, pattern=r"^[a-z][a-z0-9_-]{0,63}$")
]
AssetName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
AssetStatus = Literal["available", "maintenance", "lost", "damaged", "retired"]


class AssetFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("asset_code", "asset_type", mode="before", check_fields=False)
    @classmethod
    def normalize_identifiers(cls, value: object, info: ValidationInfo) -> object:
        if not isinstance(value, str):
            return value
        return value.strip().upper() if info.field_name == "asset_code" else value.strip().lower()

    description: str | None = Field(None, max_length=10000)
    brand: str | None = Field(None, max_length=100)
    model: str | None = Field(None, max_length=100)
    serial_number: str | None = Field(None, max_length=200)
    imei: str | None = Field(None, max_length=32)
    phone_number: str | None = Field(None, max_length=64)
    mac_address: str | None = Field(None, max_length=64)
    assigned_org_unit_id: UUID | None = None
    network_device_id: int | None = Field(None, gt=0)
    vehicle_id: UUID | None = None
    notes: str | None = Field(None, max_length=10000)


class AssetCreate(AssetFields):
    asset_code: AssetCode
    asset_type: AssetType
    name: AssetName
    status: AssetStatus = "available"


class AssetUpdate(AssetFields):
    asset_type: AssetType | None = None
    name: AssetName | None = None
    status: AssetStatus | None = None
    is_active: bool | None = None

    @field_validator("asset_type", "name", "status", "is_active")
    @classmethod
    def required_if_provided(cls, value):
        if value is None:
            raise ValueError("Il campo non puo essere null")
        return value


class CustodyNotes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str | None = Field(None, max_length=10000)


class CustodyTake(CustodyNotes):
    holder_user_id: int | None = Field(None, gt=0)


class CustodyTransfer(CustodyNotes):
    holder_user_id: int = Field(gt=0)


class CustodyResponse(BaseModel):
    id: UUID
    holder_user_id: int
    holder_name: str
    handover_from_name: str | None
    taken_at: datetime
    returned_at: datetime | None
    handover_from_user_id: int | None
    recorded_by_user_id: int
    returned_by_user_id: int | None
    notes: str | None
    return_notes: str | None
    created_at: datetime


class AssetResponse(AssetFields):
    id: UUID
    asset_code: str
    asset_type: str
    name: str
    status: str
    effective_status: str
    is_active: bool
    assigned_org_unit_name: str | None
    plate_number: str | None
    vehicle_status: str | None
    current_custody: CustodyResponse | None
    created_at: datetime
    updated_at: datetime


class AssetListResponse(BaseModel):
    items: list[AssetResponse]
    total: int


class CustodyListResponse(BaseModel):
    items: list[CustodyResponse]
    total: int


class AssetFilters(BaseModel):
    search: str | None = Field(None, max_length=200)
    asset_type: str | None = Field(None, max_length=64)
    status: str | None = Field(None, max_length=32)
    org_unit_id: UUID | None = None
    holder_user_id: int | None = Field(None, gt=0)
    active: bool | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=100)
