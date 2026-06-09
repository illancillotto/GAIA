"""Sync WhiteCompany -> layer canonico organigramma.

WhiteCompany è SORGENTE, non verità. Questo modulo mappa, in modo idempotente
tramite `org_source_link`, sia:
  - aree WhiteCompany (`wc_area`) -> `org_unit`
  - nodi utente organigramma WhiteCompany (`wc_org_chart_entry`) -> `org_assignment`

Le righe con `is_manual_locked=True` non vengono mai sovrascritte.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

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


def _resolve_root_unit(db: Session, chart_wc_id: int) -> OrgUnit | None:
    link = _find_unit_link(db, chart_wc_id)
    if link is None or link.org_unit_id is None:
        return None
    return db.get(OrgUnit, link.org_unit_id)


def _resolve_unit_by_wc_id(db: Session, area_wc_id: int) -> OrgUnit | None:
    link = _find_unit_link(db, area_wc_id)
    if link is None or link.org_unit_id is None:
        return None
    return db.get(OrgUnit, link.org_unit_id)


def _sort_chart_rows(
    rows: list[tuple[WCOrgChartEntry, WCOrgChart]],
) -> list[tuple[WCOrgChartEntry, WCOrgChart]]:
    return sorted(
        rows,
        key=lambda row: (
            row[1].wc_id,
            row[0].sort_order if row[0].sort_order is not None else 0,
            row[0].created_at,
        ),
    )


def _target_depth_for_role(role: str | None) -> int | None:
    if not role:
        return None
    normalized = role.strip().lower()
    if "dirigent" in normalized or "amministrator" in normalized:
        return 0
    if "capo settore" in normalized:
        return 1
    if "capo sezione" in normalized:
        return 2
    if "capo reparto" in normalized:
        return 3
    return None


def _unit_bucket(unit: OrgUnit) -> str | None:
    normalized = unit.nome.strip().lower()
    if normalized.startswith("area ") or normalized == "area agraria" or normalized == "area catasto":
        return "area"
    if normalized.startswith("settore "):
        return "settore"
    if normalized.startswith("sezione "):
        return "sezione"
    if normalized.startswith("reparto "):
        return "reparto"
    if normalized.startswith("distr_") or normalized.startswith("distretto "):
        return "distretto"
    return None


def _target_bucket_for_role(role: str | None) -> str | None:
    if not role:
        return None
    normalized = role.strip().lower()
    if "dirigent" in normalized or "amministrator" in normalized:
        return "area"
    if "capo settore" in normalized:
        return "settore"
    if "capo sezione" in normalized:
        return "sezione"
    if "capo reparto" in normalized:
        return "reparto"
    return None


def _collect_descendants(
    *,
    parent_unit: OrgUnit,
    child_units_by_parent_id: dict[UUID, list[OrgUnit]],
) -> list[OrgUnit]:
    collected: list[OrgUnit] = []
    stack = list(reversed(child_units_by_parent_id.get(parent_unit.id) or []))
    while stack:
        current = stack.pop()
        collected.append(current)
        children = child_units_by_parent_id.get(current.id) or []
        stack.extend(reversed(children))
    return collected


def _pick_child_unit(
    *,
    parent_unit: OrgUnit,
    child_units_by_parent_id: dict[UUID, list[OrgUnit]],
    next_child_cursor_by_parent_key: dict[tuple[UUID, int], int],
    target_depth: int | None,
    unit_depth_by_id: dict[UUID, int],
) -> OrgUnit | None:
    child_units = child_units_by_parent_id.get(parent_unit.id) or []
    if not child_units:
        return None

    candidates = child_units
    if target_depth is not None:
        depth_matched = [unit for unit in child_units if unit_depth_by_id.get(unit.id) == target_depth]
        if depth_matched:
            candidates = depth_matched

    cursor_key = (parent_unit.id, target_depth if target_depth is not None else -1)
    cursor = next_child_cursor_by_parent_key[cursor_key]
    index = min(cursor, len(candidates) - 1)
    next_child_cursor_by_parent_key[cursor_key] = cursor + 1
    return candidates[index]


def _pick_descendant_unit_by_bucket(
    *,
    parent_unit: OrgUnit,
    child_units_by_parent_id: dict[UUID, list[OrgUnit]],
    next_descendant_cursor_by_parent_key: dict[tuple[UUID, str], int],
    target_bucket: str,
) -> OrgUnit | None:
    candidates = [
        unit
        for unit in _collect_descendants(
            parent_unit=parent_unit,
            child_units_by_parent_id=child_units_by_parent_id,
        )
        if _unit_bucket(unit) == target_bucket
    ]
    if not candidates:
        return None
    cursor_key = (parent_unit.id, target_bucket)
    cursor = next_descendant_cursor_by_parent_key[cursor_key]
    index = min(cursor, len(candidates) - 1)
    next_descendant_cursor_by_parent_key[cursor_key] = cursor + 1
    return candidates[index]


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

    area_chart_rows = _sort_chart_rows(
        db.execute(
            select(WCOrgChartEntry, WCOrgChart)
            .join(WCOrgChart, WCOrgChart.id == WCOrgChartEntry.org_chart_id)
            .where(WCOrgChart.chart_type == "area")
        ).all()
    )
    for entry, _chart in area_chart_rows:
        link = _find_unit_link(db, entry.wc_id)
        if link is None:
            continue
        link.last_synced_at = now
        if link.is_manual_locked:
            continue
        unit = db.get(OrgUnit, link.org_unit_id) if link.org_unit_id else None
        if unit is None:
            continue

        metadata = _parse_source_field(entry.source_field)
        parent_wc_id = metadata.get("parent")
        parent_unit_id: UUID | None = None
        if parent_wc_id and parent_wc_id.isdigit():
            parent_unit = _resolve_unit_by_wc_id(db, int(parent_wc_id))
            if parent_unit is not None and parent_unit.id != unit.id:
                parent_unit_id = parent_unit.id

        unit.parent_id = parent_unit_id
        if entry.sort_order is not None:
            unit.sort_order = entry.sort_order
        if entry.label:
            unit.nome = entry.label
        if entry.role:
            normalized_role = entry.role.strip().lower()
            if normalized_role in {"direzione", "distretto", "settore", "squadra"}:
                unit.tipo = normalized_role
        unit.source = "whitecompany"
        unit.updated_by_user_id = user_id

    operators = db.execute(select(WCOperator)).scalars().all()
    operators_by_wc_id = {operator.wc_id: operator for operator in operators}
    gaia_user_by_wc_operator_id = {
        operator.id: operator.gaia_user_id
        for operator in operators
        if operator.gaia_user_id is not None
    }

    user_chart_rows = _sort_chart_rows(
        db.execute(
            select(WCOrgChartEntry, WCOrgChart)
            .join(WCOrgChart, WCOrgChart.id == WCOrgChartEntry.org_chart_id)
            .where(WCOrgChart.chart_type == "user")
        ).all()
    )

    area_rows_by_root_wc_id: dict[int, list[tuple[WCOrgChartEntry, WCOrgChart]]] = defaultdict(list)
    current_root_wc_id_by_chart: dict[int, int] = {}
    for entry, chart in area_chart_rows:
        metadata = _parse_source_field(entry.source_field)
        if "parent" not in metadata:
            current_root_wc_id_by_chart[chart.wc_id] = entry.wc_id
        root_wc_id = current_root_wc_id_by_chart.get(chart.wc_id)
        if root_wc_id is not None:
            area_rows_by_root_wc_id[root_wc_id].append((entry, chart))

    user_rows_by_chart_wc_id: dict[int, list[tuple[WCOrgChartEntry, WCOrgChart]]] = defaultdict(list)
    for entry, chart in user_chart_rows:
        user_rows_by_chart_wc_id[chart.wc_id].append((entry, chart))

    seen_user_ids: set[int] = set()
    for chart_wc_id, chart_rows in user_rows_by_chart_wc_id.items():
        root_unit = _resolve_root_unit(db, chart_wc_id)
        if root_unit is None:
            continue

        area_children_by_unit_id: dict[UUID, list[OrgUnit]] = defaultdict(list)
        area_unit_depth_by_id: dict[UUID, int] = {root_unit.id: 0}
        for area_entry, _area_chart in area_rows_by_root_wc_id.get(chart_wc_id, []):
            metadata = _parse_source_field(area_entry.source_field)
            parent_wc_id = metadata.get("parent")
            depth = metadata.get("depth")
            if not parent_wc_id or not parent_wc_id.isdigit():
                area_unit = _resolve_unit_by_wc_id(db, area_entry.wc_id)
                if area_unit is not None and depth and depth.isdigit():
                    area_unit_depth_by_id[area_unit.id] = int(depth)
                continue
            area_unit = _resolve_unit_by_wc_id(db, area_entry.wc_id)
            parent_unit = _resolve_unit_by_wc_id(db, int(parent_wc_id))
            if area_unit is None or parent_unit is None:
                continue
            area_children_by_unit_id[parent_unit.id].append(area_unit)
            if depth and depth.isdigit():
                area_unit_depth_by_id[area_unit.id] = int(depth)

        for child_units in area_children_by_unit_id.values():
            child_units.sort(key=lambda unit: (unit.sort_order, unit.nome.lower(), str(unit.id)))

        operator_children_count: dict[int, int] = defaultdict(int)
        for entry, _chart in chart_rows:
            metadata = _parse_source_field(entry.source_field)
            parent_wc_id = metadata.get("parent")
            if parent_wc_id and parent_wc_id.isdigit():
                operator_children_count[int(parent_wc_id)] += 1

        assigned_unit_by_operator_wc_id: dict[int, OrgUnit] = {}
        next_child_cursor_by_parent_key: dict[tuple[UUID, int], int] = defaultdict(int)
        next_descendant_cursor_by_parent_key: dict[tuple[UUID, str], int] = defaultdict(int)

        for entry, _chart in chart_rows:
            if entry.wc_operator_id is None:
                continue

            gaia_user_id = gaia_user_by_wc_operator_id.get(entry.wc_operator_id)
            if gaia_user_id is None or gaia_user_id in seen_user_ids:
                continue

            metadata = _parse_source_field(entry.source_field)
            parent_operator_wc_id: int | None = None
            manager_user_id: int | None = None
            if (raw_parent_wc_id := metadata.get("parent")) and raw_parent_wc_id.isdigit():
                parent_operator_wc_id = int(raw_parent_wc_id)
                parent_operator = operators_by_wc_id.get(parent_operator_wc_id)
                if parent_operator is not None and parent_operator.gaia_user_id != gaia_user_id:
                    manager_user_id = parent_operator.gaia_user_id

            unit = root_unit
            role_target_depth = _target_depth_for_role(entry.role)
            role_target_bucket = _target_bucket_for_role(entry.role)
            if parent_operator_wc_id is not None:
                parent_unit = assigned_unit_by_operator_wc_id.get(parent_operator_wc_id, root_unit)
                parent_depth = area_unit_depth_by_id.get(parent_unit.id, 0)
                if role_target_depth is not None:
                    if role_target_depth <= parent_depth:
                        unit = parent_unit
                    else:
                        picked_unit = None
                        if role_target_bucket is not None:
                            picked_unit = _pick_descendant_unit_by_bucket(
                                parent_unit=parent_unit,
                                child_units_by_parent_id=area_children_by_unit_id,
                                next_descendant_cursor_by_parent_key=next_descendant_cursor_by_parent_key,
                                target_bucket=role_target_bucket,
                            )
                        if picked_unit is None:
                            picked_unit = _pick_child_unit(
                                parent_unit=parent_unit,
                                child_units_by_parent_id=area_children_by_unit_id,
                                next_child_cursor_by_parent_key=next_child_cursor_by_parent_key,
                                target_depth=role_target_depth,
                                unit_depth_by_id=area_unit_depth_by_id,
                            )
                        unit = picked_unit or parent_unit
                elif operator_children_count.get(entry.wc_id, 0) > 0:
                    picked_unit = _pick_child_unit(
                        parent_unit=parent_unit,
                        child_units_by_parent_id=area_children_by_unit_id,
                        next_child_cursor_by_parent_key=next_child_cursor_by_parent_key,
                        target_depth=None,
                        unit_depth_by_id=area_unit_depth_by_id,
                    )
                    unit = picked_unit or parent_unit
                else:
                    picked_unit = _pick_child_unit(
                        parent_unit=parent_unit,
                        child_units_by_parent_id=area_children_by_unit_id,
                        next_child_cursor_by_parent_key=next_child_cursor_by_parent_key,
                        target_depth=None,
                        unit_depth_by_id=area_unit_depth_by_id,
                    )
                    unit = picked_unit or parent_unit

            assigned_unit_by_operator_wc_id[entry.wc_id] = unit

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
