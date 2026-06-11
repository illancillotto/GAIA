from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.organigramma.models import (
    OrgAssignment,
    OrgChangeEvent,
    OrgDraft,
    OrgRevision,
    OrgRevisionAssignment,
    OrgRevisionUnit,
    OrgUnit,
    OrgVisibilityOverride,
)
from app.modules.organigramma.schemas import (
    OrgAssignmentCreate,
    OrgAssignmentUpdate,
    OrgDraftCreate,
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


# --------------------------------------------------------------------------- #
# Revisioni e bozze
# --------------------------------------------------------------------------- #
def list_revisions(db: Session) -> list[OrgRevision]:
    return list(
        db.execute(
            select(OrgRevision).order_by(
                OrgRevision.published_at.desc().nullslast(),
                OrgRevision.created_at.desc(),
            )
        ).scalars().all()
    )


def get_revision(db: Session, revision_id: UUID) -> OrgRevision | None:
    return db.get(OrgRevision, revision_id)


def get_current_published_revision(db: Session) -> OrgRevision | None:
    return db.execute(
        select(OrgRevision)
        .where(OrgRevision.status == "published")
        .order_by(OrgRevision.published_at.desc().nullslast(), OrgRevision.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def create_revision(
    db: Session,
    *,
    label: str,
    status: str,
    created_by_user_id: int | None,
    notes: str | None = None,
    source_revision_id: UUID | None = None,
    published_by_user_id: int | None = None,
    published_at: datetime | None = None,
) -> OrgRevision:
    revision = OrgRevision(
        label=label,
        status=status,
        notes=notes,
        source_revision_id=source_revision_id,
        created_by_user_id=created_by_user_id,
        published_by_user_id=published_by_user_id,
        published_at=published_at,
    )
    db.add(revision)
    db.flush()
    return revision


def list_revision_units(db: Session, revision_id: UUID) -> list[OrgRevisionUnit]:
    return list(
        db.execute(
            select(OrgRevisionUnit)
            .where(OrgRevisionUnit.revision_id == revision_id)
            .order_by(OrgRevisionUnit.sort_order, OrgRevisionUnit.nome)
        ).scalars().all()
    )


def list_revision_assignments(db: Session, revision_id: UUID) -> list[OrgRevisionAssignment]:
    return list(
        db.execute(
            select(OrgRevisionAssignment)
            .where(OrgRevisionAssignment.revision_id == revision_id)
            .order_by(OrgRevisionAssignment.created_at, OrgRevisionAssignment.logical_org_assignment_id)
        ).scalars().all()
    )


def snapshot_revision_from_canonical(db: Session, revision_id: UUID) -> None:
    units = list_units(db)
    assignments = list_assignments(db)
    for unit in units:
        db.add(
            OrgRevisionUnit(
                revision_id=revision_id,
                logical_org_unit_id=unit.id,
                nome=unit.nome,
                tipo=unit.tipo,
                parent_id=unit.parent_id,
                is_active=unit.is_active,
                sort_order=unit.sort_order,
                canvas_x=unit.canvas_x,
                canvas_y=unit.canvas_y,
                source=unit.source,
                wc_area_id=unit.wc_area_id,
                legacy_team_id=unit.legacy_team_id,
                created_at=unit.created_at,
                updated_at=unit.updated_at,
            )
        )
    for assignment in assignments:
        db.add(
            OrgRevisionAssignment(
                revision_id=revision_id,
                logical_org_assignment_id=assignment.id,
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
                created_at=assignment.created_at,
                updated_at=assignment.updated_at,
            )
        )
    db.flush()


def clone_revision_snapshot(db: Session, *, source_revision_id: UUID, target_revision_id: UUID) -> None:
    units = list_revision_units(db, source_revision_id)
    assignments = list_revision_assignments(db, source_revision_id)
    for unit in units:
        db.add(
            OrgRevisionUnit(
                revision_id=target_revision_id,
                logical_org_unit_id=unit.logical_org_unit_id,
                nome=unit.nome,
                tipo=unit.tipo,
                parent_id=unit.parent_id,
                is_active=unit.is_active,
                sort_order=unit.sort_order,
                canvas_x=unit.canvas_x,
                canvas_y=unit.canvas_y,
                source=unit.source,
                wc_area_id=unit.wc_area_id,
                legacy_team_id=unit.legacy_team_id,
                created_at=unit.created_at,
                updated_at=unit.updated_at,
            )
        )
    for assignment in assignments:
        db.add(
            OrgRevisionAssignment(
                revision_id=target_revision_id,
                logical_org_assignment_id=assignment.logical_org_assignment_id,
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
                created_at=assignment.created_at,
                updated_at=assignment.updated_at,
            )
        )
    db.flush()


def get_active_draft_for_user(db: Session, user_id: int) -> OrgDraft | None:
    return db.execute(
        select(OrgDraft)
        .where(OrgDraft.created_by_user_id == user_id, OrgDraft.status == "draft")
        .order_by(OrgDraft.updated_at.desc(), OrgDraft.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_draft(db: Session, draft_id: UUID) -> OrgDraft | None:
    return db.get(OrgDraft, draft_id)


def create_draft(
    db: Session,
    payload: OrgDraftCreate,
    *,
    user_id: int | None,
    base_revision_id: UUID,
    working_revision_id: UUID,
) -> OrgDraft:
    draft = OrgDraft(
        name=payload.name,
        notes=payload.notes,
        status="draft",
        base_revision_id=base_revision_id,
        working_revision_id=working_revision_id,
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
    )
    db.add(draft)
    db.flush()
    return draft


def update_draft_status(
    db: Session,
    draft: OrgDraft,
    *,
    status: str,
    user_id: int | None,
    published_at: datetime | None = None,
) -> OrgDraft:
    draft.status = status
    draft.updated_by_user_id = user_id
    if status == "published":
        draft.published_by_user_id = user_id
        draft.published_at = published_at
    db.add(draft)
    db.flush()
    return draft


def list_change_events(db: Session, draft_id: UUID) -> list[OrgChangeEvent]:
    return list(
        db.execute(
            select(OrgChangeEvent)
            .where(OrgChangeEvent.draft_id == draft_id)
            .order_by(OrgChangeEvent.changed_at.desc())
        ).scalars().all()
    )


def count_change_events(db: Session, draft_id: UUID) -> int:
    return (
        db.execute(
            select(func.count(OrgChangeEvent.id)).where(OrgChangeEvent.draft_id == draft_id)
        ).scalar_one()
        or 0
    )


def add_change_event(
    db: Session,
    *,
    draft_id: UUID,
    entity_type: str,
    entity_id: UUID,
    action: str,
    changed_by_user_id: int | None,
    before_json: dict | None = None,
    after_json: dict | None = None,
) -> OrgChangeEvent:
    event = OrgChangeEvent(
        draft_id=draft_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before_json=before_json,
        after_json=after_json,
        changed_by_user_id=changed_by_user_id,
    )
    db.add(event)
    db.flush()
    return event


def archive_published_revisions(db: Session, except_revision_id: UUID | None = None) -> None:
    query = update(OrgRevision).where(OrgRevision.status == "published")
    if except_revision_id is not None:
        query = query.where(OrgRevision.id != except_revision_id)
    db.execute(query.values(status="archived"))
    db.flush()


def publish_revision(
    db: Session,
    revision: OrgRevision,
    *,
    user_id: int | None,
    published_at: datetime | None = None,
) -> OrgRevision:
    revision.status = "published"
    revision.published_by_user_id = user_id
    revision.published_at = published_at or datetime.now(timezone.utc)
    db.add(revision)
    db.flush()
    return revision
