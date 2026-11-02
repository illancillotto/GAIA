"""Placeholder tax codes never merge recipients or select another taxpayer's data."""

from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import select

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloAvviso, RuoloTributiReminderBatchItem
from app.modules.ruolo.portal_access_models import RuoloTaxpayerPortalAccess
from app.modules.ruolo.services import notice_recipient_identity as identity
from app.modules.ruolo.services import taxpayer_portal_access as portal
from app.modules.ruolo.services.tributi_reminder_service import reminder_storage_dir

from .test_payer_assignments import HEIR, _person, _put
from .test_tributi_api import (
    TestingSessionLocal,
    auth_headers,
    client,
    seed_avviso,
    seed_subject_with_nas,
)
from .test_tributi_api import setup_database as setup_database


@pytest.mark.parametrize("code", ["C", "S", None, "", "01234567890"])
def test_invalid_identity_uses_the_avviso_and_never_resolves_an_archive(code):
    avviso = SimpleNamespace(
        id="original-id", codice_fiscale_raw=code, nominativo_raw="ORIGINAL NAME", subject_id=1
    )
    assert not identity.valid_tax_code(code)
    assert identity.display_name(avviso, "OTHER NAME") == "ORIGINAL NAME"
    assert identity.group_key(avviso) == "avviso:original-id"
    assert identity.subject_id(avviso) is None

    def forbidden(*_args):
        pytest.fail("An invalid CF must not resolve a taxpayer archive")

    assert identity.resolve_archive(None, code, 1, forbidden) == (None, None)


@pytest.mark.parametrize("code", ["rssmra80a01h501u", "00048250955"])
def test_valid_identity_keeps_the_updated_anagrafica_and_archive(code):
    avviso = SimpleNamespace(
        id="original-id", codice_fiscale_raw=code, nominativo_raw="ORIGINAL NAME", subject_id=1
    )
    assert identity.valid_tax_code(code)
    assert identity.display_name(avviso, "UPDATED NAME") == "UPDATED NAME"
    assert identity.display_name(avviso, None) == "ORIGINAL NAME"
    assert identity.group_key(avviso) == code.upper()
    assert identity.subject_id(avviso) == 1
    assert identity.resolve_archive("db", code, 1, lambda *_args: (1, "/archive")) == (
        1,
        "/archive",
    )


def _seed(tmp_path, code):
    subject = seed_subject_with_nas(tmp_path, tax_code=code)
    ids = [
        seed_avviso(tax_code=code, subject_id=subject, nominativo=name, amount=amount)
        for name, amount in [("FIRST RECIPIENT", 100), ("SECOND RECIPIENT", 200)]
    ]
    with TestingSessionLocal() as db:
        for index, value in enumerate(ids):
            avviso = db.get(RuoloAvviso, UUID(value))
            avviso.codice_utenza = f"UT-{index}"
            avviso.residenza_raw = f"VIA ORIGINALE {index + 1} 09170 ORISTANO OR"
            avviso.codice_cnc = f"12345678901234{index}"
        db.add(
            RuoloTaxpayerPortalAccess(
                account_code="UNSAFE",
                tax_code=code,
                pin_encrypted=b"unsafe",
                source_sha256="a" * 64,
            )
        )
        db.commit()
    return subject, ids


def _generate(monkeypatch, source):
    rendered = []

    def render(payload, *, output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.4 recipient test")
        rendered.append((payload, output_path))

    monkeypatch.setattr(repo, "generate_batch_reminder_pdf", render)
    policy = client.post(
        "/ruolo/tributi/calculation-policies",
        headers=auth_headers(),
        json={"name": "2024", "year_from": 2024, "year_to": 2024, "notice_number_source": source},
    )
    assert policy.status_code == 200, policy.text
    return rendered


def _batch(code):
    response = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=auth_headers(),
        json={"codice_fiscale": [code], "filters": {"years": [2024]}},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("code", ["C", "S"])
@pytest.mark.parametrize("source", ["gaia", "incass"])
def test_invalid_cf_produces_separate_notices_with_original_names_addresses_and_amounts(
    tmp_path, monkeypatch, code, source
):
    _seed(tmp_path, code)
    rendered = _generate(monkeypatch, source)
    response = client.get(
        "/ruolo/tributi/solleciti/candidates",
        params={"codice_fiscale": code},
        headers=auth_headers(),
    )
    assert response.status_code == 200, response.text
    candidates = response.json()["items"]
    assert len(candidates) == 2
    assert {c["display_name"] for c in candidates} == {"FIRST RECIPIENT", "SECOND RECIPIENT"}
    assert all(c["subject_id"] is None and not c["has_nas_folder"] for c in candidates)

    batch = _batch(code)
    assert batch["items_generated"] == batch["items_total"] == 2
    assert len({str(path) for _, path in rendered}) == 2
    for payload, path in rendered:
        assert path.parent == reminder_storage_dir()
        assert payload["display_name"] == payload["avvisi"][0]["nominativo_raw"]
        assert payload[portal.PORTAL_ACCESS_KEY] == []
        assert payload["avvisi"][0]["residenza_raw"].startswith("VIA ORIGINALE")
    assert {p["due_amount"] for p, _ in rendered} == {"100.00 EUR", "200.00 EUR"}
    assert all(i["subject_id"] is None and i["nas_folder_path"] is None for i in batch["items"])


def test_recompute_corrects_an_existing_wrong_recipient_without_changing_its_number(
    tmp_path, monkeypatch
):
    subject, _ = _seed(tmp_path, "C")
    rendered = _generate(monkeypatch, "incass")
    item = _batch("C")["items"][0]
    old_path = tmp_path / "wrong_archive" / "old.pdf"
    old_path.parent.mkdir()
    old_path.write_bytes(b"old document")
    with TestingSessionLocal() as db:
        record = db.get(RuoloTributiReminderBatchItem, UUID(item["id"]))
        record.display_name = "WRONG NAME"
        record.subject_id = subject
        record.nas_folder_path = str(old_path.parent)
        record.generated_document_path = str(old_path)
        record.payload_json = {**record.payload_json, "display_name": "WRONG NAME"}
        db.commit()
    response = client.post(
        f"/ruolo/tributi/solleciti/items/{item['id']}/regenerate",
        headers=auth_headers(),
        json={"mode": "recompute"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["outcome"] == "regenerated"
    with TestingSessionLocal() as db:
        record = db.get(RuoloTributiReminderBatchItem, UUID(item["id"]))
        assert record.subject_id is None and record.nas_folder_path is None
        assert record.display_name == record.payload_json["avvisi"][0]["nominativo_raw"]
        assert record.payload_json["notice_number"] == item["payload_json"]["notice_number"]
        assert Path(record.generated_document_path).parent == reminder_storage_dir()
    assert rendered[-1][0]["display_name"] != "WRONG NAME"
    assert old_path.read_bytes() == b"old document"


def test_normalization_does_not_turn_an_invalid_original_cf_into_a_trusted_recipient(
    tmp_path, monkeypatch
):
    # Removing punctuation would produce a valid CF and incorrectly re-enable its archive/access.
    code = "RSS-MRA80A01H501U"
    _seed(tmp_path, code)
    rendered = _generate(monkeypatch, "gaia")
    with TestingSessionLocal() as db:
        candidates, total = repo.list_reminder_candidates(db)
        assert total == 2
        assert all(c["codice_fiscale"] == code and c["subject_id"] is None for c in candidates)
        assert all(c["nas_folder_path"] is None for c in candidates)
    response = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=auth_headers(),
        json={"codice_fiscale": [], "filters": {"years": [2024]}},
    )
    assert response.status_code == 200, response.text
    assert response.json()["items_generated"] == 2
    assert all(payload["codice_fiscale"] == code for payload, _ in rendered)
    assert all(payload[portal.PORTAL_ACCESS_KEY] == [] for payload, _ in rendered)


def test_explicit_payer_assignment_still_takes_precedence_over_invalid_original_cf(
    tmp_path, monkeypatch
):
    _, ids = _seed(tmp_path, "C")
    _person(nas=str(tmp_path / "heir"))
    assert _put(ids[0]).status_code == 200
    _generate(monkeypatch, "gaia")
    batch = _batch("C")
    with TestingSessionLocal() as db:
        items = db.scalars(select(RuoloTributiReminderBatchItem)).all()
        heir = next(i for i in items if i.codice_fiscale == HEIR)
        assert heir.display_name == "FLORIS FABRIZIO" and heir.subject_id is not None
        original = next(i for i in items if i.codice_fiscale == "C")
        assert original.display_name == "SECOND RECIPIENT" and original.subject_id is None
    assert batch["items_generated"] == 2
