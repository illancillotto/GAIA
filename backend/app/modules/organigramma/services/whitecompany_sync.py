"""Sync WhiteCompany -> layer canonico organigramma (MVP-light).

WhiteCompany è SORGENTE, non verità. Questo modulo mappa, in modo idempotente
tramite `org_source_link`, le aree WhiteCompany (`wc_area`) verso `org_unit`,
SENZA mai sovrascrivere le righe con `is_manual_locked=True`.

Stato:
  - sync UNITÀ da `wc_area`: implementato (idempotente, rispetta i lock).
  - sync ASSEGNAZIONI da `wc_operator`: documentato come follow-up. Il
    posizionamento operatore->unità richiede la mappa org-chart
    (`wc_org_chart_entry`) area<->operatore, non disponibile a livello di
    singolo `wc_operator`; viene quindi lasciato come passo successivo e qui
    conteggiato a zero. Vedi `accessi/sync_org_charts.py` per il grafo sorgente.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.operazioni.models.wc_area import WCArea
from app.modules.organigramma.models import OrgSourceLink, OrgUnit
from app.modules.organigramma.schemas import WhiteCompanySyncResult

SOURCE_SYSTEM = "whitecompany"


def _find_unit_link(db: Session, external_wc_id: int) -> OrgSourceLink | None:
    return db.scalar(
        select(OrgSourceLink).where(
            OrgSourceLink.entity_type == "org_unit",
            OrgSourceLink.source_system == SOURCE_SYSTEM,
            OrgSourceLink.external_wc_id == external_wc_id,
        )
    )


def sync_from_whitecompany(db: Session, *, user_id: int | None) -> WhiteCompanySyncResult:
    now = datetime.now(timezone.utc)
    result = WhiteCompanySyncResult()

    areas = db.execute(select(WCArea)).scalars().all()
    for area in areas:
        link = _find_unit_link(db, area.wc_id)
        if link is not None:
            link.last_synced_at = now
            if link.is_manual_locked:
                result.units_skipped_locked += 1
                continue
            unit = db.get(OrgUnit, link.org_unit_id) if link.org_unit_id else None
            if unit is not None:
                # aggiorna solo i campi derivati dalla sorgente; la struttura
                # (parent, tipo manuale) resta verità canonica e non viene toccata.
                unit.nome = area.name
                unit.source = "whitecompany"
                unit.wc_area_id = area.id
                unit.updated_by_user_id = user_id
                result.units_updated += 1
            continue

        tipo = "distretto" if area.is_district else "settore"
        unit = OrgUnit(
            nome=area.name,
            tipo=tipo,
            parent_id=None,
            source="whitecompany",
            wc_area_id=area.id,
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        db.add(unit)
        db.flush()
        db.add(
            OrgSourceLink(
                entity_type="org_unit",
                source_system=SOURCE_SYSTEM,
                external_wc_id=area.wc_id,
                org_unit_id=unit.id,
                wc_area_id=area.id,
                last_synced_at=now,
                created_by_user_id=user_id,
                updated_by_user_id=user_id,
            )
        )
        result.units_created += 1

    db.commit()
    result.message = (
        f"WhiteCompany sync: {result.units_created} unità create, "
        f"{result.units_updated} aggiornate, {result.units_skipped_locked} bloccate manualmente. "
        f"Assegnazioni operatori: follow-up (richiede mappa org-chart)."
    )
    return result
