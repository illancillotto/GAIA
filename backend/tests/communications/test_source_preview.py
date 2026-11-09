"""Preview before account selection; byte equality is rechecked at draft creation."""

from uuid import uuid4

import pytest
from ruolo.test_notice_register_api import _headers
from sqlalchemy import func, select

from app.modules.communications import models, ruolo_source
from app.modules.communications.policy import sha256

from .conftest import create, pdf


def preview(api, **kwargs):
    return api.client.get(f"/communications/ruolo/candidates/{api.source_id}/preview", **kwargs)


def test_immediate_preview_is_read_only_and_needs_no_account(api):
    with api.session() as db:
        for account in db.scalars(select(models.CommunicationAccount)):
            account.active = False
        db.commit()
    response = preview(api)
    assert response.status_code == 200
    assert response.content == pdf()
    assert response.headers["X-Content-SHA256"] == sha256(pdf())
    assert response.headers["X-PDF-Pages"] == "3"
    assert response.headers["Cache-Control"] == "no-store, private"
    assert "X-Communication-Review" not in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    with api.session() as db:
        for model in (
            models.CommunicationMessage,
            models.CommunicationReview,
            models.CommunicationJob,
        ):
            assert db.scalar(select(func.count()).select_from(model)) == 0


def test_preview_bytes_become_identical_immutable_draft_snapshot(api):
    response = preview(api)
    value = create(api, expected_source_sha256=response.headers["X-Content-SHA256"])
    part = value["attachments"][0]
    content = api.client.get(
        f"/communications/messages/{value['id']}/attachments/{part['id']}/preview"
    )
    assert response.content == content.content
    assert part["sha256"] == response.headers["X-Content-SHA256"]


def test_changed_pdf_rejects_draft_without_side_effects(api):
    first = preview(api)
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        from pathlib import Path

        Path(item.generated_document_path).write_bytes(pdf(4))
    response = api.client.post(
        "/communications/messages",
        json={
            "source_entity_id": str(api.source_id),
            "channel": "pec",
            "recipient": "recipient@example.org",
            "subject": "Synthetic",
            "body": "Synthetic",
            "expected_source_sha256": first.headers["X-Content-SHA256"],
        },
    )
    assert response.status_code == 409 and "dopo l'anteprima" in response.text
    with api.session() as db:
        assert db.scalar(select(func.count()).select_from(models.CommunicationMessage)) == 0


@pytest.mark.parametrize("change", ["missing", "invalid", "pending", "year"])
def test_missing_invalid_or_nondefinitive_pdf_has_actionable_error(api, change):
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        if change == "missing":
            item.generated_document_path = None
        elif change == "invalid":
            from pathlib import Path

            Path(item.generated_document_path).write_bytes(b"not a pdf")
        elif change == "pending":
            item.status = "pending"
        else:
            item.years_json = [2022]
        db.commit()
    assert preview(api).status_code == 409


def test_preview_permissions_and_missing_identity(api):
    for user, status in ((2, 200), (3, 403), (4, 401), (5, 403)):
        assert preview(api, headers=_headers(user)).status_code == status
    assert api.client.get(f"/communications/ruolo/candidates/{uuid4()}/preview").status_code == 404
    assert api.client.get("/communications/ruolo/candidates/not-a-uuid/preview").status_code == 422
    response = api.client.post(
        "/communications/messages",
        json={
            "source_entity_id": str(api.source_id),
            "channel": "pec",
            "recipient": "test@example.org",
            "expected_source_sha256": "invalid",
        },
    )
    assert response.status_code == 422
