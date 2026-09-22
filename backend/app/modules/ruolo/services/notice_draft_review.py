"""Whole-generation integrity checks and serialized private-lot confirmation.

The review-only function never authorizes export. Confirmation is a separate
transaction that persists the reviewed digest and only promotes reservations;
it does not send or export documents.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, defer

from app.modules.ruolo.models import (
    RuoloTributiNoticeNumber,
    RuoloTributiReminder,
    RuoloTributiReminderBatch,
    RuoloTributiReminderBatchItem,
)
from app.modules.ruolo.notice_confirmation_models import NoticeGenerationConfirmation
from app.modules.ruolo.notice_draft_models import NoticeDraft
from app.modules.ruolo.services.notice_revision import (
    GenerationRevision,
    lock_revision,
    read_revision,
)
from app.modules.ruolo.services.tributi_notice_registry import build_notice_identity_key

MAX_REVIEW_BYTES = 64 * 1024 * 1024
MAX_REVIEW_ITEMS = 100


class DraftReviewBlocked(ValueError):
    """The generation must be regenerated or repaired, never partially approved."""


@dataclass(frozen=True)
class DraftInputReview:
    generation_id: UUID
    draft_ids: tuple[UUID, ...]
    digest: str
    basis: GenerationRevision
    authorizes_dispatch: bool = False
    confirmation_available: bool = False


def _basis(drafts) -> GenerationRevision:
    basis = drafts[0].input_basis
    if not isinstance(basis, dict) or any(draft.input_basis != basis for draft in drafts):
        raise DraftReviewBlocked("Revisione assente o incoerente nel lotto: rigenerare")
    if (
        type(basis.get("version")) is not int
        or basis["version"] != 1
        or type(basis.get("revision")) is not int
        or basis["revision"] < 0
        or basis.get("calculation_date") != date.today().isoformat()
    ):
        raise DraftReviewBlocked("Revisione o data di calcolo non valida: rigenerare")
    try:
        return GenerationRevision(UUID(basis["epoch"]), basis["revision"])
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise DraftReviewBlocked("Epoch di generazione non valida: rigenerare") from exc


def _records(db, generation_id, batch, *, expected_status="review_required"):
    if not batch:
        record = db.scalar(
            select(RuoloTributiReminder)
            .where(RuoloTributiReminder.id == generation_id)
            .with_for_update()
        )
        if record is None:
            raise DraftReviewBlocked("Generazione non trovata")
        return [record]
    parent = db.scalar(
        select(RuoloTributiReminderBatch)
        .where(RuoloTributiReminderBatch.id == generation_id)
        .with_for_update()
    )
    if parent is None:
        raise DraftReviewBlocked("Lotto non trovato")
    records = list(
        db.scalars(
            select(RuoloTributiReminderBatchItem)
            .where(RuoloTributiReminderBatchItem.batch_id == generation_id)
            .order_by(RuoloTributiReminderBatchItem.id)
            .with_for_update()
        )
    )
    if (
        parent.status != expected_status
        or parent.items_generated != 0
        or parent.items_failed != 0
        or not records
        or parent.items_total != len(records)
    ):
        raise DraftReviewBlocked("Lotto incompleto o non in revisione")
    return records


def _drafts(db, generation_id, records, batch):
    ids = [record.id for record in records]
    source = "gaia_batch_item" if batch else "gaia_reminder"
    scope = (NoticeDraft.source_system == source) & NoticeDraft.source_id.in_(ids)
    if batch:
        scope = or_(scope, NoticeDraft.batch_id == generation_id)
    drafts = list(
        db.scalars(
            select(NoticeDraft)
            .options(defer(NoticeDraft.artifact))
            .where(scope)
            .order_by(NoticeDraft.id)
            .with_for_update()
        )
    )
    if len(drafts) != len(records) or {draft.source_id for draft in drafts} != set(ids):
        raise DraftReviewBlocked("Artefatti mancanti o estranei al lotto")
    if any(
        draft.source_system != source or draft.batch_id != (generation_id if batch else None)
        for draft in drafts
    ):
        raise DraftReviewBlocked("Provenienza degli artefatti incoerente")
    return drafts


def _check_review_size(db, drafts):
    size = db.scalar(
        select(func.sum(func.length(NoticeDraft.artifact))).where(
            NoticeDraft.id.in_([draft.id for draft in drafts])
        )
    )
    if len(drafts) > MAX_REVIEW_ITEMS or size > MAX_REVIEW_BYTES:
        raise DraftReviewBlocked("Lotto oltre i limiti di revisione: suddividere la generazione")


def _integrity(records, drafts, *, expected_status="draft") -> str:
    payloads = {record.id: record.payload_json for record in records}
    if any(record.status != expected_status or record.generated_document_path for record in records):
        raise DraftReviewBlocked("Generazione non privata o stato non valido")
    manifest = []
    for draft in drafts:
        if (
            draft.state != "review_required"
            or draft.manifest != payloads[draft.source_id]
            or not draft.artifact
            or draft.artifact_format not in {"docx", "pdf"}
            or hashlib.sha256(draft.artifact).hexdigest() != draft.artifact_sha256
        ):
            raise DraftReviewBlocked("Artefatto o manifest modificato: rigenerare")
        manifest.append(
            {
                "draft_id": str(draft.id),
                "source_id": str(draft.source_id),
                "sha256": draft.artifact_sha256,
                "format": draft.artifact_format,
                "payload": draft.manifest,
                "input_basis": draft.input_basis,
            }
        )
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode("utf-8")).hexdigest()


def check_generation_inputs(engine, generation_id: UUID, *, batch: bool) -> DraftInputReview:
    """Use fresh ORM state and one atomic check for all members, including mixed lots."""
    with Session(engine) as db, db.begin():
        # Read a token first, then acquire the fence before touching generation rows.
        current = read_revision(db.connection())
        lock_revision(db.connection(), current)
        records = _records(db, generation_id, batch)
        drafts = _drafts(db, generation_id, records, batch)
        _check_review_size(db, drafts)
        basis = _basis(drafts)
        lock_revision(db.connection(), basis)
        digest = _integrity(records, drafts)
        return DraftInputReview(generation_id, tuple(draft.id for draft in drafts), digest, basis)


def _confirmed_identity(payload):
    identity = payload.get("notice_identity_key")
    if not isinstance(identity, str) or len(identity) != 64:
        raise DraftReviewBlocked("Identita avviso assente: rigenerare la bozza")
    try:
        expected_identity = build_notice_identity_key(
            payload,
            emission_year=int(payload["notice_emission_year"]),
            reference_years=list(payload["notice_reference_years"]),
        )
    except (KeyError, TypeError, ValueError):
        raise DraftReviewBlocked("Identita avviso incompleta: rigenerare la bozza") from None
    if identity != expected_identity:
        raise DraftReviewBlocked("Identita avviso incoerente: rigenerare")
    return identity


def _confirm_reservation(db, record, identity):
    reservation_id = getattr(record, "notice_number_id", None)
    if reservation_id is None:
        raise DraftReviewBlocked("Prenotazione numerica assente: rigenerare la bozza")
    reservation = db.get(RuoloTributiNoticeNumber, reservation_id, with_for_update=True)
    if reservation is None:
        raise DraftReviewBlocked("Prenotazione numerica assente: rigenerare la bozza")
    number = record.payload_json.get("notice_number")
    if (
        reservation.identity_key != identity
        or reservation.notice_number != number
        or reservation.status not in {"draft", "reserved"}
    ):
        raise DraftReviewBlocked("Numero incoerente o gia confermato per un altro lotto")
    reservation.status = "confirmed"
    return number


def _confirm_numbers(db, records):
    identities, numbers = [], []
    for record in records:
        identity = _confirmed_identity(record.payload_json or {})
        if identity in identities:
            raise DraftReviewBlocked("Identita duplicata nel lotto")
        identities.append(identity)
        number = _confirm_reservation(db, record, identity)
        if isinstance(number, str) and number:
            numbers.append(number)
    return identities, numbers


def confirm_generation(
    db: Session, generation_id: UUID, *, batch: bool, actor_id: int
) -> NoticeGenerationConfirmation:
    """Validate and promote one complete private generation in one transaction."""
    kind = "batch" if batch else "reminder"
    if db.new or db.dirty or db.deleted:
        raise DraftReviewBlocked("Conferma richiede una transazione senza modifiche pendenti")
    db.expire_all()
    current = read_revision(db.connection())
    lock_revision(db.connection(), current)
    existing = db.scalar(
        select(NoticeGenerationConfirmation)
        .where(
            NoticeGenerationConfirmation.generation_id == generation_id,
            NoticeGenerationConfirmation.generation_kind == kind,
        )
        .with_for_update()
    )
    if existing is not None:
        basis = existing.input_basis
        lock_revision(db.connection(), GenerationRevision(UUID(basis["epoch"]), basis["revision"]))
        if basis.get("calculation_date") != date.today().isoformat():
            raise DraftReviewBlocked("Conferma obsoleta: rigenerare")
        return existing

    records = _records(db, generation_id, batch)
    drafts = _drafts(db, generation_id, records, batch)
    _check_review_size(db, drafts)
    basis = _basis(drafts)
    lock_revision(db.connection(), basis)
    digest = _integrity(records, drafts)
    identity_keys, notice_numbers = _confirm_numbers(db, records)
    confirmation = NoticeGenerationConfirmation(
        generation_id=generation_id,
        generation_kind=kind,
        review_digest=digest,
        input_basis=dict(drafts[0].input_basis),
        identity_keys=identity_keys,
        notice_numbers=notice_numbers,
        confirmed_by=actor_id,
    )
    db.add(confirmation)
    if batch:
        parent = db.get(RuoloTributiReminderBatch, generation_id)
        parent.status = "confirmed"
        for record in records:
            record.status = "confirmed"
    else:
        records[0].status = "confirmed"
    db.flush()
    return confirmation
