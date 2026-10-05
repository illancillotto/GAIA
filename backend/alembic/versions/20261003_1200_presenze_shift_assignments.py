"""Dated GATE/GAIA shift-worker assignments, independent from INAZ imports."""

from alembic import op
import sqlalchemy as sa

revision = "20261003_1200"
down_revision = "20261002_1030"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("presenze_shift_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("collaborator_id", sa.Uuid(), sa.ForeignKey("presenze_collaborators.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False), sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("shift_worker_type", sa.String(32), nullable=False), sa.Column("source", sa.String(16), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("application_users.id"), nullable=False),
        sa.Column("command_id", sa.String(120), nullable=False, unique=True),
        sa.CheckConstraint("date_from <= date_to", name="ck_shift_assignment_dates"),
        sa.CheckConstraint("shift_worker_type IN ('none', 'acquaiolo', 'telecontrollo')", name="ck_shift_assignment_type"),
        sa.CheckConstraint("source IN ('gate', 'gaia')", name="ck_shift_assignment_source"))
    op.create_index("ix_shift_assignment_person_dates", "presenze_shift_assignments", ["collaborator_id", "date_from", "date_to"])


def downgrade():
    op.drop_table("presenze_shift_assignments")
