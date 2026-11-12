"""Explicit portal PDF revisions preserve originals, amounts, audit and dispatch exclusions."""

import io
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from ruolo.test_notice_register_api import _headers
from sqlalchemy import select

from app.modules.communications import ruolo_source, source_repair
from app.modules.communications.policy import sha256
from app.modules.ruolo.notice_register_models import NoticeAudit, NoticeDocument
from app.modules.ruolo.portal_access_models import RuoloTaxpayerPortalAccess
from app.modules.ruolo.services import taxpayer_portal_access

from .conftest import pdf


def text_pdf(text):
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {
                    NameObject("/F1"): DictionaryObject(
                        {
                            NameObject("/Type"): NameObject("/Font"),
                            NameObject("/Subtype"): NameObject("/Type1"),
                            NameObject("/BaseFont"): NameObject("/Helvetica"),
                        }
                    )
                }
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 30 800 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(stream)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


@pytest.fixture
def repair(api, monkeypatch):
    RuoloTaxpayerPortalAccess.__table__.create(api.engine, checkfirst=True)
    key = Fernet(Fernet.generate_key())
    monkeypatch.setattr(taxpayer_portal_access, "get_credential_fernet", lambda: key)
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        item.payload_json = {
            **item.payload_json,
            "saldo_amount": "10.00",
            "notification_amount": "11.55",
        }
        db.add(
            RuoloTaxpayerPortalAccess(
                account_code="0001234",
                tax_code=item.codice_fiscale,
                pin_encrypted=key.encrypt(b"0007654"),
                source_sha256="a" * 64,
            )
        )
        db.commit()
    monkeypatch.setattr(source_repair, "reminder_storage_dir", lambda: api.tmp_path)

    def render(payload, output_path):
        output_path.write_bytes(
            text_pdf(
                f"{payload['notice_number']} Codice utenza: 0001234 PIN: 0007654 Importo: 21,55"
            )
        )
        return "generated", str(output_path), None

    monkeypatch.setattr(source_repair.ruolo_source.repo, "_generate_batch_document", render)
    return key


def request(api, **kwargs):
    return api.client.post(
        f"/communications/ruolo/candidates/{api.source_id}/complete-portal-snapshot",
        params={"expected_source_sha256": sha256(pdf())},
        **kwargs,
    )


def test_explicit_revision_preserves_original_financial_snapshot_and_audit(api, repair):
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        oldpath = item.generated_document_path
        old = dict(item.payload_json)
    response = request(api)
    assert response.status_code == 200, response.text
    digest = response.json()["source_sha256"]
    assert digest != sha256(pdf())
    assert __import__("pathlib").Path(oldpath).read_bytes() == pdf()
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        assert item.generated_document_path != oldpath
        assert sha256(ruolo_source.read_pdf(item)) == digest
        assert {
            k: v
            for k, v in item.payload_json.items()
            if k not in ("taxpayer_portal_access", "template_path")
        } == {k: v for k, v in old.items() if k not in ("taxpayer_portal_access", "template_path")}
        fields = ruolo_source.template_variables(item)
        assert fields["codice_utenza"] == "0001234" and fields["pin_utenza"] == "0007654"
        audit = db.scalar(
            select(NoticeAudit).where(NoticeAudit.action == "complete_portal_snapshot")
        )
        assert audit.before_json["document_path"] == oldpath
        assert audit.before_json["pdf_sha256"] == sha256(pdf())
        assert "0007654" not in str(audit.after_json)
        doc = db.scalar(
            select(NoticeDocument).where(NoticeDocument.source_system == "gaia_batch_item")
        )
        assert doc.version == 2
        assert doc.original_json["payload"] == item.payload_json
    same = api.client.post(
        f"/communications/ruolo/candidates/{api.source_id}/complete-portal-snapshot",
        params={"expected_source_sha256": digest},
    )
    assert same.status_code == 200 and same.json() == response.json()
    assert request(api).status_code == 409


@pytest.mark.parametrize(
    "change",
    ["missing", "ambiguous", "invalid", "pending", "year", "failed_render", "missing_text"],
)
def test_failed_revision_never_changes_source(api, repair, monkeypatch, change):
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        original = item.generated_document_path
        access = db.scalar(select(RuoloTaxpayerPortalAccess))
        if change == "missing":
            db.delete(access)
        elif change == "ambiguous":
            db.add(
                RuoloTaxpayerPortalAccess(
                    account_code="999",
                    tax_code=item.codice_fiscale,
                    pin_encrypted=access.pin_encrypted,
                    source_sha256="b" * 64,
                )
            )
        elif change == "invalid":
            access.pin_encrypted = repair.encrypt(b"not-a-pin")
        elif change == "pending":
            item.status = "pending"
        elif change == "year":
            item.years_json = [2022]
        elif change == "failed_render":
            monkeypatch.setattr(
                source_repair.ruolo_source.repo,
                "_generate_batch_document",
                lambda *a, **k: ("failed", None, "synthetic"),
            )
        else:

            def blank(payload, output_path):
                output_path.write_bytes(pdf())
                return "generated", str(output_path), None

            monkeypatch.setattr(source_repair.ruolo_source.repo, "_generate_batch_document", blank)
        db.commit()
    assert request(api).status_code == 409
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        assert item.generated_document_path == original
        assert not item.payload_json.get("taxpayer_portal_access")
        assert (
            db.scalar(select(NoticeAudit).where(NoticeAudit.action == "complete_portal_snapshot"))
            is None
        )


def test_revision_requires_manage_and_valid_existing_source(api, repair):
    for user, status in ((2, 403), (3, 403), (4, 401), (5, 403)):
        assert request(api, headers=_headers(user)).status_code == status
    response = api.client.post(
        f"/communications/ruolo/candidates/{uuid4()}/complete-portal-snapshot",
        params={"expected_source_sha256": sha256(pdf())},
    )
    assert response.status_code == 404
    assert (
        api.client.post(
            f"/communications/ruolo/candidates/{api.source_id}/complete-portal-snapshot",
            params={"expected_source_sha256": "invalid"},
        ).status_code
        == 422
    )
