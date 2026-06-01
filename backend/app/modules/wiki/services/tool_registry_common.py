from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.policy import WikiToolMeta


@dataclass(frozen=True)
class WikiToolDefinition:
    meta: WikiToolMeta
    intents: tuple[str, ...]
    priority: int
    matcher: Callable[[str], int]
    handler: Callable[[Session, ApplicationUser, str], WikiChatResponse]


UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
NAS_USER_RE = re.compile(r"\butente(?:\s+nas)?\s+([a-z0-9._-]{2,})\b", re.IGNORECASE)
TAX_ID_RE = re.compile(r"\b(?:[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]|\d{11})\b", re.IGNORECASE)
SECTION_KEY_RE = re.compile(r"\b[a-z]+(?:\.[a-z0-9_-]+)+\b")
SHARE_RE = re.compile(r"\bshare\s+([a-z0-9._/-]{2,})\b", re.IGNORECASE)


def normalize(question: str) -> str:
    return question.strip().lower()


def contains_any(question: str, *terms: str) -> bool:
    normalized = normalize(question)
    return any(term in normalized for term in terms)


def score_terms(question: str, *terms: str) -> int:
    normalized = normalize(question)
    return sum(1 for term in terms if term in normalized)


def has_uuid(question: str) -> bool:
    return UUID_RE.search(question) is not None


def has_tax_id(question: str) -> bool:
    return TAX_ID_RE.search(question.upper()) is not None


def parse_uuid(question: str) -> UUID | None:
    match = UUID_RE.search(question)
    if match is None:
        return None
    return UUID(match.group(0))
