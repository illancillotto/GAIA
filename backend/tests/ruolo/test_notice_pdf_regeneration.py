"""Generated reminder PDFs are rebuilt by the backend: when missing, or on request."""

from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.application_user import ApplicationUser
from app.modules.ruolo.models import (
    RuoloTributiPayment,
    RuoloTributiReminderBatchItem,
)
from app.modules.ruolo.notice_register_models import NoticeAudit, NoticeDocument
from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem
from app.modules.ruolo.services import notice_pdf_regeneration as regeneration
from app.modules.ruolo.services import poste_dispatch
from app.modules.ruolo.services.poste_dispatch_state import DispatchConflict
from app.modules.ruolo.services.tributi_reminder_service import reminder_storage_dir

from .test_tributi_api import (
    TestingSessionLocal,
    auth_headers,
    client,
    seed_avviso,
    seed_subject_with_nas,
)
from .test_tributi_api import setup_database as setup_database

RENDERER = "app.modules.ruolo.tributi_repositories.generate_batch_reminder_pdf"
TAX_CODE = "RSSMRA80A01H501Z"


@pytest.fixture
def renders(monkeypatch: pytest.MonkeyPatch) -> list[tuple[dict, Path]]:
    calls: list[tuple[dict, Path]] = []

    def render(payload: dict, *, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(f"%PDF-1.4 render {len(calls) + 1}".encode())
        calls.append((payload, output_path))

    monkeypatch.setattr(RENDERER, render)
    return calls


def _batch(
    tmp_path: Path,
    *,
    years: tuple[int, ...] = (2024,),
    preview: bool = False,
    tax_code: str = TAX_CODE,
) -> tuple[dict, list[str]]:
    subject_id = seed_subject_with_nas(tmp_path, tax_code=tax_code)
    avvisi = [
        seed_avviso(amount=100.0, anno=year, subject_id=subject_id, tax_code=tax_code)
        for year in years
    ]
    filters = {"anno_from": min(years), "anno_to": max(years), "years": list(years)}
    response = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=auth_headers(),
        json={
            "title": "Rigenerazione",
            "codice_fiscale": [tax_code],
            "filters": filters | ({"preview_only": True} if preview else {}),
            "template_path": "/tmp/template.docx",
        },
    )
    assert response.status_code == 200
    return response.json()["items"][0], avvisi


def _regenerate(item_id: str, mode: str = "template", username: str = "ruolo-tributi-admin"):
    return client.post(
        f"/ruolo/tributi/solleciti/items/{item_id}/regenerate",
        headers=auth_headers(username),
        json={"mode": mode},
    )


def _item(item_id: str) -> RuoloTributiReminderBatchItem:
    db = TestingSessionLocal()
    try:
        return db.get(RuoloTributiReminderBatchItem, UUID(item_id))
    finally:
        db.close()


def _audits(item_id: str) -> list[NoticeAudit]:
    db = TestingSessionLocal()
    try:
        document = db.scalar(select(NoticeDocument).where(NoticeDocument.source_key == item_id))
        return list(
            db.scalars(
                select(NoticeAudit)
                .where(NoticeAudit.document_id == document.id)
                .order_by(NoticeAudit.version)
            )
        )
    finally:
        db.close()


def _pay(avviso_id: str, amount: str) -> None:
    db = TestingSessionLocal()
    db.add(
        RuoloTributiPayment(
            avviso_id=UUID(avviso_id), amount=Decimal(amount), source="manual", status="valid"
        )
    )
    db.commit()
    db.close()


def test_a_lost_preview_pdf_is_rebuilt_in_the_persistent_storage_once(tmp_path, renders):
    item, _ = _batch(tmp_path, preview=True)
    Path(item["generated_document_path"]).unlink()
    first = client.get(item["download_url"], headers=auth_headers("ruolo-tributi-viewer"))
    second = client.get(item["download_url"], headers=auth_headers())
    assert first.status_code == second.status_code == 200
    assert first.content == b"%PDF-1.4 render 2"
    rebuilt = Path(_item(item["id"]).generated_document_path)
    assert rebuilt.parent == reminder_storage_dir() and rebuilt.is_file()
    assert len(renders) == 2
    assert renders[1][0] == _item(item["id"]).payload_json


def test_template_regeneration_rewrites_the_official_pdf_and_audits_it(tmp_path, renders):
    item, _ = _batch(tmp_path)
    response = _regenerate(item["id"])
    assert response.json() == {"item_id": item["id"], "outcome": "regenerated", "detail": None}
    assert Path(item["generated_document_path"]).read_bytes() == b"%PDF-1.4 render 2"
    assert _item(item["id"]).generated_document_path == item["generated_document_path"]
    audit = _audits(item["id"])[-1]
    assert (audit.version, audit.action, audit.reason) == (
        2,
        "regenerate_document",
        regeneration.REASONS["template"],
    )
    assert audit.after_json["mode"] == "template"
    assert audit.after_json["notice_number"] == item["payload_json"]["notice_number"]


def test_recompute_reads_payments_and_rules_again_keeping_the_notice_number(tmp_path, renders):
    item, [avviso_id] = _batch(tmp_path)
    _pay(avviso_id, "30.00")
    assert _regenerate(item["id"], "recompute").json()["outcome"] == "regenerated"
    payload = renders[-1][0]
    assert payload["paid_amount"] == "30.00 EUR" and payload["saldo_amount"] == "70.00 EUR"
    assert payload["notice_number"] == item["payload_json"]["notice_number"]
    stored = _item(item["id"])
    assert (
        stored.saldo_amount == Decimal("70.00")
        and stored.payload_json["paid_amount"] == "30.00 EUR"
    )
    assert _audits(item["id"])[-1].after_json["mode"] == "recompute"


def test_recompute_skips_a_settled_position_and_leaves_the_pdf(tmp_path, renders):
    item, [avviso_id] = _batch(tmp_path)
    _pay(avviso_id, "100.00")
    assert _regenerate(item["id"], "recompute").json() == {
        "item_id": item["id"],
        "outcome": "skipped",
        "detail": regeneration.CHANGED_SKIP,
    }
    assert len(renders) == 1 and len(_audits(item["id"])) == 1


def test_recompute_skips_a_reminder_without_positions(tmp_path, renders):
    item, _ = _batch(tmp_path)
    db = TestingSessionLocal()
    db.get(RuoloTributiReminderBatchItem, UUID(item["id"])).avviso_ids_json = []
    db.commit()
    db.close()
    assert _regenerate(item["id"], "recompute").json()["detail"] == regeneration.CHANGED_SKIP


def test_drafts_and_failed_reminders_are_not_regenerated(tmp_path, renders):
    draft, _ = _batch(tmp_path, years=(2022,))
    assert draft["status"] == "draft"
    assert _regenerate(draft["id"]).json()["detail"] == regeneration.DRAFT_SKIP
    db = TestingSessionLocal()
    db.get(RuoloTributiReminderBatchItem, UUID(draft["id"])).status = "failed"
    db.commit()
    db.close()
    assert _regenerate(draft["id"]).json() == {
        "item_id": draft["id"],
        "outcome": "skipped",
        "detail": "Nessun PDF definitivo da rigenerare (stato failed)",
    }


def test_a_rendering_failure_keeps_the_previous_pdf(tmp_path, renders, monkeypatch):
    item, _ = _batch(tmp_path)

    def broken(payload, *, output_path):
        raise RuntimeError("Chromium non trovato")

    monkeypatch.setattr(RENDERER, broken)
    assert _regenerate(item["id"]).json() == {
        "item_id": item["id"],
        "outcome": "failed",
        "detail": "Chromium non trovato",
    }
    assert Path(item["generated_document_path"]).read_bytes() == b"%PDF-1.4 render 1"
    Path(item["generated_document_path"]).unlink()
    response = client.get(item["download_url"], headers=auth_headers())
    assert response.status_code == 503
    assert response.json()["detail"] == "PDF non ricostruibile: Chromium non trovato"


def test_targets_list_final_pdfs_by_batch_and_count_excluded_drafts(tmp_path, renders):
    item, _ = _batch(tmp_path)
    draft, _ = _batch(tmp_path / "bozza", years=(2023,), tax_code="BNCLGU80A01H501Y")
    every = client.get(
        "/ruolo/tributi/solleciti/regeneration-targets", headers=auth_headers()
    ).json()
    assert [entry["item_id"] for entry in every["items"]] == [item["id"]] and every[
        "excluded_drafts"
    ] == 1
    assert every["items"][0] == {
        "item_id": item["id"],
        "batch_id": item["batch_id"],
        "display_name": item["display_name"],
        "codice_fiscale": TAX_CODE,
    }
    only_draft = client.get(
        f"/ruolo/tributi/solleciti/regeneration-targets?batch_id={draft['batch_id']}",
        headers=auth_headers(),
    ).json()
    assert only_draft == {"items": [], "excluded_drafts": 1}


def test_only_editors_regenerate(tmp_path, renders):
    item, _ = _batch(tmp_path)
    viewer = auth_headers("ruolo-tributi-viewer")
    assert (
        client.get("/ruolo/tributi/solleciti/regeneration-targets", headers=viewer).status_code
        == 403
    )
    assert _regenerate(item["id"], username="ruolo-tributi-viewer").status_code == 403
    assert _regenerate("00000000-0000-0000-0000-000000000000").status_code == 404


def test_a_nas_copy_is_overwritten_in_place(tmp_path, renders, monkeypatch):
    item, _ = _batch(tmp_path)
    remote = "/volume1/archivio/R/RSSMRA80A01H501Z/solleciti/avviso.pdf"
    db = TestingSessionLocal()
    db.get(RuoloTributiReminderBatchItem, UUID(item["id"])).generated_document_path = remote
    db.commit()
    db.close()
    uploads: list[str] = []
    monkeypatch.setattr(
        "app.modules.ruolo.tributi_repositories._upload_reminder_document_to_nas",
        lambda local_path, *, remote_path: uploads.append(remote_path),
    )
    assert _regenerate(item["id"]).json()["outcome"] == "regenerated"
    assert uploads == [remote] and _item(item["id"]).generated_document_path == remote


def test_a_poste_lot_rebuilds_a_lost_pdf_or_refuses_it(tmp_path, renders, monkeypatch):
    item, _ = _batch(tmp_path)
    Path(item["generated_document_path"]).unlink()
    db = TestingSessionLocal()
    actor = db.scalar(
        select(ApplicationUser.id).where(ApplicationUser.username == "ruolo-tributi-admin")
    )
    lot = poste_dispatch.create_lot(
        db, title="Poste", batch_item_ids=[UUID(item["id"])], actor_id=actor
    )
    assert (
        Path(_item_in(db, item["id"]).generated_document_path).read_bytes() == b"%PDF-1.4 render 2"
    )
    dispatch = db.scalar(select(PosteDispatchItem).where(PosteDispatchItem.lot_id == lot.id))
    assert dispatch.artifact_size == len(b"%PDF-1.4 render 2")
    db.rollback()
    db.close()

    monkeypatch.setattr(
        RENDERER,
        lambda payload, *, output_path: (_ for _ in ()).throw(
            RuntimeError("NAS non raggiungibile")
        ),
    )
    db = TestingSessionLocal()
    with pytest.raises(DispatchConflict, match="non ricostruibile: NAS non raggiungibile"):
        poste_dispatch.create_lot(
            db, title="Poste", batch_item_ids=[UUID(item["id"])], actor_id=actor
        )
    db.close()


def _item_in(db, item_id: str) -> RuoloTributiReminderBatchItem:
    return db.get(RuoloTributiReminderBatchItem, UUID(item_id))


def test_a_lost_single_reminder_is_rebuilt_and_audited():
    avviso_id = seed_avviso(amount=100.0, anno=2024)
    created = client.post(
        f"/ruolo/tributi/avvisi/{avviso_id}/reminders", headers=auth_headers(), json={}
    ).json()
    Path(created["generated_document_path"]).unlink()
    assert client.get(created["download_url"], headers=auth_headers()).status_code == 200
    db = TestingSessionLocal()
    document = db.scalar(select(NoticeDocument).where(NoticeDocument.source_key == created["id"]))
    audit = db.scalar(
        select(NoticeAudit).where(NoticeAudit.document_id == document.id, NoticeAudit.version == 2)
    )
    assert (audit.action, audit.reason) == ("regenerate_document", regeneration.MISSING_REASON)
    db.close()
