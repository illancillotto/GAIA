"""Partite that describe an avviso imported without any.

Avvisi of the non-ordinary inCASS lists (e.g. ``2021.B``, CNC series
``01.02021780…``) are imported from the inCASS headers only: they carry no
partite and inCASS returns an empty partitario for them. Their land is the
one of the contribuente's ordinary (ORD) avviso of the same year, whose CNC
belongs to the ordinary series ``01.0<year>0…`` (lists ``<year>.01`` to ``.04``).
"""

import uuid

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloAvviso, RuoloPartita


def ord_cnc_prefix(year: int) -> str:
    return f"01.0{year}0"


def partite_source_avviso_id(db: Session, avviso_id: uuid.UUID) -> uuid.UUID:
    """The avviso itself when it has partite, else its same-year ORD avviso with partite."""
    has_partite = exists().where(RuoloPartita.avviso_id == RuoloAvviso.id)
    avviso = db.get(RuoloAvviso, avviso_id)
    tax_code = (avviso.codice_fiscale_raw or "").strip().upper() if avviso else ""
    if not tax_code or db.scalar(select(has_partite.where(RuoloAvviso.id == avviso_id))):
        return avviso_id
    reference = db.scalar(
        select(RuoloAvviso.id)
        .where(
            RuoloAvviso.id != avviso_id,
            RuoloAvviso.anno_tributario == avviso.anno_tributario,
            func.upper(func.trim(RuoloAvviso.codice_fiscale_raw)) == tax_code,
            RuoloAvviso.codice_cnc.startswith(ord_cnc_prefix(avviso.anno_tributario)),
            has_partite,
        )
        .order_by(RuoloAvviso.codice_cnc)
        .limit(1)
    )
    return reference or avviso_id
