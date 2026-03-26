from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


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


class NetworkDevice(Base):
    __tablename__ = "network_devices"
    __table_args__ = (UniqueConstraint("ip_address", name="uq_network_devices_ip_address"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    last_scan_id: Mapped[int | None] = mapped_column(ForeignKey("network_scans.id", ondelete="SET NULL"), nullable=True, index=True)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mac_address: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    operating_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="online", nullable=False, index=True)
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    open_ports: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
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
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="info", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
