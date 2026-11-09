"""Explicit Presenze team association, without changing the legacy team bridge."""

import sqlalchemy as sa

from alembic import op

revision = "20261107_0900"
down_revision = "20261106_1000"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "presenze_team_organization",
        sa.Column(
            "team_id",
            sa.Uuid(),
            sa.ForeignKey("organization_teams.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "org_unit_id",
            sa.Uuid(),
            sa.ForeignKey("org_unit.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "updated_by_user_id",
            sa.Integer(),
            sa.ForeignKey("application_users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_presenze_team_organization_org_unit_id", "presenze_team_organization", ["org_unit_id"]
    )


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM presenze_team_organization")):
        raise RuntimeError("Unlink Presenze teams explicitly before downgrade")
    op.drop_index(
        "ix_presenze_team_organization_org_unit_id", table_name="presenze_team_organization"
    )
    op.drop_table("presenze_team_organization")
