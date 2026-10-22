"""Link STEP documents to ``ruolo_avvisi`` through the notice code only.

Rules (see ``domain-docs/ruolo/docs/STEP_IMPORT_IMPLEMENTAZIONE.md``):

- the only identifier is the 15 digit ``codice_cnc`` printed by STEP in the
  tributo description (``Avv. N. 020190006018040 ...``);
- a link is created only for a unique match, using the tributo year solely as
  the second half of the ``(codice_cnc, anno_tributario)`` key;
- tax code, name and amounts are never used; unrecognized references, missing
  and ambiguous notices stay visible as anomalies;
- links are a read model: they do not change the notice register, its STEP
  assessment or GAIA payments.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.elaborazioni.step import parsing
from app.modules.elaborazioni.step.models import StepDocumento, StepRuoloLink, StepTributo
from app.modules.ruolo.models import RuoloAvviso

LINK_STATUSES = ("linked", "not_found", "ambiguous", "unrecognized")


@dataclass
class _ReferenceGroup:
    codice_cnc: str | None
    years: set[int] = field(default_factory=set)
    tributi: int = 0
    imp_carico: Decimal = Decimal("0")
    imp_carico_pagato: Decimal = Decimal("0")
    imp_discaricato: Decimal = Decimal("0")

    def add(self, tributo: StepTributo) -> None:
        self.tributi += 1
        if tributo.anno_rif is not None:
            self.years.add(tributo.anno_rif)
        self.imp_carico += tributo.imp_carico or Decimal("0")
        self.imp_carico_pagato += tributo.imp_carico_pagato or Decimal("0")
        self.imp_discaricato += tributo.imp_discaricato or Decimal("0")

    @property
    def year(self) -> int | None:
        return next(iter(self.years)) if len(self.years) == 1 else None


def _groups(tributi: list[StepTributo]) -> dict[str, _ReferenceGroup]:
    groups: dict[str, _ReferenceGroup] = {}
    for tributo in tributi:
        key = tributo.codice_cnc or tributo.avviso_reference_raw or "(assente)"
        groups.setdefault(key, _ReferenceGroup(codice_cnc=tributo.codice_cnc)).add(tributo)
    return groups


def _candidates(db: Session, codes: set[str]) -> dict[str, list[tuple[uuid.UUID, int]]]:
    found: dict[str, list[tuple[uuid.UUID, int]]] = defaultdict(list)
    if not codes:
        return found
    rows = db.execute(
        select(RuoloAvviso.codice_cnc, RuoloAvviso.id, RuoloAvviso.anno_tributario).where(
            RuoloAvviso.codice_cnc.in_(codes)
        )
    ).all()
    for code, avviso_id, anno in rows:
        found[code].append((avviso_id, anno))
    return found


def _resolve(
    group: _ReferenceGroup, candidates: list[tuple[uuid.UUID, int]]
) -> tuple[str, uuid.UUID | None]:
    if group.codice_cnc is None:
        return "unrecognized", None
    if not candidates:
        return "not_found", None
    narrowed = candidates
    if len(candidates) > 1 and group.year is not None:
        narrowed = [candidate for candidate in candidates if candidate[1] == group.year]
    if len(narrowed) == 1:
        return "linked", narrowed[0][0]
    return "ambiguous", None


def link_documents(db: Session, documento_ids: list[uuid.UUID], *, now: datetime) -> dict[str, int]:
    """Rebuild the links of the given documents and return counts by status."""

    counts = dict.fromkeys(LINK_STATUSES, 0)
    if not documento_ids:
        return counts
    db.execute(delete(StepRuoloLink).where(StepRuoloLink.documento_id.in_(documento_ids)))
    tributi = db.scalars(
        select(StepTributo)
        .where(StepTributo.documento_id.in_(documento_ids))
        .order_by(StepTributo.position)
    ).all()
    by_document: dict[uuid.UUID, list[StepTributo]] = defaultdict(list)
    for tributo in tributi:
        # Re-derived on every run so a parser fix reaches already imported rows.
        tributo.avviso_reference_raw, tributo.codice_cnc = parsing.avviso_reference(
            (tributo.raw_json or {}).get("DES_TRI1")
        )
        by_document[tributo.documento_id].append(tributo)
    groups = {document_id: _groups(rows) for document_id, rows in by_document.items()}
    codes = {
        group.codice_cnc
        for items in groups.values()
        for group in items.values()
        if group.codice_cnc
    }
    candidates = _candidates(db, codes)
    for document_id, items in groups.items():
        for reference_key, group in items.items():
            pool = candidates.get(group.codice_cnc or "", [])
            status, avviso_id = _resolve(group, pool)
            counts[status] += 1
            db.add(
                StepRuoloLink(
                    id=uuid.uuid4(),
                    documento_id=document_id,
                    reference_key=reference_key[:300],
                    codice_cnc=group.codice_cnc,
                    anno_rif=group.year,
                    status=status,
                    ruolo_avviso_id=avviso_id,
                    candidate_avviso_ids=[str(item[0]) for item in pool]
                    if status == "ambiguous"
                    else None,
                    tributi_count=group.tributi,
                    imp_carico=group.imp_carico,
                    imp_carico_pagato=group.imp_carico_pagato,
                    imp_discaricato=group.imp_discaricato,
                    resolved_at=now,
                )
            )
    db.flush()
    return counts


def relink_all(db: Session, *, now: datetime, batch_size: int = 500) -> dict[str, int]:
    """Re-resolve every STEP document, e.g. after new ruolo avvisi were imported."""

    totals = dict.fromkeys(LINK_STATUSES, 0)
    ids = list(db.scalars(select(StepDocumento.id).order_by(StepDocumento.id)).all())
    for start in range(0, len(ids), batch_size):
        for status, count in link_documents(db, ids[start : start + batch_size], now=now).items():
            totals[status] += count
    return totals
