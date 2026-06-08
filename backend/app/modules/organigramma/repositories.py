from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.organigramma.models import (
    OrgAssignment,
    OrgUnit,
    OrgVisibilityOverride,
)
from app.modules.organigramma.schemas import (
    OrgAssignmentCreate,
    OrgAssignmentUpdate,
    OrgUnitCreate,
    OrgUnitUpdate,
    OrgVisibilityOverrideCreate,
    OrgVisibilityOverrideUpdate,
)


# --------------------------------------------------------------------------- #
# Org unit
# --------------------------------------------------------------------------- #
def list_units(db: Session) -> list[OrgUnit]:
    return list(
        db.execute(select(OrgUnit).order_by(OrgUnit.sort_order, OrgUnit.nome)).scalars().all()
    )


def get_unit(db: Session, unit_id: UUID) -> OrgUnit | None:
    return db.get(OrgUnit, unit_id)


def create_unit(db: Session, payload: OrgUnitCreate, *, user_id: int | None) -> OrgUnit:
    unit = OrgUnit(
        **payload.model_dump(),
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


def update_unit(
    db: Session, unit: OrgUnit, payload: OrgUnitUpdate, *, user_id: int | None
) -> OrgUnit:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(unit, key, value)
    unit.updated_by_user_id = user_id
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


def unit_has_children(db: Session, unit_id: UUID) -> bool:
    return db.execute(
        select(OrgUnit.id).where(OrgUnit.parent_id == unit_id).limit(1)
    ).first() is not None


def unit_has_assignments(db: Session, unit_id: UUID) -> bool:
    return db.execute(
        select(OrgAssignment.id).where(OrgAssignment.org_unit_id == unit_id).limit(1)
    ).first() is not None


def delete_unit(db: Session, unit: OrgUnit) -> None:
    db.delete(unit)
    db.commit()


# --------------------------------------------------------------------------- #
# Assignment
# --------------------------------------------------------------------------- #
def list_assignments(
    db: Session, *, unit_id: UUID | None = None, user_id: int | None = None
) -> list[OrgAssignment]:
    query = select(OrgAssignment)
    if unit_id is not None:
        query = query.where(OrgAssignment.org_unit_id == unit_id)
    if user_id is not None:
        query = query.where(OrgAssignment.user_id == user_id)
    return list(db.execute(query.order_by(OrgAssignment.created_at)).scalars().all())


def get_assignment(db: Session, assignment_id: UUID) -> OrgAssignment | None:
    return db.get(OrgAssignment, assignment_id)


def create_assignment(
    db: Session, payload: OrgAssignmentCreate, *, user_id: int | None
) -> OrgAssignment:
    assignment = OrgAssignment(
        **payload.model_dump(),
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def update_assignment(
    db: Session, assignment: OrgAssignment, payload: OrgAssignmentUpdate, *, user_id: int | None
) -> OrgAssignment:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(assignment, key, value)
    assignment.updated_by_user_id = user_id
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def delete_assignment(db: Session, assignment: OrgAssignment) -> None:
    db.delete(assignment)
    db.commit()


# --------------------------------------------------------------------------- #
# Visibility override
# --------------------------------------------------------------------------- #
def list_overrides(db: Session) -> list[OrgVisibilityOverride]:
    return list(
        db.execute(
            select(OrgVisibilityOverride).order_by(OrgVisibilityOverride.created_at.desc())
        ).scalars().all()
    )


def get_override(db: Session, override_id: UUID) -> OrgVisibilityOverride | None:
    return db.get(OrgVisibilityOverride, override_id)


def create_override(
    db: Session, payload: OrgVisibilityOverrideCreate, *, user_id: int | None
) -> OrgVisibilityOverride:
    override = OrgVisibilityOverride(
        **payload.model_dump(),
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
    )
    db.add(override)
    db.commit()
    db.refresh(override)
    return override


def update_override(
    db: Session,
    override: OrgVisibilityOverride,
    payload: OrgVisibilityOverrideUpdate,
    *,
    user_id: int | None,
) -> OrgVisibilityOverride:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(override, key, value)
    override.updated_by_user_id = user_id
    db.add(override)
    db.commit()
    db.refresh(override)
    return override


def delete_override(db: Session, override: OrgVisibilityOverride) -> None:
    db.delete(override)
    db.commit()


# --------------------------------------------------------------------------- #
# People
# --------------------------------------------------------------------------- #
def get_people_map(db: Session, user_ids: set[int]) -> dict[int, ApplicationUser]:
    if not user_ids:
        return {}
    rows = db.execute(
        select(ApplicationUser).where(ApplicationUser.id.in_(user_ids))
    ).scalars().all()
    return {row.id: row for row in rows}
