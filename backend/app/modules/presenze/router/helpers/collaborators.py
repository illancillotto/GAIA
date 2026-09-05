from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeSupervisorAssignment,
)
from app.modules.presenze.router.helpers.schedules import (
    _load_latest_template_codes_by_collaborator,
)
from app.modules.presenze.schemas import (
    PresenzeCollaboratorResponse,
    PresenzeSupervisorAssignmentResponse,
)
from app.modules.presenze.services.contract_profile import (
    PresenzeContractProfile,
    normalize_contract_kind,
    resolve_contract_profile,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

def _serialize_collaborator(
    db: Session,
    collaborator: PresenzeCollaborator,
    *,
    template_code: str | None = None,
) -> PresenzeCollaboratorResponse:
    profile, _ = _resolve_collaborator_contract_profile(db, collaborator, template_code=template_code)
    return PresenzeCollaboratorResponse.model_validate(
        {
            **collaborator.__dict__,
            "contract_kind": profile.contract_kind,
            "standard_daily_minutes": profile.standard_daily_minutes,
        }
    )

def _resolve_collaborator_contract_profile(
    db: Session,
    collaborator: PresenzeCollaborator,
    *,
    template_code: str | None = None,
) -> tuple[PresenzeContractProfile, str]:
    resolved_template_code = template_code
    if resolved_template_code is None:
        resolved_template_code = _load_latest_template_codes_by_collaborator(db, [collaborator.id]).get(collaborator.id)
    has_explicit_profile = normalize_contract_kind(collaborator.contract_kind) is not None or collaborator.standard_daily_minutes is not None
    profile = resolve_contract_profile(
        collaborator.contract_kind,
        collaborator.standard_daily_minutes,
        template_code=resolved_template_code,
    )
    if has_explicit_profile:
        return profile, "explicit"
    if profile.contract_kind is not None or profile.standard_daily_minutes is not None:
        return profile, "derived"
    return profile, "missing"

def _serialize_supervisor_assignment(
    db: Session,
    assignment: PresenzeSupervisorAssignment,
) -> PresenzeSupervisorAssignmentResponse:
    collaborator = db.get(PresenzeCollaborator, assignment.collaborator_id)
    supervisor = db.get(ApplicationUser, assignment.supervisor_user_id)
    supervisor_payload = None
    if supervisor is not None:
        supervisor_payload = {
            "id": supervisor.id,
            "username": supervisor.username,
            "full_name": supervisor.full_name,
            "email": supervisor.email,
            "role": supervisor.role,
            "is_active": supervisor.is_active,
        }
    return PresenzeSupervisorAssignmentResponse.model_validate(
        {
            **assignment.__dict__,
            "supervisor": supervisor_payload,
            "collaborator": _serialize_collaborator(db, collaborator) if collaborator is not None else None,
        }
    )

# fmt: on

__all__ = [
    "_resolve_collaborator_contract_profile",
    "_serialize_collaborator",
    "_serialize_supervisor_assignment",
]
