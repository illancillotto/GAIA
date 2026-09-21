"""Private drafts only: confirmation/export are deliberately unavailable here."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from sqlalchemy import inspect, select

from app.modules.ruolo.models import RuoloAvviso, RuoloTributiNoticeNumber, RuoloTributiReminder
from app.modules.ruolo.notice_draft_models import NoticeDraft
from app.modules.ruolo.services.notice_draft_inputs import basis_for

PROTECTED_YEARS = {2022, 2023, "2022", "2023"}
PRIVATE_BATCH_KEY = "gaia_private_draft"
MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
DRAFT_MESSAGE = "Bozza privata: conferma ed esportazione non ancora disponibili"


def requires_draft(years) -> bool:
    return any(year in PROTECTED_YEARS for year in years)


def prepare_batch(batch, candidates) -> None:
    protected = any(requires_draft(candidate["years"]) for candidate in candidates)
    batch.filters_json = {**(batch.filters_json or {}), PRIVATE_BATCH_KEY: protected}
    for candidate in candidates:
        candidate[PRIVATE_BATCH_KEY] = protected


def finish_batch(batch):
    if batch.filters_json.get(PRIVATE_BATCH_KEY) and batch.items_failed < batch.items_total:
        batch.status = "review_required"
    return batch


def _persist(db, record, path: Path, *, source: str, actor_id: int):
    if actor_id is None:
        raise ValueError("Operatore obbligatorio per la bozza")
    if path.is_symlink():
        raise ValueError("Percorso artefatto bozza non valido")
    with path.open("rb") as stream:
        artifact = stream.read(MAX_ARTIFACT_BYTES + 1)
    if not artifact or len(artifact) > MAX_ARTIFACT_BYTES:
        raise ValueError("Artefatto bozza vuoto o superiore a 32 MiB")
    manifest = json.loads(json.dumps(record.payload_json))
    draft = NoticeDraft(
        source_system=source,
        source_id=record.id,
        batch_id=getattr(record, "batch_id", None),
        actor_id=actor_id,
        manifest=manifest,
        input_basis=basis_for(db),
        artifact=artifact,
        artifact_sha256=hashlib.sha256(artifact).hexdigest(),
        artifact_format=path.suffix.lstrip("."),
    )
    db.add(draft)
    record.generated_document_path = None
    record.status = "draft"
    db.flush()


def render_reminder(db, record, render, output_path: Path) -> None:
    payload = record.payload_json
    if not requires_draft([payload["anno_tributario"]]):
        render(payload, output_path=output_path)
        record.generated_document_path = str(output_path)
        return
    # TemporaryDirectory is 0700. Durable bytes live in SQL, never on the NAS.
    with TemporaryDirectory(prefix="gaia_notice_draft_") as directory:
        path = Path(directory) / "draft.docx"
        render(payload, output_path=path)
        _persist(db, record, path, source="gaia_reminder", actor_id=record.generated_by)


def render_batch_item(db, item, batch, render, output_path: Path):
    if not batch.filters_json.get(PRIVATE_BATCH_KEY):
        return render(item.payload_json or {}, output_path=output_path)
    with TemporaryDirectory(prefix="gaia_notice_draft_") as directory:
        path = Path(directory) / "draft.pdf"
        status, rendered_path, detail = render(item.payload_json or {}, output_path=path)
        if status not in {"generated", "generated_docx"}:
            return status, None, detail
        expected = path.with_suffix(".docx") if status == "generated_docx" else path
        if rendered_path != str(expected) or expected.is_symlink():
            raise ValueError("Percorso artefatto bozza non valido")
        _persist(db, item, expected, source="gaia_batch_item", actor_id=batch.generated_by)
    return "draft", None, DRAFT_MESSAGE


def retain_draft_number(db, item) -> None:
    if item.status == "draft":
        reservation = db.get(RuoloTributiNoticeNumber, item.notice_number_id)
        if reservation is not None:
            reservation.status = "draft"


def published_document_path(record) -> Path | None:
    payload = getattr(record, "payload_json", None) or {}
    years = getattr(record, "years_json", None) or [payload.get("anno_tributario")]
    if (
        requires_draft(years)
        or _protected_linked_year(record)
        or getattr(record, "status", None) == "draft"
        or not record.generated_document_path
    ):
        return None
    path = Path(record.generated_document_path)
    if path.is_file() or str(path).startswith("/volume1/"):
        return path
    return None


def _protected_linked_year(record) -> bool:
    state = inspect(record, raiseerr=False)
    if state is None or state.session is None:
        return False
    if isinstance(record, RuoloTributiReminder):
        ids = [record.avviso_id]
    else:
        ids = [UUID(value) for value in (record.avviso_ids_json or [])]
    return (
        state.session.scalar(
            select(RuoloAvviso.id)
            .where(RuoloAvviso.id.in_(ids), RuoloAvviso.anno_tributario.in_([2022, 2023]))
            .limit(1)
        )
        is not None
    )
