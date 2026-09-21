from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.modules.ruolo.notice_lifecycle_schemas import RecordedAttempt
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeAudit,
    NoticeDocument,
    NoticeEvidence,
    NoticeNotification,
)
from app.modules.ruolo.notice_register_schemas import DocumentDetails, OperatorChange
from app.modules.ruolo.services import notice_attempts as service
from app.modules.ruolo.services import notice_document_eligibility as checks
from app.modules.ruolo.services.notice_register import RegisterConflict, revise_document

from .test_notice_eligibility import eligible_item
from .test_notice_import import api_engine as api_engine
from .test_notice_reconciliation import race_engine as race_engine
from .test_notice_reconciliation import seed_race
from .test_notice_register_api import (
    URL,
    _add_position,
    _create,
    _detail,
    _headers,
    _perfect_notification,
    _request,
)
from .test_notice_register_api import api as api


def attempt_data(**overrides):
    return {
        "channel": "posta",
        "tracking_code": "TRACK-1",
        "sent_at": "2024-06-29T12:00:00+02:00",
        "evidence_reference": "Distinta 42",
        "confirmed": True,
        **overrides,
    }


def test_record_past_attempt_is_audited_atomic_and_stale_retry_does_not_duplicate(api):
    doc = _create(api)
    original = _detail(api, doc)
    request = _request(attempt_data())
    response = api.client.post(f"{URL}/{doc}/invii", json=request)
    assert response.status_code == 201, response.text
    assert response.json()["version"] == 2
    assert api.client.post(f"{URL}/{doc}/invii", json=request).status_code == 409
    assert (
        api.client.post(f"{URL}/{doc}/invii", json=_request(attempt_data(), 2)).status_code == 409
    )
    after = _detail(api, doc)
    assert after["notification_state"] == "da_verificare"
    assert after["original_json"] == original["original_json"]
    assert after["positions"] == []
    attempts = api.client.get(f"{URL}/{doc}/invii").json()
    assert attempts["total"] == 1
    assert attempts["items"][0]["tracking_code"] == "TRACK-1"
    assert attempts["items"][0]["registered_mail_id"] is None
    evidence = api.client.get(f"{URL}/{doc}/evidenze").json()["items"][0]
    assert evidence["attempt_id"] == response.json()["resource_id"]
    assert evidence["original_json"] == attempt_data()
    audit = api.client.get(f"{URL}/{doc}/storico").json()["items"][0]
    assert audit["action"] == "record_attempt" and audit["actor_id"] == 1
    assert audit["reason"] == request["reason"]


@pytest.mark.parametrize("channel", ["posta", "pec", "messo", "altro"])
def test_duplicate_detection_includes_imported_postal_attempts(api, channel):
    doc = _create(api)
    with api.session() as db:
        db.add(
            NoticeAttempt(
                document_id=UUID(doc),
                source_system="poste_db",
                source_key=str(uuid4()),
                channel="raccomandata" if channel == "posta" else channel,
                tracking_code="TRACK-1",
            )
        )
        db.commit()
    assert (
        api.client.post(
            f"{URL}/{doc}/invii", json=_request(attempt_data(channel=channel))
        ).status_code
        == 409
    )
    assert _detail(api, doc)["version"] == 1


def test_record_missing_notification_and_rollback_after_audit(api, monkeypatch):
    doc = _create(api)
    with api.session() as db:
        db.execute(delete(NoticeNotification).where(NoticeNotification.document_id == UUID(doc)))
        db.commit()
    original_audit = service._audit

    def fail(*args):
        original_audit(*args)
        raise ValueError("Interruzione simulata")

    with monkeypatch.context() as patch:
        patch.setattr(service, "_audit", fail)
        assert (
            api.client.post(f"{URL}/{doc}/invii", json=_request(attempt_data())).status_code == 422
        )
    with api.session() as db:
        assert db.scalar(select(NoticeAttempt)) is None
        assert db.scalar(select(NoticeEvidence)) is None
        assert db.get(NoticeNotification, UUID(doc)) is None
        assert db.get(NoticeDocument, UUID(doc)).version == 1
    assert (
        api.client.post(
            f"{URL}/{doc}/invii", json=_request(attempt_data(tracking_code=None))
        ).status_code
        == 201
    )
    assert _detail(api, doc)["notification_state"] == "da_verificare"


def test_record_attempt_preserves_previous_notification_in_audit_and_deduplicates_undated_tracking(
    api,
):
    doc = _create(api)
    proof = _perfect_notification(api, doc)
    response = api.client.post(
        f"{URL}/{doc}/invii", json=_request(attempt_data(tracking_code=None), 3)
    )
    assert response.status_code == 201
    audit = api.client.get(f"{URL}/{doc}/storico").json()["items"][0]
    assert audit["before_json"]["notification"]["evidence_id"] == proof
    assert audit["before_json"]["notification"]["state"] == "perfezionata"
    assert (
        api.client.post(
            f"{URL}/{doc}/invii", json=_request(attempt_data(tracking_code=None), 4)
        ).status_code
        == 409
    )
    assert api.client.get(f"{URL}/{doc}/evidenze").json()["total"] == 2


@pytest.mark.parametrize(
    "changes",
    [
        {"confirmed": False},
        {"sent_at": "2024-06-29T12:00:00"},
        {"sent_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()},
        {"channel": "automatic"},
        {"evidence_reference": " "},
        {"tracking_code": " "},
        {"source_system": "poste_db"},
        {"actor_id": 2},
    ],
)
def test_invalid_or_future_declarations_are_rejected(api, changes):
    doc = _create(api)
    assert (
        api.client.post(f"{URL}/{doc}/invii", json=_request(attempt_data(**changes))).status_code
        == 422
    )
    assert _detail(api, doc)["version"] == 1


@pytest.mark.parametrize("user, status", [(2, 403), (3, 403), (4, 401), (5, 403)])
def test_attempt_permissions_are_server_enforced(api, user, status):
    doc = _create(api)
    assert (
        api.client.post(
            f"{URL}/{doc}/invii", headers=_headers(user), json=_request(attempt_data())
        ).status_code
        == status
    )
    assert api.client.get(f"{URL}/{doc}/ammissibilita", headers=_headers(user)).status_code == (
        200 if user == 2 else status
    )


def test_missing_reconciled_and_unauthenticated_documents(api):
    assert api.client.get(f"{URL}/{uuid4()}/ammissibilita").status_code == 404
    assert (
        api.client.post(f"{URL}/{uuid4()}/invii", json=_request(attempt_data())).status_code == 404
    )
    doc, target = _create(api), _create(api)
    with api.session() as db:
        db.get(NoticeDocument, UUID(doc)).reconciled_into_id = UUID(target)
        db.commit()
    assert (
        api.client.post(f"{URL}/{doc}/invii", json=_request(attempt_data(), 2)).status_code == 409
    )
    assert (
        "documento_riconciliato" in api.client.get(f"{URL}/{doc}/ammissibilita").json()["reasons"]
    )
    api.client.headers.clear()
    assert api.client.get(f"{URL}/{doc}/ammissibilita").status_code == 401
    assert api.client.post(f"{URL}/{doc}/invii", json=_request(attempt_data())).status_code == 401


def test_diagnostic_empty_unlinked_and_missing_avviso_is_read_only(api, monkeypatch):
    doc = _create(api)
    result = api.client.get(f"{URL}/{doc}/ammissibilita").json()
    assert result["reasons"] == ["posizioni_assenti"]
    assert result["authorizes_dispatch"] is False
    _add_position(api, doc)
    result = api.client.get(f"{URL}/{doc}/ammissibilita").json()
    assert result["positions"][0]["reasons"] == ["collegamenti_mancanti"]
    assert result["version"] == _detail(api, doc)["version"]
    item, linked_doc = eligible_item(api)
    monkeypatch.setattr(checks.tributi_repositories, "get_tributi_avviso", lambda *_: None)
    result = api.client.get(f"{URL}/{linked_doc}/ammissibilita").json()
    assert result["reasons"] == ["collegamenti_mancanti"]
    assert result["eligible"] is False
    assert item["avviso"].id


def test_diagnostic_reloads_history_and_never_authorizes_dispatch(api, monkeypatch):
    item, doc = eligible_item(api)
    item["reminder_enabled"] = True
    monkeypatch.setattr(checks.tributi_repositories, "get_tributi_avviso", lambda *_: item)
    result = api.client.get(f"{URL}/{doc}/ammissibilita").json()
    assert result["eligible"] is True and result["authorizes_dispatch"] is False
    assert result["reasons"] == [] and len(result["positions"]) == 2
    item["reminder_enabled"] = False
    assert (
        "generazione_non_abilitata"
        in api.client.get(f"{URL}/{doc}/ammissibilita").json()["reasons"]
    )
    assert (
        api.client.post(
            f"{URL}/{doc}/invii", json=_request(attempt_data(), result["version"])
        ).status_code
        == 201
    )
    result = api.client.get(f"{URL}/{doc}/ammissibilita").json()
    assert result["eligible"] is False
    assert {"notifica_da_verificare", "invii_non_chiariti"} <= set(result["reasons"])


@pytest.mark.parametrize("other", ["attempt", "edit"])
def test_concurrent_attempts_and_edits_are_serialized(race_engine, other):
    _, doc, *_ = seed_race(race_engine)
    barrier = Barrier(2)
    change = OperatorChange(actor_id=1, expected_version=1, reason="Test concorrente")

    def execute(index):
        with Session(race_engine) as db:
            barrier.wait(timeout=10)
            try:
                if other == "attempt" or index == 0:
                    service.record_attempt(db, doc, RecordedAttempt(**attempt_data()), change)
                else:
                    revise_document(db, doc, DocumentDetails(document_number="Correzione"), change)
                db.commit()
                return "saved"
            except RegisterConflict:
                db.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(execute, range(2))) == ["conflict", "saved"]
    with Session(race_engine) as db:
        assert db.get(NoticeDocument, doc).version == 2
        assert (
            db.scalar(
                select(func.count())
                .select_from(NoticeAudit)
                .where(NoticeAudit.document_id == doc, NoticeAudit.version == 2)
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(NoticeAttempt)
                .where(NoticeAttempt.document_id == doc)
            )
            <= 1
        )
