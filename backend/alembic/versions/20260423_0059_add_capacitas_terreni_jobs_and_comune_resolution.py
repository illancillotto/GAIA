"""add capacitas terreni jobs and comune resolution fields

Revision ID: 20260423_0059
Revises: 20260423_0058
Create Date: 2026-04-23

"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision = "20260423_0059"
down_revision: Union[str, None] = "20260423_0058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cat_consorzio_units", sa.Column("source_comune_id", sa.Uuid(), nullable=True))
    op.add_column("cat_consorzio_units", sa.Column("source_cod_comune_capacitas", sa.Integer(), nullable=True))
    op.add_column("cat_consorzio_units", sa.Column("source_codice_catastale", sa.String(length=4), nullable=True))
    op.add_column("cat_consorzio_units", sa.Column("source_comune_label", sa.String(length=100), nullable=True))
    op.add_column("cat_consorzio_units", sa.Column("comune_resolution_mode", sa.String(length=40), nullable=True))
    op.create_foreign_key(
        "fk_cat_consorzio_units_source_comune_id",
        "cat_consorzio_units",
        "cat_comuni",
        ["source_comune_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_cat_consorzio_units_source_comune_id"), "cat_consorzio_units", ["source_comune_id"])
    op.create_index(
        op.f("ix_cat_consorzio_units_source_cod_comune_capacitas"),
        "cat_consorzio_units",
        ["source_cod_comune_capacitas"],
    )
    op.create_index(
        op.f("ix_cat_consorzio_units_source_codice_catastale"),
        "cat_consorzio_units",
        ["source_codice_catastale"],
    )
    op.create_index(
        op.f("ix_cat_consorzio_units_comune_resolution_mode"),
        "cat_consorzio_units",
        ["comune_resolution_mode"],
    )

    op.create_table(
        "capacitas_terreni_sync_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=True),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["credential_id"], ["capacitas_credentials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_capacitas_terreni_sync_jobs_credential_id"), "capacitas_terreni_sync_jobs", ["credential_id"])
    op.create_index(
        op.f("ix_capacitas_terreni_sync_jobs_requested_by_user_id"),
        "capacitas_terreni_sync_jobs",
        ["requested_by_user_id"],
    )
    op.create_index(op.f("ix_capacitas_terreni_sync_jobs_status"), "capacitas_terreni_sync_jobs", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_capacitas_terreni_sync_jobs_status"), table_name="capacitas_terreni_sync_jobs")
    op.drop_index(
        op.f("ix_capacitas_terreni_sync_jobs_requested_by_user_id"),
        table_name="capacitas_terreni_sync_jobs",
    )
    op.drop_index(op.f("ix_capacitas_terreni_sync_jobs_credential_id"), table_name="capacitas_terreni_sync_jobs")
    op.drop_table("capacitas_terreni_sync_jobs")

    op.drop_index(op.f("ix_cat_consorzio_units_comune_resolution_mode"), table_name="cat_consorzio_units")
    op.drop_index(op.f("ix_cat_consorzio_units_source_codice_catastale"), table_name="cat_consorzio_units")
    op.drop_index(op.f("ix_cat_consorzio_units_source_cod_comune_capacitas"), table_name="cat_consorzio_units")
    op.drop_index(op.f("ix_cat_consorzio_units_source_comune_id"), table_name="cat_consorzio_units")
    op.drop_constraint("fk_cat_consorzio_units_source_comune_id", "cat_consorzio_units", type_="foreignkey")
    op.drop_column("cat_consorzio_units", "comune_resolution_mode")
    op.drop_column("cat_consorzio_units", "source_comune_label")
    op.drop_column("cat_consorzio_units", "source_codice_catastale")
    op.drop_column("cat_consorzio_units", "source_cod_comune_capacitas")
    op.drop_column("cat_consorzio_units", "source_comune_id")
