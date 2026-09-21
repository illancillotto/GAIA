from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NoticeGenerationConfirmationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    generation_id: UUID
    generation_kind: str
    review_digest: str
    input_basis: dict
    identity_keys: list
    notice_numbers: list
    confirmed_by: int
    confirmed_at: datetime


class NoticeGenerationConfirmRequest(BaseModel):
    batch: bool = True
