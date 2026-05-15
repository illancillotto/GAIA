from app.schemas.catasto import (
    CatastoBatchDetailResponse as ElaborazioneBatchDetailResponse,
    CatastoBatchResponse as ElaborazioneBatchResponse,
    CatastoCredentialCreateRequest as ElaborazioneCredentialCreateRequest,
    CatastoCaptchaSolveRequest as ElaborazioneCaptchaSolveRequest,
    CatastoCaptchaSummaryResponse as ElaborazioneCaptchaSummaryResponse,
    CatastoCredentialResponse as ElaborazioneCredentialResponse,
    CatastoCredentialStatusResponse as ElaborazioneCredentialStatusResponse,
    CatastoCredentialTestResponse as ElaborazioneCredentialTestResponse,
    CatastoCredentialTestRequest as ElaborazioneCredentialTestRequest,
    CatastoCredentialUpdateRequest as ElaborazioneCredentialUpdateRequest,
    CatastoOperationResponse as ElaborazioneOperationResponse,
    CatastoSingleVisuraCreateRequest as ElaborazioneRichiestaCreateRequest,
    CatastoVisuraRequestResponse as ElaborazioneRichiestaResponse,
)
from datetime import date, datetime

from pydantic import BaseModel, Field

__all__ = [
    "ElaborazioneBatchDetailResponse",
    "ElaborazioneBatchResponse",
    "ElaborazioneCaptchaSolveRequest",
    "ElaborazioneCaptchaSummaryResponse",
    "ElaborazioneCredentialCreateRequest",
    "ElaborazioneCredentialResponse",
    "ElaborazioneCredentialStatusResponse",
    "ElaborazioneCredentialTestResponse",
    "ElaborazioneCredentialTestRequest",
    "ElaborazioneCredentialUpdateRequest",
    "ElaborazioneOperationResponse",
    "ElaborazioneAnprRunItemResponse",
    "ElaborazioneAnprSummaryResponse",
    "ElaborazioneRichiestaCreateRequest",
    "ElaborazioneRichiestaResponse",
]


class ElaborazioneAnprRunItemResponse(BaseModel):
    id: str
    run_date: date
    ruolo_year: int
    status: str
    daily_calls_before: int
    daily_calls_after: int
    subjects_selected: int
    subjects_processed: int
    deceased_found: int
    errors: int
    calls_used: int
    started_at: datetime
    completed_at: datetime | None = None


class ElaborazioneAnprSummaryResponse(BaseModel):
    calls_today: int
    configured_daily_limit: int
    hard_daily_limit: int
    effective_daily_limit: int
    batch_size: int
    ruolo_year: int | None = None
    recent_runs: list[ElaborazioneAnprRunItemResponse] = Field(default_factory=list)
