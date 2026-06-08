"""Sync WhiteCompany -> layer canonico organigramma.

WhiteCompany è SORGENTE, non verità. Questo modulo mappa, in modo idempotente
tramite `org_source_link`, sia:
  - aree WhiteCompany (`wc_area`) -> `org_unit`
  - nodi utente organigramma WhiteCompany (`wc_org_chart_entry`) -> `org_assignment`

Le righe con `is_manual_locked=True` non vengono mai sovrascritte.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.accessi.wc_org_charts import WCOrgChart, WCOrgChartEntry
from app.modules.operazioni.models.wc_area import WCArea
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.organigramma.models import OrgAssignment, OrgSourceLink, OrgUnit
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


def _find_assignment_link(db: Session, external_wc_id: int) -> OrgSourceLink | None:
    return db.scalar(
        select(OrgSourceLink).where(
            OrgSourceLink.entity_type == "org_assignment",
            OrgSourceLink.source_system == SOURCE_SYSTEM,
            OrgSourceLink.external_wc_id == external_wc_id,
        )
    )


def _parse_source_field(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    result: dict[str, str] = {}
    for token in value.split("|"):
        if "=" not in token:
            continue
        key, raw = token.split("=", 1)
        result[key.strip()] = raw.strip()
    return result


def _resolve_root_unit_id(db: Session, chart_wc_id: int) -> OrgUnit | None:
    link = _find_unit_link(db, chart_wc_id)
    if link is None or link.org_unit_id is None:
        return None
    return db.get(OrgUnit, link.org_unit_id)


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

    operators = db.execute(select(WCOperator)).scalars().all()
    gaia_user_by_wc_operator_id = {
        operator.id: operator.gaia_user_id
        for operator in operators
        if operator.gaia_user_id is not None
    }

    user_chart_rows = db.execute(
        select(WCOrgChartEntry, WCOrgChart)
        .join(WCOrgChart, WCOrgChart.id == WCOrgChartEntry.org_chart_id)
        .where(WCOrgChart.chart_type == "user")
        .order_by(WCOrgChart.wc_id.asc(), WCOrgChartEntry.sort_order.asc(), WCOrgChartEntry.created_at.asc())
    ).all()

    seen_user_ids: set[int] = set()
    for entry, chart in user_chart_rows:
        if entry.wc_operator_id is None:
            continue

        gaia_user_id = gaia_user_by_wc_operator_id.get(entry.wc_operator_id)
        if gaia_user_id is None:
            continue
        if gaia_user_id in seen_user_ids:
            continue

        unit = _resolve_root_unit_id(db, chart.wc_id)
        if unit is None:
            continue

        metadata = _parse_source_field(entry.source_field)
        manager_user_id: int | None = None
        parent_wc_id = metadata.get("parent")
        if parent_wc_id and parent_wc_id.isdigit():
            parent_wc_operator = db.scalar(
                select(WCOperator).where(WCOperator.wc_id == int(parent_wc_id))
            )
            if parent_wc_operator is not None and parent_wc_operator.gaia_user_id != gaia_user_id:
                manager_user_id = parent_wc_operator.gaia_user_id

        link = _find_assignment_link(db, entry.wc_id)
        if link is not None:
            link.last_synced_at = now
            if link.is_manual_locked:
                result.assignments_skipped_locked += 1
                seen_user_ids.add(gaia_user_id)
                continue
            assignment = db.get(OrgAssignment, link.org_assignment_id) if link.org_assignment_id else None
            if assignment is not None:
                assignment.user_id = gaia_user_id
                assignment.org_unit_id = unit.id
                assignment.manager_user_id = manager_user_id
                assignment.title = entry.role
                assignment.is_primary = True
                assignment.active = True
                assignment.source = "whitecompany"
                assignment.wc_operator_id = entry.wc_operator_id
                assignment.updated_by_user_id = user_id
                link.wc_operator_id = entry.wc_operator_id
                link.wc_org_chart_entry_id = entry.id
                result.assignments_updated += 1
                seen_user_ids.add(gaia_user_id)
                continue

        assignment = db.scalar(
            select(OrgAssignment).where(OrgAssignment.wc_operator_id == entry.wc_operator_id)
        )
        if assignment is None:
            assignment = OrgAssignment(
                user_id=gaia_user_id,
                org_unit_id=unit.id,
                manager_user_id=manager_user_id,
                title=entry.role,
                is_primary=True,
                active=True,
                source="whitecompany",
                wc_operator_id=entry.wc_operator_id,
                created_by_user_id=user_id,
                updated_by_user_id=user_id,
            )
            db.add(assignment)
            db.flush()
            db.add(
                OrgSourceLink(
                    entity_type="org_assignment",
                    source_system=SOURCE_SYSTEM,
                    external_wc_id=entry.wc_id,
                    org_assignment_id=assignment.id,
                    wc_operator_id=entry.wc_operator_id,
                    wc_org_chart_entry_id=entry.id,
                    last_synced_at=now,
                    created_by_user_id=user_id,
                    updated_by_user_id=user_id,
                )
            )
            result.assignments_created += 1
            seen_user_ids.add(gaia_user_id)
            continue

        assignment.user_id = gaia_user_id
        assignment.org_unit_id = unit.id
        assignment.manager_user_id = manager_user_id
        assignment.title = entry.role
        assignment.is_primary = True
        assignment.active = True
        assignment.source = "whitecompany"
        assignment.wc_operator_id = entry.wc_operator_id
        assignment.updated_by_user_id = user_id
        db.add(assignment)
        db.flush()
        db.add(
            OrgSourceLink(
                entity_type="org_assignment",
                source_system=SOURCE_SYSTEM,
                external_wc_id=entry.wc_id,
                org_assignment_id=assignment.id,
                wc_operator_id=entry.wc_operator_id,
                wc_org_chart_entry_id=entry.id,
                last_synced_at=now,
                created_by_user_id=user_id,
                updated_by_user_id=user_id,
            )
        )
        result.assignments_updated += 1
        seen_user_ids.add(gaia_user_id)

    db.commit()
    result.message = (
        f"WhiteCompany sync: {result.units_created} unità create, "
        f"{result.units_updated} aggiornate, {result.units_skipped_locked} bloccate manualmente. "
        f"Assegnazioni: {result.assignments_created} create, "
        f"{result.assignments_updated} aggiornate, {result.assignments_skipped_locked} bloccate."
    )
    return result
