"""Canonical template preview is private, read-only and never creates a draft."""

from uuid import uuid4

import pytest
from ruolo.test_notice_register_api import _headers
from sqlalchemy import event, func, select

from app.modules.communications import models, ruolo_source
from app.modules.communications.policy import render_template, sha256

from .conftest import create, pdf


def template(api, channel="pec", **changes):
    values = {
        "code": "preview-synthetic",
        "name": "Synthetic preview",
        "channel": channel,
        "module": "ruolo",
        "status": "approved",
        "subject": "Avviso {{numero_avviso}} / {{anno_tributario}}",
        "body": "{{contribuente_nome}} · {{codice_fiscale}} · {{importo}} · {{ente_nome}}",
        "version": 1,
        **changes,
    }
    with api.session() as db:
        row = models.CommunicationTemplate(**values)
        db.add(row)
        db.commit()
        return row.id


def preview(api, identity, channel="pec", **kwargs):
    return api.client.get(
        f"/communications/ruolo/candidates/{api.source_id}/template-preview",
        params={"template_id": str(identity), "channel": channel},
        **kwargs,
    )


@pytest.mark.parametrize("channel", ["pec", "email"])
def test_preview_renders_canonical_variables_without_writes_or_accounts(api, channel):
    identity = template(api, channel)
    with api.session() as db:
        for account in db.scalars(select(models.CommunicationAccount)):
            account.active = False
        db.commit()
        variables = ruolo_source.template_variables(ruolo_source.source_item(db, api.source_id))
        stored = db.get(models.CommunicationTemplate, identity)
        expected = {
            "subject": render_template(stored.subject, variables),
            "body": render_template(stored.body, variables),
            "source_sha256": sha256(pdf()),
            "missing_variables": [],
            "send_blockers": [],
        }
    statements = []

    def record(_conn, _cursor, statement, _params, _context, _many):
        statements.append(statement.strip().split()[0].upper())

    event.listen(api.engine, "before_cursor_execute", record)
    try:
        response = preview(api, identity, channel)
    finally:
        event.remove(api.engine, "before_cursor_execute", record)
    assert response.status_code == 200, response.text
    assert response.json() == expected
    assert response.headers["Cache-Control"] == "no-store, private"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert not {"INSERT", "UPDATE", "DELETE"}.intersection(statements)
    with api.session() as db:
        for model in (
            models.CommunicationMessage,
            models.CommunicationJob,
            models.CommunicationReview,
        ):
            assert db.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize("channel", ["pec", "email"])
def test_preview_text_and_pdf_are_identical_to_the_template_draft(api, channel):
    identity = template(api, channel)
    rendered = preview(api, identity, channel).json()
    draft = create(
        api,
        channel,
        template_id=str(identity),
        subject=None,
        body=None,
        expected_source_sha256=rendered["source_sha256"],
    )
    assert draft["subject"] == rendered["subject"]
    assert draft["body"] == rendered["body"]
    assert draft["attachments"][0]["sha256"] == rendered["source_sha256"]


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "draft"},
        {"channel": "email"},
        {"module": "utenze"},
    ],
)
def test_unapproved_incompatible_or_incomplete_template_is_rejected(api, changes):
    identity = template(api, **changes)
    response = preview(api, identity)
    assert response.status_code == 409
    assert "subject" not in response.json() and "body" not in response.json()


@pytest.mark.parametrize("change", ["pending", "year"])
def test_preview_rechecks_source_eligibility(api, change):
    identity = template(api)
    with api.session() as db:
        source = ruolo_source.source_item(db, api.source_id)
        if change == "pending":
            source.status = "pending"
        else:
            source.years_json = [2022]
        db.commit()
    assert preview(api, identity).status_code == 409


def test_preview_requires_manage_permission_and_valid_existing_identities(api):
    identity = template(api)
    for user, status in ((2, 403), (3, 403), (4, 401), (5, 403)):
        assert preview(api, identity, headers=_headers(user)).status_code == status
    assert preview(api, identity, headers={"Authorization": ""}).status_code == 401
    assert preview(api, uuid4()).status_code == 409
    assert (
        api.client.get(
            f"/communications/ruolo/candidates/{uuid4()}/template-preview",
            params={"template_id": str(identity), "channel": "pec"},
        ).status_code
        == 404
    )
    for parameters in (
        {},
        {"template_id": "invalid", "channel": "pec"},
        {"template_id": str(identity), "channel": "sms"},
    ):
        assert (
            api.client.get(
                f"/communications/ruolo/candidates/{api.source_id}/template-preview",
                params=parameters,
            ).status_code
            == 422
        )


def test_incomplete_text_and_unverified_history_remain_visible_but_cannot_create(api):
    identity = template(api, body="Accesso {{codice_utenza}} PIN {{pin_utenza}}")
    api.summary["payment_status"] = "paid"
    response = preview(api, identity)
    assert response.status_code == 200
    result = response.json()
    assert result["missing_variables"] == ["codice_utenza", "pin_utenza"]
    assert (
        result["body"] == "Accesso [Da verificare: codice_utenza] PIN [Da verificare: pin_utenza]"
    )
    assert result["subject"].startswith("Avviso ")
    assert result["send_blockers"] and "saldo_non_esigibile" in result["send_blockers"][0]
    response = api.client.post(
        "/communications/messages",
        json={
            "source_entity_id": str(api.source_id),
            "channel": "pec",
            "recipient": "synthetic@example.org",
            "template_id": str(identity),
            "subject": result["subject"],
            "body": result["body"],
        },
    )
    assert response.status_code == 409


def test_required_template_fields_cannot_be_bypassed_by_edited_text(api):
    identity = template(api, body="PIN {{pin_utenza}}")
    response = api.client.post(
        "/communications/messages",
        json={
            "source_entity_id": str(api.source_id),
            "channel": "pec",
            "recipient": "synthetic@example.org",
            "template_id": str(identity),
            "subject": "Testo modificato",
            "body": "Testo modificato",
        },
    )
    assert response.status_code == 409
    assert "pin_utenza" in response.json()["detail"]


def test_pdf_change_during_text_preparation_blocks_composition(api, monkeypatch):
    from app.modules.communications import template_composition

    original = ruolo_source.inspect

    def changed(db, identity):
        source, document, _, fingerprint = original(db, identity)
        return source, document, pdf(4), fingerprint

    monkeypatch.setattr(template_composition.ruolo_source, "inspect", changed)
    result = preview(api, template(api)).json()
    assert result["subject"].startswith("Avviso ")
    assert "PDF cambiato" in result["send_blockers"][0]
