"""Consultative checks and declarations of shipments that already occurred."""

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from app.modules.ruolo.notice_register_schemas import NonBlank, RegisterCommand


class RecordedAttempt(RegisterCommand):
    channel: Literal["posta", "pec", "messo", "altro"]
    tracking_code: Annotated[NonBlank, Field(max_length=100)] | None = None
    sent_at: AwareDatetime
    evidence_reference: NonBlank
    confirmed: Literal[True]

    @model_validator(mode="after")
    def past_shipment(self) -> "RecordedAttempt":
        if self.sent_at > datetime.now(UTC):
            raise ValueError("Registrare solo invii gia effettuati, non date future")
        return self


class PositionEligibility(BaseModel):
    position_id: UUID
    avviso_id: UUID | None
    tax_year: int
    eligible: bool
    reasons: list[str]


class DocumentEligibility(BaseModel):
    document_id: UUID
    version: int
    checked_at: datetime
    eligible: bool
    reasons: list[str]
    positions: list[PositionEligibility]
    authorizes_dispatch: Literal[False] = False
