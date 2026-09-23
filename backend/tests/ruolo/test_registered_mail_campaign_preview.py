from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloTributiRegisteredMail
from app.modules.ruolo.notice_register_models import NoticeAttempt, NoticeDocument, NoticePosition
from app.modules.ruolo.services import registered_mail_campaign_preview as service

from .test_notice_import import _metadata
from .test_notice_import import api as api_fixture  # noqa: F401
from .test_notice_import import api_engine as api_engine
from .test_notice_register import _avviso
from .test_notice_register_api import _headers

CUTOFF = datetime(2026, 9, 24, tzinfo=UTC)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    _metadata().create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def pair(db, subject=None):
    subject = subject or uuid4()
    notices = [_avviso(db, year) for year in (2022, 2023)]
    for notice in notices:
        notice.subject_id = subject
    db.flush()
    return notices


def mail(db, **kwargs):
    record = RuoloTributiRegisteredMail(
        source_shipment_id=str(uuid4()),
        created_at=datetime(2026, 9, 23, tzinfo=UTC),
        **kwargs,
    )
    db.add(record)
    db.flush()
    return record


def preview(db):
    return service.preview_campaign(db, created_before=CUTOFF)


def register(db, record, notices, *, source="manual", extra=None):
    document = NoticeDocument(
        source_system=source,
        source_key=str(uuid4()),
        document_number="Cumulative",
        original_json={},
    )
    db.add(document)
    db.flush()
    db.add(
        NoticeAttempt(
            document_id=document.id,
            source_system="poste_db",
            source_key=str(record.id),
            registered_mail_id=record.id,
            channel="posta",
        )
    )
    for notice in notices:
        db.add(
            NoticePosition(
                document_id=document.id,
                source_namespace="gaia",
                source_reference=str(notice.id),
                tax_year=notice.anno_tributario,
                avviso_id=notice.id,
            )
        )
    if extra:
        db.add(NoticePosition(document_id=document.id, source_namespace="incass", **extra))
    db.flush()
    return document


def test_pairs_include_existing_links_all_statuses_and_no_writes(db):
    notices = pair(db)
    linked = mail(
        db, avviso_id=notices[0].id, subject_id=notices[0].subject_id, match_status="matched"
    )
    suggested = mail(
        db,
        match_status="ambiguous",
        raw_payload_json={"candidate_avviso_ids": [str(notices[1].id), "invalid", None]},
    )
    db.commit()
    statements = []
    event.listen(db.bind, "before_cursor_execute", lambda c, u, s, p, x, m: statements.append(s))
    result = preview(db)
    assert result["counts"] == {"extend_single_link": 1, "proposed_pair": 1}
    items = {item["mail_id"]: item for item in result["items"]}
    assert items[str(linked.id)]["legacy_avviso_id"] == str(notices[0].id)
    assert items[str(suggested.id)]["candidate_notices"] == [service._notice(n) for n in notices]
    assert all(item["requires_operator_confirmation"] for item in result["items"])
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    assert not db.new and not db.dirty and not db.deleted
    assert linked.avviso_id == notices[0].id


def test_scope_is_explicit_cutoff_and_source_not_annualita_json(db):
    notices = pair(db)
    included = mail(db, subject_id=notices[0].subject_id, annualita_json=[2024, 2025])
    future = mail(db)
    future.created_at = CUTOFF
    mail(db, source_system="other")
    db.flush()
    result = preview(db)
    assert [item["mail_id"] for item in result["items"]] == [str(included.id)]
    assert result["expected_years"] == [2022, 2023]
    assert result["read_only"] is True


@pytest.mark.parametrize("payload", [None, {}, {"candidate_avviso_ids": "not-a-list"}])
def test_missing_identity_never_inferred_from_name(db, payload):
    notices = pair(db)
    notices[0].nominativo_raw = notices[1].nominativo_raw = "Same Name"
    mail(db, recipient_name="Same Name", raw_payload_json=payload)
    item = preview(db)["items"][0]
    assert item["classification"] == "review_required"
    assert item["reasons"] == ["identity_unresolved"]
    assert item["candidate_notices"] == []


def test_conflicting_unknown_and_out_of_campaign_hints(db):
    a, b = pair(db)
    b.subject_id = uuid4()
    c = _avviso(db, 2025)
    mail(
        db,
        subject_id=a.subject_id,
        raw_payload_json={"candidate_avviso_ids": [str(b.id), str(c.id)]},
    )
    reasons = preview(db)["items"][0]["reasons"]
    assert reasons == ["conflicting_subjects", "missing_or_out_of_campaign_hint"]


def test_unmapped_notice_and_manual_unlink_remain_review(db):
    notice = _avviso(db)
    mail(
        db,
        avviso_id=notice.id,
        raw_payload_json={"manual_association": {"active": True, "avviso_id": None}},
    )
    item = preview(db)["items"][0]
    assert item["reasons"] == ["identity_unresolved", "manual_unlinked"]


def test_incomplete_and_duplicate_years(db):
    a, b = pair(db)
    b.subject_id = uuid4()
    mail(db, avviso_id=a.id)
    assert preview(db)["items"][0]["classification"] == "incomplete"
    b.subject_id = a.subject_id
    duplicate = _avviso(db)
    duplicate.subject_id = a.subject_id
    db.flush()
    assert preview(db)["items"][0]["classification"] == "ambiguous"


def test_subject_without_notices_is_incomplete(db):
    mail(db, subject_id=uuid4())
    assert preview(db)["items"][0]["classification"] == "incomplete"


def test_registry_complete_and_empty_provisional(db):
    notices = pair(db)
    first = mail(db, avviso_id=notices[0].id)
    second = mail(db, subject_id=notices[0].subject_id)
    document = register(db, first, notices)
    register(db, second, [], source="poste_db")
    items = {item["mail_id"]: item for item in preview(db)["items"]}
    assert items[str(first.id)]["classification"] == "already_registered"
    assert items[str(first.id)]["register_document_id"] == str(document.id)
    assert items[str(second.id)]["classification"] == "proposed_pair"


@pytest.mark.parametrize("kind", ["single", "extra", "unlinked", "archived", "empty", "identity"])
def test_existing_registry_is_never_silently_replaced(db, kind):
    notices = pair(db)
    record = mail(db, subject_id=notices[0].subject_id)
    linked = notices[:1] if kind == "single" else notices
    if kind == "empty":
        linked = []
    extra = {"tax_year": 2024, "source_reference": "extra"} if kind == "extra" else None
    document = register(db, record, linked, extra=extra)
    if kind == "unlinked":
        db.scalar(
            select(NoticePosition).where(NoticePosition.document_id == document.id)
        ).avviso_id = None
    if kind == "archived":
        document.reconciled_into_id = uuid4()
    if kind == "identity":
        record.subject_id = None
    db.flush()
    item = preview(db)["items"][0]
    assert item["classification"] == "review_required"
    assert "existing_register_scope_requires_review" in item["reasons"]


def test_preview_rejects_naive_cutoff_and_overflow(db, monkeypatch):
    with pytest.raises(ValueError, match="fuso orario"):
        service.preview_campaign(db, created_before=datetime(2026, 9, 24))
    mail(db)
    monkeypatch.setattr(service, "MAX_MAILS", 0)
    with pytest.raises(ValueError, match="10000"):
        preview(db)


def test_empty_preview_does_not_flush_pending_changes(db):
    db.add(RuoloTributiRegisteredMail(source_shipment_id="pending"))
    assert preview(db)["total"] == 0
    assert len(db.new) == 1


def test_campaign_preview_api_permissions_cutoff_and_legacy_links(api_fixture):  # noqa: F811
    url = "/ruolo/tributi/raccomandate/campaign-preview"
    params = {"created_before": CUTOFF.isoformat()}
    with api_fixture.session() as session:
        notice = _avviso(session)
        record = mail(session, avviso_id=notice.id)
        record_id = str(record.id)
        session.commit()
    response = api_fixture.client.get(url, params=params)
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["mail_id"] == record_id
    assert response.json()["read_only"] is True
    assert api_fixture.client.get(url).status_code == 422
    assert api_fixture.client.get(url, params={"created_before": "2026-09-24"}).status_code == 422
    assert api_fixture.client.get(url, params=params, headers=_headers(2)).status_code == 403
    assert api_fixture.client.get(url, params=params, headers=_headers(3)).status_code == 403
