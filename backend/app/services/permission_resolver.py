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


def _candidate_enabled_modules(enabled_modules: list[str]) -> list[str]:
    expanded = list(enabled_modules)
    if "presenze" in enabled_modules and "inaz" not in expanded:
        expanded.append("inaz")
    return expanded


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


def _resolved_priority(section: Section, resolved: ResolvedPermission) -> tuple[int, int, int]:
    is_canonical_row = int(
        section.module == canonicalize_section_module(section.module)
        and section.key == canonicalize_section_key(section.key)
    )
    source_rank = {
        "user_override": 4,
        "role_default": 3,
        "min_role": 2,
        "denied": 1,
        "super_admin": 5,
    }.get(resolved.source, 0)
    return (source_rank, is_canonical_row, -section.id)


def resolve_user_permissions(db: Session, user: ApplicationUser) -> list[ResolvedPermission]:
    if user.is_super_admin:
        enabled_modules = ["accessi", "rete", "inventario", "catasto", "utenze", "operazioni", "riordino", "ruolo", "presenze", "organigramma"]
    else:
        enabled_modules = user.enabled_modules

    if not enabled_modules:
        return []

    candidate_modules = _candidate_enabled_modules(enabled_modules)
    sections = db.execute(
        select(Section)
        .where(Section.is_active.is_(True), Section.module.in_(candidate_modules))
        .order_by(Section.module, Section.sort_order, Section.id)
    ).scalars().all()
    deduped: dict[str, tuple[ResolvedPermission, tuple[int, int, int]]] = {}
    order: list[str] = []

    for section in sections:
        resolved = _resolve_for_section(db, user, section)
        priority = _resolved_priority(section, resolved)
        current = deduped.get(resolved.section_key)
        if current is None:
            deduped[resolved.section_key] = (resolved, priority)
            order.append(resolved.section_key)
            continue
        if priority > current[1]:
            deduped[resolved.section_key] = (resolved, priority)

    return [deduped[key][0] for key in order]


def can_access_section(db: Session, user: ApplicationUser, section_key: str) -> bool:
    section = db.execute(
        select(Section).where(Section.key.in_(_candidate_section_keys(section_key)), Section.is_active.is_(True))
    ).scalar_one_or_none()
    if section is None:
        return False
    resolved = _resolve_for_section(db, user, section)
    return resolved.is_granted
