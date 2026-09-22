import hashlib
import shutil
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import pytest
from pypdf import PdfReader, PdfWriter
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.modules.ruolo.notice_draft_models import NoticeDraft
from app.modules.ruolo.services import notice_preview as service


def pdf_bytes(*, pages=2, encrypted=False):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    if encrypted:
        writer.encrypt("password")
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


@pytest.fixture
def preview():
    engine = create_engine("sqlite://")
    NoticeDraft.__table__.create(engine)
    batch_id, item_id = uuid4(), uuid4()
    artifact = pdf_bytes()
    with Session(engine) as db, db.begin():
        db.add(
            NoticeDraft(
                source_system="gaia_batch_item",
                source_id=item_id,
                batch_id=batch_id,
                actor_id=1,
                manifest={},
                artifact=artifact,
                artifact_format="pdf",
                artifact_sha256=hashlib.sha256(artifact).hexdigest(),
            )
        )
    yield engine, batch_id, item_id, artifact
    engine.dispose()


def test_every_page_is_marked_original_is_unchanged(preview):
    engine, batch_id, item_id, original = preview
    result = service.preview_item(engine, batch_id, item_id)
    assert result != original
    reader = PdfReader(BytesIO(result))
    assert len(reader.pages) == 2
    assert all(service.PREVIEW_LABEL in page.extract_text() for page in reader.pages)
    with Session(engine) as db:
        assert db.scalar(select(NoticeDraft)).artifact == original


def test_item_must_belong_to_requested_batch(preview):
    engine, _, item_id, _ = preview
    with pytest.raises(LookupError):
        service.preview_item(engine, uuid4(), item_id)


@pytest.mark.parametrize("fault", ["size", "hash", "format", "empty"])
def test_invalid_private_artifacts_refused(preview, monkeypatch, fault):
    engine, batch_id, item_id, _ = preview
    with Session(engine) as db, db.begin():
        draft = db.scalar(select(NoticeDraft))
        if fault == "size":
            monkeypatch.setattr(service, "MAX_ARTIFACT_BYTES", 1)
        elif fault == "hash":
            draft.artifact_sha256 = "f" * 64
        elif fault == "format":
            draft.artifact_format = "html"
        else:
            draft.artifact = b""
    with pytest.raises(service.DraftReviewBlocked):
        service.preview_item(engine, batch_id, item_id)


@pytest.mark.parametrize("kind", ["encrypted", "empty", "many", "malformed"])
def test_unsupported_pdf_fails_closed(preview, monkeypatch, kind):
    engine, batch_id, item_id, _ = preview
    content = (
        b"bad"
        if kind == "malformed"
        else pdf_bytes(pages=0 if kind == "empty" else 2, encrypted=kind == "encrypted")
    )
    if kind == "many":
        monkeypatch.setattr(service, "MAX_PREVIEW_PAGES", 1)
    monkeypatch.setattr(service, "_read_artifact", lambda *args: (content, "pdf"))
    with pytest.raises(service.PreviewUnavailable):
        service.preview_item(engine, batch_id, item_id)


def test_docx_conversion_is_private_and_output_is_marked(preview, monkeypatch):
    engine, batch_id, item_id, _ = preview
    paths = []

    def convert(source, *, output_dir):
        assert source.read_bytes() == b"private docx"
        assert output_dir.stat().st_mode & 0o777 == 0o700
        result = output_dir / "preview.pdf"
        result.write_bytes(pdf_bytes())
        paths.append(result)
        return result

    monkeypatch.setattr(service, "_read_artifact", lambda *args: (b"private docx", "docx"))
    monkeypatch.setattr(service, "convert_docx_to_pdf", convert)
    result = service.preview_item(engine, batch_id, item_id)
    assert service.PREVIEW_LABEL in PdfReader(BytesIO(result)).pages[0].extract_text()
    assert not paths[0].exists()


def test_conversion_failures_and_oversized_output_are_not_original_downloads(
    preview, monkeypatch, tmp_path
):
    engine, batch_id, item_id, _ = preview
    monkeypatch.setattr(service, "_read_artifact", lambda *args: (b"docx", "docx"))
    monkeypatch.setattr(
        service, "convert_docx_to_pdf", lambda *args, **kwargs: Path("/missing/preview.pdf")
    )
    with pytest.raises(service.PreviewUnavailable):
        service.preview_item(engine, batch_id, item_id)
    output = tmp_path / "oversized.pdf"
    output.write_bytes(b"large")
    monkeypatch.setattr(service, "MAX_ARTIFACT_BYTES", 1)
    monkeypatch.setattr(service, "convert_docx_to_pdf", lambda *args, **kwargs: output)
    with pytest.raises(service.PreviewUnavailable):
        service.preview_item(engine, batch_id, item_id)


def test_real_libreoffice_preview_preserves_text_and_adds_watermark(preview):
    if not shutil.which("libreoffice"):
        pytest.skip("LibreOffice richiesto per lo smoke DOCX reale")
    content = BytesIO()
    with ZipFile(content, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        )
        archive.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        )
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Sollecito di prova 2022/2023</w:t></w:r></w:p></w:body></w:document>',
        )
    engine, batch_id, item_id, _ = preview
    with Session(engine) as db, db.begin():
        draft = db.scalar(select(NoticeDraft))
        draft.artifact = content.getvalue()
        draft.artifact_format = "docx"
        draft.artifact_sha256 = hashlib.sha256(draft.artifact).hexdigest()
    result = service.preview_item(engine, batch_id, item_id)
    text = PdfReader(BytesIO(result)).pages[0].extract_text()
    assert "Sollecito di prova 2022/2023" in text
    assert service.PREVIEW_LABEL in text
