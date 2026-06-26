from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUserRole
from app.models.section_permission import RoleSectionPermission, Section, UserSectionPermission
from app.schemas.permissions import BulkRolePermissionsRequest, BulkUserPermissionsRequest, SectionCreate, SectionUpdate
from app.services.permission_resolver import ROLE_HIERARCHY


def canonicalize_section_module(module: str) -> str:
    return "presenze" if module == "inaz" else module


def canonicalize_section_key(key: str) -> str:
    return f"presenze.{key[len('inaz.'):]}" if key.startswith("inaz.") else key


def _candidate_section_modules(module: str) -> tuple[str, ...]:
    canonical = canonicalize_section_module(module)
    if canonical == "presenze":
        return ("presenze", "inaz")
    return (canonical,)


def _candidate_section_keys(key: str) -> tuple[str, ...]:
    canonical = canonicalize_section_key(key)
    if canonical.startswith("presenze."):
        return (canonical, f"inaz.{canonical[len('presenze.'):]}")
    return (canonical,)


def _section_identity_priority(section: Section) -> tuple[int, int]:
    canonical_module = canonicalize_section_module(section.module)
    canonical_key = canonicalize_section_key(section.key)
    is_canonical_row = int(section.module == canonical_module and section.key == canonical_key)
    return (is_canonical_row, -section.id)


def _dedupe_sections(sections: list[Section]) -> list[Section]:
    by_canonical_key: dict[str, Section] = {}
    order: list[str] = []

    for section in sections:
        canonical_key = canonicalize_section_key(section.key)
        current = by_canonical_key.get(canonical_key)
        if current is None:
            by_canonical_key[canonical_key] = section
            order.append(canonical_key)
            continue

        if _section_identity_priority(section) > _section_identity_priority(current):
            by_canonical_key[canonical_key] = section

    return [by_canonical_key[key] for key in order]


def list_sections(db: Session, module: str | None = None, active_only: bool = False) -> list[Section]:
    query = select(Section)
    if module:
        query = query.where(Section.module.in_(_candidate_section_modules(module)))
    if active_only:
        query = query.where(Section.is_active.is_(True))
    sections = db.execute(query.order_by(Section.module, Section.sort_order, Section.id)).scalars().all()
    return _dedupe_sections(sections)


def get_section_by_id(db: Session, section_id: int) -> Section | None:
    return db.execute(select(Section).where(Section.id == section_id)).scalar_one_or_none()


def get_section_by_key(db: Session, key: str) -> Section | None:
    return db.execute(select(Section).where(Section.key.in_(_candidate_section_keys(key)))).scalar_one_or_none()


def _seed_role_defaults(db: Session, section: Section, updated_by_id: int | None = None) -> None:
    min_rank = ROLE_HIERARCHY.get(section.min_role, 999)
    for role in [
        ApplicationUserRole.SUPER_ADMIN.value,
        ApplicationUserRole.ADMIN.value,
        ApplicationUserRole.REVIEWER.value,
        ApplicationUserRole.VIEWER.value,
        ApplicationUserRole.OPERATOR.value,
    ]:
        rank = ROLE_HIERARCHY.get(role, 0)
        is_granted = role == ApplicationUserRole.SUPER_ADMIN.value or rank >= min_rank
        db.add(
            RoleSectionPermission(
                section_id=section.id,
                role=role,
                is_granted=is_granted,
                updated_by_id=updated_by_id,
            )
        )


def create_section(db: Session, payload: SectionCreate, updated_by_id: int | None = None) -> Section:
    payload_data = payload.model_dump()
    payload_data["module"] = canonicalize_section_module(payload_data["module"])
    payload_data["key"] = canonicalize_section_key(payload_data["key"])
    section = Section(**payload_data)
    db.add(section)
    db.flush()
    _seed_role_defaults(db, section, updated_by_id=updated_by_id)
    db.commit()
    db.refresh(section)
    return section


def update_section(db: Session, section: Section, payload: SectionUpdate) -> Section:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(section, key, value)
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


def deactivate_section(db: Session, section: Section) -> Section:
    section.is_active = False
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


def get_role_permissions_for_section(db: Session, section_id: int) -> list[RoleSectionPermission]:
    return db.execute(
        select(RoleSectionPermission)
        .where(RoleSectionPermission.section_id == section_id)
        .order_by(RoleSectionPermission.id)
    ).scalars().all()


def bulk_update_role_permissions(
    db: Session,
    section_id: int,
    payload: BulkRolePermissionsRequest,
    updated_by_id: int | None,
) -> list[RoleSectionPermission]:
    for entry in payload.permissions:
        existing = db.execute(
            select(RoleSectionPermission).where(
                RoleSectionPermission.section_id == section_id,
                RoleSectionPermission.role == entry.role,
            )
        ).scalar_one_or_none()
        if existing:
            existing.is_granted = entry.is_granted
            existing.updated_by_id = updated_by_id
            db.add(existing)
        else:
            db.add(
                RoleSectionPermission(
                    section_id=section_id,
                    role=entry.role,
                    is_granted=entry.is_granted,
                    updated_by_id=updated_by_id,
                )
            )
    db.commit()
    return get_role_permissions_for_section(db, section_id)


def get_user_overrides(db: Session, user_id: int) -> list[UserSectionPermission]:
    return db.execute(
        select(UserSectionPermission).where(UserSectionPermission.user_id == user_id)
    ).scalars().all()


def bulk_update_user_permissions(
    db: Session,
    user_id: int,
    payload: BulkUserPermissionsRequest,
    granted_by_id: int | None,
) -> list[UserSectionPermission]:
    for entry in payload.permissions:
        existing = db.execute(
            select(UserSectionPermission).where(
                UserSectionPermission.user_id == user_id,
                UserSectionPermission.section_id == entry.section_id,
            )
        ).scalar_one_or_none()
        if existing:
            existing.is_granted = entry.is_granted
            existing.granted_by_id = granted_by_id
            db.add(existing)
        else:
            db.add(
                UserSectionPermission(
                    user_id=user_id,
                    section_id=entry.section_id,
                    is_granted=entry.is_granted,
                    granted_by_id=granted_by_id,
                )
            )
    db.commit()
    return get_user_overrides(db, user_id)


def delete_user_override(db: Session, user_id: int, section_id: int) -> None:
    override = db.execute(
        select(UserSectionPermission).where(
            UserSectionPermission.user_id == user_id,
            UserSectionPermission.section_id == section_id,
        )
    ).scalar_one_or_none()
    if override is not None:
        db.delete(override)
        db.commit()
