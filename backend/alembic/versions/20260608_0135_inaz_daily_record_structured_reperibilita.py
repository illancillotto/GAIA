"""convert inaz reperibilita to structured fields

Revision ID: 20260608_0135
Revises: 20260608_0134
Create Date: 2026-06-08 15:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260608_0135"
down_revision = "20260608_0134"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inaz_daily_records",
        sa.Column("reperibilita_unit", sa.String(length=16), nullable=False, server_default="none"),
    )
    op.add_column("inaz_daily_records", sa.Column("reperibilita_quantity", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE inaz_daily_records
        SET reperibilita_unit = CASE WHEN reperibilita_flag IS TRUE THEN 'shifts' ELSE 'none' END,
            reperibilita_quantity = CASE WHEN reperibilita_flag IS TRUE THEN 1 ELSE NULL END
        """
    )
    op.drop_column("inaz_daily_records", "reperibilita_flag")
    op.alter_column("inaz_daily_records", "reperibilita_unit", server_default=None)


def downgrade() -> None:
    op.add_column(
        "inaz_daily_records",
        sa.Column("reperibilita_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        """
        UPDATE inaz_daily_records
        SET reperibilita_flag = CASE
            WHEN reperibilita_unit <> 'none' AND COALESCE(reperibilita_quantity, 0) > 0 THEN TRUE
            ELSE FALSE
        END
        """
    )
    op.drop_column("inaz_daily_records", "reperibilita_quantity")
    op.drop_column("inaz_daily_records", "reperibilita_unit")
    op.alter_column("inaz_daily_records", "reperibilita_flag", server_default=None)
