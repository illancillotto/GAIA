"""Validated daily edit contract shared by both GATE transports."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, StrictBool, model_validator

from app.modules.presenze.shift_worker_schemas import GateShiftWorkerAssignmentRequest


class GatePresenzeDailyRecordPatchRequest(BaseModel):
    shift_worker_type: Literal["none", "acquaiolo", "telecontrollo", "tecnico_turnista"] | None = None
    date_from: date | None = None
    date_to: date | None = None
    gate_shift_requested_at: datetime | None = None
    gate_shift_command_id: str | None = Field(default=None, max_length=120)
    meal_voucher_manual: StrictBool = False
    km_value: int | None = Field(default=None, ge=0, le=5000)
    trasferta_minutes: int | None = Field(default=None, ge=0, le=1440)
    trasferta_montano: bool | None = None
    reperibilita_unit: Literal["none", "hours", "days", "shifts"] | None = None
    reperibilita_quantity: int | None = Field(default=None, ge=0, le=24)
    override_straordinario_minutes: int | None = Field(default=None, ge=0, le=1440)
    override_mpe_minutes: int | None = Field(default=None, ge=0, le=1440)
    manual_note: str | None = Field(default=None, max_length=1000)
    operator_note: str | None = Field(default=None, max_length=1000)
    client_request_id: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_shift_assignment(self):
        assignment_fields = {
            "shift_worker_type",
            "date_from",
            "date_to",
            "gate_shift_requested_at",
            "gate_shift_command_id",
        }
        present = self.model_fields_set & assignment_fields
        if not present:
            return self
        if present != assignment_fields:
            raise ValueError(
                "Assegnazione turnista incompleta: tipo, date, timestamp e command_id richiesti"
            )
        if self.model_fields_set - assignment_fields - {"operator_note", "client_request_id"}:
            raise ValueError("Inviare l'assegnazione turnista separatamente dalle altre modifiche")
        GateShiftWorkerAssignmentRequest.model_validate(self.model_dump())
        if not self.gate_shift_command_id:
            raise ValueError("gate_shift_command_id richiesto")
        return self

    @model_validator(mode="after")
    def validate_reperibilita(self) -> GatePresenzeDailyRecordPatchRequest:
        if self.reperibilita_unit is None and self.reperibilita_quantity is None:
            return self
        unit = self.reperibilita_unit or "none"
        quantity = self.reperibilita_quantity
        if unit == "none":
            if quantity not in (None, 0):
                raise ValueError(
                    "reperibilita_quantity must be empty when reperibilita_unit is 'none'"
                )
            self.reperibilita_quantity = None
            return self
        if quantity is None or quantity <= 0:
            raise ValueError(
                "reperibilita_quantity must be greater than zero when reperibilita is set"
            )
        return self
