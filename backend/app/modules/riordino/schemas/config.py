"""Configuration schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.riordino.schemas.base import TimestampedResponse


class StepTemplateUpdate(BaseModel):
    title: str | None = None
    is_required: bool | None = None
    branch: str | None = None
    activation_condition: dict | None = None
    requires_document: bool | None = None
    is_decision: bool | None = None
    outcome_options: list[str] | None = None
    is_active: bool | None = None


class StepTemplateResponse(TimestampedResponse):
    phase_code: str
    code: str
    title: str
    sequence_no: int
    is_required: bool
    branch: str | None = None
    activation_condition: dict | None = None
    requires_document: bool
    is_decision: bool
    outcome_options: list | None = None
    is_active: bool
    updated_at: datetime


class DocumentTypeConfigBase(BaseModel):
    code: str
    label: str
    description: str | None = None
    is_active: bool = True
    sort_order: int = 0


class DocumentTypeConfigCreate(DocumentTypeConfigBase):
    pass


class DocumentTypeConfigUpdate(BaseModel):
    code: str | None = None
    label: str | None = None
    description: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class DocumentTypeConfigResponse(TimestampedResponse):
    code: str
    label: str
    description: str | None = None
    is_active: bool
    sort_order: int
    updated_at: datetime


class IssueTypeConfigBase(BaseModel):
    code: str
    label: str
    category: str
    default_severity: str = "medium"
    description: str | None = None
    is_active: bool = True
    sort_order: int = 0


class IssueTypeConfigCreate(IssueTypeConfigBase):
    pass


class IssueTypeConfigUpdate(BaseModel):
    code: str | None = None
    label: str | None = None
    category: str | None = None
    default_severity: str | None = None
    description: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class IssueTypeConfigResponse(TimestampedResponse):
    code: str
    label: str
    category: str
    default_severity: str
    description: str | None = None
    is_active: bool
    sort_order: int
    updated_at: datetime
