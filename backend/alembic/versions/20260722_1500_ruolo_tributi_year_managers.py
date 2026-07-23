"""ruolo tributi year managers

Revision ID: 20260722_1500
Revises: 20260722_1000
Create Date: 2026-07-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from uuid import uuid4


revision = "20260722_1500"
down_revision = "20260722_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table = op.create_table(
        "ruolo_tributi_year_managers",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("manager_key", sa.String(length=40), nullable=False),
        sa.Column("manager_label", sa.String(length=160), nullable=False),
        sa.Column("year_from", sa.Integer(), nullable=True),
        sa.Column("year_to", sa.Integer(), nullable=True),
        sa.Column("calculation_policy", sa.String(length=40), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["updated_by"], ["application_users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ruolo_tributi_year_managers_is_active", "ruolo_tributi_year_managers", ["is_active"])
    op.create_index("ix_ruolo_tributi_year_managers_manager_key", "ruolo_tributi_year_managers", ["manager_key"])
    op.create_index("ix_ruolo_tributi_year_managers_updated_by", "ruolo_tributi_year_managers", ["updated_by"])
    op.create_index("ix_ruolo_tributi_year_managers_year_from", "ruolo_tributi_year_managers", ["year_from"])
    op.create_index("ix_ruolo_tributi_year_managers_year_to", "ruolo_tributi_year_managers", ["year_to"])

    op.bulk_insert(
        table,
        [
            {
                "id": uuid4(),
                "manager_key": "agenzia_entrate",
                "manager_label": "Agenzia delle Entrate",
                "year_from": None,
                "year_to": 2017,
                "calculation_policy": "external_ade",
                "is_active": True,
                "notes": "Annualita fino al 2017 in gestione esterna Agenzia delle Entrate.",
            },
            {
                "id": uuid4(),
                "manager_key": "step",
                "manager_label": "STEP - Agenzia recupero crediti",
                "year_from": 2018,
                "year_to": 2021,
                "calculation_policy": "external_recovery",
                "is_active": True,
                "notes": "Annualita 2018-2021 in gestione STEP. Il 2022 e configurato in GAIA/Consorzio.",
            },
            {
                "id": uuid4(),
                "manager_key": "gaia",
                "manager_label": "Consorzio/GAIA",
                "year_from": 2022,
                "year_to": None,
                "calculation_policy": "internal_gaia",
                "is_active": True,
                "notes": "Annualita dal 2022 in gestione diretta Consorzio/GAIA.",
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_ruolo_tributi_year_managers_year_to", table_name="ruolo_tributi_year_managers")
    op.drop_index("ix_ruolo_tributi_year_managers_year_from", table_name="ruolo_tributi_year_managers")
    op.drop_index("ix_ruolo_tributi_year_managers_updated_by", table_name="ruolo_tributi_year_managers")
    op.drop_index("ix_ruolo_tributi_year_managers_manager_key", table_name="ruolo_tributi_year_managers")
    op.drop_index("ix_ruolo_tributi_year_managers_is_active", table_name="ruolo_tributi_year_managers")
    op.drop_table("ruolo_tributi_year_managers")
