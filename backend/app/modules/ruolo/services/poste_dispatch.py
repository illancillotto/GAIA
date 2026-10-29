"""Operator commands on Posta Online lots. GAIA prepares drafts; INVIA stays manual.

Each command runs in the caller's transaction. Portal work is queued as a
Posta Online job, so only the Poste worker ever opens the portal.
"""

from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.posta_online import PostaOnlineRegisteredMailSyncJob
from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloTributiReminderBatch, RuoloTributiReminderBatchItem
from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem, PosteDispatchLot
from app.modules.ruolo.services import notice_pdf_regeneration as regeneration
from app.modules.ruolo.services import poste_dispatch_recipient as recipients
from app.modules.ruolo.services.poste_dispatch_state import (
    DispatchConflict,
    DispatchNotFound,
    attach_artifact,
    get_item,
    get_lot,
    record_event,
    release,
    transition,
)
from app.services.elaborazioni_posta_online import ACTIVE_JOB_STATUSES

MAX_LOT_ITEMS = 50
MAX_ARTIFACT_BYTES = 7 * 1024 * 1024
JOB_MODES = {
    "addresses": "poste_dispatch_addresses",
    "drafts": "poste_dispatch_drafts",
    "reconcile": "poste_dispatch_reconcile",
    "delete": "poste_dispatch_delete",
}
# GAIA does not touch the colour, duplex or tax-code fields: the portal defaults apply.
POSTAL_OPTIONS = {"product": "raccomandata_ar_online", "tax_code": False, "portal_defaults": True}
_JOB_READY_STATUSES = {
    "addresses": {"address_pending"},
    "drafts": {"address_ok", "draft_error", "draft_missing"},
    "delete": {"cancel_requested"},
}
_EDITABLE_STATUSES = {
    "address_pending",
    "address_review",
    "address_ok",
    "draft_error",
    "draft_missing",
}
_LOCAL_CANCEL_STATUSES = _EDITABLE_STATUSES
_PORTAL_CANCEL_STATUSES = {"draft_created", "draft_priced", "draft_uncertain"}
DocumentReader = Callable[[RuoloTributiReminderBatchItem], bytes]


def read_batch_document(db: Session, item: RuoloTributiReminderBatchItem, actor_id: int) -> bytes:
    try:
        path = regeneration.ensure_batch_item_document(db, item, actor_id=actor_id)
    except regeneration.RegenerationFailed as exc:
        raise DispatchConflict(f"PDF del sollecito non ricostruibile: {exc}") from exc
    if path is None or path.suffix.lower() != ".pdf":
        raise DispatchConflict("Sollecito senza PDF definitivo: non spedibile da GAIA")
    if repo.is_remote_reminder_document_path(path):
        return repo.read_remote_reminder_document(path)
    return path.read_bytes()


def _candidate_query():
    active = exists().where(
        PosteDispatchItem.batch_item_id == RuoloTributiReminderBatchItem.id,
        PosteDispatchItem.active_source_key.is_not(None),
    )
    return (
        select(RuoloTributiReminderBatchItem, RuoloTributiReminderBatch.title)
        .join(
            RuoloTributiReminderBatch,
            RuoloTributiReminderBatch.id == RuoloTributiReminderBatchItem.batch_id,
        )
        .where(
            RuoloTributiReminderBatchItem.status == "generated",
            RuoloTributiReminderBatchItem.generated_document_path.ilike("%.pdf"),
            ~active,
        )
    )


def list_candidates(db: Session, *, q: str | None, page: int, page_size: int):
    query = _candidate_query()
    if q:
        term = f"%{q.strip()}%"
        query = query.where(
            RuoloTributiReminderBatchItem.display_name.ilike(term)
            | RuoloTributiReminderBatchItem.codice_fiscale.ilike(term)
            | RuoloTributiReminderBatch.title.ilike(term)
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(RuoloTributiReminderBatchItem.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return rows, total


def _new_item(lot: PosteDispatchLot, item: RuoloTributiReminderBatchItem, read: DocumentReader):
    if item.status != "generated":
        raise DispatchConflict(f"Sollecito {item.id} non generato in via definitiva")
    notice_number = str((item.payload_json or {}).get("notice_number") or "").strip()
    name = recipients.shipment_name(notice_number)
    recipient = recipients.recipient_from_payload(item.payload_json or {})
    artifact = read(item)
    if not artifact.startswith(b"%PDF") or len(artifact) > MAX_ARTIFACT_BYTES:
        raise DispatchConflict(
            f"Avviso {notice_number}: PDF non valido o oltre 7 MB (limite Poste)"
        )
    dispatch = PosteDispatchItem(
        lot_id=lot.id,
        batch_item_id=item.id,
        notice_number=notice_number,
        shipment_name=name,
        active_key=name,
        active_source_key=str(item.id),
        status="address_pending",
        recipient=recipient,
    )
    attach_artifact(dispatch, artifact)
    return dispatch


def create_lot(
    db: Session,
    *,
    title: str,
    batch_item_ids: list[UUID],
    actor_id: int,
    read: DocumentReader | None = None,
) -> PosteDispatchLot:
    if not 1 <= len(set(batch_item_ids)) == len(batch_item_ids) <= MAX_LOT_ITEMS:
        raise DispatchConflict(f"Un lotto contiene da 1 a {MAX_LOT_ITEMS} solleciti distinti")
    items = list(
        db.scalars(
            select(RuoloTributiReminderBatchItem).where(
                RuoloTributiReminderBatchItem.id.in_(batch_item_ids)
            )
        )
    )
    if len(items) != len(batch_item_ids):
        raise DispatchNotFound("Uno o più solleciti non esistono")
    lot = PosteDispatchLot(
        title=title.strip(), status="open", postal_options=dict(POSTAL_OPTIONS), created_by=actor_id
    )
    db.add(lot)
    db.flush()
    try:
        with db.begin_nested():
            reader = read or (lambda item: read_batch_document(db, item, actor_id))
            dispatches = [_new_item(lot, item, reader) for item in items]
            db.add_all(dispatches)
            db.flush()
    except IntegrityError as exc:
        raise DispatchConflict("Un sollecito è già in un altro lotto Poste attivo") from exc
    record_event(db, lot, None, "lot_created", actor_id=actor_id, detail={"items": len(dispatches)})
    for dispatch in dispatches:
        problems = recipients.recipient_problems(dispatch.recipient)
        if problems:
            transition(
                db,
                dispatch,
                "address_review",
                "recipient_incomplete",
                actor_id=actor_id,
                detail={"problems": problems},
            )
            dispatch.address_review = {
                "reason": "Dati destinatario incompleti",
                "problems": problems,
            }
    enqueue_job(db, lot, "addresses", actor_id=actor_id, required=False)
    return lot


def active_job(db: Session, lot_id: UUID) -> PostaOnlineRegisteredMailSyncJob | None:
    jobs = db.scalars(
        select(PostaOnlineRegisteredMailSyncJob)
        .where(
            PostaOnlineRegisteredMailSyncJob.mode.in_(tuple(JOB_MODES.values())),
            PostaOnlineRegisteredMailSyncJob.status.in_(tuple(ACTIVE_JOB_STATUSES)),
        )
        .order_by(PostaOnlineRegisteredMailSyncJob.id.desc())
    )
    return next(
        (job for job in jobs if (job.payload_json or {}).get("lot_id") == str(lot_id)), None
    )


def enqueue_job(
    db: Session, lot: PosteDispatchLot, kind: str, *, actor_id: int, required: bool = True
):
    if active_job(db, lot.id) is not None:
        raise DispatchConflict("C'è già un'operazione Poste in corso su questo lotto")
    ready = _JOB_READY_STATUSES.get(kind)
    if ready is not None and not db.scalar(
        select(func.count()).where(
            PosteDispatchItem.lot_id == lot.id, PosteDispatchItem.status.in_(ready)
        )
    ):
        if not required:
            return None
        raise DispatchConflict("Nessun avviso del lotto è pronto per questa operazione")
    job = PostaOnlineRegisteredMailSyncJob(
        requested_by_user_id=actor_id,
        status="pending",
        mode=JOB_MODES[kind],
        payload_json={"lot_id": str(lot.id)},
    )
    db.add(job)
    db.flush()
    record_event(db, lot, None, f"job_{kind}_queued", actor_id=actor_id, job_id=job.id)
    return job


def request_job(db: Session, lot_id: UUID, kind: str, *, actor_id: int):
    if kind not in JOB_MODES:
        raise DispatchNotFound("Operazione Poste sconosciuta")
    return enqueue_job(db, get_lot(db, lot_id, lock=True), kind, actor_id=actor_id)


def update_recipient(
    db: Session, lot_id: UUID, item_id: UUID, fields: dict[str, Any], *, actor_id: int
):
    item = get_item(db, lot_id, item_id)
    if item.status not in _EDITABLE_STATUSES:
        raise DispatchConflict(
            "Destinatario modificabile solo prima della bozza Poste: eliminare prima la bozza"
        )
    recipient = recipients.normalize_recipient(fields)
    problems = recipients.recipient_problems(recipient)
    if problems:
        raise DispatchConflict("; ".join(problems))
    before = dict(item.recipient)
    item.recipient, item.poste_address, item.address_review = recipient, None, None
    transition(
        db,
        item,
        "address_pending",
        "recipient_corrected",
        actor_id=actor_id,
        detail={"before": before},
    )
    return item


def accept_manual_address(db: Session, lot_id: UUID, item_id: UUID, *, actor_id: int):
    item = get_item(db, lot_id, item_id)
    if item.status != "address_review":
        raise DispatchConflict("Indirizzo manuale ammesso solo per avvisi da rivedere")
    problems = recipients.recipient_problems(item.recipient, manual=True)
    if problems:
        raise DispatchConflict("; ".join(problems))
    item.poste_address = {"mode": "manual"}
    transition(db, item, "address_ok", "manual_address_accepted", actor_id=actor_id)
    return item


def cancel_item(db: Session, lot_id: UUID, item_id: UUID, *, actor_id: int):
    item = get_item(db, lot_id, item_id)
    if item.status in _LOCAL_CANCEL_STATUSES:
        release(item)
        transition(db, item, "cancelled", "cancelled", actor_id=actor_id)
    elif item.status in _PORTAL_CANCEL_STATUSES:
        transition(db, item, "cancel_requested", "cancel_requested", actor_id=actor_id)
    else:
        raise DispatchConflict("Avviso già spedito, annullato o in lavorazione")
    return item
