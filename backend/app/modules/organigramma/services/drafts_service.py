from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.organigramma import repositories as repo
from app.modules.organigramma.models import OrgDraft, OrgRevisionAssignment, OrgRevisionUnit
from app.modules.organigramma.schemas import (
    OrgAssignmentResponse,
    OrgDraftCreate,
    OrgDraftDetailResponse,
    OrgDraftResponse,
    OrgRevisionResponse,
    OrgUnitTreeNode,
    PersonRef,
)


def _person_ref(user: ApplicationUser | None) -> PersonRef | None:
    if user is None:
        return None
    return PersonRef.model_validate(user)


def _revision_assignment_response(
    assignment: OrgRevisionAssignment,
    people: dict[int, ApplicationUser],
) -> OrgAssignmentResponse:
    response = OrgAssignmentResponse.model_validate(
        {
            "id": assignment.logical_org_assignment_id,
            "user_id": assignment.user_id,
            "org_unit_id": assignment.org_unit_id,
            "manager_user_id": assignment.manager_user_id,
            "title": assignment.title,
            "is_primary": assignment.is_primary,
            "active": assignment.active,
            "valid_from": assignment.valid_from,
            "valid_to": assignment.valid_to,
            "source": assignment.source,
            "wc_operator_id": assignment.wc_operator_id,
            "created_at": assignment.created_at,
            "updated_at": assignment.updated_at,
        }
    )
    response.person = _person_ref(people.get(assignment.user_id))
    if assignment.manager_user_id is not None:
        response.manager = _person_ref(people.get(assignment.manager_user_id))
    return response


def ensure_published_revision(db: Session, *, user_id: int | None) -> OrgRevisionResponse:
    current = repo.get_current_published_revision(db)
    if current is None:
        now = datetime.now(timezone.utc)
        created = repo.create_revision(
            db,
            label=f"Pubblicato iniziale {now.strftime('%Y-%m-%d %H:%M')}",
            status="published",
            created_by_user_id=user_id,
            published_by_user_id=user_id,
            published_at=now,
        )
        repo.snapshot_revision_from_canonical(db, created.id)
        db.commit()
        db.refresh(created)
        current = created
    return OrgRevisionResponse.model_validate(current)


def list_revision_responses(db: Session) -> list[OrgRevisionResponse]:
    return [OrgRevisionResponse.model_validate(revision) for revision in repo.list_revisions(db)]


def get_active_draft_response(db: Session, *, user_id: int) -> OrgDraftDetailResponse | None:
    draft = repo.get_active_draft_for_user(db, user_id)
    if draft is None:
        return None
    return build_draft_detail(db, draft)


def build_draft_detail(db: Session, draft: OrgDraft) -> OrgDraftDetailResponse:
    return OrgDraftDetailResponse(
        **OrgDraftResponse.model_validate(draft).model_dump(),
        event_count=repo.count_change_events(db, draft.id),
        unit_count=len(repo.list_revision_units(db, draft.working_revision_id)),
        assignment_count=len(repo.list_revision_assignments(db, draft.working_revision_id)),
    )


def create_draft_from_current(
    db: Session,
    payload: OrgDraftCreate,
    *,
    user_id: int,
) -> OrgDraftDetailResponse:
    current = repo.get_active_draft_for_user(db, user_id)
    if current is not None:
        raise ValueError("Esiste già una bozza attiva per questo utente.")

    base_revision = repo.get_current_published_revision(db)
    if base_revision is None:
        ensure_published_revision(db, user_id=user_id)
        base_revision = repo.get_current_published_revision(db)
    assert base_revision is not None

    working_revision = repo.create_revision(
        db,
        label=f"Bozza {payload.name}",
        status="draft",
        created_by_user_id=user_id,
        notes=payload.notes,
        source_revision_id=base_revision.id,
    )
    repo.clone_revision_snapshot(
        db,
        source_revision_id=base_revision.id,
        target_revision_id=working_revision.id,
    )
    draft = repo.create_draft(
        db,
        payload,
        user_id=user_id,
        base_revision_id=base_revision.id,
        working_revision_id=working_revision.id,
    )
    repo.add_change_event(
        db,
        draft_id=draft.id,
        entity_type="draft",
        entity_id=draft.id,
        action="draft_created",
        changed_by_user_id=user_id,
        after_json={
            "name": draft.name,
            "base_revision_id": str(draft.base_revision_id),
            "working_revision_id": str(draft.working_revision_id),
        },
    )
    db.commit()
    db.refresh(draft)
    return build_draft_detail(db, draft)


def build_tree_for_revision(db: Session, revision_id: UUID) -> list[OrgUnitTreeNode]:
    units = repo.list_revision_units(db, revision_id)
    assignments = repo.list_revision_assignments(db, revision_id)

    children_by_parent: dict[UUID | None, list[OrgRevisionUnit]] = {}
    for unit in units:
        children_by_parent.setdefault(unit.parent_id, []).append(unit)

    active_people_by_unit: Counter[UUID] = Counter()
    for assignment in assignments:
        if assignment.active:
            active_people_by_unit[assignment.org_unit_id] += 1

    def to_node(unit: OrgRevisionUnit) -> OrgUnitTreeNode:
        children = children_by_parent.get(unit.logical_org_unit_id, [])
        return OrgUnitTreeNode(
            id=unit.logical_org_unit_id,
            nome=unit.nome,
            tipo=unit.tipo,
            parent_id=unit.parent_id,
            source=unit.source,
            canvas_x=unit.canvas_x,
            canvas_y=unit.canvas_y,
            wc_area_id=unit.wc_area_id,
            legacy_team_id=unit.legacy_team_id,
            is_active=unit.is_active,
            sort_order=unit.sort_order,
            person_count=active_people_by_unit.get(unit.logical_org_unit_id, 0),
            child_count=len(children),
            children=[to_node(child) for child in children],
        )

    return [to_node(root) for root in children_by_parent.get(None, [])]


def list_assignment_responses_for_revision(
    db: Session,
    revision_id: UUID,
) -> list[OrgAssignmentResponse]:
    assignments = repo.list_revision_assignments(db, revision_id)
    user_ids: set[int] = set()
    for assignment in assignments:
        user_ids.add(assignment.user_id)
        if assignment.manager_user_id is not None:
            user_ids.add(assignment.manager_user_id)
    people = repo.get_people_map(db, user_ids)
    return [_revision_assignment_response(assignment, people) for assignment in assignments]


def publish_draft(db: Session, draft: OrgDraft, *, user_id: int) -> OrgDraftDetailResponse:
    now = datetime.now(timezone.utc)
    working_revision = repo.get_revision(db, draft.working_revision_id)
    if working_revision is None:
        raise ValueError("Revisione di lavoro non trovata.")
    repo.archive_published_revisions(db, except_revision_id=working_revision.id)
    repo.publish_revision(db, working_revision, user_id=user_id, published_at=now)
    repo.update_draft_status(db, draft, status="published", user_id=user_id, published_at=now)
    repo.add_change_event(
        db,
        draft_id=draft.id,
        entity_type="draft",
        entity_id=draft.id,
        action="published",
        changed_by_user_id=user_id,
        before_json={"status": "draft"},
        after_json={"status": "published", "published_revision_id": str(working_revision.id)},
    )
    db.commit()
    db.refresh(draft)
    return build_draft_detail(db, draft)


def discard_draft(db: Session, draft: OrgDraft, *, user_id: int) -> OrgDraftDetailResponse:
    repo.update_draft_status(db, draft, status="discarded", user_id=user_id)
    repo.add_change_event(
        db,
        draft_id=draft.id,
        entity_type="draft",
        entity_id=draft.id,
        action="discarded",
        changed_by_user_id=user_id,
        before_json={"status": "draft"},
        after_json={"status": "discarded"},
    )
    db.commit()
    db.refresh(draft)
    return build_draft_detail(db, draft)
