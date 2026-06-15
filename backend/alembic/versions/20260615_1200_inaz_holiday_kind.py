"""replace inaz holiday workday override with explicit holiday kind

Revision ID: 20260615_1200
Revises: 20260612_1100
Create Date: 2026-06-15 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260615_1200"
down_revision = "20260612_1100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inaz_holidays",
        sa.Column("holiday_kind", sa.String(length=32), nullable=False, server_default="ordinary"),
    )
    op.execute(
        """
        UPDATE inaz_holidays
        SET holiday_kind = CASE
            WHEN is_workday_override IS TRUE THEN 'working_override'
            ELSE 'ordinary'
        END
        """
    )
    op.drop_column("inaz_holidays", "is_workday_override")
    op.create_index(op.f("ix_inaz_holidays_holiday_kind"), "inaz_holidays", ["holiday_kind"], unique=False)
    op.alter_column("inaz_holidays", "holiday_kind", server_default=None)


def downgrade() -> None:
    op.add_column(
        "inaz_holidays",
        sa.Column("is_workday_override", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        """
        UPDATE inaz_holidays
        SET is_workday_override = CASE
            WHEN holiday_kind IN ('suppressed', 'working_override') THEN TRUE
            ELSE FALSE
        END
        """
    )
    op.drop_index(op.f("ix_inaz_holidays_holiday_kind"), table_name="inaz_holidays")
    op.drop_column("inaz_holidays", "holiday_kind")
    op.alter_column("inaz_holidays", "is_workday_override", server_default=None)
