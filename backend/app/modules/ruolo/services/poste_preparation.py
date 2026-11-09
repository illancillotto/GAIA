"""Queue address verification then drafts, retaining all existing upload guards."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select

from app.models.posta_online import PostaOnlineRegisteredMailSyncJob
from app.modules.ruolo.models import RuoloTributiReminderBatchItem
from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem, PosteDispatchLot
from app.modules.ruolo.services import poste_dispatch as dispatch
from app.modules.ruolo.services.poste_dispatch_state import (
    DRAFT_STATUSES,
    DispatchConflict,
    get_lot,
)


def prepare(db, *, item_ids, credential_id, actor_id):
    reserved = db.scalar(
        select(PosteDispatchItem.id)
        .join(
            RuoloTributiReminderBatchItem,
            ("GAIA " + RuoloTributiReminderBatchItem.payload_json["notice_number"].as_string())
            == PosteDispatchItem.shipment_name,
        )
        .where(
            RuoloTributiReminderBatchItem.id.in_(item_ids), PosteDispatchItem.status != "cancelled"
        )
        .limit(1)
    )
    if reserved is not None:
        raise DispatchConflict(
            "Avviso già assegnato o spedito: aggiornare lo stato, senza ricaricarlo"
        )
    lot = dispatch.create_lot(
        db,
        title="Preparazione avvisi Posta Online",
        batch_item_ids=item_ids,
        credential_id=credential_id,
        actor_id=actor_id,
    )
    job = dispatch.active_job(db, lot.id)
    if job is not None:
        job.payload_json = {**job.payload_json, "prepare_drafts_after_addresses": True}
    return lot


def _continue(db, job):
    if job.status != "succeeded" or not (job.payload_json or {}).get(
        "prepare_drafts_after_addresses"
    ):
        return
    job.payload_json = {**job.payload_json, "prepare_drafts_after_addresses": False}
    db.flush()
    try:
        lot = get_lot(db, UUID(job.payload_json["lot_id"]), lock=True)
        dispatch.enqueue_job(db, lot, "drafts", actor_id=job.requested_by_user_id, required=False)
    except DispatchConflict as exc:
        job.result_json = {**job.result_json, "next_step_error": str(exc)}


def finish_job(db, job_id, status, result):
    job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
    job.status = status
    job.error_detail = result.get("error")
    job.completed_at = datetime.now(UTC)
    job.result_json = result
    _continue(db, job)


def reconcile_account(db, *, credential_id, year, actor_id):
    dispatch.accounts.selected_account(db, credential_id)
    candidates = db.execute(
        select(PosteDispatchItem.lot_id, RuoloTributiReminderBatchItem.years_json)
        .join(PosteDispatchLot, PosteDispatchLot.id == PosteDispatchItem.lot_id)
        .join(
            RuoloTributiReminderBatchItem,
            RuoloTributiReminderBatchItem.id == PosteDispatchItem.batch_item_id,
        )
        .where(
            PosteDispatchLot.credential_id == credential_id,
            PosteDispatchItem.status.in_(DRAFT_STATUSES),
        )
    )
    lots = {lot_id for lot_id, years in candidates if year is None or year in (years or [])}
    queued, busy = [], 0
    for lot_id in sorted(lots):
        lot = get_lot(db, lot_id, lock=True)
        if dispatch.active_job(db, lot_id) is not None:
            busy += 1
            continue
        queued.append(dispatch.enqueue_job(db, lot, "reconcile", actor_id=actor_id).id)
    return {"queued_jobs": queued, "busy_lots": busy}
