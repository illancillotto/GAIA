"""Durable WAHA receipts, including callbacks arriving before the send response."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.modules.presenze.services.whatsapp_waha import WhatsAppAck
from app.modules.presenze.whatsapp_models import PresenzeWhatsAppMessage, PresenzeWhatsAppReceipt

RECEIPT_RANK = {"SENT": 1, "FAILED": 2, "DELIVERED": 3, "READ": 4}


def store_receipt(db: Session, event: WhatsAppAck, moment: datetime) -> None:
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert
    statement = insert(PresenzeWhatsAppReceipt).values(
        provider_message_id=event.provider_message_id,
        status=event.status,
        rank=RECEIPT_RANK[event.status],
        received_at=moment,
    )
    db.execute(
        statement.on_conflict_do_update(
            index_elements=[PresenzeWhatsAppReceipt.provider_message_id],
            set_={
                "status": statement.excluded.status,
                "rank": statement.excluded.rank,
                "received_at": statement.excluded.received_at,
            },
            where=PresenzeWhatsAppReceipt.rank < statement.excluded.rank,
        )
    )


def matching_receipts(db: Session) -> list[PresenzeWhatsAppReceipt]:
    return list(
        db.scalars(
            select(PresenzeWhatsAppReceipt)
            .join(
                PresenzeWhatsAppMessage,
                PresenzeWhatsAppMessage.provider_message_id
                == PresenzeWhatsAppReceipt.provider_message_id,
            )
            .where(PresenzeWhatsAppMessage.status != PresenzeWhatsAppReceipt.status)
            .execution_options(populate_existing=True)
        ).all()
    )
