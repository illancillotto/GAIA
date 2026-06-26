from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.section_permission import RoleSectionPermission, Section, UserSectionPermission

ROLE_HIERARCHY: dict[str, int] = {
    ApplicationUserRole.OPERATOR.value: 1,
    ApplicationUserRole.VIEWER.value: 1,
    ApplicationUserRole.REVIEWER.value: 2,
    ApplicationUserRole.HR_MANAGER.value: 2,
    ApplicationUserRole.ADMIN.value: 3,
    ApplicationUserRole.SUPER_ADMIN.value: 4,
}


def canonicalize_section_module(module: str) -> str:
    return "presenze" if module == "inaz" else module


def canonicalize_section_key(section_key: str) -> str:
    return f"presenze.{section_key[len('inaz.'):]}" if section_key.startswith("inaz.") else section_key


def _candidate_section_keys(section_key: str) -> tuple[str, ...]:
    canonical = canonicalize_section_key(section_key)
    if canonical.startswith("presenze."):
        return (canonical, f"inaz.{canonical[len('presenze.'):]}")
    return (canonical,)


@dataclass
class ResolvedPermission:
    section_key: str
    section_label: str
    module: str
    is_granted: bool
    source: str


def _resolve_for_section(db: Session, user: ApplicationUser, section: Section) -> ResolvedPermission:
    canonical_section_key = canonicalize_section_key(section.key)
    canonical_module = canonicalize_section_module(section.module)
    if user.is_super_admin:
        return ResolvedPermission(canonical_section_key, section.label, canonical_module, True, "super_admin")

    user_override = db.execute(
        select(UserSectionPermission).where(
            UserSectionPermission.user_id == user.id,
            UserSectionPermission.section_id == section.id,
        )
    ).scalar_one_or_none()
    if user_override is not None:
        return ResolvedPermission(
            canonical_section_key,
            section.label,
            canonical_module,
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
            canonical_section_key,
            section.label,
            canonical_module,
            role_default.is_granted,
            "role_default",
        )

    user_rank = ROLE_HIERARCHY.get(user.role, 0)
    min_rank = ROLE_HIERARCHY.get(section.min_role, 999)
    if user_rank >= min_rank:
        return ResolvedPermission(canonical_section_key, section.label, canonical_module, True, "min_role")

    return ResolvedPermission(canonical_section_key, section.label, canonical_module, False, "denied")


def resolve_user_permissions(db: Session, user: ApplicationUser) -> list[ResolvedPermission]:
    if user.is_super_admin:
        enabled_modules = ["accessi", "rete", "inventario", "catasto", "utenze", "operazioni", "riordino", "ruolo", "presenze", "organigramma"]
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
        select(Section).where(Section.key.in_(_candidate_section_keys(section_key)), Section.is_active.is_(True))
    ).scalar_one_or_none()
    if section is None:
        return False
    resolved = _resolve_for_section(db, user, section)
    return resolved.is_granted
