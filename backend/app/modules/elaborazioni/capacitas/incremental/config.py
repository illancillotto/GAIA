"""Independent settings: importing the legacy worker never enables this pipeline."""

from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class IncrementalSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INCASS_INCREMENTAL_", extra="ignore")

    mode: Literal["off", "shadow", "active"] = "off"
    hour: int = Field(default=7, ge=0, le=23)
    credential_id: int | None = None
    root: Path = Path("/runtime-data/incass-incremental")
    missing_fraction: float = Field(default=0.05, ge=0, lt=1)
    retry_seconds: int = Field(default=3600, ge=60)
    max_attempts: int = Field(default=3, ge=1, le=10)
    max_jobs: int = Field(default=100, ge=1)
    sample_size: int = Field(default=0, ge=0)
    full_audit_days: int = Field(default=0, ge=0)
    # Explicit live-schema review is required before active dispatch.
    schema_verified: bool = False
    coverage_verified: bool = False
    min_shadow_cycles: int = Field(default=7, ge=2)
    allow_new: bool = False
    bootstrap_keys: set[str] = Field(default_factory=set)
    header_map: dict[str, str] = Field(default_factory=dict)
    empty_years: set[str] = Field(default_factory=set)

    @model_validator(mode="after")
    def validate_mode(self):
        if len(self.bootstrap_keys) > self.max_jobs:
            raise ValueError("bootstrap_keys exceeds max_jobs")
        if self.mode != "off" and self.credential_id is None:
            raise ValueError("incremental requires a dedicated credential_id")
        if self.mode == "active" and not (
            self.schema_verified
            and self.coverage_verified
            and self.sample_size
            and self.full_audit_days
        ):
            raise ValueError(
                "active requires verified schema/coverage, sample_size and full_audit_days"
            )
        return self

    def slot(self, now: datetime) -> datetime:
        local = now.astimezone(ZoneInfo("Europe/Rome"))
        slot = datetime.combine(local.date(), time(self.hour), tzinfo=local.tzinfo)
        return slot if slot <= local else slot - timedelta(days=1)
