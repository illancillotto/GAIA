"""Workflow schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StepAdvanceRequest(BaseModel):
    outcome_code: str | None = None
    outcome_notes: str | None = None


class StepSkipRequest(BaseModel):
    skip_reason: str = Field(min_length=1)


class PhaseCompleteRequest(BaseModel):
    notes: str | None = None
