"""Record who pays an avviso instead of its registered taxpayer."""

import sqlalchemy as sa

from alembic import op

revision = "20261027_0900"
down_revision = "20261026_1600"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ruolo_tributi_payer_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "avviso_id",
            sa.Uuid(),
            sa.ForeignKey("ruolo_avvisi.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "payer_subject_id",
            sa.Uuid(),
            sa.ForeignKey("ana_subjects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("application_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "voided_by",
            sa.Integer(),
            sa.ForeignKey("application_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "reason IN ('decesso', 'vendita', 'ufficio')", name="ck_ruolo_payer_assignment_reason"
        ),
    )
    op.create_index(
        "ix_ruolo_tributi_payer_assignments_avviso_id",
        "ruolo_tributi_payer_assignments",
        ["avviso_id"],
    )
    op.create_index(
        "ix_ruolo_tributi_payer_assignments_payer_subject_id",
        "ruolo_tributi_payer_assignments",
        ["payer_subject_id"],
    )
    op.create_index(
        "uq_ruolo_payer_assignment_active",
        "ruolo_tributi_payer_assignments",
        ["avviso_id"],
        unique=True,
        postgresql_where=sa.text("voided_at IS NULL"),
        sqlite_where=sa.text("voided_at IS NULL"),
    )


def downgrade():
    op.drop_table("ruolo_tributi_payer_assignments")
