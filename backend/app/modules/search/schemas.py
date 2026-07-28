from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SearchModule = Literal["utenze", "ruolo", "catasto"]


class OperationalSearchResult(BaseModel):
    id: str
    module: SearchModule
    type: str
    title: str
    subtitle: str
    description: str | None = None
    href: str
    score: int = Field(ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OperationalSearchResponse(BaseModel):
    query: str
    items: list[OperationalSearchResult]
    total: int
    modules: list[SearchModule]
