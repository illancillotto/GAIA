from datetime import date, datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class RuoloTributiCalculationPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    year_from: int | None = None
    year_to: int | None = None
    bonario_due_date: date | None = None
    surcharge_rate_percent: float
    surcharge_from: date | None = None
    euribor_6m_rate_percent: float = 0
    euribor_source_url: str | None = None
    euribor_reference_period: str | None = None
    euribor_fetched_at: datetime | None = None
    interest_rate_percent: float
    effective_interest_rate_percent: float = 0
    interest_from: date | None = None
    interest_start_mode: str = "fixed_date"
    bollettino_causale: str | None = None
    bollettino_esercizio: str | None = None
    is_active: bool
    notes: str | None = None
    updated_by: int | None = None
    created_at: datetime
    updated_at: datetime


class RuoloTributiCalculationPolicyUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    year_from: int | None = None
    year_to: int | None = None
    bonario_due_date: date | None = None
    surcharge_rate_percent: float = Field(default=0, ge=0)
    surcharge_from: date | None = None
    euribor_6m_rate_percent: float = Field(default=0, ge=0)
    euribor_source_url: str | None = None
    euribor_reference_period: str | None = None
    euribor_fetched_at: datetime | None = None
    interest_rate_percent: float = Field(default=0, ge=0)
    interest_from: date | None = None
    interest_start_mode: str = Field(default="fixed_date", pattern="^(fixed_date|notification_date)$")
    bollettino_causale: str | None = Field(default=None, pattern=r"^\d{3}$")
    bollettino_esercizio: str | None = Field(default=None, pattern=r"^\d{4}$")
    is_active: bool = True
    notes: str | None = None


class RuoloTributiCalculationPolicyListResponse(BaseModel):
    items: list[RuoloTributiCalculationPolicyResponse]


class RuoloTributiEuriborRateResponse(BaseModel):
    year: int
    rate_percent: float
    reference_period: str
    source_url: str
    verification_url: str
    fetched_at: datetime
    observations_count: int
