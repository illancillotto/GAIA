from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NetworkDashboardSummary(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    open_alerts: int
    scans_last_24h: int
    floor_plans: int
    latest_scan_at: datetime | None


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


class NetworkDeviceHistoryEntry(BaseModel):
    scan_id: int
    observed_at: datetime
    status: str
    hostname: str | None = None
    ip_address: str
    open_ports: str | None = None


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
    is_known_device: bool
    metadata_sources: dict[str, Any] | None = None
    status: str
    is_monitored: bool
    open_ports: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime
    positions: list[DevicePositionResponse] = Field(default_factory=list)
    scan_history: list[NetworkDeviceHistoryEntry] = Field(default_factory=list)


class NetworkDeviceUpdateRequest(BaseModel):
    display_name: str | None = None
    asset_label: str | None = None
    model_name: str | None = None
    device_type: str | None = None
    operating_system: str | None = None
    location_hint: str | None = None
    notes: str | None = None
    is_known_device: bool | None = None
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


class NetworkAlertUpdateRequest(BaseModel):
    status: str = Field(pattern="^(open|resolved|ignored)$")


class ScanDeltaSummary(BaseModel):
    new_devices_count: int = 0
    missing_devices_count: int = 0
    changed_devices_count: int = 0


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
    delta: ScanDeltaSummary = Field(default_factory=ScanDeltaSummary)


class NetworkScanTriggerResponse(BaseModel):
    scan: NetworkScanResponse
    devices_upserted: int
    alerts_created: int


class NetworkScanDeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_id: int
    device_id: int | None
    ip_address: str
    mac_address: str | None
    hostname: str | None
    hostname_source: str | None
    display_name: str | None
    asset_label: str | None
    vendor: str | None
    model_name: str | None
    device_type: str | None
    operating_system: str | None
    dns_name: str | None
    location_hint: str | None
    metadata_sources: dict[str, Any] | None = None
    status: str
    open_ports: str | None
    observed_at: datetime


class NetworkScanDetailResponse(NetworkScanResponse):
    devices: list[NetworkScanDeviceResponse] = Field(default_factory=list)


class NetworkScanDiffEntry(BaseModel):
    key: str
    before: NetworkScanDeviceResponse | None = None
    after: NetworkScanDeviceResponse | None = None
    change_type: str


class NetworkScanDiffResponse(BaseModel):
    from_scan_id: int
    to_scan_id: int
    summary: ScanDeltaSummary
    changes: list[NetworkScanDiffEntry] = Field(default_factory=list)


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


class FloorPlanCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    floor_label: str = Field(min_length=1, max_length=64)
    building: str | None = Field(default=None, max_length=255)
    svg_content: str | None = None
    image_url: str | None = Field(default=None, max_length=1024)
    width: float | None = None
    height: float | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "FloorPlanCreateRequest":
        if not self.svg_content and not self.image_url:
            raise ValueError("Either svg_content or image_url must be provided")
        return self


class FloorPlanDetailResponse(FloorPlanResponse):
    positions: list[DevicePositionResponse] = Field(default_factory=list)


class FloorPlanDeviceResponse(BaseModel):
    position: DevicePositionResponse
    device: NetworkDeviceResponse


class DevicePositionUpdateRequest(BaseModel):
    floor_plan_id: int
    x: float
    y: float
    label: str | None = Field(default=None, max_length=255)
