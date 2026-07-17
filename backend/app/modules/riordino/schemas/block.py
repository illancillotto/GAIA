"""Block schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.modules.riordino.schemas.base import PaginatedResponse, RiordinoSchema, TimestampedResponse
from app.modules.riordino.schemas.event import EventResponse


class BlockParcelRef(BaseModel):
    codice_catastale: str | None = None
    administrative_unit: str | None = None
    foglio: str
    particella: str


class BlockCreate(BaseModel):
    title: str
    coordinator_user_id: int
    selection_type: str = Field(pattern="^(municipality|lot|parcel_list|gis_selection)$")
    description: str | None = None
    municipality: str | None = None
    codice_catastale: str | None = None
    administrative_unit: str | None = None
    foglio: str | None = None
    grid_code: str | None = None
    lot_code: str | None = None
    ade_particella_ids: list[uuid.UUID] = []
    parcel_refs: list[BlockParcelRef] = []
    operator_user_ids: list[int] = []

    @model_validator(mode="after")
    def validate_selection(self) -> "BlockCreate":
        if self.selection_type == "municipality" and not (self.codice_catastale or self.administrative_unit):
            raise ValueError("municipality selection requires codice_catastale or administrative_unit")
        if self.selection_type == "lot" and not (
            (self.codice_catastale or self.administrative_unit) and self.foglio
        ):
            raise ValueError("lot selection requires codice_catastale/administrative_unit and foglio")
        if self.selection_type == "parcel_list" and not (self.ade_particella_ids or self.parcel_refs):
            raise ValueError("parcel_list selection requires ade_particella_ids or parcel_refs")
        if self.selection_type == "gis_selection" and not self.ade_particella_ids:
            raise ValueError("gis_selection selection requires ade_particella_ids")
        return self


class BlockUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    coordinator_user_id: int | None = None
    operator_user_ids: list[int] | None = None


class BlockAssignmentResponse(RiordinoSchema):
    id: uuid.UUID
    block_id: uuid.UUID
    user_id: int
    assignment_role: str
    is_active: bool
    assigned_by: int
    assigned_at: datetime


class BlockParcelSnapshotResponse(TimestampedResponse):
    block_id: uuid.UUID
    ade_particella_id: uuid.UUID | None = None
    national_cadastral_reference: str
    administrative_unit: str | None = None
    codice_catastale: str | None = None
    sezione_catastale: str | None = None
    foglio: str | None = None
    particella: str | None = None
    label: str | None = None
    cat_particella_id: uuid.UUID | None = None
    cat_particella_match_status: str
    cat_particella_match_reason: str | None = None
    capacitas_payload_json: dict | None = None
    operator_review_status: str
    operator_review_notes: str | None = None
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    sister_visura_status: str
    sister_visura_request_id: str | None = None
    sister_visura_document_ref: str | None = None
    sister_visura_error: str | None = None
    sister_visura_requested_by: int | None = None
    sister_visura_requested_at: datetime | None = None
    sister_visura_completed_by: int | None = None
    sister_visura_completed_at: datetime | None = None


class BlockParcelReviewRequest(BaseModel):
    status: str = Field(pattern="^(pending|aligned|mismatch|resolved)$")
    notes: str | None = None


class BlockSisterVisuraRequest(BaseModel):
    enqueue: bool = True
    request_id: str | None = None
    notes: str | None = None


class BlockSisterVisuraCompleteRequest(BaseModel):
    status: str = Field(pattern="^(downloaded|failed)$")
    document_ref: str | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_completion(self) -> "BlockSisterVisuraCompleteRequest":
        if self.status == "downloaded" and not self.document_ref:
            raise ValueError("document_ref is required when status is downloaded")
        if self.status == "failed" and not self.error_message:
            raise ValueError("error_message is required when status is failed")
        return self


class BlockWizardTaskResponse(RiordinoSchema):
    code: str
    title: str
    status: str
    snapshot_id: uuid.UUID | None = None
    phase: str
    assignee_hint: str
    blocking_reason: str | None = None


class BlockWizardResponse(RiordinoSchema):
    block_id: uuid.UUID
    block_code: str
    tasks: list[BlockWizardTaskResponse]


class BlockCoordinatorOperatorSummary(RiordinoSchema):
    user_id: int
    assignment_role: str
    is_active: bool
    reviewed_count: int
    sister_requested_count: int
    sister_completed_count: int
    last_activity_at: datetime | None = None


class BlockCoordinatorSummaryResponse(RiordinoSchema):
    block_id: uuid.UUID
    block_code: str
    coordinator_user_id: int
    parcel_count: int
    mismatch_count: int
    review_status_counts: dict[str, int]
    sister_status_counts: dict[str, int]
    task_status_counts: dict[str, int]
    operators: list[BlockCoordinatorOperatorSummary]
    recent_events: list[EventResponse]


class BlockResponse(TimestampedResponse):
    code: str
    title: str
    description: str | None = None
    municipality: str | None = None
    selection_type: str
    selection_json: dict
    status: str
    coordinator_user_id: int
    created_by: int
    parcel_count: int
    mismatch_count: int
    updated_at: datetime
    deleted_at: datetime | None = None


class BlockDetailResponse(BlockResponse):
    assignments: list[BlockAssignmentResponse] = []
    parcel_snapshots: list[BlockParcelSnapshotResponse] = []
    events: list[EventResponse] = []


class BlockListResponse(PaginatedResponse):
    items: list[BlockResponse]
