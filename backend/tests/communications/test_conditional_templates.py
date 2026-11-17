"""Optional portal sections use source credentials, never preview placeholders."""

from email import policy as email_policy
from email.parser import BytesParser
from uuid import UUID

import pytest

from app.modules.communications import models, ruolo_source, store, transports
from app.modules.communications import rich_template as rich
from app.modules.communications.policy import Conflict

from . import test_office_templates as office
from .conftest import create
from .test_rich_templates import document
from .test_template_preview import preview, template

portal_key = office.portal_key
PORTAL_BLOCKS = [
    {"kind": "paragraph", "text": "Avviso {{numero_avviso}}"},
    {
        "kind": "paragraph",
        "text": "SERVIZIO ICATASTO: {{codice_utenza}} PIN: {{pin_utenza}}",
        "condition": "icatasto",
    },
    {
        "kind": "button",
        "text": "Accedi a ICATASTO",
        "url": "https://example.org/portal",
        "condition": "icatasto",
    },
]


@pytest.mark.parametrize(
    "credentials",
    [
        {},
        {"codice_utenza": "001"},
        {"pin_utenza": "002"},
        {"codice_utenza": "001", "pin_utenza": " \t"},
        {"codice_utenza": "", "pin_utenza": "002"},
        {"codice_utenza": None, "pin_utenza": "002"},
        {"codice_utenza": "001", "pin_utenza": 2},
    ],
)
def test_incomplete_credentials_omit_the_entire_section_and_link(credentials):
    body = rich.render_template(document(PORTAL_BLOCKS), {"numero_avviso": "001", **credentials})
    assert rich.decode(body) == [{"kind": "paragraph", "text": "Avviso 001"}]
    plain, html, _ = rich.email_content(body)
    assert "ICATASTO" not in plain + html and "example.org" not in plain + html
    assert rich.render_template(document(PORTAL_BLOCKS[1:]), credentials) == ""


def test_conditions_are_removed_from_snapshots_and_normal_required_fields_still_fail():
    variables = {"codice_utenza": "0001", "pin_utenza": "0002", "numero_avviso": "001"}
    body = rich.render_template(document(PORTAL_BLOCKS), variables)
    assert "condition" not in body and "PIN: 0002" in body
    assert 'href="https://example.org/portal"' in rich.email_content(body)[1]
    blocks = [*PORTAL_BLOCKS, {"kind": "paragraph", "text": "PIN obbligatorio {{pin_utenza}}"}]
    with pytest.raises(Conflict, match="pin_utenza"):
        rich.render_template(document(blocks), {"numero_avviso": "001"})
    with pytest.raises(Conflict, match="prima dell'invio"):
        rich.email_content(document(PORTAL_BLOCKS))


@pytest.mark.parametrize("condition", [None, "", "unknown", [], {}, False])
def test_invalid_conditions_are_rejected_even_when_the_block_would_be_hidden(api, condition):
    body = document([{**PORTAL_BLOCKS[1], "condition": condition}])
    response = api.client.post(
        "/communications/templates",
        json={
            "code": "invalid",
            "name": "Invalid",
            "channel": "pec",
            "subject": "Test",
            "body": body,
        },
    )
    assert response.status_code == 422
    with pytest.raises(Conflict, match="Condizione"):
        rich.render_template(body, {})


def test_hidden_blocks_still_validate_destinations_and_unknown_variables(api):
    with pytest.raises(Conflict, match="HTTPS"):
        rich.render_template(document([{**PORTAL_BLOCKS[2], "url": "javascript:alert(1)"}]), {})
    response = api.client.post(
        "/communications/templates",
        json={
            "code": "unknown-field",
            "name": "Unknown",
            "channel": "pec",
            "subject": "Test",
            "body": document([{**PORTAL_BLOCKS[1], "text": "{{unknown_field}}"}]),
        },
    )
    assert response.status_code == 409


@pytest.mark.parametrize("channel", ["email", "pec"])
@pytest.mark.parametrize("credential_state", ["complete", "absent", "corrupt", "ambiguous"])
def test_preview_draft_and_mime_agree_using_saved_pdf_credentials(
    api, portal_key, channel, credential_state
):
    available = credential_state == "complete"
    entry = office.access(portal_key)
    entries = {
        "complete": [entry],
        "absent": [],
        "corrupt": [{**entry, "pin_encrypted": "invalid-ciphertext"}],
        "ambiguous": [entry, office.access(portal_key, pin="0007655")],
    }[credential_state]
    with api.session() as db:
        source = ruolo_source.source_item(db, api.source_id)
        source.payload_json = {
            **source.payload_json,
            "taxpayer_portal_access": entries,
        }
        db.commit()
    saved = api.client.post(
        "/communications/templates",
        json={
            "code": "conditional-portal",
            "name": "Accesso ICATASTO",
            "channel": channel,
            "subject": "Avviso {{numero_avviso}}",
            "body": document(PORTAL_BLOCKS),
        },
    )
    assert saved.status_code == 201, saved.text
    identity = UUID(saved.json()["id"])
    assert preview(api, identity, channel).status_code == 409
    assert api.client.post(f"/communications/templates/{identity}/approve").status_code == 200
    result = preview(api, identity, channel).json()
    assert result["missing_variables"] == [] and result["send_blockers"] == []
    assert ("ICATASTO" in result["body"]) == available
    assert ("PIN: 0007654" in result["body"]) == available
    assert "Da verificare" not in result["body"] and "condition" not in result["body"]
    message = create(api, channel, template_id=str(identity), subject=None, body=None)
    assert message["body"] == result["body"]
    with api.session() as db:
        row = db.get(models.CommunicationMessage, UUID(message["id"]))
        account = db.get(models.CommunicationAccount, row.account_id)
        mime = BytesParser(policy=email_policy.default).parsebytes(
            transports.mime_message(row, account, store.attachments(db, row.id), "<test@invalid>")
        )
        for kind in ("plain", "html"):
            content = mime.get_body(preferencelist=(kind,)).get_content()
            assert ("ICATASTO" in content) == available
            assert ("https://example.org/portal" in content) == available
        assert db.get(models.CommunicationTemplate, identity).body == document(PORTAL_BLOCKS)


@pytest.mark.parametrize("available", [True, False])
def test_conditional_logo_is_embedded_only_when_its_section_is_included(available):
    from email.message import EmailMessage

    blocks = [*PORTAL_BLOCKS, {"kind": "logo", "condition": "icatasto"}]
    variables = {"numero_avviso": "001"}
    if available:
        variables.update(codice_utenza="0001", pin_utenza="0002")
    message = EmailMessage()
    rich.set_message_content(message, rich.render_template(document(blocks), variables))
    images = [part for part in message.walk() if part.get_content_type() == "image/png"]
    assert len(images) == int(available)
    html = message.get_body(preferencelist=("html",)).get_content()
    assert (f"cid:{rich.LOGO_CID}" in html) == available


def test_preview_retains_missing_fields_outside_the_conditional_section(api):
    identity = template(
        api, body=document([*PORTAL_BLOCKS, {"kind": "paragraph", "text": "{{pin_utenza}}"}])
    )
    result = preview(api, identity).json()
    assert result["missing_variables"] == ["pin_utenza"]
    assert "ICATASTO" not in result["body"] and "[Da verificare: pin_utenza]" in result["body"]


def test_a_template_with_only_excluded_blocks_cannot_create_an_empty_message(api):
    identity = template(api, body=document(PORTAL_BLOCKS[1:]))
    result = preview(api, identity).json()
    assert result["body"] == "" and result["missing_variables"] == []
    response = api.client.post(
        "/communications/messages",
        json={
            "source_entity_id": str(api.source_id),
            "channel": "pec",
            "recipient": "synthetic@example.org",
            "template_id": str(identity),
        },
    )
    assert response.status_code == 409 and "testo obbligatori" in response.json()["detail"]
    assert api.client.get("/communications/messages").json()["total"] == 0
