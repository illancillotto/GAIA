"""Private artifacts are durable, but never downloadable as confirmed notices."""

import hashlib
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import (
    RuoloAvviso,
    RuoloTributiReminder,
    RuoloTributiReminderBatch,
    RuoloTributiReminderBatchItem,
)
from app.modules.ruolo.notice_draft_models import NoticeDraft
from app.modules.ruolo.notice_register_models import NoticeDocument
from app.modules.ruolo.services import notice_drafts as drafts

from .test_notice_generation_concurrency import generation_engine as generation_engine
from .test_tributi_api import TestingSessionLocal, auth_headers, client, engine, seed_avviso
from .test_tributi_api import setup_database as setup_database


def _render(payload, *, output_path):
    assert output_path.parent.stat().st_mode & 0o777 == 0o700
    output_path.write_bytes(b"synthetic draft artifact")


@pytest.mark.parametrize("year", [2022, 2023])
def test_single_draft_is_private_and_durable(year, monkeypatch):
    avviso_id = seed_avviso(anno=year, verified_history=True)
    paths = []

    def render(payload, *, output_path):
        paths.append(output_path)
        _render(payload, output_path=output_path)

    monkeypatch.setattr(repo, "generate_reminder_docx", render)
    result = client.post(
        f"/ruolo/tributi/avvisi/{avviso_id}/reminders", headers=auth_headers(), json={}
    )
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["status"] == "draft"
    assert data["generated_document_path"] is data["download_url"] is None
    assert not paths[0].parent.exists()
    with TestingSessionLocal() as db:
        draft = db.scalar(select(NoticeDraft))
        assert draft.actor_id == 1 and draft.batch_id is None
        assert draft.state == "review_required"
        assert draft.artifact == b"synthetic draft artifact"
        assert draft.artifact_sha256 == hashlib.sha256(draft.artifact).hexdigest()
        assert draft.manifest == data["payload_json"]
        assert draft.source_id == UUID(data["id"])
        assert (
            db.scalar(select(NoticeDocument).where(NoticeDocument.source_system == "gaia_reminder"))
            is None
        )
    download = client.get(f"/ruolo/tributi/reminders/{data['id']}/download", headers=auth_headers())
    assert download.status_code == 404


@pytest.mark.parametrize("preview_only", [False, True])
def test_whole_mixed_batch_is_private_without_nas(preview_only, monkeypatch):
    seed_avviso(anno=2022, verified_history=True)
    seed_avviso(anno=2024, tax_code="BNCLGU80A01H501Y")
    monkeypatch.setattr(repo, "_generate_and_store_batch_reminder_pdf", _render)
    result = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=auth_headers(),
        json={
            "codice_fiscale": [],
            "filters": {
                "years": [2022, 2024],
                "preview_only": preview_only,
                "gaia_private_draft": False,
            },
        },
    )
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["status"] == "review_required" and data["items_generated"] == 0
    assert len(data["items"]) == 2
    for item in data["items"]:
        assert item["status"] == "draft"
        assert item["download_url"] is item["generated_document_path"] is None
        assert (
            client.get(
                f"/ruolo/tributi/solleciti/items/{item['id']}/download", headers=auth_headers()
            ).status_code
            == 404
        )
    with TestingSessionLocal() as db:
        assert len(db.scalars(select(NoticeDraft)).all()) == 2
        assert (
            db.scalar(
                select(NoticeDocument).where(NoticeDocument.source_system == "gaia_batch_item")
            )
            is None
        )


def test_draft_and_record_rollback_together(monkeypatch):
    avviso_id = UUID(seed_avviso(anno=2022, verified_history=True))
    monkeypatch.setattr(repo, "generate_reminder_docx", _render)
    with TestingSessionLocal() as db:
        repo.create_generated_reminder(db, avviso=db.get(RuoloAvviso, avviso_id), generated_by=1)
        assert db.scalar(select(NoticeDraft)) is not None
        db.rollback()
    with TestingSessionLocal() as db:
        assert db.scalar(select(NoticeDraft)) is None
        assert db.scalar(select(RuoloTributiReminder)) is None


def test_render_failure_removes_private_directory(monkeypatch):
    avviso_id = UUID(seed_avviso(anno=2022, verified_history=True))
    paths = []

    def fail(payload, *, output_path):
        paths.append(output_path)
        _render(payload, output_path=output_path)
        raise OSError("render failed")

    monkeypatch.setattr(repo, "generate_reminder_docx", fail)
    with TestingSessionLocal() as db, pytest.raises(OSError, match="render failed"):
        repo.create_generated_reminder(db, avviso=db.get(RuoloAvviso, avviso_id), generated_by=1)
    assert not paths[0].parent.exists()


def test_artifact_validation_and_uniqueness(tmp_path, monkeypatch):
    path = tmp_path / "draft.pdf"
    record = SimpleNamespace(id=uuid4(), payload_json={"avvisi": []})
    with TestingSessionLocal() as db:
        with pytest.raises(ValueError, match="Operatore"):
            drafts._persist(db, record, path, source="test", actor_id=None)
        link = tmp_path / "link.pdf"
        link.symlink_to(path)
        with pytest.raises(ValueError, match="Percorso"):
            drafts._persist(db, record, link, source="test", actor_id=1)
        path.write_bytes(b"")
        with pytest.raises(ValueError, match="vuoto"):
            drafts._persist(db, record, path, source="test", actor_id=1)
        monkeypatch.setattr(drafts, "MAX_ARTIFACT_BYTES", 1)
        path.write_bytes(b"ab")
        with pytest.raises(ValueError, match="32 MiB"):
            drafts._persist(db, record, path, source="test", actor_id=1)
        path.write_bytes(b"a")
        drafts._persist(db, record, path, source="test", actor_id=1)
        record.payload_json["avvisi"].append("changed")
        assert db.scalar(select(NoticeDraft)).manifest == {"avvisi": []}
        with pytest.raises(IntegrityError):
            drafts._persist(db, record, path, source="test", actor_id=1)
        db.rollback()


@pytest.mark.parametrize("status", ["generated_docx", "failed", "pending", "wrong_path", "symlink"])
def test_batch_render_outcomes(status, tmp_path):
    batch = RuoloTributiReminderBatch(
        id=uuid4(), generated_by=1, filters_json={drafts.PRIVATE_BATCH_KEY: True}
    )
    item = SimpleNamespace(id=uuid4(), batch_id=batch.id, payload_json={})
    paths = []

    def render(payload, *, output_path):
        paths.append(output_path)
        if status == "generated_docx":
            output_path = output_path.with_suffix(".docx")
            _render(payload, output_path=output_path)
        if status == "symlink":
            output_path.symlink_to(tmp_path / "outside.pdf")
        if status in {"wrong_path", "symlink"}:
            return "generated", "wrong" if status == "wrong_path" else str(output_path), None
        return status, str(output_path), "detail"

    with TestingSessionLocal() as db:
        db.add(batch)
        db.flush()
        if status in {"wrong_path", "symlink"}:
            with pytest.raises(ValueError, match="Percorso"):
                drafts.render_batch_item(db, item, batch, render, tmp_path / "final.pdf")
        else:
            result = drafts.render_batch_item(db, item, batch, render, tmp_path / "final.pdf")
            assert result[0] == ("draft" if status == "generated_docx" else status)
            assert result[1] is None
        assert not paths[0].parent.exists()


def test_legacy_download_cannot_release_protected_artifact(tmp_path):
    path = tmp_path / "old.docx"
    path.write_bytes(b"old document")
    record = SimpleNamespace(
        generated_document_path=str(path),
        payload_json={"anno_tributario": 2022},
        status="generated",
    )
    assert drafts.published_document_path(record) is None
    record.payload_json = {}
    record.years_json = [2024, "2023"]
    assert drafts.published_document_path(record) is None
    record.years_json, record.status = [2024], "draft"
    assert drafts.published_document_path(record) is None
    with TestingSessionLocal() as db:
        drafts.retain_draft_number(db, SimpleNamespace(status="draft", notice_number_id=uuid4()))


def test_draft_migration_round_trip():
    NoticeDraft.__table__.drop(engine)
    migration = load_python_file(
        str(Path(__file__).parents[2] / "alembic" / "versions"), "20260921_1500_notice_drafts.py"
    )
    basis_migration = load_python_file(
        str(Path(__file__).parents[2] / "alembic" / "versions"),
        "20260921_1900_notice_draft_input_basis.py",
    )
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            basis_migration.upgrade()
            connection.execute(NoticeDraft.__table__.select())
            basis_migration.downgrade()
            migration.downgrade()
            migration.upgrade()
            basis_migration.upgrade()


@pytest.mark.parametrize("kind", ["single", "batch"])
def test_old_download_with_missing_year_payload_is_still_blocked(kind, tmp_path):
    avviso_id = UUID(seed_avviso(anno=2022))
    path = tmp_path / "old.pdf"
    path.write_bytes(b"old published artifact")
    with TestingSessionLocal() as db:
        if kind == "single":
            record = RuoloTributiReminder(
                avviso_id=avviso_id, status="generated", generated_document_path=str(path)
            )
            endpoint = "reminders"
        else:
            batch = RuoloTributiReminderBatch()
            db.add(batch)
            db.flush()
            record = RuoloTributiReminderBatchItem(
                batch_id=batch.id,
                codice_fiscale="TEST",
                avviso_ids_json=[str(avviso_id)],
                years_json=[2024],
                status="generated",
                generated_document_path=str(path),
            )
            endpoint = "solleciti/items"
        db.add(record)
        db.commit()
        record_id = record.id
    assert (
        client.get(
            f"/ruolo/tributi/{endpoint}/{record_id}/download", headers=auth_headers()
        ).status_code
        == 404
    )


def test_protected_batch_all_failures_not_reviewable(monkeypatch):
    seed_avviso(anno=2023, verified_history=True)
    monkeypatch.setattr(
        repo,
        "_generate_batch_document",
        lambda *args, **kwargs: ("failed", None, "Rendering failed"),
    )
    result = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=auth_headers(),
        json={"codice_fiscale": [], "filters": {"years": [2023]}},
    )
    assert result.status_code == 200
    assert result.json()["status"] == "failed"
    with TestingSessionLocal() as db:
        assert db.scalar(select(NoticeDraft)) is None


@pytest.mark.postgres
def test_draft_migration_postgres_parity(generation_engine):
    from alembic.autogenerate import compare_metadata
    from sqlalchemy import MetaData

    NoticeDraft.__table__.drop(generation_engine)
    migration = load_python_file(
        str(Path(__file__).parents[2] / "alembic" / "versions"), "20260921_1500_notice_drafts.py"
    )
    basis_migration = load_python_file(
        str(Path(__file__).parents[2] / "alembic" / "versions"),
        "20260921_1900_notice_draft_input_basis.py",
    )
    metadata = MetaData()
    NoticeDraft.__table__.to_metadata(metadata)
    with generation_engine.begin() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()
            basis_migration.upgrade()
            # Reflect the other tables, retaining the draft model for comparison.
            metadata.reflect(connection, extend_existing=False)
            assert compare_metadata(context, metadata) == []
            basis_migration.downgrade()
            migration.downgrade()
            migration.upgrade()
            basis_migration.upgrade()
