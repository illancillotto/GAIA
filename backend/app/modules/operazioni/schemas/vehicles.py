"""Vehicle domain Pydantic schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# --- Vehicle ---


class VehicleCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    plate_number: str | None = Field(default=None, max_length=20)
    asset_tag: str | None = Field(default=None, max_length=100)
    name: str = Field(..., min_length=1, max_length=150)
    vehicle_type: str = Field(..., min_length=1, max_length=100)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    year_of_manufacture: int | None = None
    fuel_type: str | None = Field(default=None, max_length=50)
    ownership_type: str | None = Field(default=None, max_length=50)
    gps_provider_code: str | None = Field(default=None, max_length=100)
    has_gps_device: bool = False
    notes: str | None = None


class VehicleUpdate(BaseModel):
    plate_number: str | None = None
    asset_tag: str | None = None
    name: str | None = None
    vehicle_type: str | None = None
    brand: str | None = None
    model: str | None = None
    year_of_manufacture: int | None = None
    fuel_type: str | None = None
    ownership_type: str | None = None
    gps_provider_code: str | None = None
    has_gps_device: bool | None = None
    notes: str | None = None
    current_status: str | None = None


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    plate_number: str | None
    asset_tag: str | None
    name: str
    vehicle_type: str
    brand: str | None
    model: str | None
    fuel_type: str | None
    current_status: str
    has_gps_device: bool
    gps_provider_code: str | None
    is_active: bool
    current_assignment: dict[str, Any] | None = None
    last_odometer_km: float | None = None
    created_at: datetime
    updated_at: datetime


class VehicleListResponse(BaseModel):
    items: list[VehicleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# --- Vehicle Assignment ---


class VehicleAssignmentCreate(BaseModel):
    assignment_target_type: str = Field(..., pattern="^(operator|team)$")
    operator_user_id: int | None = None
    team_id: UUID | None = None
    start_at: datetime
    reason: str | None = None
    notes: str | None = None


class VehicleAssignmentClose(BaseModel):
    end_at: datetime
    notes: str | None = None


class VehicleAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    assignment_target_type: str
    operator_user_id: int | None
    team_id: UUID | None
    assigned_by_user_id: int
    start_at: datetime
    end_at: datetime | None
    reason: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


# --- Vehicle Usage Session ---


class VehicleUsageSessionStart(BaseModel):
    vehicle_id: UUID
    actual_driver_user_id: int | None = None
    team_id: UUID | None = None
    related_assignment_id: UUID | None = None
    started_at: datetime
    start_odometer_km: Decimal
    start_latitude: Decimal | None = None
    start_longitude: Decimal | None = None
    gps_source: str | None = None
    notes: str | None = None


class VehicleUsageSessionStop(BaseModel):
    ended_at: datetime
    end_odometer_km: Decimal
    end_latitude: Decimal | None = None
    end_longitude: Decimal | None = None
    gps_source: str | None = None
    route_distance_km: Decimal | None = None
    engine_hours: Decimal | None = None
    notes: str | None = None


class VehicleUsageSessionValidate(BaseModel):
    validated_at: datetime
    note: str | None = None


class VehicleUsageSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    started_by_user_id: int
    actual_driver_user_id: int | None
    team_id: UUID | None
    started_at: datetime
    ended_at: datetime | None
    start_odometer_km: Decimal
    end_odometer_km: Decimal | None
    start_latitude: Decimal | None
    start_longitude: Decimal | None
    end_latitude: Decimal | None
    end_longitude: Decimal | None
    gps_source: str | None
    route_distance_km: Decimal | None
    engine_hours: Decimal | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


# --- Vehicle Odometer ---


class VehicleOdometerReadingCreate(BaseModel):
    reading_at: datetime
    odometer_km: Decimal
    source_type: str
    usage_session_id: UUID | None = None
    notes: str | None = None


class VehicleOdometerReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    reading_at: datetime
    odometer_km: Decimal
    source_type: str
    usage_session_id: UUID | None
    recorded_by_user_id: int | None
    notes: str | None
    created_at: datetime


# --- Vehicle Fuel Log ---


class VehicleFuelLogCreate(BaseModel):
    usage_session_id: UUID | None = None
    fueled_at: datetime
    liters: Decimal
    total_cost: Decimal | None = None
    odometer_km: Decimal | None = None
    station_name: str | None = None
    notes: str | None = None


class VehicleFuelLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    usage_session_id: UUID | None
    recorded_by_user_id: int
    fueled_at: datetime
    liters: Decimal
    total_cost: Decimal | None
    odometer_km: Decimal | None
    station_name: str | None
    notes: str | None
    created_at: datetime


# --- Vehicle Maintenance ---


class VehicleMaintenanceCreate(BaseModel):
    maintenance_type_id: UUID | None = None
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    status: str = "planned"
    opened_at: datetime
    scheduled_for: datetime | None = None
    odometer_km: Decimal | None = None
    supplier_name: str | None = None
    cost_amount: Decimal | None = None
    notes: str | None = None


class VehicleMaintenanceUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    scheduled_for: datetime | None = None
    odometer_km: Decimal | None = None
    supplier_name: str | None = None
    cost_amount: Decimal | None = None
    notes: str | None = None


class VehicleMaintenanceComplete(BaseModel):
    completed_at: datetime
    cost_amount: Decimal | None = None
    notes: str | None = None


class VehicleMaintenanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    maintenance_type_id: UUID | None
    title: str
    description: str | None
    status: str
    opened_at: datetime
    scheduled_for: datetime | None
    completed_at: datetime | None
    odometer_km: Decimal | None
    supplier_name: str | None
    cost_amount: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


# --- Vehicle Maintenance Type ---


class VehicleMaintenanceTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    is_active: bool


# --- Vehicle Document ---


class VehicleDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    document_type: str
    title: str
    document_number: str | None
    issued_at: date | None
    expires_at: date | None
    attachment_id: UUID
    notes: str | None
    created_at: datetime
    updated_at: datetime


# --- Organizational ---


class TeamCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)
    description: str | None = None
    supervisor_user_id: int | None = None


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    supervisor_user_id: int | None
    is_active: bool
    created_at: datetime


class TeamMembershipCreate(BaseModel):
    team_id: UUID
    user_id: int
    role_in_team: str | None = None
    valid_from: datetime
    valid_to: datetime | None = None
    is_primary: bool = False


class TeamMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    user_id: int
    role_in_team: str | None
    valid_from: datetime
    valid_to: datetime | None
    is_primary: bool
    created_at: datetime


class OperatorProfileCreate(BaseModel):
    user_id: int
    employee_code: str | None = None
    phone: str | None = None
    can_drive_vehicles: bool = False
    notes: str | None = None


class OperatorProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    employee_code: str | None
    phone: str | None
    can_drive_vehicles: bool
    notes: str | None
    is_active: bool
    created_at: datetime


# --- Common ---


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ApiResponse(BaseModel):
    data: Any = None
    meta: dict[str, Any] = {}
    error: ErrorResponse | None = None
