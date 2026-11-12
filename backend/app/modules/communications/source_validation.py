"""Canonical inCASS numbering and the temporary exclusion of reconciled Poste notices."""

import re
from uuid import UUID

from sqlalchemy import exists, func, or_, select

from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.notice_register_models import NoticeAttempt, NoticePosition
from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem
from app.modules.ruolo.services.incass_notice_numbering import incass_year_checker
from app.modules.utenze.models import AnagraficaPaymentNotice

from .policy import Conflict


def definitive_number(db, item, number, reservation):
    if reservation is not None:
        return reservation.status == "generated"
    identities = item.avviso_ids_json or []
    if item.notice_number_id is not None or len(identities) != 1:
        return False
    if not re.fullmatch(r"[0-9]{15}", number) or not incass_year_checker(db)(2021):
        return False
    notice = AnagraficaPaymentNotice
    avviso = RuoloAvviso
    identifier = item.codice_fiscale.strip().upper()
    return bool(
        db.scalar(
            select(
                exists().where(
                    avviso.id == UUID(identities[0]),
                    avviso.anno_tributario == 2021,
                    avviso.codice_cnc.in_((number, f"01.{number[:-1]}")),
                    avviso.subject_id == item.subject_id,
                    notice.source_system == "incass",
                    notice.source_notice_id == number,
                    notice.anno == "2021",
                    notice.subject_id == avviso.subject_id,
                    or_(
                        func.upper(func.trim(notice.codice_fiscale)) == identifier,
                        func.upper(func.trim(notice.partita_iva)) == identifier,
                    ),
                )
            )
        )
    )


def exclude_reconciled_poste(db, item):
    identities = [UUID(value) for value in item.avviso_ids_json or []]
    linked = exists().where(
        NoticePosition.document_id == NoticeAttempt.document_id,
        NoticePosition.avviso_id.in_(identities),
        NoticeAttempt.registered_mail_id.is_not(None),
    )
    dispatched = exists().where(
        or_(
            PosteDispatchItem.batch_item_id == item.id,
            PosteDispatchItem.notice_number == (item.payload_json or {}).get("notice_number"),
        ),
        PosteDispatchItem.registered_mail_id.is_not(None),
    )
    if db.scalar(select(or_(linked, dispatched))):
        raise Conflict("Avviso riconciliato con Poste: invio PEC/email escluso per ora")
