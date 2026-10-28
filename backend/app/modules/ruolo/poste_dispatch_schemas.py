"""API contract of the Posta Online outbox. No schema here can trigger INVIA."""

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]


class PosteDispatchCandidate(BaseModel):
    batch_item_id: UUID
    batch_title: str | None
    display_name: str | None
    codice_fiscale: str
    notice_number: str | None
    years: list[Any]
    created_at: datetime


class PosteDispatchCandidateList(BaseModel):
    items: list[PosteDispatchCandidate]
    total: int
    page: int
    page_size: int


class PosteDispatchLotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    batch_item_ids: list[UUID] = Field(min_length=1, max_length=50)


class PosteDispatchRecipientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Text
    name_extra: Text = ""
    address: Text
    cap: Text = ""
    city: Text
    province: Text = ""


class PosteDispatchJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["addresses", "drafts", "reconcile", "delete"]


class PosteDispatchItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    batch_item_id: UUID
    notice_number: str
    shipment_name: str
    status: str
    recipient: dict[str, str]
    poste_address: dict[str, Any] | None
    address_review: dict[str, Any] | None
    artifact_sha256: str
    artifact_size: int
    poste_draft_id: str | None
    poste_status: str | None
    price_amount: float | None
    draft_created_at: datetime | None
    sent_at: datetime | None
    tracking_number: str | None
    registered_mail_id: UUID | None
    error_detail: str | None
    updated_at: datetime


class PosteDispatchJobOut(BaseModel):
    id: int
    mode: str
    status: str
    error_detail: str | None
    created_at: datetime


class PosteDispatchEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: str
    item_id: UUID | None
    from_status: str | None
    to_status: str | None
    actor_id: int | None
    job_id: int | None
    created_at: datetime


class PosteDispatchLotSummary(BaseModel):
    id: UUID
    title: str
    status: str
    created_by: int
    created_at: datetime
    counts: dict[str, int]
    priced_total: float


class PosteDispatchLotDetail(PosteDispatchLotSummary):
    postal_options: dict[str, Any]
    portal_snapshot: dict[str, Any] | None
    draft_expires_at: datetime | None
    active_job: PosteDispatchJobOut | None
    items: list[PosteDispatchItemOut]
    events: list[PosteDispatchEventOut]


class PosteDispatchLotList(BaseModel):
    items: list[PosteDispatchLotSummary]
    total: int
    page: int
    page_size: int
