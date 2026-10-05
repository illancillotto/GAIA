import uuid
from dataclasses import dataclass
from datetime import date, datetime

from pydantic import BaseModel


@dataclass(frozen=True)
class CardUpload:
    filename: str
    content: bytes
    tracking_number: str
    scanned_on: date
    source_reference: str | None


@dataclass(frozen=True)
class CardMetadata:
    tracking_number: str
    scanned_on: date
    source_reference: str | None


class RegisteredMailDocumentView(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    subject_id: uuid.UUID
    filename: str
    tracking_number: str
    sha256: str
    scanned_on: date
    source_reference: str | None
    created_at: datetime
