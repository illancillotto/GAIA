from datetime import datetime
import re

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, Field, field_validator

LOCAL_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.local$", re.IGNORECASE)


def normalize_email(value: str) -> str:
    candidate = value.strip()
    try:
        return validate_email(candidate, check_deliverability=False).normalized
    except EmailNotValidError as exc:
        if LOCAL_EMAIL_PATTERN.fullmatch(candidate):
            return candidate.lower()
        raise ValueError("Invalid email address") from exc


class ApplicationUserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "viewer"
    is_active: bool = True
    module_accessi: bool = True
    module_rete: bool = False
    module_inventario: bool = False
    module_catasto: bool = False
    module_anagrafica: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")
        return value


class ApplicationUserUpdate(BaseModel):
    email: str | None = None
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None
    module_accessi: bool | None = None
    module_rete: bool | None = None
    module_inventario: bool | None = None
    module_catasto: bool | None = None
    module_anagrafica: bool | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        if value is not None and len(value) < 8:
            raise ValueError("Password must be at least 8 characters")
        return value


class ApplicationUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    is_active: bool
    module_accessi: bool
    module_rete: bool
    module_inventario: bool
    module_catasto: bool
    module_anagrafica: bool
    enabled_modules: list[str]
    created_at: datetime
    updated_at: datetime


class ApplicationUserListResponse(BaseModel):
    items: list[ApplicationUserResponse]
    total: int = Field(ge=0)
