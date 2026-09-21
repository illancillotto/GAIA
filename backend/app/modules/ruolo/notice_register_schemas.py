"""Validated domain commands for manual register operations."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Reference = Annotated[NonBlank, Field(max_length=100)]
NotificationState = Literal[
    "nessuna_evidenza",
    "invio_in_corso",
    "tentativo_senza_notifica",
    "perfezionata",
    "da_verificare",
]
RecoveryState = Literal[
    "da_verificare",
    "non_affidato_verificato",
    "affidato",
    "revocato",
    "chiuso",
]


class RegisterCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OperatorChange(RegisterCommand):
    actor_id: int = Field(gt=0)
    reason: NonBlank
    expected_version: int = Field(ge=1)


class PositionInput(RegisterCommand):
    source_namespace: Annotated[NonBlank, Field(max_length=40)]
    source_reference: Reference
    tax_year: int = Field(ge=1900, le=9999)


class DocumentDetails(RegisterCommand):
    document_number: Reference
    tax_code: Annotated[NonBlank, Field(max_length=20)] | None = None
    issued_on: date | None = None


class HistoricalDocument(DocumentDetails):
    positions: list[PositionInput] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def unique_positions(self) -> "HistoricalDocument":
        keys = {(p.source_namespace, p.source_reference, p.tax_year) for p in self.positions}
        if len(keys) != len(self.positions):
            raise ValueError("Riferimenti annuali duplicati")
        return self


class EvidenceInput(RegisterCommand):
    source_system: Annotated[NonBlank, Field(max_length=40)]
    source_key: Annotated[NonBlank, Field(max_length=200)]
    kind: Annotated[NonBlank, Field(max_length=60)]
    reference: NonBlank
    occurred_on: date | None = None
    attempt_id: UUID | None = None
    original_json: dict = Field(default_factory=dict)


class NotificationDecision(RegisterCommand):
    state: NotificationState
    notified_on: date | None = None
    evidence_id: UUID | None = None

    @model_validator(mode="after")
    def notification_proof(self) -> "NotificationDecision":
        if self.state == "perfezionata":
            if self.notified_on is None or self.evidence_id is None:
                raise ValueError("Notifica perfezionata: data ed evidenza obbligatorie")
            if self.notified_on > date.today():
                raise ValueError("La notifica non puo essere futura")
        elif self.notified_on is not None:
            raise ValueError("Data notifica ammessa solo per notifica perfezionata")
        return self


class RecoveryDecision(RegisterCommand):
    state: RecoveryState
    case_reference: Annotated[NonBlank, Field(max_length=200)] | None = None
    verified_on: date | None = None
    evidence_reference: NonBlank | None = None
    amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)

    @model_validator(mode="after")
    def recovery_proof(self) -> "RecoveryDecision":
        if self.state != "da_verificare":
            if self.verified_on is None or self.evidence_reference is None:
                raise ValueError("Verifica STEP: data ed evidenza obbligatorie")
            if self.verified_on > date.today():
                raise ValueError("La verifica STEP non puo essere futura")
        if self.state in {"affidato", "revocato", "chiuso"} and self.case_reference is None:
            raise ValueError("Riferimento pratica STEP obbligatorio")
        return self
