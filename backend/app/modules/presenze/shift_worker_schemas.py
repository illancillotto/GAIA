"""Explicit type and bounded or ongoing validity for a shift worker assignment."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, model_validator

ShiftWorkerType = Literal["none", "acquaiolo", "telecontrollo"]


class ShiftWorkerAssignmentRequest(BaseModel):
    shift_worker_type: ShiftWorkerType
    date_from: date
    date_to: date | None

    @model_validator(mode="after")
    def validate_dates(self):
        validate_shift_assignment_range(self.date_from, self.date_to)
        return self


class GateShiftWorkerAssignmentRequest(ShiftWorkerAssignmentRequest):
    gate_shift_requested_at: datetime

    @model_validator(mode="after")
    def validate_timestamp(self):
        if self.gate_shift_requested_at.tzinfo is None:
            raise ValueError("gate_shift_requested_at richiede il fuso orario")
        return self


class ShiftWorkerFields(BaseModel):
    shift_calendar: list[bool] | None = None
    shift_ccnl: dict | None = None
    shift_covered_absence_minutes: int = 0
    shift_worker_type: ShiftWorkerType = "none"
    shift_worker_source: Literal["gate", "gaia"] | None = None
    shift_rules_version: str = "shift-v1"


def validate_shift_assignment_range(date_from: date, date_to: date | None) -> None:
    """An explicit null end means ongoing; bounded edits retain their monthly scope."""
    if date_to is None:
        return
    if date_from > date_to:
        raise ValueError("La data iniziale deve precedere quella finale")
    if (date_from.year, date_from.month) != (date_to.year, date_to.month):
        raise ValueError("Selezionare un intervallo nello stesso mese")
