from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GisLayer(Base):
    __tablename__ = "gis_layers"
    __table_args__ = (UniqueConstraint("workspace", "name", name="uq_gis_layers_workspace_name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain_module: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(32), default="postgis", nullable=False, index=True)
    official_source: Mapped[str] = mapped_column(String(32), default="postgis", nullable=False)
    postgis_schema: Mapped[str | None] = mapped_column(String(80), default="public", nullable=True)
    postgis_table: Mapped[str | None] = mapped_column(String(160), nullable=True)
    geometry_column: Mapped[str | None] = mapped_column(String(80), default="geometry", nullable=True)
    geometry_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    srid: Mapped[int | None] = mapped_column(default=4326, nullable=True)
    feature_id_column: Mapped[str | None] = mapped_column(String(80), default="id", nullable=True)
    martin_layer_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    ogc_service_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    qgis_project_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    nas_export_root: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    permissions: Mapped[list["GisLayerPermission"]] = relationship(
        back_populates="layer", cascade="all, delete-orphan"
    )
    annotations: Mapped[list["GisAnnotation"]] = relationship(
        back_populates="layer", cascade="all, delete-orphan"
    )
    change_requests: Mapped[list["GisChangeRequest"]] = relationship(
        back_populates="layer", cascade="all, delete-orphan"
    )
    exports: Mapped[list["GisLayerExport"]] = relationship(
        back_populates="layer", cascade="all, delete-orphan"
    )


class GisLayerPermission(Base):
    __tablename__ = "gis_layer_permissions"
    __table_args__ = (UniqueConstraint("layer_id", "principal_type", "principal_key", name="uq_gis_layer_permissions_principal"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    layer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gis_layers.id", ondelete="CASCADE"), nullable=False, index=True)
    principal_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    principal_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("application_users.id", ondelete="CASCADE"), nullable=True, index=True)
    can_view: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_annotate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_edit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_approve: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_manage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    granted_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    layer: Mapped[GisLayer] = relationship(back_populates="permissions")


class GisAnnotation(Base):
    __tablename__ = "gis_annotations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    layer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gis_layers.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    geometry_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    attachment_refs_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    layer: Mapped[GisLayer] = relationship(back_populates="annotations")


class GisChangeRequest(Base):
    __tablename__ = "gis_change_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    layer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gis_layers.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    change_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="submitted", nullable=False, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    layer: Mapped[GisLayer] = relationship(back_populates="change_requests")


class GisLayerExport(Base):
    __tablename__ = "gis_layer_exports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    layer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gis_layers.id", ondelete="CASCADE"), nullable=False, index=True)
    version_label: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="requested", nullable=False, index=True)
    nas_path: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    layer: Mapped[GisLayer] = relationship(back_populates="exports")


class GisShapefileImport(Base):
    __tablename__ = "gis_shapefile_imports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    workspace: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    domain_module: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    target_layer_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    target_layer_title: Mapped[str] = mapped_column(String(255), nullable=False)
    official_source: Mapped[str] = mapped_column(String(32), default="shapefile_upload", nullable=False)
    source_srid: Mapped[int] = mapped_column(nullable=False)
    encoding: Mapped[str] = mapped_column(String(40), default="utf-8", nullable=False)
    staging_schema: Mapped[str | None] = mapped_column(String(80), nullable=True)
    staging_table: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    feature_count: Mapped[int] = mapped_column(default=0, nullable=False)
    geometry_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bbox_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    field_schema_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    validation_report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class GisAuditLog(Base):
    __tablename__ = "gis_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    layer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("gis_layers.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True)
    target_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
