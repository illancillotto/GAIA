"""Explicit accounting approval of a frozen position, never a dispatch command."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Reference = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Checksum = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class CampaignApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_sha256: Checksum
    row_number: int = Field(ge=2, le=10000)
    amount_source: Literal["excel", "gaia"]
    notification_fee: Literal["0.00", "11.55"]
    channel: Literal["nessuno", "pec", "raccomandata"]
    fee_evidence: Reference
    reason: Reference
    resolutions: dict[str, Reference] = Field(default_factory=dict)
    confirmed: Literal[True]
