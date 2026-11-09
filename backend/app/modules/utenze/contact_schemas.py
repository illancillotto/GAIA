"""Classification requires an explicit channel and evidence, never a domain guess."""

from typing import Literal

from email_validator import validate_email
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def normalize_address(value: str) -> str:
    return validate_email(value.strip(), check_deliverability=False).normalized.lower()


class ContactClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: str = Field(max_length=254)
    channel: Literal["pec", "email", "unclassified"]
    state: Literal["active", "review", "revoked"]
    source: str = Field(min_length=1, max_length=80)
    evidence_reference: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=0)

    _address = field_validator("address")(normalize_address)

    @field_validator("source", "evidence_reference")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Provenienza e riferimento obbligatori")
        return value.strip()

    @model_validator(mode="after")
    def classified_if_active(self):
        if self.channel == "unclassified" and self.state == "active":
            raise ValueError("Un recapito non classificato richiede revisione")
        return self
