"""Archive credentials supplement communications; document and reviewed MIME stay frozen."""

from email import policy
from email.parser import BytesParser
from uuid import UUID

import pytest
from sqlalchemy import event, func, select

from app.modules.communications import models, ruolo_source, store, transports
from app.modules.communications.schemas import CHECKS
from app.modules.ruolo.notice_register_models import NoticeAudit
from app.modules.ruolo.portal_access_models import RuoloTaxpayerPortalAccess

from . import test_office_templates as office
from .conftest import create
from .test_conditional_templates import PORTAL_BLOCKS
from .test_rich_templates import document
from .test_template_preview import preview, template
from .test_worker_receipts import FakeSMTP, run_job

portal_key = office.portal_key


def seed_access(api, key, *, account="0001234", pin=b"0007654", tax_code=None):
    with api.session() as db:
        source = ruolo_source.source_item(db, api.source_id)
        row = RuoloTaxpayerPortalAccess(
            account_code=account,
            tax_code=tax_code or source.codice_fiscale,
            pin_encrypted=key.encrypt(pin),
            source_sha256="a" * 64,
        )
        db.add(row)
        db.commit()


@pytest.mark.parametrize("channel", ["pec", "email"])
@pytest.mark.parametrize("rich", [False, True])
def test_archive_access_matches_preview_draft_and_mime_without_changing_pdf(
    api, portal_key, channel, rich
):
    seed_access(api, portal_key)
    body = document(PORTAL_BLOCKS) if rich else "Utenza {{codice_utenza}} PIN: {{pin_utenza}}"
    identity = template(api, channel, body=body)
    with api.session() as db:
        source = ruolo_source.source_item(db, api.source_id)
        old_payload = dict(source.payload_json)
        old_path = source.generated_document_path
        old_pdf = ruolo_source.read_pdf(source)
    statements = []

    def record(_conn, _cursor, statement, _params, _context, _many):
        statements.append(statement.strip().split()[0].upper())

    event.listen(api.engine, "before_cursor_execute", record)
    try:
        response = preview(api, identity, channel)
    finally:
        event.remove(api.engine, "before_cursor_execute", record)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["portal_access_source"] == "archive"
    assert "0001234" in result["body"] and "PIN: 0007654" in result["body"]
    assert result["missing_variables"] == result["send_blockers"] == []
    assert not {"INSERT", "UPDATE", "DELETE"}.intersection(statements)
    value = create(
        api,
        channel,
        template_id=str(identity),
        subject=None,
        body=None,
        expected_source_sha256=result["source_sha256"],
    )
    assert value["state"] == "draft" and value["body"] == result["body"]
    with api.session() as db:
        source = ruolo_source.source_item(db, api.source_id)
        assert source.payload_json == old_payload and source.generated_document_path == old_path
        assert ruolo_source.read_pdf(source) == old_pdf
        row = db.get(models.CommunicationMessage, UUID(value["id"]))
        account = db.get(models.CommunicationAccount, row.account_id)
        mime = BytesParser(policy=policy.default).parsebytes(
            transports.mime_message(row, account, store.attachments(db, row.id), "<test@invalid>")
        )
        assert next(mime.iter_attachments()).get_payload(decode=True) == old_pdf
        assert "PIN: 0007654" in mime.get_body().get_content()
        assert db.scalar(select(func.count()).select_from(NoticeAudit)) == 0
        for model in (models.CommunicationJob, models.CommunicationAuthorization):
            assert db.scalar(select(func.count()).select_from(model)) == 0
        assert "0007654" not in str(list(db.scalars(select(models.CommunicationEvent.detail))))


@pytest.mark.parametrize("snapshot", [None, []])
def test_missing_and_empty_document_snapshots_use_archive_without_mutating_source(
    api, portal_key, snapshot
):
    seed_access(api, portal_key)
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        item.payload_json = {**item.payload_json, "taxpayer_portal_access": snapshot}
        fields = ruolo_source.template_variables(item, db=db)
        assert fields["codice_utenza"] == "0001234" and fields["pin_utenza"] == "0007654"
        assert item.payload_json["taxpayer_portal_access"] is snapshot
        assert not db.dirty.difference({item})


@pytest.mark.parametrize("snapshot_state", ["valid", "corrupt", "ambiguous", "malformed"])
def test_existing_snapshot_has_precedence_and_invalid_snapshots_never_fall_back(
    api, portal_key, snapshot_state
):
    seed_access(api, portal_key)
    entry = office.access(portal_key, pin="0001111")
    entries = {
        "valid": [entry],
        "corrupt": [{**entry, "pin_encrypted": "corrupt"}],
        "ambiguous": [entry, entry],
        "malformed": {"account_code": "0001234"},
    }[snapshot_state]
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        item.payload_json = {**item.payload_json, "taxpayer_portal_access": entries}
        db.commit()
    result = preview(api, template(api, body=document(PORTAL_BLOCKS))).json()
    if snapshot_state == "valid":
        assert result["portal_access_source"] == "document"
        assert "PIN: 0001111" in result["body"]
    else:
        assert result["portal_access_source"] == "unavailable"
        assert "ICATASTO" not in result["body"]
    assert "0007654" not in result["body"]


@pytest.mark.parametrize(
    "state",
    [
        "absent",
        "other_cf",
        "ambiguous",
        "invalid_cf",
        "invalid_account",
        "invalid_pin",
        "corrupt",
        "binary_ciphertext",
        "unicode",
        "missing_key",
    ],
)
def test_unusable_archive_access_stays_hidden_or_blocks_required_fields(
    api, portal_key, monkeypatch, state
):
    if state != "absent":
        seed_access(
            api,
            portal_key,
            account="invalid" if state == "invalid_account" else "0001234",
            pin={"invalid_pin": b"bad", "unicode": b"\xff"}.get(state, b"0007654"),
            tax_code="VRDLGI80A01H501Z" if state == "other_cf" else None,
        )
    if state == "ambiguous":
        seed_access(api, portal_key, account="0001235")
    with api.session() as db:
        if state == "invalid_cf":
            item = ruolo_source.source_item(db, api.source_id)
            item.codice_fiscale = "NOT_A_TAX_CODE"
            db.get(RuoloTaxpayerPortalAccess, "0001234").tax_code = item.codice_fiscale
        if state == "corrupt":
            db.get(RuoloTaxpayerPortalAccess, "0001234").pin_encrypted = b"corrupt"
        if state == "binary_ciphertext":
            db.get(RuoloTaxpayerPortalAccess, "0001234").pin_encrypted = b"\xff"
        db.commit()
    if state == "missing_key":

        def unavailable():
            raise office.ElaborazioneCredentialConfigurationError("missing key")

        monkeypatch.setattr(office.taxpayer_portal_access, "get_credential_fernet", unavailable)
    identity = template(api, body=document(PORTAL_BLOCKS))
    result = preview(api, identity).json()
    assert result["portal_access_source"] == "unavailable"
    assert "ICATASTO" not in result["body"] and result["missing_variables"] == []
    required = template(api, body="PIN {{pin_utenza}}", code="required")
    result = preview(api, required).json()
    assert result["missing_variables"] == ["pin_utenza"]
    response = api.client.post(
        "/communications/messages",
        json={
            "source_entity_id": str(api.source_id),
            "channel": "pec",
            "recipient": "synthetic@example.org",
            "template_id": str(required),
        },
    )
    assert response.status_code == 409
    with api.session() as db:
        assert db.scalar(select(func.count()).select_from(models.CommunicationMessage)) == 0


@pytest.mark.parametrize("channel", ["pec", "email"])
def test_worker_sends_reviewed_archive_snapshot_even_after_archive_changes(
    api, portal_key, monkeypatch, channel
):
    seed_access(api, portal_key)
    identity = template(api, channel, body=document(PORTAL_BLOCKS))
    value = create(api, channel, template_id=str(identity), subject=None, body=None)
    base = f"/communications/messages/{value['id']}"
    part = value["attachments"][0]
    with api.session() as db:
        db.get(RuoloTaxpayerPortalAccess, "0001234").pin_encrypted = portal_key.encrypt(b"9999999")
        db.commit()
    inspected = api.client.get(f"{base}/attachments/{part['id']}/preview")
    assert (
        api.client.post(
            f"{base}/attachments/{part['id']}/rendered",
            json={
                "review_id": inspected.headers["X-Communication-Review"],
                "expected_version": 1,
                "pages": part["pages"],
                "sha256": part["sha256"],
            },
        ).status_code
        == 200
    )
    assert api.client.post(f"{base}/validate", json={"expected_version": 1}).status_code == 200
    assert (
        api.client.post(
            f"{base}/approve",
            json={
                "expected_version": 1,
                "confirmed": True,
                "checklist": dict.fromkeys(CHECKS, True),
            },
        ).status_code
        == 200
    )
    dispatched = api.client.post(f"{base}/dispatch", json={"expected_version": 1})
    assert dispatched.status_code == 202
    smtp = FakeSMTP()
    run_job(api, UUID(dispatched.json()["id"]), monkeypatch, smtp=smtp)
    assert len(smtp.sent) == 1
    mime = BytesParser(policy=policy.default).parsebytes(smtp.sent[0][2])
    for kind in ("plain", "html"):
        content = mime.get_body(preferencelist=(kind,)).get_content()
        assert "PIN: 0007654" in content and "9999999" not in content
    assert next(mime.iter_attachments()).get_payload(decode=True) == inspected.content
    with api.session() as db:
        stored = db.get(models.CommunicationMessage, UUID(value["id"]))
        assert stored.body == value["body"] and stored.state == "submitted"
