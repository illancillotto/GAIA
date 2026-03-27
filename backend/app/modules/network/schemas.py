from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NetworkDashboardSummary(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    open_alerts: int
    scans_last_24h: int
    floor_plans: int
    latest_scan_at: datetime | None


class NetworkDeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_scan_id: int | None
    ip_address: str
    mac_address: str | None
    hostname: str | None
    hostname_source: str | None = None
    display_name: str | None = None
    asset_label: str | None = None
    vendor: str | None = None
    model_name: str | None = None
    device_type: str | None = None
    operating_system: str | None = None
    dns_name: str | None = None
    location_hint: str | None = None
    notes: str | None = None
    metadata_sources: dict[str, Any] | None = None
    status: str
    is_monitored: bool
    open_ports: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime


class NetworkDeviceUpdateRequest(BaseModel):
    display_name: str | None = None
    asset_label: str | None = None
    model_name: str | None = None
    device_type: str | None = None
    operating_system: str | None = None
    location_hint: str | None = None
    notes: str | None = None
    is_monitored: bool | None = None


class NetworkDeviceListResponse(BaseModel):
    items: list[NetworkDeviceResponse]
    total: int
    page: int
    page_size: int


class NetworkAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int | None
    scan_id: int | None
    alert_type: str
    severity: str
    status: str
    title: str
    message: str | None
    created_at: datetime
    acknowledged_at: datetime | None


class NetworkScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    network_range: str
    scan_type: str
    status: str
    hosts_scanned: int
    active_hosts: int
    discovered_devices: int
    initiated_by: str | None
    notes: str | None
    started_at: datetime
    completed_at: datetime


class NetworkScanTriggerResponse(BaseModel):
    scan: NetworkScanResponse
    devices_upserted: int
    alerts_created: int


class FloorPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    building: str | None
    floor_label: str
    svg_content: str | None
    image_url: str | None
    width: float | None
    height: float | None
    created_at: datetime
    updated_at: datetime


class DevicePositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    floor_plan_id: int
    x: float
    y: float
    label: str | None
    created_at: datetime
    updated_at: datetime


class FloorPlanDetailResponse(FloorPlanResponse):
    positions: list[DevicePositionResponse] = Field(default_factory=list)
