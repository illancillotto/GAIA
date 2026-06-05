from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NetworkDashboardSummary(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    open_alerts: int
    firewalls_online: int = 0
    scans_last_24h: int
    floor_plans: int
    latest_scan_at: datetime | None


class NetworkStatisticsCountItem(BaseModel):
    key: str
    label: str
    count: int


class NetworkStatisticsTrafficItem(BaseModel):
    label: str
    ip_address: str | None = None
    device_id: int | None = None
    events_count: int
    bytes_in: int = 0
    bytes_out: int = 0
    bytes_total: int = 0
    tracked_subject_id: int | None = None


class NetworkStatisticsTimelinePoint(BaseModel):
    bucket: str
    events_count: int
    bytes_in: int = 0
    bytes_out: int = 0


class NetworkStatisticsSummary(BaseModel):
    window_hours: int = 24
    generated_at: datetime
    total_devices: int
    active_devices: int
    retired_devices: int
    online_devices: int
    offline_devices: int
    known_devices: int
    unknown_devices: int
    monitored_devices: int
    assigned_devices: int
    unassigned_devices: int
    placeholder_profiles: int
    devices_with_traffic: int
    firewall_count: int
    open_alerts: int
    total_events: int = 0
    allowed_events: int = 0
    blocked_events: int = 0
    bytes_in: int = 0
    bytes_out: int = 0
    unique_external_peers: int = 0
    unique_domains: int = 0
    top_device_types: list[NetworkStatisticsCountItem] = Field(default_factory=list)
    top_vendors: list[NetworkStatisticsCountItem] = Field(default_factory=list)
    top_offices: list[NetworkStatisticsCountItem] = Field(default_factory=list)
    top_assignees: list[NetworkStatisticsCountItem] = Field(default_factory=list)
    severity_breakdown: list[NetworkStatisticsCountItem] = Field(default_factory=list)
    protocol_breakdown: list[NetworkStatisticsCountItem] = Field(default_factory=list)
    top_event_types: list[NetworkStatisticsCountItem] = Field(default_factory=list)
    top_firewall_rules: list[NetworkStatisticsCountItem] = Field(default_factory=list)
    top_domains: list[NetworkStatisticsTrafficItem] = Field(default_factory=list)
    top_destinations: list[NetworkStatisticsTrafficItem] = Field(default_factory=list)
    top_source_devices: list[NetworkStatisticsTrafficItem] = Field(default_factory=list)
    hourly_timeline: list[NetworkStatisticsTimelinePoint] = Field(default_factory=list)


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


class NetworkDeviceTrafficPeerSummary(BaseModel):
    ip_address: str
    label: str | None = None
    events_count: int
    bytes_in: int
    bytes_out: int
    tracked_subject_id: int | None = None


class NetworkDeviceTrafficEventSummary(BaseModel):
    id: int
    event_type: str
    severity: str
    protocol: str | None = None
    src_ip: str | None = None
    dst_ip: str | None = None
    peer_ip: str | None = None
    peer_label: str | None = None
    bytes_in: int = 0
    bytes_out: int = 0
    observed_at: datetime
    tracked_peer_ip_subject_id: int | None = None
    tracked_peer_label_subject_id: int | None = None
    tracked_url_subject_id: int | None = None


class NetworkDeviceTrafficSummary(BaseModel):
    window_hours: int = 24
    total_events: int = 0
    allowed_events: int = 0
    blocked_events: int = 0
    bytes_in: int = 0
    bytes_out: int = 0
    last_observed_at: datetime | None = None
    top_peers: list[NetworkDeviceTrafficPeerSummary] = Field(default_factory=list)
    recent_events: list[NetworkDeviceTrafficEventSummary] = Field(default_factory=list)


class NetworkAssignedUserSummary(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    full_name: str | None = None
    office_location: str | None = None
    phone_extension: str | None = None
    is_placeholder_profile: bool = False


class NetworkDeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_scan_id: int | None
    ip_address: str
    mac_address: str | None
    hostname: str | None
    hostname_source: str | None = None
    display_name: str | None = None
    resolved_label: str
    label_source: str
    lifecycle_state: str = "active"
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
    assigned_user_id: int | None = None
    assigned_user: NetworkAssignedUserSummary | None = None
    retired_at: datetime | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime
    positions: list[DevicePositionResponse] = Field(default_factory=list)
    scan_history: list[NetworkDeviceHistoryEntry] = Field(default_factory=list)
    traffic_summary: NetworkDeviceTrafficSummary | None = None


class NetworkDeviceUpdateRequest(BaseModel):
    display_name: str | None = None
    lifecycle_state: str | None = Field(default=None, pattern="^(active|retired)$")
    asset_label: str | None = None
    model_name: str | None = None
    device_type: str | None = None
    operating_system: str | None = None
    location_hint: str | None = None
    notes: str | None = None
    assigned_user_id: int | None = None
    is_known_device: bool | None = None
    is_monitored: bool | None = None


class NetworkDeviceBulkUpdateRequest(BaseModel):
    device_ids: list[int] = Field(min_length=1)
    is_known_device: bool | None = None
    location_hint: str | None = None
    notes_append: str | None = None


class NetworkDeviceBulkUpdateResponse(BaseModel):
    updated_count: int
    items: list[NetworkDeviceResponse]


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


class NetworkScanTriggerRequest(BaseModel):
    scan_type: str = Field(default="incremental", pattern="^(incremental|arp)$")
    network_range: str | None = Field(default=None, max_length=64)


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
    resolved_label: str | None = None
    label_source: str | None = None
    assigned_user_label: str | None = None
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


class NetworkFirewallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor: str
    name: str
    model_name: str | None = None
    serial_number: str | None = None
    management_ip: str | None = None
    status: str
    metadata_sources: dict[str, Any] | None = None
    last_seen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class NetworkFirewallEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    firewall_id: int
    device_id: int | None = None
    source: str
    event_type: str
    severity: str
    log_id: str | None = None
    message: str | None = None
    src_ip: str | None = None
    src_device_label: str | None = None
    dst_ip: str | None = None
    dst_device_label: str | None = None
    protocol: str | None = None
    raw_payload: dict[str, Any] | None = None
    observed_at: datetime
    tracked_src_ip_subject_id: int | None = None
    tracked_dst_ip_subject_id: int | None = None
    tracked_domain_subject_id: int | None = None
    tracked_url_subject_id: int | None = None


class NetworkFirewallMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    firewall_id: int
    metric_key: str
    metric_value: float | None = None
    metric_text: str | None = None
    unit: str | None = None
    severity: str
    raw_payload: dict[str, Any] | None = None
    observed_at: datetime


class SophosSyslogIngestRequest(BaseModel):
    message: str = Field(min_length=1)
    firewall_id: int | None = None
    firewall_name: str | None = Field(default=None, max_length=255)
    management_ip: str | None = Field(default=None, max_length=64)
    observed_at: datetime | None = None


class NetworkTrackedSubjectActivityEvent(BaseModel):
    id: int
    firewall_id: int
    device_id: int | None = None
    event_type: str
    severity: str
    protocol: str | None = None
    src_ip: str | None = None
    src_device_label: str | None = None
    dst_ip: str | None = None
    dst_device_label: str | None = None
    domain: str | None = None
    url: str | None = None
    bytes_in: int = 0
    bytes_out: int = 0
    matched_on: str
    matched_value: str
    observed_at: datetime


class NetworkTrackedSubjectActivitySummary(BaseModel):
    window_hours: int = 168
    total_events: int = 0
    allowed_events: int = 0
    blocked_events: int = 0
    bytes_in: int = 0
    bytes_out: int = 0
    last_observed_at: datetime | None = None
    recent_events: list[NetworkTrackedSubjectActivityEvent] = Field(default_factory=list)


class NetworkTrackedSubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    normalized_value: str
    value: str
    label: str | None = None
    resolved_label: str
    notes: str | None = None
    is_active: bool
    device_id: int | None = None
    device_label: str | None = None
    created_by_user_id: int | None = None
    created_by_username: str | None = None
    created_at: datetime
    updated_at: datetime
    activity_summary: NetworkTrackedSubjectActivitySummary | None = None


class NetworkTrackedSubjectCreateRequest(BaseModel):
    entity_type: str = Field(pattern="^(device|ip|domain|url)$")
    value: str | None = Field(default=None, min_length=1, max_length=1024)
    device_id: int | None = None
    label: str | None = Field(default=None, max_length=255)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "NetworkTrackedSubjectCreateRequest":
        if self.entity_type == "device":
            if self.device_id is None:
                raise ValueError("device_id is required when entity_type=device")
            return self
        if not self.value or not self.value.strip():
            raise ValueError("value is required for ip, domain and url tracking")
        return self


class NetworkTrackedSubjectUpdateRequest(BaseModel):
    label: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    is_active: bool | None = None
