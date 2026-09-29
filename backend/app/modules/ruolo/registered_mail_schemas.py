from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class RegisteredMailReviewEvidence(BaseModel):
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sheet: str = Field(pattern=r"^Dati$")
    row: int = Field(ge=2)
    ref_2022: str
    ref_2023: str


class RegisteredMailReferenceCheckRequest(BaseModel):
    ref_2022: str = Field(min_length=1, max_length=128)
    ref_2023: str = Field(min_length=1, max_length=128)


class RuoloTributiRegisteredMailAssociationRequest(BaseModel):
    avviso_id: uuid.UUID | None = None
    avviso_ids: list[uuid.UUID] | None = None
    review_evidence: RegisteredMailReviewEvidence | None = None


class RuoloTributiRegisteredMailSummaryResponse(BaseModel):
    total: int
    associated: int
    anomalies: int
