"""organigramma structure kind split

Revision ID: 20260612_0900
Revises: 20260611_1735
Create Date: 2026-06-12 09:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260612_0900"
down_revision = "20260611_1735"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "org_unit",
        sa.Column("structure_kind", sa.String(length=32), nullable=False, server_default="organigramma"),
    )
    op.add_column(
        "org_assignment",
        sa.Column("structure_kind", sa.String(length=32), nullable=False, server_default="organigramma"),
    )
    op.add_column(
        "org_visibility_override",
        sa.Column("structure_kind", sa.String(length=32), nullable=False, server_default="organigramma"),
    )

    op.create_index("ix_org_unit_structure_kind", "org_unit", ["structure_kind"], unique=False)
    op.create_index("ix_org_assignment_structure_kind", "org_assignment", ["structure_kind"], unique=False)
    op.create_index("ix_org_visibility_override_structure_kind", "org_visibility_override", ["structure_kind"], unique=False)

    op.alter_column("org_unit", "structure_kind", server_default=None)
    op.alter_column("org_assignment", "structure_kind", server_default=None)
    op.alter_column("org_visibility_override", "structure_kind", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_org_visibility_override_structure_kind", table_name="org_visibility_override")
    op.drop_index("ix_org_assignment_structure_kind", table_name="org_assignment")
    op.drop_index("ix_org_unit_structure_kind", table_name="org_unit")

    op.drop_column("org_visibility_override", "structure_kind")
    op.drop_column("org_assignment", "structure_kind")
    op.drop_column("org_unit", "structure_kind")
