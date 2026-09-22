"""Private, visibly marked copies; never expose the original draft bytes."""

import hashlib
from io import BytesIO
from pathlib import Path
from subprocess import TimeoutExpired
from tempfile import TemporaryDirectory

from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.errors import PyPdfError
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import func, select
from sqlalchemy.orm import Session, defer

from app.modules.ruolo.notice_draft_models import NoticeDraft
from app.modules.ruolo.services.notice_draft_review import DraftReviewBlocked
from app.modules.ruolo.services.notice_drafts import MAX_ARTIFACT_BYTES
from app.modules.ruolo.services.tributi_reminder_service import convert_docx_to_pdf

PREVIEW_LABEL = "BOZZA - NON VALIDA PER INVIO"
MAX_PREVIEW_PAGES = 200


class PreviewUnavailable(RuntimeError):
    """The original stays private when conversion or PDF validation fails."""


def _read_artifact(engine, batch_id, item_id):
    with Session(engine) as db:
        draft = db.scalar(
            select(NoticeDraft)
            .options(defer(NoticeDraft.artifact))
            .where(
                NoticeDraft.batch_id == batch_id,
                NoticeDraft.source_id == item_id,
                NoticeDraft.source_system == "gaia_batch_item",
            )
        )
        if draft is None:
            raise LookupError("Bozza non trovata nel lotto")
        size = db.scalar(
            select(func.length(NoticeDraft.artifact)).where(NoticeDraft.id == draft.id)
        )
        if size > MAX_ARTIFACT_BYTES:
            raise DraftReviewBlocked("Artefatto oltre il limite di anteprima")
        artifact = draft.artifact
        if (
            not artifact
            or draft.artifact_format not in {"pdf", "docx"}
            or hashlib.sha256(artifact).hexdigest() != draft.artifact_sha256
        ):
            raise DraftReviewBlocked("Artefatto bozza non integro")
        return artifact, draft.artifact_format


def _as_pdf(content, artifact_format):
    if artifact_format == "pdf":
        return content
    with TemporaryDirectory(prefix="gaia_notice_preview_") as directory:
        source = Path(directory) / "preview.docx"
        source.write_bytes(content)
        path = convert_docx_to_pdf(source, output_dir=Path(directory))
        with path.open("rb") as stream:
            pdf = stream.read(MAX_ARTIFACT_BYTES + 1)
        if len(pdf) > MAX_ARTIFACT_BYTES:
            raise PreviewUnavailable("Anteprima PDF oltre il limite")
        return pdf


def _overlay(width, height):
    page = PageObject.create_blank_page(width=width, height=height)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica-Bold"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/FBozza"): font})}
    )
    stream = DecodedStreamObject()
    # Both the banner and diagonal text are part of every delivered PDF page.
    stream.set_data(
        (
            "q "
            f"0.65 0.1 0.1 rg BT /FBozza 11 Tf 12 {height - 17} Td ({PREVIEW_LABEL}) Tj ET "
            f"0.7 0.3 0.3 rg BT /FBozza 22 Tf "
            f"0.707 0.707 -0.707 0.707 30 {height / 3} Tm ({PREVIEW_LABEL}) Tj ET Q"
        ).encode("ascii")
    )
    page[NameObject("/Contents")] = stream
    return page


def marked_pdf(content):
    reader = PdfReader(BytesIO(content))
    if reader.is_encrypted or not 0 < len(reader.pages) <= MAX_PREVIEW_PAGES:
        raise PreviewUnavailable("PDF protetto, vuoto o con troppe pagine")
    writer = PdfWriter()
    for page in reader.pages:
        page.transfer_rotation_to_content()
        page.pop(NameObject("/Annots"), None)
        page.pop(NameObject("/AA"), None)
        page.merge_page(_overlay(float(page.mediabox.width), float(page.mediabox.height)))
        writer.add_page(page)
    writer.add_metadata({"/Title": PREVIEW_LABEL})
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def preview_item(engine, batch_id, item_id):
    content, artifact_format = _read_artifact(engine, batch_id, item_id)
    try:
        return marked_pdf(_as_pdf(content, artifact_format))
    except (RuntimeError, OSError, TimeoutExpired, PyPdfError, ValueError) as exc:
        raise PreviewUnavailable(
            "Anteprima non disponibile: verificare il PDF o il convertitore"
        ) from exc
