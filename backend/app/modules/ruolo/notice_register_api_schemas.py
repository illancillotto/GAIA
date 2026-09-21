"""HTTP contracts: actor and source provenance are assigned by the server."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.modules.ruolo.notice_register_schemas import (
    NonBlank,
    NotificationState,
    RecoveryState,
    RegisterCommand,
)

T = TypeVar("T")
SearchText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=100)]


class Pagination(RegisterCommand):
    page: int = Field(default=1, ge=1, le=100000)
    page_size: int = Field(default=50, ge=1, le=100)


class RegisterFilters(Pagination):
    q: SearchText | None = None
    tax_year: int | None = Field(default=None, ge=1900, le=9999)
    view: Literal["tutti", "anomalie", "affidamenti", "riconciliati"] = "tutti"
    reconciliation_candidates: bool = False
    notification_state: NotificationState | None = None
    recovery_state: RecoveryState | None = None


class CandidateFilters(Pagination):
    q: SearchText


class Mutation(RegisterCommand, Generic[T]):
    reason: NonBlank
    expected_version: int = Field(ge=1)
    data: T


class LinkInput(RegisterCommand):
    avviso_id: UUID | None
    confirmed: Literal[True]


class ReconciliationInput(RegisterCommand):
    target_document_id: UUID
    target_version: int = Field(ge=1)
    confirmed: Literal[True]


class ManualEvidence(RegisterCommand):
    kind: Annotated[NonBlank, Field(max_length=60)]
    reference: NonBlank
    occurred_on: date | None = None
    attempt_id: UUID | None = None


class MutationResult(BaseModel):
    document_id: UUID
    version: int
    resource_id: UUID


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class OrmView(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DocumentView(OrmView):
    id: UUID
    source_system: str
    source_key: str
    document_number: str
    tax_code: str | None
    issued_on: date | None
    version: int
    reconciled_into_id: UUID | None
    created_at: datetime


class DocumentSummary(DocumentView):
    notification_state: str
    position_count: int
    unlinked_count: int
    conflicting_count: int
    recovery_review_count: int
    anomalies: list[str]


class NotificationView(OrmView):
    state: str
    notified_on: date | None
    evidence_id: UUID | None


class RecoveryView(OrmView):
    state: str
    case_reference: str | None
    verified_on: date | None
    evidence_reference: str | None
    amount: Decimal | None


class CandidateView(OrmView):
    id: UUID
    codice_cnc: str
    anno_tributario: int
    codice_fiscale_raw: str | None
    nominativo_raw: str | None
    subject_id: UUID | None
    importo_totale_euro: Decimal | None


class PositionView(OrmView):
    id: UUID
    source_namespace: str
    source_reference: str
    tax_year: int
    avviso_id: UUID | None
    avviso: CandidateView | None
    recovery: RecoveryView | None


class DocumentDetail(DocumentSummary):
    original_json: dict
    notification: NotificationView | None
    positions: list[PositionView]


class CandidateResult(CandidateView):
    already_linked: bool


class AttemptView(OrmView):
    id: UUID
    source_system: str
    source_key: str
    channel: str
    tracking_code: str | None
    sent_at: datetime | None
    registered_mail_id: UUID | None


class EvidenceView(OrmView):
    id: UUID
    source_system: str
    source_key: str
    attempt_id: UUID | None
    kind: str
    occurred_on: date | None
    reference: str
    original_json: dict


class AuditView(OrmView):
    id: UUID
    version: int
    actor_id: int
    action: str
    reason: str
    before_json: dict
    after_json: dict
    created_at: datetime
