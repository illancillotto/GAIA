"""Office starting texts, real rendering rules and synthetic-only composition."""

from email import policy as email_policy
from email.parser import BytesParser
from types import SimpleNamespace
from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from ruolo.test_notice_register_api import _headers
from sqlalchemy import func, select

from app.modules.communications import models, policy, registry, ruolo_source, store, transports
from app.modules.communications.schemas import TemplateInput
from app.modules.communications.template_catalog import load_catalog
from app.modules.ruolo.services import taxpayer_portal_access
from app.modules.ruolo.services.notice_branding import TAXPAYER_PORTAL_URL
from app.modules.ruolo.services.notice_communication_fields import template_variables
from app.modules.ruolo.services.notice_payment_deadline import front_payment_due_phrase
from app.modules.ruolo.services.tributi_reminder_service import (
    _gaia_bollettino_due_date,
    notice_total_amount,
)
from app.services.elaborazioni_credentials import ElaborazioneCredentialConfigurationError


def source(payload=None, **changes):
    return SimpleNamespace(
        **{
            "payload_json": payload,
            "display_name": "Ditta sintetica & Figli",
            "codice_fiscale": "00000000000",
            "saldo_amount": "99.00",
            "years_json": [2021],
            **changes,
        }
    )


@pytest.fixture
def portal_key(monkeypatch):
    key = Fernet(Fernet.generate_key())
    monkeypatch.setattr(taxpayer_portal_access, "get_credential_fernet", lambda: key)
    return key


def access(key, pin="0007654"):
    return {"account_code": "0001234", "pin_encrypted": key.encrypt(pin.encode()).decode()}


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"saldo_amount": "1234.56", "notification_amount": "11.55"}, "1.246,11"),
        ({"due_amount": "44.59"}, "56,14"),
        ({"saldo_amount": "0.00", "due_amount": "999", "notification_amount": "1"}, "1,00"),
    ],
)
def test_document_total_uses_saved_pdf_formula_including_fees(payload, expected):
    payload = {"notice_number": "020210000000001", **payload}
    fields = template_variables(source(payload))
    assert fields["importo_documento"] == expected
    assert fields["numero_avviso"] == "020210000000001"
    assert fields["anno_tributario"] == "2021"
    assert fields["codice_fiscale"] == "00000000000"
    assert fields["url_portale"] == TAXPAYER_PORTAL_URL
    assert notice_total_amount(payload) > 0


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"saldo_amount": ""},
        {"saldo_amount": "invalid"},
        {"saldo_amount": "NaN"},
        {"saldo_amount": "Infinity"},
        {"saldo_amount": "1.234,56", "notification_amount": "1,55"},
        {"saldo_amount": "10", "notification_amount": "invalid"},
        {"saldo_amount": "10", "notification_amount": "NaN"},
    ],
)
def test_missing_or_invalid_source_total_cannot_be_invented(payload):
    fields = template_variables(source(payload, display_name=None))
    assert fields["contribuente_nome"] == "00000000000"
    assert "importo_documento" not in fields
    with pytest.raises(policy.Conflict, match="importo_documento"):
        policy.render_template("Totale {{importo_documento}}", fields)


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({}, "entro 60 giorni dalla data di notifica"),
        (
            {"due_date": "2026-12-31"},
            "scadenza 31/12/2026 E comunque entro 60 giorni dalla data di notifica.",
        ),
        (
            {"deadline": "2026-12-31", "payment_deadline_mode": "notification_60_days"},
            "scadenza 31/12/2026 E comunque entro 60 giorni dalla data di notifica.",
        ),
    ],
)
def test_deadline_matches_pdf_without_calculating_a_notification_date(payload, expected):
    fields = template_variables(source(payload))
    assert fields["termine_pagamento"] == expected
    assert fields["termine_pagamento"] == front_payment_due_phrase(
        payload, [2021], _gaia_bollettino_due_date
    )


def test_legacy_variables_remain_compatible_and_personal_portal_access_is_not_exposed():
    payload = {
        "notice_number": "001",
        "notice_total_amount": "123.45",
        "saldo_amount": "10",
        "taxpayer_portal_access": [{"account_code": "synthetic", "pin_encrypted": "invalid"}],
    }
    fields = template_variables(source(payload))
    assert fields["importo"] == "123.45"
    assert fields["contribuente_nome"] == "Ditta sintetica & Figli"
    assert not any("pin" in key or "utenza" in key for key in fields)
    assert "invalid" not in str(fields)
    assert ruolo_source.template_variables is template_variables


def test_catalog_is_read_only_editable_and_contains_only_supported_variables(api, portal_key):
    response = api.client.get("/communications/admin/template-catalog")
    assert response.status_code == 200
    catalog = response.json()
    assert catalog == load_catalog()
    fields = template_variables(
        source({"saldo_amount": "10", "taxpayer_portal_access": [access(portal_key)]})
    )
    assert set(catalog["variables"]) == set(registry.VARIABLES) == set(fields)
    assert {value["channel"] for value in catalog["proposals"]} == {"pec", "email"}
    for proposal in catalog["proposals"]:
        TemplateInput(**proposal)
        text = policy.render_template(proposal["body"], fields)
        assert "{{" not in text
        assert "31 dicembre 2026" in text and "PIN: 0007654" in text
        assert "IBAN: IT15L0760117400001007214826" in text
        assert all(term in text for term in ("2 rate", "4 rate", "6 rate", "12 rate", "18 rate"))
    iban = "IT15L0760117400001007214826"
    rearranged = iban[4:] + iban[:4]
    assert int("".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)) % 97 == 1
    assert api.client.get("/communications/admin/templates").json() == []
    with api.session() as db:
        assert db.scalar(select(func.count()).select_from(models.CommunicationMessage)) == 0
        assert db.scalar(select(func.count()).select_from(models.CommunicationJob)) == 0
        assert db.scalar(select(func.count()).select_from(models.CommunicationAuthorization)) == 0
    catalog["proposals"][0]["body"] = "local edit"
    assert load_catalog()["proposals"][0]["body"] != "local edit"


@pytest.mark.parametrize("user,status", [(2, 403), (4, 401)])
def test_catalog_requires_active_admin(api, user, status):
    assert (
        api.client.get("/communications/admin/template-catalog", headers=_headers(user)).status_code
        == status
    )


def test_catalog_requires_authentication(api):
    api.client.headers.clear()
    assert api.client.get("/communications/admin/template-catalog").status_code == 401


@pytest.mark.parametrize("channel", ["pec", "email"])
def test_catalog_draft_requires_approval_then_composes_exact_snapshot_and_mime(
    api, channel, portal_key
):
    proposal = next(p for p in load_catalog()["proposals"] if p["channel"] == channel)
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        item.payload_json = {
            **item.payload_json,
            "saldo_amount": "44.59",
            "due_date": "2026-12-31",
            "taxpayer_portal_access": [access(portal_key)],
        }
        db.commit()
        expected_pdf = ruolo_source.read_pdf(item)
        number = item.payload_json["notice_number"]
    created = api.client.post("/communications/templates", json=proposal)
    assert created.status_code == 201
    template = created.json()
    assert template["status"] == "draft"
    payload = {
        "source_entity_id": str(api.source_id),
        "channel": channel,
        "recipient": "synthetic@example.org",
        "template_id": template["id"],
        "purpose": "courtesy" if channel == "email" else "pec_notice",
    }
    assert api.client.post("/communications/messages", json=payload).status_code == 409
    assert api.client.post(f"/communications/templates/{template['id']}/approve").status_code == 200
    message = api.client.post("/communications/messages", json=payload)
    assert message.status_code == 201, message.text
    value = message.json()
    assert value["state"] == "draft"
    assert number in value["subject"] and "56,14" in value["body"]
    assert "31/12/2026" in value["body"] and "{{" not in value["body"]
    assert "PIN: 0007654" in value["body"] and "0001234" in value["body"]
    attachment = value["attachments"][0]
    preview = api.client.get(
        f"/communications/messages/{value['id']}/attachments/{attachment['id']}/preview"
    )
    assert preview.content == expected_pdf
    with api.session() as db:
        stored = db.get(models.CommunicationMessage, UUID(value["id"]))
        account = db.get(models.CommunicationAccount, stored.account_id)
        mime = BytesParser(policy=email_policy.default).parsebytes(
            transports.mime_message(
                stored, account, store.attachments(db, stored.id), "<test@invalid>"
            )
        )
        assert next(mime.iter_attachments()).get_payload(decode=True) == expected_pdf
        assert mime.get_body().get_content().replace("\r\n", "\n").rstrip() == value["body"]
        assert db.scalar(select(func.count()).select_from(models.CommunicationJob)) == 0
        assert db.scalar(select(func.count()).select_from(models.CommunicationAuthorization)) == 0
        assert "0007654" not in str(list(db.scalars(select(models.CommunicationEvent.detail))))
    assert (
        "cortesia" in value["body"] if channel == "email" else "ricevuta PEC" not in value["body"]
    )


def test_approved_proposal_with_missing_total_fails_without_partial_message(api):
    proposal = load_catalog()["proposals"][0]
    value = api.client.post("/communications/templates", json=proposal).json()
    api.client.post(f"/communications/templates/{value['id']}/approve")
    response = api.client.post(
        "/communications/messages",
        json={
            "source_entity_id": str(api.source_id),
            "channel": "pec",
            "recipient": "synthetic@example.org",
            "template_id": value["id"],
        },
    )
    assert response.status_code == 409
    assert "importo_documento" in response.json()["detail"]
    assert api.client.get("/communications/messages").json()["total"] == 0


def test_portal_fields_match_existing_pdf_snapshot_preserving_leading_zeroes(portal_key):
    from app.modules.ruolo.services.notice_branding import notice_portal_html

    payload = {"taxpayer_portal_access": [access(portal_key)]}
    fields = template_variables(source(payload))
    assert fields["codice_utenza"] == "0001234"
    assert fields["pin_utenza"] == "0007654"
    html = notice_portal_html(payload)
    assert fields["codice_utenza"] in html and fields["pin_utenza"] in html


@pytest.mark.parametrize(
    "entries",
    [
        None,
        [],
        "x",
        ["x"],
        [{}, {}],
        [{}],
        [{"account_code": "123", "pin_encrypted": None}],
        [
            {
                "account_code": "\N{FULLWIDTH DIGIT ONE}\N{FULLWIDTH DIGIT TWO}\N{FULLWIDTH DIGIT THREE}",
                "pin_encrypted": "bad",
            }
        ],
        [{"account_code": "1" * 33, "pin_encrypted": "bad"}],
        [{"account_code": "123", "pin_encrypted": "not-an-encrypted-pin"}],
        [{"account_code": "123", "pin_encrypted": "non-ascii-é"}],
    ],
)
def test_missing_ambiguous_or_corrupt_access_never_selects_another_account(entries, portal_key):
    fields = template_variables(source({"taxpayer_portal_access": entries}))
    assert "pin_utenza" not in fields and "codice_utenza" not in fields
    with pytest.raises(policy.Conflict, match="pin_utenza"):
        policy.render_template("PIN: {{pin_utenza}}", fields)


@pytest.mark.parametrize(
    "pin",
    [
        "",
        "abc",
        "\N{FULLWIDTH DIGIT ONE}\N{FULLWIDTH DIGIT TWO}\N{FULLWIDTH DIGIT THREE}",
        "1" * 33,
    ],
)
def test_decrypted_invalid_pin_is_never_rendered(portal_key, pin):
    fields = template_variables(source({"taxpayer_portal_access": [access(portal_key, pin)]}))
    assert "pin_utenza" not in fields and "codice_utenza" not in fields


def test_missing_master_key_or_unreadable_pin_fail_closed_without_exposing_it(
    portal_key, monkeypatch
):
    payload = {"taxpayer_portal_access": [access(portal_key)]}

    def missing_key():
        raise ElaborazioneCredentialConfigurationError("synthetic configuration unavailable")

    monkeypatch.setattr(taxpayer_portal_access, "get_credential_fernet", missing_key)
    assert "pin_utenza" not in template_variables(source(payload))
    monkeypatch.setattr(taxpayer_portal_access, "get_credential_fernet", lambda: portal_key)
    payload["taxpayer_portal_access"][0]["pin_encrypted"] = portal_key.encrypt(b"\xff").decode()
    assert "pin_utenza" not in template_variables(source(payload))


@pytest.mark.parametrize("channel", ["pec", "email"])
def test_approved_office_template_requires_own_utenza_and_pin(api, channel):
    proposal = next(p for p in load_catalog()["proposals"] if p["channel"] == channel)
    value = api.client.post("/communications/templates", json=proposal).json()
    api.client.post(f"/communications/templates/{value['id']}/approve")
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        item.payload_json = {**item.payload_json, "saldo_amount": "10"}
        db.commit()
    response = api.client.post(
        "/communications/messages",
        json={
            "source_entity_id": str(api.source_id),
            "channel": channel,
            "recipient": "synthetic@example.org",
            "template_id": value["id"],
            "purpose": "courtesy" if channel == "email" else "pec_notice",
        },
    )
    assert response.status_code == 409 and "codice_utenza" in response.json()["detail"]
    assert api.client.get("/communications/messages").json()["total"] == 0
