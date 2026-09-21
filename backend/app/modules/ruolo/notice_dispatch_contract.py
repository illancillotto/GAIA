"""Pure outbound protocol for the future Poste outbox, not a sending service.

No routes or worker execute this protocol yet. Persistence, serialized approval
and the provider adapter are mandatory before production submission is possible.
"""

from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Reference = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
DispatchState = Literal[
    "draft", "ready", "submitting", "accepted", "rejected", "unknown", "cancelled", "blocked"
]
DispatchEvent = Literal[
    "approve",
    "invalidate",
    "cancel",
    "start",
    "accept",
    "reject",
    "uncertain",
    "reconcile_accept",
    "reconcile_reject",
]


class DispatchEnvelope(BaseModel):
    """Pin exact bytes, recipient/options and account; do not embed personal data."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: UUID
    document_version: int = Field(ge=1)
    credential_id: int = Field(gt=0)
    account_sha256: Digest
    artifact_sha256: Digest
    recipient_sha256: Digest
    postal_options_sha256: Digest

    @property
    def local_deduplication_key(self) -> str:
        # Local identity only: never assume Poste supports an idempotency header.
        return sha256(self.model_dump_json().encode("utf-8")).hexdigest()


class SubmissionReview(BaseModel):
    """Server-side proofs to be issued by the future serialized approval service.

    This is not an API request schema. The consultative eligibility GET cannot
    supply these proofs. Their truth must be re-established at worker claim.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    reviewed_envelope_key: Digest
    valid_until: AwareDatetime
    eligible: bool = False
    serialized_with_writers: bool = False
    artifact_verified: bool = False
    provider_contract_verified: bool = False
    operator_approved: bool = False

    def blockers(self, envelope: DispatchEnvelope) -> tuple[str, ...]:
        checks = {
            "envelope_changed": self.reviewed_envelope_key == envelope.local_deduplication_key,
            "review_expired": self.valid_until > datetime.now(UTC),
            "not_eligible": self.eligible,
            "concurrent_validation_missing": self.serialized_with_writers,
            "artifact_not_verified": self.artifact_verified,
            "poste_contract_missing": self.provider_contract_verified,
            "operator_approval_missing": self.operator_approved,
        }
        return tuple(reason for reason, satisfied in checks.items() if not satisfied)


class ProviderProof(BaseModel):
    """An authoritative business receipt, not an HTTP 200 or a tracking guess."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    envelope_key: Digest
    provider_submission_id: Reference
    evidence_reference: Reference


class DispatchSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    envelope: DispatchEnvelope
    state: DispatchState = "draft"
    proof: ProviderProof | None = None

    @model_validator(mode="after")
    def receipt_scope(self):
        if (self.state in {"accepted", "rejected"}) != (self.proof is not None):
            raise ValueError("Esito definitivo e ricevuta devono essere presenti insieme")
        if self.proof and self.proof.envelope_key != self.envelope.local_deduplication_key:
            raise ValueError("Ricevuta appartenente a un altro contenuto o account")
        return self


_TRANSITIONS = {
    ("draft", "approve"): "ready",
    ("draft", "cancel"): "cancelled",
    ("draft", "invalidate"): "blocked",
    ("ready", "invalidate"): "blocked",
    ("ready", "cancel"): "cancelled",
    ("ready", "start"): "submitting",
    ("submitting", "accept"): "accepted",
    ("submitting", "reject"): "rejected",
    ("submitting", "uncertain"): "unknown",
    ("unknown", "reconcile_accept"): "accepted",
    ("unknown", "reconcile_reject"): "rejected",
}


def advance_dispatch(
    snapshot: DispatchSnapshot,
    event: DispatchEvent,
    *,
    review: SubmissionReview | None = None,
    proof: ProviderProof | None = None,
) -> DispatchSnapshot:
    """Calculate a transition. Caller must atomically persist it and its audit.

    Persist submitting BEFORE external I/O; an abandoned submitting claim goes
    to unknown, never back to ready. Acceptance is not legal notification.
    """
    target = _TRANSITIONS.get((snapshot.state, event))
    if target is None:
        raise ValueError("Transizione di spedizione non ammessa; nessun reinvio automatico")
    if event in {"approve", "start"}:
        if review is None or review.blockers(snapshot.envelope):
            raise ValueError("Verifica coordinata e approvazione server mancanti o obsolete")
    return DispatchSnapshot(envelope=snapshot.envelope, state=target, proof=proof)


def require_poste_submission_adapter() -> None:
    """Fail closed, independent of env/config, until a verified adapter exists."""
    raise RuntimeError(
        "Invio automatico Poste non attivo: endpoint, outbox persistente e "
        "protocollo concorrente da implementare e collaudare"
    )
