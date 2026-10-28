"""API shapes for who pays an avviso instead of its registered taxpayer."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PayerReason = Literal["decesso", "vendita", "ufficio"]


class PayerAssignmentRequest(BaseModel):
    payer_tax_code: str = Field(min_length=11, max_length=16)
    reason: PayerReason
    notes: str | None = Field(default=None, max_length=2000)


class PayerAssignmentView(BaseModel):
    id: uuid.UUID
    reason: PayerReason
    reason_label: str
    notes: str | None
    payer_subject_id: uuid.UUID
    payer_tax_code: str | None
    payer_name: str | None
    payer_address: str | None
    created_at: datetime
    voided_at: datetime | None


class PayerAssignmentsResponse(BaseModel):
    active: PayerAssignmentView | None
    history: list[PayerAssignmentView]
