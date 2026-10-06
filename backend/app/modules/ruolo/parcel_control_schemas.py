from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ControlCommand(BaseModel):
    command_id: UUID
    expected_version: int = Field(default=1, ge=1)
    reason: str = Field(min_length=3, max_length=3000)
    data: dict = Field(default_factory=dict)

    @field_validator("reason")
    @classmethod
    def meaningful_reason(cls, value: str) -> str:
        if len(value.strip()) < 3:
            raise ValueError("Motivazione obbligatoria")
        return value.strip()


class ControlFilters(BaseModel):
    view: Literal["all", "missing", "cf", "cases", "closed", "proposals", "visure", "recovered"] = (
        "all"
    )
    search: str = Field(default="", max_length=100)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
