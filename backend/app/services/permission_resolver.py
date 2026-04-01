from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.section_permission import RoleSectionPermission, Section, UserSectionPermission

ROLE_HIERARCHY: dict[str, int] = {
    ApplicationUserRole.VIEWER.value: 1,
    ApplicationUserRole.REVIEWER.value: 2,
    ApplicationUserRole.ADMIN.value: 3,
    ApplicationUserRole.SUPER_ADMIN.value: 4,
}


@dataclass
class ResolvedPermission:
    section_key: str
    section_label: str
    module: str
    is_granted: bool
    source: str


def _resolve_for_section(db: Session, user: ApplicationUser, section: Section) -> ResolvedPermission:
    if user.is_super_admin:
        return ResolvedPermission(section.key, section.label, section.module, True, "super_admin")

    user_override = db.execute(
        select(UserSectionPermission).where(
            UserSectionPermission.user_id == user.id,
            UserSectionPermission.section_id == section.id,
        )
    ).scalar_one_or_none()
    if user_override is not None:
        return ResolvedPermission(
            section.key,
            section.label,
            section.module,
            user_override.is_granted,
            "user_override",
        )

    role_default = db.execute(
        select(RoleSectionPermission).where(
            RoleSectionPermission.section_id == section.id,
            RoleSectionPermission.role == user.role,
        )
    ).scalar_one_or_none()
    if role_default is not None:
        return ResolvedPermission(
            section.key,
            section.label,
            section.module,
            role_default.is_granted,
            "role_default",
        )

    user_rank = ROLE_HIERARCHY.get(user.role, 0)
    min_rank = ROLE_HIERARCHY.get(section.min_role, 999)
    if user_rank >= min_rank:
        return ResolvedPermission(section.key, section.label, section.module, True, "min_role")

    return ResolvedPermission(section.key, section.label, section.module, False, "denied")


def resolve_user_permissions(db: Session, user: ApplicationUser) -> list[ResolvedPermission]:
    if user.is_super_admin:
        enabled_modules = ["accessi", "rete", "inventario", "catasto", "utenze"]
    else:
        enabled_modules = user.enabled_modules

    if not enabled_modules:
        return []

    sections = db.execute(
        select(Section)
        .where(Section.is_active.is_(True), Section.module.in_(enabled_modules))
        .order_by(Section.module, Section.sort_order, Section.id)
    ).scalars().all()
    return [_resolve_for_section(db, user, section) for section in sections]


def can_access_section(db: Session, user: ApplicationUser, section_key: str) -> bool:
    section = db.execute(
        select(Section).where(Section.key == section_key, Section.is_active.is_(True))
    ).scalar_one_or_none()
    if section is None:
        return False
    resolved = _resolve_for_section(db, user, section)
    return resolved.is_granted
