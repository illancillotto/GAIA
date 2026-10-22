from __future__ import annotations

import hashlib
import json
from zipfile import ZipFile

import pytest
from sqlalchemy import select
from step_fixtures import PDF, add_avviso, build_archive, scheda

from app.modules.elaborazioni.step import storage
from app.modules.elaborazioni.step.archive import import_archive, verify_archive
from app.modules.elaborazioni.step.models import StepContribuente, StepDocumento, StepRuoloLink


def test_import_archive_is_verified_linked_and_idempotent(db, storage_dirs, tmp_path) -> None:
    documents_root, _ = storage_dirs
    avviso_id = add_avviso(db, "01.02019000601804", 2019)
    unavailable = scheda("BBBBBB80A01G113X", pdf={"status": "unavailable"})
    unavailable["summary"]["DENOMINAZIONE"] = "BIANCHI"
    archive_path = tmp_path / "raccolta.zip"
    build_archive(archive_path, [scheda(), unavailable, scheda("CCCCCC80A01G113X")])
    progress: list[dict] = []

    first = import_archive(db, archive_path, job_id=None, batch_size=2, progress=progress.append)

    assert first["imported"] == 3 and first["changed"] == 3 and first["pagamenti"] == 6
    assert first["verification"] == {
        "contributors": 3,
        "documents": 3,
        "tributi": 3,
        "pdfs": 2,
        "unavailablePdfs": 1,
        "sha256": "abc",
    }
    assert first["links"] == {"linked": 3, "not_found": 0, "ambiguous": 0, "unrecognized": 0}
    assert [item["imported"] for item in progress] == [2, 3]
    stored = (
        documents_root
        / "14215"
        / hashlib.sha256(PDF).hexdigest()[:2]
        / f"{hashlib.sha256(PDF).hexdigest()}.pdf"
    )
    assert stored.read_bytes() == PDF
    statuses = sorted(db.scalars(select(StepDocumento.pdf_status)).all())
    assert statuses == ["downloaded", "downloaded", "unavailable"]
    assert (
        db.scalar(
            select(StepDocumento).where(StepDocumento.pdf_status == "unavailable")
        ).pdf_unavailable_reason
        == "PDF non disponibile su STEP"
    )
    assert {link.ruolo_avviso_id for link in db.scalars(select(StepRuoloLink)).all()} == {avviso_id}

    second = import_archive(db, archive_path, job_id=None)
    assert second["changed"] == 0 and second["links"]["linked"] == 0
    assert len(db.scalars(select(StepContribuente)).all()) == 3


def test_verify_archive_rejects_totals_mismatch(tmp_path) -> None:
    archive_path = tmp_path / "bad.zip"
    build_archive(archive_path, [scheda()], verification={"contributors": 2})
    with ZipFile(archive_path) as archive, pytest.raises(ValueError, match=r"verification\.json"):
        verify_archive(archive)


def test_import_rejects_corrupt_or_unsafe_pdfs(db, storage_dirs, tmp_path) -> None:
    archive_path = tmp_path / "corrupt.zip"
    build_archive(archive_path, [scheda()], pdf=b"%PDF-1.4 altered %%EOF")
    with pytest.raises(ValueError, match="SHA-256"):
        import_archive(db, archive_path, job_id=None)
    db.rollback()

    unsafe = scheda()
    unsafe["documents"][0]["pdf"]["file"] = "../escape.pdf"
    unsafe_path = tmp_path / "unsafe.zip"
    build_archive(unsafe_path, [unsafe])
    with pytest.raises(ValueError, match="Percorso PDF"):
        import_archive(db, unsafe_path, job_id=None)


def test_storage_validation_and_path_resolution(storage_dirs) -> None:
    documents_root, import_root = storage_dirs
    with pytest.raises(ValueError, match="PDF completo"):
        storage.validate_pdf(b"<html>")
    first = storage.store_pdf(PDF, cod_ent="14215", original_filename=None)
    again = storage.store_pdf(PDF, cod_ent="14215", original_filename="Doc.pdf")
    assert first.path == again.path and again.original_filename == "Doc.pdf"
    assert storage.resolve_stored_pdf(first.path) == (documents_root / first.path).resolve()
    with pytest.raises(FileNotFoundError):
        storage.resolve_stored_pdf("../outside.pdf")
    with pytest.raises(FileNotFoundError):
        storage.resolve_stored_pdf("14215/missing.pdf")

    import_root.mkdir()
    (import_root / "raccolta.zip").write_bytes(b"zip")
    (import_root / "notes.txt").write_text(json.dumps({}))
    assert (
        storage.resolve_import_archive("raccolta.zip") == (import_root / "raccolta.zip").resolve()
    )
    for name in ("notes.txt", "missing.zip", "../raccolta.zip"):
        with pytest.raises(ValueError, match="Archivio STEP"):
            storage.resolve_import_archive(name)


def test_storage_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STEP_DOCUMENT_STORAGE_PATH", raising=False)
    monkeypatch.delenv("STEP_IMPORT_ROOT", raising=False)
    assert str(storage.document_storage_root()) == "/data/catasto/step/documents"
    assert str(storage.import_root()) == "/data/catasto/step/import"
