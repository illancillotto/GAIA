from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUserRole
from app.models.section_permission import RoleSectionPermission, Section, UserSectionPermission
from app.schemas.permissions import BulkRolePermissionsRequest, BulkUserPermissionsRequest, SectionCreate, SectionUpdate
from app.services.permission_resolver import ROLE_HIERARCHY


def list_sections(db: Session, module: str | None = None, active_only: bool = False) -> list[Section]:
    query = select(Section)
    if module:
        query = query.where(Section.module == module)
    if active_only:
        query = query.where(Section.is_active.is_(True))
    return db.execute(query.order_by(Section.module, Section.sort_order, Section.id)).scalars().all()


def get_section_by_id(db: Session, section_id: int) -> Section | None:
    return db.execute(select(Section).where(Section.id == section_id)).scalar_one_or_none()


def get_section_by_key(db: Session, key: str) -> Section | None:
    return db.execute(select(Section).where(Section.key == key)).scalar_one_or_none()


def _seed_role_defaults(db: Session, section: Section, updated_by_id: int | None = None) -> None:
    min_rank = ROLE_HIERARCHY.get(section.min_role, 999)
    for role in [
        ApplicationUserRole.SUPER_ADMIN.value,
        ApplicationUserRole.ADMIN.value,
        ApplicationUserRole.REVIEWER.value,
        ApplicationUserRole.VIEWER.value,
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
    section = Section(**payload.model_dump())
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
