"""Confirmation transaction tests; PostgreSQL contention needs separate validation."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.modules.ruolo.services import notice_draft_review as service
from app.modules.ruolo.services.tributi_notice_registry import build_notice_identity_key


@pytest.fixture
def context(monkeypatch):
    basis = service.GenerationRevision(uuid4(), 4)
    payload = {
        "codice_fiscale": "RSSMRA80A01H501Z",
        "avvisi": [{"id": str(uuid4())}],
        "notice_emission_year": 2026,
        "notice_reference_years": [2022, 2023],
        "notice_number": "12026222300001",
    }
    payload["notice_identity_key"] = build_notice_identity_key(
        payload, emission_year=2026, reference_years=[2022, 2023]
    )
    record = SimpleNamespace(payload_json=payload, notice_number_id=uuid4(), status="draft")
    reservation = SimpleNamespace(
        identity_key=payload["notice_identity_key"],
        notice_number=payload["notice_number"],
        status="draft",
    )
    draft = SimpleNamespace(
        input_basis={
            "epoch": str(basis.epoch),
            "revision": 4,
            "calculation_date": date.today().isoformat(),
        }
    )
    parent = SimpleNamespace(status="review_required")
    db = Mock(new=[], dirty=[], deleted=[])
    db.scalar.return_value = None
    db.get.side_effect = lambda model, *args, **kwargs: (
        reservation if model is service.RuoloTributiNoticeNumber else parent
    )
    monkeypatch.setattr(service, "read_revision", Mock(return_value=basis))
    monkeypatch.setattr(service, "lock_revision", Mock())
    monkeypatch.setattr(service, "_records", Mock(return_value=[record]))
    monkeypatch.setattr(service, "_drafts", Mock(return_value=[draft]))
    monkeypatch.setattr(service, "_check_review_size", Mock())
    monkeypatch.setattr(service, "_basis", Mock(return_value=basis))
    monkeypatch.setattr(service, "_integrity", Mock(return_value="a" * 64))
    return db, record, reservation, draft, parent


def test_confirmation_persists_snapshot_and_promotes_number(context):
    db, record, number, draft, parent = context
    result = service.confirm_generation(db, uuid4(), batch=True, actor_id=1)
    assert result.input_basis == draft.input_basis
    assert result.identity_keys == [number.identity_key]
    assert result.notice_numbers == [number.notice_number]
    assert record.status == parent.status == number.status == "confirmed"
    db.add.assert_called_once_with(result)
    db.commit.assert_not_called()


def test_repeat_checks_revision_before_returning_existing_confirmation(context):
    db, _, _, draft, _ = context
    existing = SimpleNamespace(input_basis=draft.input_basis)
    db.scalar.return_value = existing
    assert service.confirm_generation(db, uuid4(), batch=True, actor_id=1) is existing
    assert service.lock_revision.call_count == 2
    db.add.assert_not_called()


@pytest.mark.parametrize(
    "fault", ["missing", "mismatch", "incomplete", "number", "issued", "pending"]
)
def test_invalid_identity_number_or_transaction_is_refused(context, fault):
    db, record, number, _, _ = context
    if fault == "missing":
        record.payload_json.pop("notice_identity_key")
    elif fault == "mismatch":
        record.payload_json["notice_identity_key"] = "f" * 64
    elif fault == "incomplete":
        record.payload_json.pop("avvisi")
    elif fault == "number":
        number.notice_number = "different"
    elif fault == "issued":
        number.status = "confirmed"
    else:
        db.new = [object()]
    with pytest.raises(service.DraftReviewBlocked):
        service.confirm_generation(db, uuid4(), batch=True, actor_id=1)
    db.add.assert_not_called()


def test_revision_or_integrity_failure_prevents_persistence(context):
    db, _, _, _, _ = context
    service._integrity.side_effect = service.DraftReviewBlocked("Artefatto modificato")
    with pytest.raises(service.DraftReviewBlocked, match="Artefatto"):
        service.confirm_generation(db, uuid4(), batch=True, actor_id=1)
    db.add.assert_not_called()


@pytest.mark.parametrize("fault", ["no_link", "no_row", "duplicate", "old_date"])
def test_confirmation_boundary_failures(context, fault):
    db, record, _, draft, _ = context
    if fault == "no_link":
        record.notice_number_id = None
    elif fault == "no_row":
        db.get.side_effect = None
        db.get.return_value = None
    elif fault == "duplicate":
        service._records.return_value = [record, record]
    else:
        db.scalar.return_value = SimpleNamespace(input_basis={**draft.input_basis, "calculation_date": "2000-01-01"})
    with pytest.raises(service.DraftReviewBlocked):
        service.confirm_generation(db, uuid4(), batch=True, actor_id=1)
    db.add.assert_not_called()


def test_single_record_internal_path(context):
    db, record, _, _, _ = context
    result = service.confirm_generation(db, uuid4(), batch=False, actor_id=1)
    assert result.generation_kind == "reminder"
    assert record.status == "confirmed"


def test_empty_legacy_number_not_listed(context):
    db, record, number, _, _ = context
    record.payload_json["notice_number"] = number.notice_number = ""
    result = service.confirm_generation(db, uuid4(), batch=True, actor_id=1)
    assert result.notice_numbers == []
