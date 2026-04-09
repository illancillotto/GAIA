"""riordino config types

Revision ID: 20260409_0035
Revises: 20260409_0034
Create Date: 2026-04-09
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op


revision = "20260409_0035"
down_revision = "20260409_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "riordino_document_type_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(
        "ix_riordino_document_type_configs_code",
        "riordino_document_type_configs",
        ["code"],
        unique=True,
    )
    op.create_index(
        "ix_riordino_document_type_configs_is_active",
        "riordino_document_type_configs",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        "ix_riordino_document_type_configs_sort_order",
        "riordino_document_type_configs",
        ["sort_order"],
        unique=False,
    )

    op.create_table(
        "riordino_issue_type_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("default_severity", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(
        "ix_riordino_issue_type_configs_code",
        "riordino_issue_type_configs",
        ["code"],
        unique=True,
    )
    op.create_index(
        "ix_riordino_issue_type_configs_category",
        "riordino_issue_type_configs",
        ["category"],
        unique=False,
    )
    op.create_index(
        "ix_riordino_issue_type_configs_is_active",
        "riordino_issue_type_configs",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        "ix_riordino_issue_type_configs_sort_order",
        "riordino_issue_type_configs",
        ["sort_order"],
        unique=False,
    )

    op.bulk_insert(
        sa.table(
            "riordino_document_type_configs",
            sa.column("id", sa.Uuid()),
            sa.column("code", sa.String()),
            sa.column("label", sa.String()),
            sa.column("description", sa.Text()),
            sa.column("is_active", sa.Boolean()),
            sa.column("sort_order", sa.Integer()),
        ),
        [
            {
                "id": uuid.uuid4(),
                "code": "decreto",
                "label": "Decreto",
                "description": "Documento di decreto o approvazione.",
                "is_active": True,
                "sort_order": 10,
            },
            {
                "id": uuid.uuid4(),
                "code": "ricorso",
                "label": "Ricorso",
                "description": "Documentazione ricorsi e allegati correlati.",
                "is_active": True,
                "sort_order": 20,
            },
            {
                "id": uuid.uuid4(),
                "code": "estratto_mappa",
                "label": "Estratto mappa",
                "description": "Estratti mappa e rappresentazioni catastali.",
                "is_active": True,
                "sort_order": 30,
            },
            {
                "id": uuid.uuid4(),
                "code": "documento_finale",
                "label": "Documento finale",
                "description": "Output finale della pratica.",
                "is_active": True,
                "sort_order": 40,
            },
        ],
    )

    op.bulk_insert(
        sa.table(
            "riordino_issue_type_configs",
            sa.column("id", sa.Uuid()),
            sa.column("code", sa.String()),
            sa.column("label", sa.String()),
            sa.column("category", sa.String()),
            sa.column("default_severity", sa.String()),
            sa.column("description", sa.Text()),
            sa.column("is_active", sa.Boolean()),
            sa.column("sort_order", sa.Integer()),
        ),
        [
            {
                "id": uuid.uuid4(),
                "code": "anomalia_documentale",
                "label": "Anomalia documentale",
                "category": "documentary",
                "default_severity": "medium",
                "description": "Documenti mancanti o non coerenti.",
                "is_active": True,
                "sort_order": 10,
            },
            {
                "id": uuid.uuid4(),
                "code": "anomalia_catastale",
                "label": "Anomalia catastale",
                "category": "cadastral",
                "default_severity": "high",
                "description": "Incongruenze catastali rilevate durante la fase 2.",
                "is_active": True,
                "sort_order": 20,
            },
            {
                "id": uuid.uuid4(),
                "code": "blocco_gis",
                "label": "Blocco GIS",
                "category": "gis",
                "default_severity": "blocking",
                "description": "Incoerenza o dipendenza GIS bloccante.",
                "is_active": True,
                "sort_order": 30,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_riordino_issue_type_configs_sort_order", table_name="riordino_issue_type_configs")
    op.drop_index("ix_riordino_issue_type_configs_is_active", table_name="riordino_issue_type_configs")
    op.drop_index("ix_riordino_issue_type_configs_category", table_name="riordino_issue_type_configs")
    op.drop_index("ix_riordino_issue_type_configs_code", table_name="riordino_issue_type_configs")
    op.drop_table("riordino_issue_type_configs")

    op.drop_index("ix_riordino_document_type_configs_sort_order", table_name="riordino_document_type_configs")
    op.drop_index("ix_riordino_document_type_configs_is_active", table_name="riordino_document_type_configs")
    op.drop_index("ix_riordino_document_type_configs_code", table_name="riordino_document_type_configs")
    op.drop_table("riordino_document_type_configs")
