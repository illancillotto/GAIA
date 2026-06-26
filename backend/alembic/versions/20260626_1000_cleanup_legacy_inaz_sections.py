"""cleanup legacy inaz section aliases

Revision ID: 20260626_1000
Revises: 20260625_1100
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260626_1000"
down_revision = "20260625_1100"
branch_labels = None
depends_on = None


sections = sa.table(
    "sections",
    sa.column("id", sa.Integer()),
    sa.column("module", sa.String()),
    sa.column("key", sa.String()),
)

role_permissions = sa.table(
    "role_section_permissions",
    sa.column("id", sa.Integer()),
    sa.column("section_id", sa.Integer()),
    sa.column("role", sa.String()),
    sa.column("is_granted", sa.Boolean()),
    sa.column("updated_by_id", sa.Integer()),
)

user_permissions = sa.table(
    "user_section_permissions",
    sa.column("id", sa.Integer()),
    sa.column("user_id", sa.Integer()),
    sa.column("section_id", sa.Integer()),
    sa.column("is_granted", sa.Boolean()),
    sa.column("granted_by_id", sa.Integer()),
)


def _canonicalize_module(module: str) -> str:
    return "presenze" if module == "inaz" else module


def _canonicalize_key(key: str) -> str:
    return f"presenze.{key[len('inaz.'):]}" if key.startswith("inaz.") else key


def upgrade() -> None:
    bind = op.get_bind()

    section_rows = bind.execute(
        sa.select(
            sections.c.id,
            sections.c.module,
            sections.c.key,
        )
        .where(
            sa.or_(
                sections.c.module == "inaz",
                sections.c.key.like("inaz.%"),
            )
        )
        .order_by(sections.c.id)
    ).mappings().all()

    for legacy in section_rows:
        canonical_module = _canonicalize_module(legacy["module"])
        canonical_key = _canonicalize_key(legacy["key"])

        if canonical_module == legacy["module"] and canonical_key == legacy["key"]:
            continue

        target = bind.execute(
            sa.select(sections.c.id)
            .where(sections.c.key == canonical_key)
            .where(sections.c.id != legacy["id"])
        ).scalar_one_or_none()

        if target is None:
            bind.execute(
                sa.update(sections)
                .where(sections.c.id == legacy["id"])
                .values(module=canonical_module, key=canonical_key)
            )
            continue

        legacy_role_rows = bind.execute(
            sa.select(
                role_permissions.c.id,
                role_permissions.c.role,
                role_permissions.c.is_granted,
                role_permissions.c.updated_by_id,
            ).where(role_permissions.c.section_id == legacy["id"])
        ).mappings().all()
        for role_row in legacy_role_rows:
            existing_role = bind.execute(
                sa.select(role_permissions.c.id).where(
                    role_permissions.c.section_id == target,
                    role_permissions.c.role == role_row["role"],
                )
            ).scalar_one_or_none()
            if existing_role is None:
                bind.execute(
                    sa.insert(role_permissions).values(
                        section_id=target,
                        role=role_row["role"],
                        is_granted=role_row["is_granted"],
                        updated_by_id=role_row["updated_by_id"],
                    )
                )

        legacy_user_rows = bind.execute(
            sa.select(
                user_permissions.c.id,
                user_permissions.c.user_id,
                user_permissions.c.is_granted,
                user_permissions.c.granted_by_id,
            ).where(user_permissions.c.section_id == legacy["id"])
        ).mappings().all()
        for user_row in legacy_user_rows:
            existing_user = bind.execute(
                sa.select(user_permissions.c.id).where(
                    user_permissions.c.section_id == target,
                    user_permissions.c.user_id == user_row["user_id"],
                )
            ).scalar_one_or_none()
            if existing_user is None:
                bind.execute(
                    sa.insert(user_permissions).values(
                        user_id=user_row["user_id"],
                        section_id=target,
                        is_granted=user_row["is_granted"],
                        granted_by_id=user_row["granted_by_id"],
                    )
                )

        bind.execute(sa.delete(role_permissions).where(role_permissions.c.section_id == legacy["id"]))
        bind.execute(sa.delete(user_permissions).where(user_permissions.c.section_id == legacy["id"]))
        bind.execute(sa.delete(sections).where(sections.c.id == legacy["id"]))


def downgrade() -> None:
    pass
