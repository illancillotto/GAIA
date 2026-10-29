"""Generated reminder PDFs are rebuilt by the backend, never at viewing time.

A missing local PDF is rebuilt from the saved snapshot. On request every PDF can be
rebuilt with the current template (same data) or with data and rules re-read now;
the notice number never changes. Each rebuild of a registered document is audited.
2022/2023 drafts keep their own confirmation protocol and are never touched here.
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import (
    RuoloAvviso,
    RuoloTributiReminder,
    RuoloTributiReminderBatch,
    RuoloTributiReminderBatchItem,
)
from app.modules.ruolo.notice_register_models import NoticeAudit, NoticeDocument
from app.modules.ruolo.services import notice_candidates, notice_drafts
from app.modules.ruolo.services.tributi_reminder_service import (
    generate_reminder_docx,
    reminder_storage_dir,
)

TEMPLATE = "template"
RECOMPUTE = "recompute"
REGENERABLE = {"generated", "generated_docx"}
MISSING_REASON = "PDF mancante: ricostruito dai dati salvati"
REASONS = {
    TEMPLATE: "Rigenerazione PDF con il template attuale, stessi dati",
    RECOMPUTE: "Rigenerazione PDF con dati e regole attuali, stesso numero avviso",
}
DRAFT_SKIP = "Bozza 2022/2023: segue il protocollo di conferma"
CHANGED_SKIP = "Posizione cambiata o saldata: generare un nuovo sollecito"
AMOUNT_FIELDS = ("due_amount", "paid_amount", "saldo_amount", "surcharge_amount", "interest_amount")


class RegenerationSkipped(Exception):
    """The sollecito stays as it is; the reason goes in the operator report."""


class RegenerationFailed(Exception):
    """Rendering failed; the transaction is rolled back and the previous PDF stays."""


def _missing_local(record) -> bool:
    path = record.generated_document_path
    return not repo.is_remote_reminder_document_path(path) and not Path(path).is_file()


def _target(record, suffix: str) -> Path:
    # NAS copies and existing files are rewritten in place; lost local files go to the persistent storage.
    if not _missing_local(record):
        return Path(record.generated_document_path).with_suffix(suffix)
    return reminder_storage_dir() / Path(record.generated_document_path).with_suffix(suffix).name


def _audit(db: Session, record, *, actor_id: int, mode: str, before: str, reason: str) -> None:
    source = "gaia_reminder" if isinstance(record, RuoloTributiReminder) else "gaia_batch_item"
    document = db.scalar(
        select(NoticeDocument)
        .where(NoticeDocument.source_system == source, NoticeDocument.source_key == str(record.id))
        .with_for_update()
    )
    if document is None:  # previews are not in the Notice Register
        return
    document.version += 1
    db.add(
        NoticeAudit(
            document_id=document.id,
            version=document.version,
            actor_id=actor_id,
            action="regenerate_document",
            reason=reason,
            before_json={"document_path": before},
            after_json={
                "document_path": record.generated_document_path,
                "mode": mode,
                "notice_number": (record.payload_json or {}).get("notice_number"),
            },
        )
    )


def _current_candidate(db: Session, item: RuoloTributiReminderBatchItem) -> dict | None:
    ids = set(item.avviso_ids_json or [])
    registered = db.scalars(
        select(RuoloAvviso.codice_fiscale_raw).where(
            RuoloAvviso.id.in_([UUID(value) for value in ids])
        )
    )
    tax_codes = sorted({code for code in map(repo._normalise_tax_code, registered) if code})
    if not tax_codes:
        return None
    collected = repo._collect_reminder_candidates(
        db,
        years=item.years_json or None,
        anno_from=None,
        anno_to=None,
        q=None,
        comune=None,
        codice_fiscale=tax_codes,
    )
    candidates = notice_candidates.batch_candidates(db, collected, tax_codes)
    return next((c for c in candidates if {str(a["id"]) for a in c["avvisi"]} == ids), None)


def _recompute(db: Session, item: RuoloTributiReminderBatchItem) -> None:
    payload = item.payload_json or {}
    candidate = _current_candidate(db, item) if payload.get("notice_number") else None
    if candidate is None:
        raise RegenerationSkipped(CHANGED_SKIP)
    batch = db.get(RuoloTributiReminderBatch, item.batch_id)
    fresh = repo._build_batch_item_payload(
        db,
        candidate,
        template_path=batch.template_path,
        generated_at=datetime.now(UTC),
        notice_number=payload["notice_number"],
        notice_emission_year=payload.get("notice_emission_year"),
        notice_progressive=payload.get("notice_progressive"),
        notice_reference_years=payload.get("notice_reference_years") or [],
    )
    item.payload_json = {**fresh, **notice_candidates.payload_overrides(candidate)}
    for field in AMOUNT_FIELDS:
        setattr(item, field, candidate.get(field))


def _skip_reason(item: RuoloTributiReminderBatchItem) -> str | None:
    if item.status in REGENERABLE and notice_drafts.publishable(item):
        return None
    if item.status == "draft" or item.generated_document_path:
        return DRAFT_SKIP
    return f"Nessun PDF definitivo da rigenerare (stato {item.status})"


def regenerate_batch_item(
    db: Session, item: RuoloTributiReminderBatchItem, mode: str, *, actor_id: int, reason: str
) -> None:
    skip = _skip_reason(item)
    if skip:
        raise RegenerationSkipped(skip)
    before = item.generated_document_path
    if mode == RECOMPUTE:
        _recompute(db, item)
    status, path, detail = repo._generate_batch_document(
        item.payload_json or {}, output_path=_target(item, ".pdf")
    )
    if status == "failed":
        raise RegenerationFailed(detail or "Generazione PDF non riuscita")
    item.status, item.generated_document_path, item.error_detail = status, path, detail
    _audit(db, item, actor_id=actor_id, mode=mode, before=before, reason=reason)
    db.flush()


def ensure_batch_item_document(
    db: Session, item: RuoloTributiReminderBatchItem, *, actor_id: int
) -> Path | None:
    if _skip_reason(item) is None and _missing_local(item):
        regenerate_batch_item(db, item, TEMPLATE, actor_id=actor_id, reason=MISSING_REASON)
    return repo.reminder_batch_item_document_path(item)


def ensure_reminder_document(
    db: Session, reminder: RuoloTributiReminder, *, actor_id: int
) -> Path | None:
    if notice_drafts.publishable(reminder) and _missing_local(reminder):
        before = reminder.generated_document_path
        notice_drafts.render_reminder(
            db, reminder, generate_reminder_docx, _target(reminder, ".docx")
        )
        _audit(db, reminder, actor_id=actor_id, mode=TEMPLATE, before=before, reason=MISSING_REASON)
        db.flush()
    return repo.reminder_document_path(reminder)


def regeneration_targets(
    db: Session, batch_id: UUID | None
) -> tuple[list[RuoloTributiReminderBatchItem], int]:
    # Drafts are listed only to count them as excluded in the report.
    query = select(RuoloTributiReminderBatchItem).where(
        RuoloTributiReminderBatchItem.status.in_(REGENERABLE | {"draft"})
    )
    if batch_id is not None:
        query = query.where(RuoloTributiReminderBatchItem.batch_id == batch_id)
    items = list(
        db.scalars(
            query.order_by(
                RuoloTributiReminderBatchItem.created_at, RuoloTributiReminderBatchItem.id
            )
        )
    )
    eligible = [
        item for item in items if item.status in REGENERABLE and notice_drafts.publishable(item)
    ]
    return eligible, len(items) - len(eligible)
