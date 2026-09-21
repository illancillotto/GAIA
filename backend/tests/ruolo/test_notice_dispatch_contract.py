from datetime import UTC, datetime, timedelta
from itertools import product
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.ruolo.notice_dispatch_contract import (
    DispatchEnvelope,
    DispatchSnapshot,
    ProviderProof,
    SubmissionReview,
    advance_dispatch,
    require_poste_submission_adapter,
)


def envelope(**changes):
    return DispatchEnvelope(
        **{
            "document_id": uuid4(),
            "document_version": 1,
            "credential_id": 1,
            "account_sha256": "a" * 64,
            "artifact_sha256": "b" * 64,
            "recipient_sha256": "c" * 64,
            "postal_options_sha256": "d" * 64,
            **changes,
        }
    )


def review(item, **changes):
    return SubmissionReview(
        **{
            "reviewed_envelope_key": item.local_deduplication_key,
            "valid_until": datetime.now(UTC) + timedelta(minutes=1),
            "eligible": True,
            "serialized_with_writers": True,
            "artifact_verified": True,
            "provider_contract_verified": True,
            "operator_approved": True,
            **changes,
        }
    )


def proof(item, **changes):
    return ProviderProof(
        **{
            "envelope_key": item.local_deduplication_key,
            "provider_submission_id": "POSTE-BUSINESS-ID",
            "evidence_reference": "private-evidence-id",
            **changes,
        }
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("document_id", uuid4()),
        ("document_version", 2),
        ("credential_id", 2),
        ("account_sha256", "e" * 64),
        ("artifact_sha256", "e" * 64),
        ("recipient_sha256", "e" * 64),
        ("postal_options_sha256", "e" * 64),
    ],
)
def test_local_identity_pins_every_input(field, value):
    item = envelope()
    assert (
        item.local_deduplication_key
        == DispatchEnvelope.model_validate_json(item.model_dump_json()).local_deduplication_key
    )
    changed = DispatchEnvelope(**(item.model_dump() | {field: value}))
    assert item.local_deduplication_key != changed.local_deduplication_key
    with pytest.raises(ValidationError):
        item.document_version = 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("artifact_sha256", "BAD"),
        ("credential_id", 0),
        ("document_version", 0),
        ("account_sha256", "A" * 64),
        ("unexpected", "token"),
    ],
)
def test_invalid_envelope(field, value):
    with pytest.raises(ValidationError):
        envelope(**{field: value})


@pytest.mark.parametrize(
    "field,reason",
    [
        ("eligible", "not_eligible"),
        ("serialized_with_writers", "concurrent_validation_missing"),
        ("artifact_verified", "artifact_not_verified"),
        ("provider_contract_verified", "poste_contract_missing"),
        ("operator_approved", "operator_approval_missing"),
    ],
)
def test_approval_and_claim_each_require_all_proofs(field, reason):
    item = envelope()
    denied = review(item, **{field: False})
    assert denied.blockers(item) == (reason,)
    for state, event in [("draft", "approve"), ("ready", "start")]:
        with pytest.raises(ValueError, match="Verifica coordinata"):
            advance_dispatch(DispatchSnapshot(envelope=item, state=state), event, review=denied)


def test_missing_stale_or_expired_reviews_and_default_fail_closed():
    item = envelope()
    snapshot = DispatchSnapshot(envelope=item)
    with pytest.raises(ValueError, match="Verifica coordinata"):
        advance_dispatch(snapshot, "approve")
    default = SubmissionReview(
        reviewed_envelope_key=item.local_deduplication_key,
        valid_until=datetime.now(UTC) + timedelta(minutes=1),
    )
    assert len(default.blockers(item)) == 5
    assert review(item, reviewed_envelope_key="0" * 64).blockers(item) == ("envelope_changed",)
    expired = review(item, valid_until=datetime.now(UTC) - timedelta(seconds=1))
    assert expired.blockers(item) == ("review_expired",)
    with pytest.raises(ValidationError):
        review(item, valid_until=datetime.now())
    ready = advance_dispatch(snapshot, "approve", review=review(item))
    with pytest.raises(ValueError):
        advance_dispatch(ready, "start", review=expired)


def test_successful_protocol_never_implies_delivery_or_notification():
    item = envelope()
    draft = DispatchSnapshot(envelope=item)
    ready = advance_dispatch(draft, "approve", review=review(item))
    submitting = advance_dispatch(ready, "start", review=review(item))
    accepted = advance_dispatch(submitting, "accept", proof=proof(item))
    assert [s.state for s in (draft, ready, submitting, accepted)] == [
        "draft",
        "ready",
        "submitting",
        "accepted",
    ]
    assert set(accepted.model_dump()) == {"envelope", "state", "proof"}
    assert DispatchSnapshot.model_validate_json(accepted.model_dump_json()) == accepted
    with pytest.raises(RuntimeError, match="non attivo"):
        require_poste_submission_adapter()


@pytest.mark.parametrize(
    "event,state", [("reconcile_accept", "accepted"), ("reconcile_reject", "rejected")]
)
def test_uncertain_submission_only_resolved_with_scoped_business_evidence(event, state):
    item = envelope()
    submitting = DispatchSnapshot(envelope=item, state="submitting")
    unknown = advance_dispatch(submitting, "uncertain")
    assert unknown.state == "unknown"
    assert advance_dispatch(unknown, event, proof=proof(item)).state == state
    with pytest.raises(ValueError, match="insieme"):
        advance_dispatch(unknown, event)
    with pytest.raises(ValueError, match="altro contenuto"):
        advance_dispatch(unknown, event, proof=proof(envelope()))


def test_rejection_needs_evidence_not_http_code_and_nonfinal_states_reject_proof():
    item = envelope()
    submitting = DispatchSnapshot(envelope=item, state="submitting")
    assert advance_dispatch(submitting, "reject", proof=proof(item)).state == "rejected"
    with pytest.raises(ValueError, match="insieme"):
        advance_dispatch(submitting, "reject")
    with pytest.raises(ValueError, match="insieme"):
        advance_dispatch(submitting, "uncertain", proof=proof(item))
    with pytest.raises(ValidationError):
        proof(item, provider_submission_id=" ")


@pytest.mark.parametrize(
    "state,event,target",
    [
        ("draft", "cancel", "cancelled"),
        ("draft", "invalidate", "blocked"),
        ("ready", "cancel", "cancelled"),
        ("ready", "invalidate", "blocked"),
    ],
)
def test_pre_submission_cancellation_and_invalidation(state, event, target):
    assert (
        advance_dispatch(DispatchSnapshot(envelope=envelope(), state=state), event).state == target
    )


@pytest.mark.parametrize(
    "state,event",
    list(
        product(
            ["submitting", "accepted", "rejected", "unknown", "cancelled", "blocked"],
            ["approve", "start", "cancel", "invalidate"],
        )
    ),
)
def test_no_retry_or_local_cancel_after_external_call(state, event):
    item = envelope()
    snapshot = DispatchSnapshot(
        envelope=item, state=state, proof=proof(item) if state in {"accepted", "rejected"} else None
    )
    with pytest.raises(ValueError, match="nessun reinvio"):
        advance_dispatch(snapshot, event, review=review(item))
