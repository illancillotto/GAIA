"""Daily edit and meal voucher contracts, re-exported by the Presenze schema facade."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PresenzeDailyRecordMealVoucherFields(BaseModel):
    meal_voucher_manual: bool = False
    meal_voucher_automatic: bool = False
    meal_voucher_count: Literal[0, 1] = 0
    meal_voucher_sources: list[Literal["automatic", "manual"]] = Field(default_factory=list)
    meal_voucher_audit: list[dict] | None = None


class PresenzeDailyRecordManualUpdate(BaseModel):
    meal_voucher_manual: bool = False
    km_value: int | None = Field(default=None, ge=0, le=5000)
    trasferta_minutes: int | None = Field(default=None, ge=0, le=1440)
    trasferta_montano: bool | None = None
    reperibilita_unit: Literal["none", "hours", "days", "shifts"] | None = None
    reperibilita_quantity: int | None = Field(default=None, ge=0, le=24)
    override_straordinario_minutes: int | None = Field(default=None, ge=0, le=1440)
    override_mpe_minutes: int | None = Field(default=None, ge=0, le=1440)
    manual_note: str | None = Field(default=None, max_length=1000)
    validation_status: Literal["pending", "validated"] | None = None
    validation_note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_reperibilita(self) -> PresenzeDailyRecordManualUpdate:
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
