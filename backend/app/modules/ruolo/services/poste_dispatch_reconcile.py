"""Record a shipment the operator sent on Poste, found in the archive by its GAIA name."""

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloTributiRegisteredMail
from app.modules.ruolo.notice_register_models import NoticeDocument
from app.modules.ruolo.notice_register_schemas import OperatorChange
from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem
from app.modules.ruolo.services.notice_register import RegisterConflict, RegisterNotFound
from app.modules.ruolo.services.notice_registered_mail_link import associate_registered_mail
from app.modules.ruolo.services.poste_dispatch_state import (
    DispatchConflict,
    get_lot,
    release,
    transition,
)

BATCH_DOCUMENT_SOURCE = "gaia_batch_item"


def _import_detail(
    db: Session, item: PosteDispatchItem, id_invio: str, detail_html: str, actor_id: int
):
    import_job = repo.import_posta_online_registered_mails(
        db,
        filename=f"poste-dispatch-{item.id}.json",
        content=json.dumps({"details": [{"idInvio": id_invio, "html": detail_html}]}).encode(
            "utf-8"
        ),
        triggered_by=actor_id,
        preserve_associations=True,
    )
    mail = db.scalar(
        select(RuoloTributiRegisteredMail)
        .where(RuoloTributiRegisteredMail.source_shipment_id == id_invio)
        .order_by(RuoloTributiRegisteredMail.recipient_index)
        .limit(1)
    )
    if (
        import_job.status == "failed"
        or mail is None
        or (mail.shipment_name or "").strip() != item.shipment_name
    ):
        raise DispatchConflict(f"Dettaglio Poste {id_invio} non coerente con {item.shipment_name}")
    return mail


def link_register(
    db: Session, item: PosteDispatchItem, mail: RuoloTributiRegisteredMail, actor_id: int
) -> str | None:
    """Attach the tracking to the notice register; a refusal is reported, never forced."""
    document = db.scalar(
        select(NoticeDocument).where(
            NoticeDocument.source_system == BATCH_DOCUMENT_SOURCE,
            NoticeDocument.source_key == str(item.batch_item_id),
        )
    )
    if document is None:
        return "Avviso non presente nel Registro: collegare la raccomandata a mano"
    change = OperatorChange(
        actor_id=actor_id,
        reason=f"Raccomandata {item.shipment_name} inviata dall'operatore su Posta Online",
        expected_version=document.version,
    )
    try:
        with db.begin_nested():
            associate_registered_mail(db, document.id, mail.id, change)
    except (RegisterConflict, RegisterNotFound, ValueError) as exc:
        return f"Registro non aggiornato: {exc}"
    return None


def record_sent(
    db: Session, item_id: UUID, *, job_id: int, id_invio: str, detail_html: str
) -> None:
    item = db.scalar(
        select(PosteDispatchItem).where(PosteDispatchItem.id == item_id).with_for_update()
    )
    actor_id = get_lot(db, item.lot_id).created_by
    mail = _import_detail(db, item, id_invio, detail_html, actor_id)
    item.registered_mail_id, item.tracking_number = mail.id, mail.tracking_number
    item.sent_at, item.price_amount = mail.sent_at, mail.price_amount or item.price_amount
    item.poste_draft_id = id_invio
    release(item, sent=True)
    transition(
        db,
        item,
        "sent",
        "sent_by_operator",
        job_id=job_id,
        detail={"poste_shipment_id": id_invio, "tracking_number": mail.tracking_number},
    )
    item.error_detail = link_register(db, item, mail, actor_id)
    db.flush()
