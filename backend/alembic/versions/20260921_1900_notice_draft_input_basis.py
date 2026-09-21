"""Input revision captured before generation; legacy drafts remain untracked.

Revision ID: 20260921_1900
Revises: 20260921_1700
"""

from alembic import op
import sqlalchemy as sa

revision = "20260921_1900"
down_revision = "20260921_1700"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ruolo_notice_drafts", sa.Column("input_basis", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("ruolo_notice_drafts", "input_basis")
