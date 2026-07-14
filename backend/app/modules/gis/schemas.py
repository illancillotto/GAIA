from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GisAccessLevel(str, Enum):
    viewer = "viewer"
    annotator = "annotator"
    editor = "editor"
    approver = "approver"
    admin = "admin"


class GisLayerCreate(BaseModel):
    workspace: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    domain_module: str | None = Field(default=None, max_length=80)
    source_type: str = Field(default="postgis", max_length=32)
    official_source: str = Field(default="postgis", max_length=32)
    postgis_schema: str | None = Field(default="public", max_length=80)
    postgis_table: str | None = Field(default=None, max_length=160)
    geometry_column: str | None = Field(default="geometry", max_length=80)
    geometry_type: str | None = Field(default=None, max_length=64)
    srid: int | None = Field(default=4326, ge=1)
    feature_id_column: str | None = Field(default="id", max_length=80)
    martin_layer_id: str | None = Field(default=None, max_length=160)
    ogc_service_url: str | None = None
    qgis_project_path: str | None = None
    nas_export_root: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GisLayerMetadataUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    ogc_service_url: str | None = None
    qgis_project_path: str | None = None
    nas_export_root: str | None = None
    metadata: dict[str, Any] | None = None


class GisLayerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace: str
    name: str
    title: str
    description: str | None = None
    domain_module: str | None = None
    source_type: str
    official_source: str
    postgis_schema: str | None = None
    postgis_table: str | None = None
    geometry_column: str | None = None
    geometry_type: str | None = None
    srid: int | None = None
    feature_id_column: str | None = None
    martin_layer_id: str | None = None
    ogc_service_url: str | None = None
    qgis_project_path: str | None = None
    nas_export_root: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    effective_access_level: GisAccessLevel
    can_view: bool
    can_annotate: bool
    can_edit: bool
    can_approve: bool
    can_manage: bool
    created_at: datetime
    updated_at: datetime


class GisLayerListResponse(BaseModel):
    items: list[GisLayerResponse]
    total: int


class GisLayerPermissionUpsert(BaseModel):
    principal_type: Literal["role", "user"]
    principal_key: str = Field(min_length=1, max_length=120)
    access_level: GisAccessLevel


class GisLayerPermissionResponse(BaseModel):
    id: UUID
    layer_id: UUID
    principal_type: str
    principal_key: str
    access_level: GisAccessLevel
    can_view: bool
    can_annotate: bool
    can_edit: bool
    can_approve: bool
    can_manage: bool
    created_at: datetime
    updated_at: datetime


class GisAnnotationCreate(BaseModel):
    feature_id: str | None = Field(default=None, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    geometry: dict[str, Any] | None = None
    attachment_refs: list[dict[str, Any]] = Field(default_factory=list)


class GisAnnotationResponse(BaseModel):
    id: UUID
    layer_id: UUID
    feature_id: str | None = None
    title: str
    body: str
    geometry: dict[str, Any] | None = None
    attachment_refs: list[dict[str, Any]] = Field(default_factory=list)
    status: str
    created_by_user_id: int | None = None
    created_at: datetime
    updated_at: datetime


class GisChangeRequestCreate(BaseModel):
    feature_id: str | None = Field(default=None, max_length=255)
    change_type: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any]
    justification: str | None = None


class GisChangeRequestApprove(BaseModel):
    review_notes: str | None = None


class GisChangeRequestResponse(BaseModel):
    id: UUID
    layer_id: UUID
    feature_id: str | None = None
    change_type: str
    status: str
    payload: dict[str, Any]
    justification: str | None = None
    requested_by_user_id: int | None = None
    reviewed_by_user_id: int | None = None
    review_notes: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class GisLayerExportRequest(BaseModel):
    version_label: str | None = Field(default=None, max_length=120)
    nas_path: str | None = None
    checksum_sha256: str | None = Field(default=None, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GisLayerExportResponse(BaseModel):
    id: UUID
    layer_id: UUID
    version_label: str
    status: str
    nas_path: str
    checksum_sha256: str | None = None
    requested_by_user_id: int | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
