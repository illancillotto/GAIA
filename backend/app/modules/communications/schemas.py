"""Strict command contracts. No API command can request arbitrary state changes."""

import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, Field, field_validator

Channel = Literal["pec", "email"]
Short = Annotated[str, Field(min_length=1, max_length=250)]


def address(value: str) -> str:
    try:
        return validate_email(value, check_deliverability=False).normalized
    except EmailNotValidError as exc:
        raise ValueError("Recapito non valido") from exc


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AccountInput(Command):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    channel: Channel
    provider: Annotated[str, Field(min_length=1, max_length=80)]
    sender: str
    display_name: Annotated[str, Field(max_length=120)] = ""
    smtp_host: str
    smtp_port: int = Field(ge=1, le=65535)
    smtp_encryption: Literal["tls", "starttls"] = "tls"
    imap_host: str
    imap_port: int = Field(ge=1, le=65535)
    imap_encryption: Literal["tls", "starttls"] = "tls"
    auth_method: Literal["password", "oauth2"] = "password"
    username: Annotated[str, Field(min_length=1, max_length=254)]
    secret_ref: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")]
    active: bool = False
    paused: bool = True
    allowed_modules: list[Literal["ruolo"]] = Field(default_factory=lambda: ["ruolo"])
    allowed_user_ids: list[int] = Field(default_factory=list, max_length=500)
    default_modules: list[Literal["ruolo"]] = Field(default_factory=list)
    is_default: bool = False
    priority: int = Field(default=100, ge=0, le=10000)
    max_bytes: int = Field(default=16 * 1024 * 1024, ge=1024, le=32 * 1024 * 1024)
    hourly_limit: int = Field(default=30, ge=1, le=10000)

    _sender = field_validator("sender")(address)

    @field_validator("smtp_host", "imap_host")
    @classmethod
    def host(cls, value):
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}", value):
            raise ValueError("Host non valido: indicare un nome DNS, senza URL")
        return value.lower()

    @field_validator("display_name", "username")
    @classmethod
    def no_controls(cls, value):
        if any(ord(character) < 32 for character in value):
            raise ValueError("Caratteri di controllo non ammessi")
        return value


class AccountChange(AccountInput):
    expected_version: int = Field(ge=1)


class TemplateInput(Command):
    code: Annotated[str, Field(pattern=r"^[a-z0-9_-]{1,80}$")]
    name: Annotated[str, Field(min_length=1, max_length=120)]
    channel: Channel
    module: Literal["ruolo"] = "ruolo"
    subject: Short
    body: Annotated[str, Field(min_length=1, max_length=20000)]


class MessageCreate(Command):
    source_entity_id: UUID
    channel: Channel
    account_id: UUID | None = None
    recipient: str
    subject: Short | None = None
    body: Annotated[str, Field(min_length=1, max_length=20000)] | None = None
    template_id: UUID | None = None
    purpose: Literal["courtesy", "pec_notice"] = "courtesy"

    _recipient = field_validator("recipient")(address)


class VersionCommand(Command):
    expected_version: int = Field(ge=1)


class MessageChange(VersionCommand):
    account_id: UUID
    recipient: str
    subject: Short
    body: Annotated[str, Field(min_length=1, max_length=20000)]

    _recipient = field_validator("recipient")(address)


CHECKS = (
    "identity",
    "address",
    "complete_pdf",
    "notice_year",
    "amounts",
    "text",
    "attachments",
    "account",
)


class Approval(VersionCommand):
    checklist: dict[str, bool]
    confirmed: Literal[True]

    @field_validator("checklist")
    @classmethod
    def complete(cls, value):
        if set(value) != set(CHECKS) or not all(value.values()):
            raise ValueError("Confermare tutti gli otto controlli")
        return value


class Rendered(VersionCommand):
    review_id: UUID
    pages: int = Field(ge=1, le=200)
    sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class Pause(Command):
    paused: bool


class CandidateFilters(Command):
    channel: Channel
    year: int = Field(2021, ge=2021, le=2021)
    q: str | None = Field(None, max_length=250)
    batch_id: UUID | None = None
    has_contact: bool | None = None
    has_pec: bool | None = None
    has_email: bool | None = None
    state: str | None = None
    document_state: str | None = None
    payment_state: str | None = None
    notification_state: str | None = None
    account_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=100)
