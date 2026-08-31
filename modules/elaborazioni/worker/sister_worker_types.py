from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.models.catasto import CatastoVisuraRequest


@dataclass(slots=True)
class ClaimedRequestSelection:
    request_id: UUID | None
    wait_reason: str | None = None
    wait_seconds: int | None = None
    execution_token: UUID | None = None

    def resolved_wait_seconds(self, fallback: int) -> int:
        return self.wait_seconds if self.wait_seconds is not None else fallback


@dataclass(slots=True)
class PreparedSisterRequest:
    request: CatastoVisuraRequest
    execution_token: UUID


@dataclass(frozen=True, slots=True)
class SisterRemoteStateUpdate:
    remote_id: str | None
    remote_url: str | None
    state: str
    credential_id: UUID | None = None
