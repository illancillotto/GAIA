from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.accessi.org_structure import OrgStructureAssignment
from app.modules.organigramma.services.visibility_service import VIA_HIERARCHY, effective_visibility
from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyRecord, PresenzeSupervisorAssignment


FULL_VISIBILITY_ROLES = frozenset({"admin", "super_admin", "hr_manager"})
APPROVAL_SCOPES = frozenset({"approve", "full"})


@dataclass(frozen=True)
class PresenzeVisibilityPolicy:
    viewer_user_id: int
    full_access: bool
    readable_user_ids: frozenset[int] = field(default_factory=frozenset)
    approvable_user_ids: frozenset[int] = field(default_factory=frozenset)
    legacy_collaborator_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)

    @property
    def subordinate_count(self) -> int:
        return len(self.readable_user_ids - {self.viewer_user_id}) + len(self.legacy_collaborator_ids)


def _legacy_hierarchy_user_ids(db: Session, viewer_user_id: int) -> set[int]:
    assignments = db.query(OrgStructureAssignment).filter(OrgStructureAssignment.is_active.is_(True)).all()
    children_by_manager: dict[int, list[int]] = {}
    for assignment in assignments:
        if assignment.manager_user_id is not None:
            children_by_manager.setdefault(assignment.manager_user_id, []).append(assignment.application_user_id)

    result: set[int] = set()
    pending = list(children_by_manager.get(viewer_user_id, ()))
    while pending:
        user_id = pending.pop()
        if user_id in result:
            continue
        result.add(user_id)
        pending.extend(children_by_manager.get(user_id, ()))
    result.discard(viewer_user_id)
    return result


def resolve_presenze_visibility(db: Session, viewer: ApplicationUser) -> PresenzeVisibilityPolicy:
    if viewer.role in FULL_VISIBILITY_ROLES:
        return PresenzeVisibilityPolicy(viewer_user_id=viewer.id, full_access=True)

    canonical = effective_visibility(db, viewer)
    legacy_users = _legacy_hierarchy_user_ids(db, viewer.id)
    readable_users = set(canonical.person_ids) | legacy_users
    approvable_users = {
        user_id
        for user_id, via in canonical.person_via.items()
        if via == VIA_HIERARCHY or canonical.person_scope.get(user_id) in APPROVAL_SCOPES
    } | legacy_users
    legacy_collaborators = frozenset(
        row[0]
        for row in db.query(PresenzeSupervisorAssignment.collaborator_id)
        .filter(PresenzeSupervisorAssignment.supervisor_user_id == viewer.id)
        .all()
    )
    return PresenzeVisibilityPolicy(
        viewer_user_id=viewer.id,
        full_access=False,
        readable_user_ids=frozenset(readable_users),
        approvable_user_ids=frozenset(approvable_users),
        legacy_collaborator_ids=legacy_collaborators,
    )


def collaborator_visibility_filter(policy: PresenzeVisibilityPolicy):
    return or_(
        PresenzeCollaborator.owner_user_id == policy.viewer_user_id,
        PresenzeCollaborator.application_user_id.in_(policy.readable_user_ids),
        PresenzeCollaborator.id.in_(policy.legacy_collaborator_ids),
    )


def daily_record_visibility_filter(policy: PresenzeVisibilityPolicy):
    return or_(
        PresenzeDailyRecord.owner_user_id == policy.viewer_user_id,
        PresenzeDailyRecord.application_user_id.in_(policy.readable_user_ids),
        PresenzeDailyRecord.collaborator_id.in_(policy.legacy_collaborator_ids),
    )


def can_read_collaborator(policy: PresenzeVisibilityPolicy, collaborator: PresenzeCollaborator) -> bool:
    return policy.full_access or any(
        (
            collaborator.owner_user_id == policy.viewer_user_id,
            collaborator.application_user_id in policy.readable_user_ids,
            collaborator.id in policy.legacy_collaborator_ids,
        )
    )


def can_read_daily_record(policy: PresenzeVisibilityPolicy, record: PresenzeDailyRecord) -> bool:
    return policy.full_access or any(
        (
            record.owner_user_id == policy.viewer_user_id,
            record.application_user_id in policy.readable_user_ids,
            record.collaborator_id in policy.legacy_collaborator_ids,
        )
    )


def can_approve_daily_record(policy: PresenzeVisibilityPolicy, record: PresenzeDailyRecord) -> bool:
    return policy.full_access or any(
        (
            record.application_user_id in policy.approvable_user_ids,
            record.collaborator_id in policy.legacy_collaborator_ids,
        )
    )
