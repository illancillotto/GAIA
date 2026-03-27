"""anagrafica import item payload

Revision ID: 20260327_0021
Revises: 20260327_0020
Create Date: 2026-03-27 13:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_0021"
down_revision = "20260327_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ana_import_job_items", sa.Column("payload_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("ana_import_job_items", "payload_json")
