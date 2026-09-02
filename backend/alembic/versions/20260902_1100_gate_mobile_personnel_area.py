"""Persist canonical personnel areas for GATE Mobile synchronization.

Revision ID: 20260902_1100
Revises: 20260901_1100
"""

import sqlalchemy as sa

from alembic import op

revision = "20260902_1100"
down_revision = "20260901_1100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("wc_operator", sa.Column("personnel_area", sa.String(length=16), nullable=True))
    op.create_index(
        "ix_wc_operator_personnel_area", "wc_operator", ["personnel_area"], unique=False
    )
    op.create_check_constraint(
        "ck_wc_operator_personnel_area",
        "wc_operator",
        "personnel_area IS NULL OR personnel_area IN ('AGRARIO', 'IMPIANTI')",
    )

    op.add_column(
        "organization_teams", sa.Column("personnel_area", sa.String(length=16), nullable=True)
    )
    op.add_column(
        "organization_teams", sa.Column("gate_mobile_team_id", sa.String(length=255), nullable=True)
    )
    op.create_index(
        "ix_organization_teams_gate_mobile_team_id",
        "organization_teams",
        ["gate_mobile_team_id"],
        unique=True,
    )
    # Explicit production attestation keyed by the canonical GAIA team UUID.
    # The legacy application scope must never determine the personnel area.
    op.execute(
        """
        UPDATE organization_teams
        SET personnel_area = 'AGRARIO'
        WHERE id = 'e23b8b83-72ae-48b2-80f3-ff6a029b80a7'
        """
    )
    connection = op.get_bind()
    missing_area_count = connection.scalar(
        sa.text("SELECT count(*) FROM organization_teams WHERE personnel_area IS NULL")
    )
    if missing_area_count:
        raise RuntimeError(
            "organization_teams contiene squadre senza personnel_area esplicita; "
            "aggiungere una mappatura canonica per UUID prima della migrazione"
        )
    op.alter_column("organization_teams", "personnel_area", nullable=False)
    op.create_index(
        "ix_organization_teams_personnel_area",
        "organization_teams",
        ["personnel_area"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_organization_teams_personnel_area",
        "organization_teams",
        "personnel_area IN ('AGRARIO', 'IMPIANTI')",
    )
    op.drop_constraint(
        "uq_organization_teams_code_scope",
        "organization_teams",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_organization_teams_code_personnel_area",
        "organization_teams",
        ["code", "personnel_area"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_organization_teams_code_personnel_area",
        "organization_teams",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_organization_teams_code_scope",
        "organization_teams",
        ["code", "scope"],
    )
    op.drop_constraint(
        "ck_organization_teams_personnel_area",
        "organization_teams",
        type_="check",
    )
    op.drop_index("ix_organization_teams_personnel_area", table_name="organization_teams")
    op.drop_index("ix_organization_teams_gate_mobile_team_id", table_name="organization_teams")
    op.drop_column("organization_teams", "gate_mobile_team_id")
    op.drop_column("organization_teams", "personnel_area")

    op.drop_constraint("ck_wc_operator_personnel_area", "wc_operator", type_="check")
    op.drop_index("ix_wc_operator_personnel_area", table_name="wc_operator")
    op.drop_column("wc_operator", "personnel_area")
