from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Chat ──────────────────────────────────────────────────────────────────────

class WikiChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    context_article: str | None = Field(None, description="Source file da pre-caricare come contesto")


class WikiChunkSource(BaseModel):
    source_file: str
    section_title: str | None
    excerpt: str  # primi 200 caratteri del chunk


class WikiChatResponse(BaseModel):
    answer: str
    sources: list[WikiChunkSource]
    found: bool  # False se nessun chunk rilevante trovato


# ── Articles ──────────────────────────────────────────────────────────────────

class WikiArticleSummary(BaseModel):
    source_file: str
    section_title: str | None
    excerpt: str
    chunk_index: int

    model_config = {"from_attributes": True}


class WikiArticleGroup(BaseModel):
    source_file: str
    chunks: list[WikiArticleSummary]


# ── Requests ──────────────────────────────────────────────────────────────────

class WikiRequestCreate(BaseModel):
    user_question: str = Field(..., min_length=1, max_length=2000)
    agent_response: str | None = None
    category: Literal["feature_request", "bug_report", "question"] = "feature_request"


class WikiRequestRead(BaseModel):
    id: uuid.UUID
    user_question: str
    agent_response: str | None
    category: str
    status: str
    created_by: str | None
    admin_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WikiRequestStatusUpdate(BaseModel):
    status: Literal["pending", "reviewed", "planned", "done"]
    admin_notes: str | None = None


# ── Index ─────────────────────────────────────────────────────────────────────

class WikiIndexResult(BaseModel):
    indexed_files: list[str]
    total_chunks: int
    message: str
