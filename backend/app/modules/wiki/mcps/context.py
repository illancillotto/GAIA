"""Trusted authorization and correlation context shared by source adapters."""

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(frozen=True)
class CallContext:
    principal: str
    scopes: frozenset[str]
    request_id: str = field(default_factory=lambda: str(uuid4()))
    conversation_id: str | None = None
    experiment_run_id: str | None = None
