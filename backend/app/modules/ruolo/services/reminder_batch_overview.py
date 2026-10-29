"""What the batch list shows without opening each batch: selectable reminders and PEC shipments."""

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import (
    RuoloAvviso,
    RuoloTributiAvvisoStatus,
    RuoloTributiReminderBatchItem,
)


def pec_sent_avvisi(db: Session, avviso_ids: set[UUID]) -> set[UUID]:
    """Same rule as «Via PEC» in Tributi: a PEC shipment found in inCASS for the avviso."""
    if not avviso_ids:
        return set()
    rows = db.execute(
        select(RuoloAvviso, RuoloTributiAvvisoStatus)
        .outerjoin(RuoloTributiAvvisoStatus, RuoloTributiAvvisoStatus.avviso_id == RuoloAvviso.id)
        .where(RuoloAvviso.id.in_(avviso_ids))
    ).all()
    notices = repo._batch_load_incass_notice_links(db, rows=rows)
    return {avviso_id for avviso_id, notice in notices.items() if notice["mailing_delivery"]}


def _avviso_ids(item: RuoloTributiReminderBatchItem) -> set[UUID]:
    return {UUID(value) for value in item.avviso_ids_json or []}


def sendable(item: RuoloTributiReminderBatchItem) -> bool:
    # Same rule as the Poste candidates: only generated PDFs become Poste drafts.
    path = (item.generated_document_path or "").lower()
    return item.status == "generated" and path.endswith(".pdf")


def batch_overview(db: Session, batch_ids: list[UUID]) -> dict[UUID, list[dict]]:
    items = db.scalars(
        select(RuoloTributiReminderBatchItem)
        .where(RuoloTributiReminderBatchItem.batch_id.in_(batch_ids))
        .order_by(RuoloTributiReminderBatchItem.created_at, RuoloTributiReminderBatchItem.id)
    ).all()
    pec = pec_sent_avvisi(db, set().union(*(_avviso_ids(item) for item in items)))
    overview: dict[UUID, list[dict]] = defaultdict(list)
    for item in items:
        overview[item.batch_id].append(
            {
                "item_id": item.id,
                "label": item.display_name or item.codice_fiscale,
                "status": item.status,
                "sendable": sendable(item),
                "pec_sent": bool(_avviso_ids(item) & pec),
            }
        )
    return overview
