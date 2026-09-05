from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyRecord,
)
from app.modules.presenze.services.visibility_policy import (
    can_approve_daily_record,
    can_read_collaborator,
    can_read_daily_record,
    resolve_presenze_visibility,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

def _is_admin_user(current_user: ApplicationUser) -> bool:
    return current_user.role in {"admin", "super_admin"}

def _is_hr_manager(current_user: ApplicationUser) -> bool:
    return current_user.role == "hr_manager"

def _can_view_all_inaz_data(current_user: ApplicationUser) -> bool:
    return _is_admin_user(current_user) or _is_hr_manager(current_user)

def _can_manage_supervisors(current_user: ApplicationUser) -> bool:
    return _is_admin_user(current_user)

def _can_access_collaborator(db: Session, current_user: ApplicationUser, collaborator: PresenzeCollaborator) -> bool:
    return can_read_collaborator(resolve_presenze_visibility(db, current_user), collaborator)

def _can_access_daily_record(db: Session, current_user: ApplicationUser, record: PresenzeDailyRecord) -> bool:
    return can_read_daily_record(resolve_presenze_visibility(db, current_user), record)

def _can_validate_daily_record(db: Session, current_user: ApplicationUser, record: PresenzeDailyRecord) -> bool:
    return can_approve_daily_record(resolve_presenze_visibility(db, current_user), record)

def _can_edit_daily_record(current_user: ApplicationUser, record: PresenzeDailyRecord) -> bool:
    if _can_view_all_inaz_data(current_user):
        return True
    return record.owner_user_id == current_user.id

# fmt: on

__all__ = [
    "_can_access_collaborator",
    "_can_access_daily_record",
    "_can_edit_daily_record",
    "_can_manage_supervisors",
    "_can_validate_daily_record",
    "_can_view_all_inaz_data",
    "_is_admin_user",
    "_is_hr_manager",
]
