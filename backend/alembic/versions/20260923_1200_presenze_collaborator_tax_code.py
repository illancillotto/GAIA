"""Store the payroll tax code on Presenze collaborators."""

import sqlalchemy as sa

from alembic import op

revision = "20260923_1200"
down_revision = "20260922_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "presenze_collaborators", sa.Column("tax_code", sa.String(length=32), nullable=True)
    )
    op.create_index(
        "ix_presenze_collaborators_tax_code",
        "presenze_collaborators",
        ["tax_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_presenze_collaborators_tax_code", table_name="presenze_collaborators")
    op.drop_column("presenze_collaborators", "tax_code")
