"""Structured templates remain immutable snapshots and produce safe MIME alternatives."""

import json
from email import policy as email_policy
from email.parser import BytesParser
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.modules.communications import models, store, transports
from app.modules.communications import rich_template as rich
from app.modules.communications.policy import Conflict
from app.modules.communications.rich_template import render_template

from .conftest import approved, create
from .test_worker_receipts import FakeSMTP, run_job


def document(blocks):
    return rich.PREFIX + json.dumps(blocks, ensure_ascii=False)


BLOCKS = [
    {"kind": "logo"},
    {"kind": "title", "text": "Avviso {{numero_avviso}}"},
    {"kind": "paragraph", "text": "Gentile {{contribuente_nome}}\nVerificare il PDF."},
    {"kind": "list", "text": "Prima voce\nSeconda voce"},
    {"kind": "link", "text": "Il sito", "url": "https://example.org/?a=1&b=2"},
    {"kind": "button", "text": "Apri portale", "url": "https://example.org/portale"},
]


@pytest.mark.parametrize("channel", ["pec", "email"])
def test_create_approve_compose_snapshot_and_mime(api, channel):
    payload = {
        "code": "rich-synthetic",
        "name": "Synthetic graphical template",
        "channel": channel,
        "subject": "Avviso {{numero_avviso}}",
        "body": document(BLOCKS),
    }
    template = api.client.post("/communications/templates", json=payload)
    assert template.status_code == 201, template.text
    template_id = template.json()["id"]
    assert api.client.post(f"/communications/templates/{template_id}/approve").status_code == 200
    preview = api.client.get(
        f"/communications/ruolo/candidates/{api.source_id}/template-preview",
        params={"template_id": template_id, "channel": channel},
    ).json()
    message = create(api, channel, template_id=template_id, subject=None, body=None)
    assert message["body"] == preview["body"]
    with api.session() as db:
        row = db.get(models.CommunicationMessage, UUID(message["id"]))
        account = db.get(models.CommunicationAccount, row.account_id)
        raw = transports.mime_message(row, account, store.attachments(db, row.id), "<test@invalid>")
        mime = BytesParser(policy=email_policy.default).parsebytes(raw)
        assert "GAIA-BLOCKS" not in mime.get_body(preferencelist=("plain",)).get_content()
        html = mime.get_body(preferencelist=("html",)).get_content()
        assert "cid:gaia-official-logo" in html
        assert 'href="https://example.org/?a=1&amp;b=2"' in html
        images = [part for part in mime.walk() if part.get_content_type() == "image/png"]
        assert len(images) == 1 and images[0].get_payload(decode=True) == rich.LOGO.read_bytes()
        assert images[0]["Content-Disposition"] == "inline"
        assert len(list(mime.iter_attachments())) == 1
        # Later versions and deletions cannot alter the rendered message snapshot.
        assert (
            api.client.post(
                "/communications/templates", json={**payload, "body": "new"}
            ).status_code
            == 201
        )
        assert (
            api.client.request(
                "DELETE", f"/communications/templates/{template_id}", json={"confirmed": True}
            ).status_code
            == 200
        )
        after = BytesParser(policy=email_policy.default).parsebytes(
            transports.mime_message(row, account, store.attachments(db, row.id), "<test@invalid>")
        )
        assert after.get_body(preferencelist=("html",)).get_content() == html
        assert row.body == preview["body"]


@pytest.mark.parametrize(
    "url",
    [
        "http://example.org",
        "javascript:alert(1)",
        "data:x",
        "//example.org",
        "https://a@b.org",
        "https://:password@b.org",
        "https://[",
        "https://example.org/\nX",
        'https://example.org/"',
        "https://example.org/\\x",
        "https://example.org/{{pin_utenza}}",
        "https://example.org/a b",
        "https://example.org/\x7f",
        None,
    ],
)
def test_unsafe_destinations_are_rejected_at_http_and_rendering(api, url):
    body = document([{"kind": "button", "text": "Click", "url": url}])
    response = api.client.post(
        "/communications/templates",
        json={
            "code": "unsafe",
            "name": "unsafe",
            "channel": "pec",
            "subject": "Test",
            "body": body,
        },
    )
    assert response.status_code == 422
    with pytest.raises(Conflict):
        render_template(body, {})


@pytest.mark.parametrize(
    "blocks",
    [
        None,
        {},
        [],
        [None],
        [{"kind": []}],
        [{"kind": {}}],
        [{"kind": None}],
        [{"kind": "html", "text": "<script>"}],
        [{"kind": "logo", "url": "https://example.org"}],
        [{"kind": "paragraph"}],
        [{"kind": "paragraph", "text": 3}],
        [{"kind": "title", "text": " "}],
        [{"kind": "link", "text": "x", "url": "https://example.org", "extra": True}],
        [{"kind": "logo"}] * 61,
    ],
)
def test_invalid_structures_cannot_be_saved_or_used_to_edit_a_message(api, blocks):
    body = document(blocks)
    with pytest.raises(Conflict):
        render_template(body, {})
    message = create(api)
    response = api.client.patch(
        f"/communications/messages/{message['id']}",
        json={
            "expected_version": message["version"],
            "account_id": message["account_id"],
            "recipient": message["recipient"],
            "subject": "Test",
            "body": body,
        },
    )
    assert response.status_code == 422


def test_escape_values_before_html_and_preserve_json_and_plain_text():
    hostile = '<script>alert("x")</script>\n"Quoted" & name'
    body = render_template(
        document([{"kind": "paragraph", "text": "{{contribuente_nome}}"}]),
        {"contribuente_nome": hostile},
    )
    assert rich.decode(body)[0]["text"] == hostile
    plain, html, logo = rich.email_content(body)
    assert plain == hostile and not logo
    assert "<script>" not in html and "&lt;script&gt;" in html and "<br>" in html
    assert rich.email_content("Old <text>\nbody") == ("Old <text>\nbody", None, False)
    assert rich.validate_body("old text") == "old text"
    with pytest.raises(Conflict, match="mancante"):
        render_template(document([{"kind": "title", "text": "{{numero_avviso}}"}]), {})
    with pytest.raises(Conflict):
        render_template(rich.PREFIX + "bad json", {})
    assert not rich.valid_url("https://example.org/a\tb")
    assert rich.valid_url("https://example.org:443/a#ref")
    assert rich.validate_body(document(BLOCKS)).startswith(rich.PREFIX)


def test_html_without_logo_and_maximum_mime_size():
    message = SimpleNamespace(
        id=uuid4(),
        sender="sender@example.org",
        recipient="recipient@example.org",
        subject="Test",
        body=document([{"kind": "paragraph", "text": "Hello"}]),
    )
    account = SimpleNamespace(display_name="Test", max_bytes=100000)
    mime = BytesParser(policy=email_policy.default).parsebytes(
        transports.mime_message(message, account, [], "<test@invalid>")
    )
    assert mime.get_body(preferencelist=("html",)) is not None
    assert not list(mime.iter_attachments())
    account.max_bytes = 1
    with pytest.raises(Conflict, match="MIME"):
        transports.mime_message(message, account, [], "<test@invalid>")


def test_rich_fields_keep_missing_credentials_visible_and_cannot_bypass_checks(api):
    payload = {
        "code": "rich-missing-pin",
        "name": "Missing PIN",
        "channel": "pec",
        "subject": "Avviso",
        "body": document([{"kind": "paragraph", "text": "PIN: {{pin_utenza}}"}]),
    }
    template = api.client.post("/communications/templates", json=payload).json()
    api.client.post(f"/communications/templates/{template['id']}/approve")
    preview = api.client.get(
        f"/communications/ruolo/candidates/{api.source_id}/template-preview",
        params={"template_id": template["id"], "channel": "pec"},
    ).json()
    assert preview["missing_variables"] == ["pin_utenza"]
    assert rich.decode(preview["body"])[0]["text"] == "PIN: [Da verificare: pin_utenza]"
    response = api.client.post(
        "/communications/messages",
        json={
            "source_entity_id": str(api.source_id),
            "channel": "pec",
            "recipient": "synthetic@example.org",
            "template_id": template["id"],
            "body": document([{"kind": "paragraph", "text": "Edited text"}]),
        },
    )
    assert response.status_code == 409 and "pin_utenza" in response.json()["detail"]
    assert api.client.get("/communications/messages").json()["total"] == 0


@pytest.mark.parametrize("channel", ["pec", "email"])
def test_graphical_edit_revokes_approval_then_worker_archives_exact_mime(api, monkeypatch, channel):
    from sqlalchemy import select

    from app.modules.communications.policy import sha256
    from app.modules.communications.schemas import CHECKS

    original = approved(api, channel)
    base = f"/communications/messages/{original['id']}"
    body = document([{"kind": "logo"}, {"kind": "paragraph", "text": "Revisione grafica"}])
    changed = api.client.patch(
        base,
        json={
            "expected_version": original["version"],
            "account_id": original["account_id"],
            "recipient": original["recipient"],
            "subject": original["subject"],
            "body": body,
        },
    )
    assert changed.status_code == 200, changed.text
    message = changed.json()
    assert message["state"] == "draft" and message["version"] == 2
    assert api.client.post(f"{base}/dispatch", json={"expected_version": 2}).status_code == 409
    assert api.client.post(f"{base}/validate", json={"expected_version": 2}).status_code == 200
    confirmation = {
        "expected_version": 2,
        "confirmed": True,
        "checklist": dict.fromkeys(CHECKS, True),
    }
    assert api.client.post(f"{base}/approve", json=confirmation).status_code == 409
    part = message["attachments"][0]
    preview = api.client.get(f"{base}/attachments/{part['id']}/preview")
    assert (
        api.client.post(
            f"{base}/attachments/{part['id']}/rendered",
            json={
                "expected_version": 2,
                "review_id": preview.headers["X-Communication-Review"],
                "pages": part["pages"],
                "sha256": part["sha256"],
            },
        ).status_code
        == 200
    )
    assert api.client.post(f"{base}/approve", json=confirmation).status_code == 200
    dispatch = api.client.post(f"{base}/dispatch", json={"expected_version": 2})
    assert dispatch.status_code == 202
    smtp = FakeSMTP()
    run_job(api, UUID(dispatch.json()["id"]), monkeypatch, smtp=smtp)
    assert len(smtp.sent) == 1
    raw = smtp.sent[0][2]
    mime = BytesParser(policy=email_policy.default).parsebytes(raw)
    assert (
        mime.get_body(preferencelist=("plain",))
        .get_content()
        .rstrip()
        .endswith("Revisione grafica")
    )
    assert "cid:gaia-official-logo" in mime.get_body(preferencelist=("html",)).get_content()
    assert sha256(next(mime.iter_attachments()).get_payload(decode=True)) == part["sha256"]
    with api.session() as db:
        attempt = db.scalar(select(models.CommunicationAttempt))
        assert attempt.mime_content == raw and attempt.mime_sha256 == sha256(raw)
        assert db.get(models.CommunicationMessage, UUID(message["id"])).state == "submitted"
