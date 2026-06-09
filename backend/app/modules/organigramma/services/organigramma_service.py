"""Assemblaggio delle risposte API dell'organigramma (tree, dettaglio, simulatore).

Logica di sola lettura che compone i dati grezzi del repository negli schemi di
risposta. Nessuna mutazione di stato qui.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.organigramma import repositories as repo
from app.modules.organigramma.models import OrgAssignment, OrgUnit, OrgVisibilityOverride
from app.modules.organigramma.schemas import (
    OrgAssignmentResponse,
    OrgUnitResponse,
    OrgUnitTreeNode,
    OrgVisibilityOverrideResponse,
    PersonRef,
    UnitDetailResponse,
    VisibilityResult,
    VisiblePerson,
    VisibleUnit,
)
from app.modules.organigramma.services.visibility_service import (
    VIA_HIERARCHY,
    effective_visibility,
    ensure_aware,
)

_LEADER_TITLE_RE = re.compile(r"capo|dirigent|direttore|responsabile", re.IGNORECASE)


def _person_ref(user: ApplicationUser | None) -> PersonRef | None:
    if user is None:
        return None
    return PersonRef.model_validate(user)


def _assignment_response(
    assignment: OrgAssignment, people: dict[int, ApplicationUser]
) -> OrgAssignmentResponse:
    response = OrgAssignmentResponse.model_validate(assignment)
    response.person = _person_ref(people.get(assignment.user_id))
    if assignment.manager_user_id is not None:
        response.manager = _person_ref(people.get(assignment.manager_user_id))
    return response


# --------------------------------------------------------------------------- #
# Tree
# --------------------------------------------------------------------------- #
def build_tree(db: Session) -> list[OrgUnitTreeNode]:
    units = repo.list_units(db)
    assignments = repo.list_assignments(db)

    children_by_parent: dict[UUID | None, list[OrgUnit]] = {}
    for unit in units:
        children_by_parent.setdefault(unit.parent_id, []).append(unit)

    active_people_by_unit: Counter[UUID] = Counter()
    for assignment in assignments:
        if assignment.active:
            active_people_by_unit[assignment.org_unit_id] += 1

    def to_node(unit: OrgUnit) -> OrgUnitTreeNode:
        children = children_by_parent.get(unit.id, [])
        return OrgUnitTreeNode(
            id=unit.id,
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
            person_count=active_people_by_unit.get(unit.id, 0),
            child_count=len(children),
            children=[to_node(child) for child in children],
        )

    return [to_node(root) for root in children_by_parent.get(None, [])]


# --------------------------------------------------------------------------- #
# Unit detail
# --------------------------------------------------------------------------- #
def _ancestor_path(unit: OrgUnit, units_by_id: dict[UUID, OrgUnit]) -> list[OrgUnit]:
    path: list[OrgUnit] = []
    current: OrgUnit | None = unit
    seen: set[UUID] = set()
    while current is not None and current.id not in seen:
        path.insert(0, current)
        seen.add(current.id)
        current = units_by_id.get(current.parent_id) if current.parent_id else None
    return path


def resolve_unit_responsabile(
    assignments: list[OrgAssignment], people: dict[int, ApplicationUser]
) -> tuple[ApplicationUser | None, str | None]:
    """Responsabile dell'unità: il caposettore/dirigente assegnato all'unità; in
    assenza, il manager comune dei membri (tipicamente nell'unità padre)."""
    members = [a for a in assignments if a.active]
    for member in members:
        if member.title and _LEADER_TITLE_RE.search(member.title):
            return people.get(member.user_id), member.title
    manager_ids = [a.manager_user_id for a in members if a.manager_user_id is not None]
    if manager_ids:
        most_common_id, _ = Counter(manager_ids).most_common(1)[0]
        return people.get(most_common_id), None
    return None, None


def get_unit_detail(db: Session, unit_id: UUID) -> UnitDetailResponse | None:
    unit = repo.get_unit(db, unit_id)
    if unit is None:
        return None

    units_by_id = {u.id: u for u in repo.list_units(db)}
    assignments = repo.list_assignments(db, unit_id=unit_id)

    user_ids: set[int] = set()
    for assignment in assignments:
        user_ids.add(assignment.user_id)
        if assignment.manager_user_id is not None:
            user_ids.add(assignment.manager_user_id)
    people = repo.get_people_map(db, user_ids)

    responsabile, responsabile_title = resolve_unit_responsabile(assignments, people)

    return UnitDetailResponse(
        unit=OrgUnitResponse.model_validate(unit),
        path=[OrgUnitResponse.model_validate(u) for u in _ancestor_path(unit, units_by_id)],
        responsabile=_person_ref(responsabile),
        responsabile_title=responsabile_title,
        assignments=[_assignment_response(a, people) for a in assignments],
    )


def list_assignment_responses(
    db: Session, *, unit_id: UUID | None = None, user_id: int | None = None
) -> list[OrgAssignmentResponse]:
    assignments = repo.list_assignments(db, unit_id=unit_id, user_id=user_id)
    user_ids: set[int] = set()
    for assignment in assignments:
        user_ids.add(assignment.user_id)
        if assignment.manager_user_id is not None:
            user_ids.add(assignment.manager_user_id)
    people = repo.get_people_map(db, user_ids)
    return [_assignment_response(a, people) for a in assignments]


# --------------------------------------------------------------------------- #
# Override status + response
# --------------------------------------------------------------------------- #
def override_status(override: OrgVisibilityOverride, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    if not override.is_active:
        return "disattivato"
    valid_from = ensure_aware(override.valid_from)
    valid_to = ensure_aware(override.valid_to)
    if valid_from is not None and valid_from > now:
        return "programmato"
    if valid_to is not None and valid_to < now:
        return "scaduto"
    return "attivo"


def override_response(
    db: Session,
    override: OrgVisibilityOverride,
    *,
    people: dict[int, ApplicationUser] | None = None,
    units_by_id: dict[UUID, OrgUnit] | None = None,
) -> OrgVisibilityOverrideResponse:
    if people is None:
        people = repo.get_people_map(
            db,
            {override.viewer_user_id}
            | ({override.target_user_id} if override.target_user_id else set()),
        )
    if units_by_id is None:
        units_by_id = {u.id: u for u in repo.list_units(db)}

    response = OrgVisibilityOverrideResponse.model_validate(override)
    response.status = override_status(override)
    response.viewer = _person_ref(people.get(override.viewer_user_id))
    if override.target_type == "user" and override.target_user_id is not None:
        target = people.get(override.target_user_id)
        response.target_label = (target.full_name or target.username) if target else None
    elif override.target_type == "org_unit" and override.target_org_unit_id is not None:
        unit = units_by_id.get(override.target_org_unit_id)
        response.target_label = unit.nome if unit else None
    return response


def list_override_responses(db: Session) -> list[OrgVisibilityOverrideResponse]:
    overrides = repo.list_overrides(db)
    user_ids: set[int] = set()
    for override in overrides:
        user_ids.add(override.viewer_user_id)
        if override.target_user_id is not None:
            user_ids.add(override.target_user_id)
    people = repo.get_people_map(db, user_ids)
    units_by_id = {u.id: u for u in repo.list_units(db)}
    return [
        override_response(db, o, people=people, units_by_id=units_by_id) for o in overrides
    ]


# --------------------------------------------------------------------------- #
# Visibility simulator
# --------------------------------------------------------------------------- #
def build_visibility_result(db: Session, viewer: ApplicationUser) -> VisibilityResult:
    visibility = effective_visibility(db, viewer)
    units_by_id = {u.id: u for u in repo.list_units(db)}
    assignments = repo.list_assignments(db)

    visible_units = [
        VisibleUnit(
            org_unit_id=unit_id,
            nome=units_by_id[unit_id].nome,
            tipo=units_by_id[unit_id].tipo,
            parent_id=units_by_id[unit_id].parent_id,
            via=via,
            scope=visibility.unit_scope.get(unit_id),
        )
        for unit_id, via in visibility.unit_via.items()
        if unit_id in units_by_id
    ]
    visible_units.sort(key=lambda u: (u.nome,))

    people = repo.get_people_map(db, visibility.person_ids)
    # Per ogni persona visibile, scegli un'assegnazione attiva su un'unità visibile.
    assignment_by_user: dict[int, OrgAssignment] = {}
    for assignment in assignments:
        if not assignment.active:
            continue
        if assignment.user_id not in visibility.person_ids:
            continue
        if assignment.org_unit_id not in visibility.unit_via:
            continue
        current = assignment_by_user.get(assignment.user_id)
        if current is None or (not current.is_primary and assignment.is_primary):
            assignment_by_user[assignment.user_id] = assignment

    visible_people: list[VisiblePerson] = []
    for user_id, via in visibility.person_via.items():
        assignment = assignment_by_user.get(user_id)
        person = people.get(user_id)
        visible_people.append(
            VisiblePerson(
                user_id=user_id,
                full_name=(person.full_name or person.username) if person else None,
                title=assignment.title if assignment else None,
                org_unit_id=assignment.org_unit_id if assignment else None,
                via=via,
            )
        )
    visible_people.sort(key=lambda p: (p.full_name or ""))

    return VisibilityResult(
        viewer=PersonRef.model_validate(viewer),
        full=visibility.full,
        units=visible_units,
        people=visible_people,
    )
