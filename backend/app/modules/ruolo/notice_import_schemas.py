"""Import HTTP contracts. Preview snapshots are server-owned and immutable."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.ruolo.notice_register_api_schemas import OrmView, Pagination
from app.modules.ruolo.notice_register_schemas import NonBlank, RegisterCommand


@dataclass
class ImportSnapshot:
    source: str
    filename: str
    content: bytes
    rows: list[dict]
    summary: dict


class ImportConfirmation(RegisterCommand):
    confirmed: Literal[True]
    digest: NonBlank
    reason: NonBlank


class ImportRowFilters(Pagination):
    review: Literal["all", "open", "resolved"] = "all"


class ConflictDecision(RegisterCommand):
    decision: Literal["keep_existing", "register_evidence"]
    document_id: UUID
    fingerprint: NonBlank
    confirmed: Literal[True]


class ImportBatchView(OrmView):
    id: UUID
    source: str
    digest: str
    filename: str
    parser_version: str
    status: str
    summary: dict
    actor_id: int
    confirmed_by: int | None
    reason: str | None
    created_at: datetime
    confirmed_at: datetime | None


class ImportRowView(OrmView):
    id: UUID
    row_number: int
    source_key: str
    fingerprint: str
    payload: dict
    anomalies: list[str]
    outcome: str
    document_id: UUID | None
    resolution: dict | None
