"""Add normalized organizational positions and reparto units.

Revision ID: 20260825_0900
Revises: 20260824_1000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260825_0900"
down_revision = "20260824_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("org_assignment", sa.Column("position_code", sa.String(length=32), nullable=True))
    op.create_index("ix_org_assignment_position_code", "org_assignment", ["position_code"])
    op.add_column("org_revision_assignment", sa.Column("position_code", sa.String(length=32), nullable=True))
    op.create_index("ix_org_revision_assignment_position_code", "org_revision_assignment", ["position_code"])
    op.execute(
        """
        UPDATE org_assignment
        SET position_code = CASE
            WHEN lower(title) LIKE '%dirigent%' OR lower(title) LIKE '%direttor%' THEN 'dirigente'
            WHEN lower(title) LIKE '%capo%settore%' THEN 'capo_settore'
            WHEN lower(title) LIKE '%capo%operai%' OR lower(title) LIKE '%capo%operaio%' THEN 'capo_operai'
            WHEN lower(title) LIKE '%capo%reparto%' THEN 'capo_reparto'
            ELSE NULL
        END
        WHERE title IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE org_revision_assignment
        SET position_code = CASE
            WHEN lower(title) LIKE '%dirigent%' OR lower(title) LIKE '%direttor%' THEN 'dirigente'
            WHEN lower(title) LIKE '%capo%settore%' THEN 'capo_settore'
            WHEN lower(title) LIKE '%capo%operai%' OR lower(title) LIKE '%capo%operaio%' THEN 'capo_operai'
            WHEN lower(title) LIKE '%capo%reparto%' THEN 'capo_reparto'
            ELSE NULL
        END
        WHERE title IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_org_revision_assignment_position_code", table_name="org_revision_assignment")
    op.drop_column("org_revision_assignment", "position_code")
    op.drop_index("ix_org_assignment_position_code", table_name="org_assignment")
    op.drop_column("org_assignment", "position_code")
