from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrgStructureUserSummary(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None = None
    role: str
    is_active: bool


class OrgStructureAssignmentUpdate(BaseModel):
    manager_user_id: int | None = None
    title: str | None = None
    area_label: str | None = None
    notes: str | None = None
    is_active: bool = True


class OrgStructureAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_user_id: int
    manager_user_id: int | None = None
    source_mode: str
    title: str | None = None
    area_label: str | None = None
    notes: str | None = None
    is_active: bool
    source_wc_role: str | None = None
    source_chart_summary: str | None = None
    last_synced_from_source_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    user: OrgStructureUserSummary
    manager: OrgStructureUserSummary | None = None
    direct_reports_count: int = Field(ge=0, default=0)
    descendants_count: int = Field(ge=0, default=0)
    depth: int = Field(ge=0, default=0)


class OrgStructureSuggestionResponse(BaseModel):
    application_user_id: int
    wc_operator_id: str | None = None
    username: str
    full_name: str | None = None
    email: str
    role: str
    wc_role: str | None = None
    chart_summary: str | None = None
    already_published: bool


class OrgStructureMetricsResponse(BaseModel):
    total_users: int = Field(ge=0)
    published_nodes: int = Field(ge=0)
    root_nodes: int = Field(ge=0)
    unassigned_users: int = Field(ge=0)
    linked_whitecompany_users: int = Field(ge=0)


class OrgStructureWorkspaceResponse(BaseModel):
    items: list[OrgStructureAssignmentResponse]
    suggestions: list[OrgStructureSuggestionResponse]
    metrics: OrgStructureMetricsResponse


class OrgStructureBootstrapResponse(BaseModel):
    created: int = Field(ge=0)
    updated: int = Field(ge=0)
    skipped: int = Field(ge=0)
