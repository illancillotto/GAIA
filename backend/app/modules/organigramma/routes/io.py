from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.organigramma.deps import (
    require_organigramma_manage_or_inaz,
    require_organigramma_read_or_inaz,
)
from app.modules.organigramma.models import OrgAssignment, OrgUnit, OrgVisibilityOverride
from app.modules.organigramma.schemas import (
    ImportModeLiteral,
    OrganigrammaImportResponse,
    OrganigrammaSnapshot,
    OrgAssignmentSnapshot,
    OrgUnitSnapshot,
    OrgVisibilityOverrideSnapshot,
    StructureKindLiteral,
)


router = APIRouter(prefix="/io", tags=["organigramma/io"])


@router.get("/export", response_model=OrganigrammaSnapshot, dependencies=[Depends(require_organigramma_read_or_inaz())])
def export_organigramma_json(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_organigramma_read_or_inaz())],
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> OrganigrammaSnapshot:
    units = db.execute(
        select(OrgUnit)
        .where(OrgUnit.structure_kind == structure_kind)
        .order_by(OrgUnit.sort_order, OrgUnit.nome)
    ).scalars().all()
    assignments = db.execute(
        select(OrgAssignment)
        .where(OrgAssignment.structure_kind == structure_kind)
        .order_by(OrgAssignment.created_at, OrgAssignment.id)
    ).scalars().all()
    overrides = db.execute(
        select(OrgVisibilityOverride)
        .where(OrgVisibilityOverride.structure_kind == structure_kind)
        .order_by(OrgVisibilityOverride.created_at.desc(), OrgVisibilityOverride.id)
    ).scalars().all()

    return OrganigrammaSnapshot(
        schema_version=1,
        exported_at=datetime.now(timezone.utc),
        exported_by_user_id=current_user.id,
        exported_by_username=current_user.username,
        units=[OrgUnitSnapshot.model_validate(unit) for unit in units],
        assignments=[OrgAssignmentSnapshot.model_validate(item) for item in assignments],
        overrides=[OrgVisibilityOverrideSnapshot.model_validate(item) for item in overrides],
    )


@router.post("/import", response_model=OrganigrammaImportResponse)
def import_organigramma_json(
    snapshot: OrganigrammaSnapshot,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
    mode: ImportModeLiteral = Query(default="merge"),
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> OrganigrammaImportResponse:
    _validate_snapshot(snapshot, db, structure_kind=structure_kind)

    units_created = 0
    units_updated = 0
    assignments_created = 0
    assignments_updated = 0
    overrides_created = 0
    overrides_updated = 0

    if mode == "replace":
        db.execute(delete(OrgVisibilityOverride).where(OrgVisibilityOverride.structure_kind == structure_kind))
        db.execute(delete(OrgAssignment).where(OrgAssignment.structure_kind == structure_kind))
        db.execute(update(OrgUnit).where(OrgUnit.structure_kind == structure_kind).values(parent_id=None))
        db.execute(delete(OrgUnit).where(OrgUnit.structure_kind == structure_kind))
        db.flush()

    existing_units = {
        item.id: item
        for item in db.execute(
            select(OrgUnit).where(
                OrgUnit.id.in_([unit.id for unit in snapshot.units]),
                OrgUnit.structure_kind == structure_kind,
            )
        ).scalars().all()
    }
    for unit in snapshot.units:
        existing = existing_units.get(unit.id)
        if existing is None:
            db.add(
                OrgUnit(
                    id=unit.id,
                    structure_kind=structure_kind,
                    nome=unit.nome,
                    tipo=unit.tipo,
                    parent_id=None,
                    is_active=unit.is_active,
                    sort_order=unit.sort_order,
                    canvas_x=unit.canvas_x,
                    canvas_y=unit.canvas_y,
                    source=unit.source,
                    wc_area_id=unit.wc_area_id,
                    legacy_team_id=unit.legacy_team_id,
                    created_by_user_id=current_user.id,
                    updated_by_user_id=current_user.id,
                )
            )
            units_created += 1
        else:
            existing.nome = unit.nome
            existing.tipo = unit.tipo
            existing.is_active = unit.is_active
            existing.sort_order = unit.sort_order
            existing.canvas_x = unit.canvas_x
            existing.canvas_y = unit.canvas_y
            existing.source = unit.source
            existing.wc_area_id = unit.wc_area_id
            existing.legacy_team_id = unit.legacy_team_id
            existing.updated_by_user_id = current_user.id
            existing.parent_id = None
            units_updated += 1
    db.flush()

    imported_unit_ids = {unit.id for unit in snapshot.units}
    all_units = {
        item.id: item
        for item in db.execute(select(OrgUnit).where(OrgUnit.id.in_(imported_unit_ids))).scalars().all()
        if item.structure_kind == structure_kind
    }
    for unit in snapshot.units:
        all_units[unit.id].parent_id = unit.parent_id
        all_units[unit.id].updated_by_user_id = current_user.id
    db.flush()

    existing_assignments = {
        item.id: item
        for item in db.execute(
            select(OrgAssignment).where(
                OrgAssignment.id.in_([assignment.id for assignment in snapshot.assignments]),
                OrgAssignment.structure_kind == structure_kind,
            )
        ).scalars().all()
    }
    for assignment in snapshot.assignments:
        existing = existing_assignments.get(assignment.id)
        if existing is None:
            db.add(
                OrgAssignment(
                    id=assignment.id,
                    structure_kind=structure_kind,
                    user_id=assignment.user_id,
                    org_unit_id=assignment.org_unit_id,
                    manager_user_id=assignment.manager_user_id,
                    title=assignment.title,
                    is_primary=assignment.is_primary,
                    active=assignment.active,
                    valid_from=assignment.valid_from,
                    valid_to=assignment.valid_to,
                    source=assignment.source,
                    wc_operator_id=assignment.wc_operator_id,
                    created_by_user_id=current_user.id,
                    updated_by_user_id=current_user.id,
                )
            )
            assignments_created += 1
        else:
            existing.user_id = assignment.user_id
            existing.org_unit_id = assignment.org_unit_id
            existing.manager_user_id = assignment.manager_user_id
            existing.title = assignment.title
            existing.is_primary = assignment.is_primary
            existing.active = assignment.active
            existing.valid_from = assignment.valid_from
            existing.valid_to = assignment.valid_to
            existing.source = assignment.source
            existing.wc_operator_id = assignment.wc_operator_id
            existing.updated_by_user_id = current_user.id
            assignments_updated += 1
    db.flush()

    existing_overrides = {
        item.id: item
        for item in db.execute(
            select(OrgVisibilityOverride).where(
                OrgVisibilityOverride.id.in_([override.id for override in snapshot.overrides]),
                OrgVisibilityOverride.structure_kind == structure_kind,
            )
        ).scalars().all()
    }
    for override in snapshot.overrides:
        existing = existing_overrides.get(override.id)
        if existing is None:
            db.add(
                OrgVisibilityOverride(
                    id=override.id,
                    structure_kind=structure_kind,
                    viewer_user_id=override.viewer_user_id,
                    target_type=override.target_type,
                    target_user_id=override.target_user_id,
                    target_org_unit_id=override.target_org_unit_id,
                    scope=override.scope,
                    motivo=override.motivo,
                    valid_from=override.valid_from,
                    valid_to=override.valid_to,
                    is_active=override.is_active,
                    created_by_user_id=current_user.id,
                    updated_by_user_id=current_user.id,
                )
            )
            overrides_created += 1
        else:
            existing.viewer_user_id = override.viewer_user_id
            existing.target_type = override.target_type
            existing.target_user_id = override.target_user_id
            existing.target_org_unit_id = override.target_org_unit_id
            existing.scope = override.scope
            existing.motivo = override.motivo
            existing.valid_from = override.valid_from
            existing.valid_to = override.valid_to
            existing.is_active = override.is_active
            existing.updated_by_user_id = current_user.id
            overrides_updated += 1

    db.commit()
    return OrganigrammaImportResponse(
        mode=mode,
        units_created=units_created,
        units_updated=units_updated,
        assignments_created=assignments_created,
        assignments_updated=assignments_updated,
        overrides_created=overrides_created,
        overrides_updated=overrides_updated,
    )


def _validate_snapshot(
    snapshot: OrganigrammaSnapshot,
    db: Session,
    *,
    structure_kind: str = "organigramma",
) -> None:
    _raise_if_duplicates("unit", [unit.id for unit in snapshot.units])
    _raise_if_duplicates("assignment", [assignment.id for assignment in snapshot.assignments])
    _raise_if_duplicates("override", [override.id for override in snapshot.overrides])

    unit_ids = {unit.id for unit in snapshot.units}
    missing_parent_ids = sorted({unit.parent_id for unit in snapshot.units if unit.parent_id is not None and unit.parent_id not in unit_ids})
    if missing_parent_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Snapshot contains unknown parent unit references: {', '.join(str(item) for item in missing_parent_ids)}",
        )

    referenced_user_ids: set[int] = set()
    referenced_unit_ids: set[UUID] = set(unit_ids)
    for assignment in snapshot.assignments:
        referenced_user_ids.add(assignment.user_id)
        if assignment.manager_user_id is not None:
            referenced_user_ids.add(assignment.manager_user_id)
        referenced_unit_ids.add(assignment.org_unit_id)
    for override in snapshot.overrides:
        referenced_user_ids.add(override.viewer_user_id)
        if override.target_user_id is not None:
            referenced_user_ids.add(override.target_user_id)
        if override.target_org_unit_id is not None:
            referenced_unit_ids.add(override.target_org_unit_id)

    existing_user_ids = {
        item[0] for item in db.execute(select(ApplicationUser.id).where(ApplicationUser.id.in_(referenced_user_ids))).all()
    }
    missing_user_ids = sorted(referenced_user_ids - existing_user_ids)
    if missing_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Snapshot references unknown users: {', '.join(str(item) for item in missing_user_ids)}",
        )

    missing_assignment_unit_ids = sorted(
        {
            unit_id
            for unit_id in referenced_unit_ids
            if unit_id not in unit_ids
            and db.execute(
                select(OrgUnit.id).where(
                    OrgUnit.id == unit_id,
                    OrgUnit.structure_kind == structure_kind,
                )
            ).scalar_one_or_none() is None
        },
        key=str,
    )
    if missing_assignment_unit_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Snapshot references unknown org units: "
                + ", ".join(str(item) for item in missing_assignment_unit_ids)
            ),
        )


def _raise_if_duplicates(entity_name: str, values: list[UUID]) -> None:
    duplicates = [value for value, count in Counter(values).items() if count > 1]
    if duplicates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Snapshot contains duplicate {entity_name} ids: {', '.join(str(item) for item in duplicates)}",
        )
