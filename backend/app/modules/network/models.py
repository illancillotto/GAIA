from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.application_user import ApplicationUser


class NetworkScan(Base):
    __tablename__ = "network_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    network_range: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scan_type: Mapped[str] = mapped_column(String(32), default="incremental", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False, index=True)
    hosts_scanned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_hosts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discovered_devices: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    initiated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class NetworkScanDevice(Base):
    __tablename__ = "network_scan_devices"
    __table_args__ = (UniqueConstraint("scan_id", "ip_address", name="uq_network_scan_devices_scan_ip"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("network_scans.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("network_devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mac_address: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hostname_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    asset_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operating_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dns_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_hint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_sources: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    open_ports: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class NetworkDevice(Base):
    __tablename__ = "network_devices"
    __table_args__ = (UniqueConstraint("ip_address", name="uq_network_devices_ip_address"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    last_scan_id: Mapped[int | None] = mapped_column(ForeignKey("network_scans.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mac_address: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    hostname_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    asset_label: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_sources: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    operating_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dns_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_hint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_known_device: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="online", nullable=False, index=True)
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    open_ports: Mapped[str | None] = mapped_column(Text, nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    assigned_user: Mapped["ApplicationUser | None"] = relationship(
        "ApplicationUser",
        back_populates="assigned_network_devices",
    )


class NetworkAlert(Base):
    __tablename__ = "network_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("network_devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scan_id: Mapped[int | None] = mapped_column(
        ForeignKey("network_scans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_to_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="info", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True)
    verification_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_to_user: Mapped["ApplicationUser | None"] = relationship("ApplicationUser")


class FloorPlan(Base):
    __tablename__ = "floor_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    building: Mapped[str | None] = mapped_column(String(255), nullable=True)
    floor_label: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    svg_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    width: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DevicePosition(Base):
    __tablename__ = "device_positions"
    __table_args__ = (UniqueConstraint("device_id", "floor_plan_id", name="uq_device_positions_device_floor"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("network_devices.id", ondelete="CASCADE"), nullable=False, index=True)
    floor_plan_id: Mapped[int] = mapped_column(ForeignKey("floor_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DeviceInventoryLink(Base):
    __tablename__ = "device_inventory_links"
    __table_args__ = (UniqueConstraint("device_id", name="uq_device_inventory_links_device_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("network_devices.id", ondelete="CASCADE"), nullable=False, index=True)
    inventory_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    inventory_hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inventory_mac_address: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class NetworkFirewall(Base):
    __tablename__ = "network_firewalls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vendor: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    management_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False, index=True)
    metadata_sources: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class NetworkFirewallMetric(Base):
    __tablename__ = "network_firewall_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    firewall_id: Mapped[int] = mapped_column(ForeignKey("network_firewalls.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    metric_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    severity: Mapped[str] = mapped_column(String(32), default="info", nullable=False, index=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class NetworkFirewallEvent(Base):
    __tablename__ = "network_firewall_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    firewall_id: Mapped[int] = mapped_column(ForeignKey("network_firewalls.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("network_devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="info", nullable=False, index=True)
    log_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    src_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    dst_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    protocol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class NetworkFirewallHourlyRollup(Base):
    __tablename__ = "network_firewall_hourly_rollups"
    __table_args__ = (UniqueConstraint("bucket_start", "category", "dimension_key", name="uq_network_firewall_hourly_rollups_bucket_category_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dimension_key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("network_devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tracked_subject_id: Mapped[int | None] = mapped_column(
        ForeignKey("network_tracked_subjects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    events_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    allowed_events: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocked_events: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bytes_in: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    bytes_out: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class NetworkTrackedSubject(Base):
    __tablename__ = "network_tracked_subjects"
    __table_args__ = (UniqueConstraint("entity_type", "normalized_value", name="uq_network_tracked_subjects_type_value"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    normalized_value: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(1024), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("network_devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class NetworkDetectionWatchlist(Base):
    __tablename__ = "network_detection_watchlist"
    __table_args__ = (UniqueConstraint("category", "match_type", "pattern", name="uq_network_detection_watchlist_rule"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    rule_mode: Mapped[str] = mapped_column(String(16), default="detect", nullable=False, index=True)
    match_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    pattern: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
