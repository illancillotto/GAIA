from __future__ import annotations

import uuid

from pydantic import BaseModel


class RuoloTributiRegisteredMailAssociationRequest(BaseModel):
    avviso_id: uuid.UUID | None = None
    avviso_ids: list[uuid.UUID] | None = None


class RuoloTributiRegisteredMailSummaryResponse(BaseModel):
    total: int
    associated: int
    anomalies: int
