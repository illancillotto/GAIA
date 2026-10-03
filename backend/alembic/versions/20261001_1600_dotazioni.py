"""Consortium operational assets, custody history and audit.

Revision ID: 20261001_1600
Revises: 20261001_1400
"""

import sqlalchemy as sa

from alembic import op

revision = "20261001_1600"
down_revision = "20261001_1400"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "application_users",
        sa.Column("module_dotazioni", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "dotazioni_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("asset_code", sa.String(64), nullable=False),
        sa.Column("asset_type", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("brand", sa.String(100)),
        sa.Column("model", sa.String(100)),
        sa.Column("serial_number", sa.String(200)),
        sa.Column("imei", sa.String(32)),
        sa.Column("phone_number", sa.String(64)),
        sa.Column("mac_address", sa.String(64)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "assigned_org_unit_id", sa.Uuid(), sa.ForeignKey("org_unit.id", ondelete="RESTRICT")
        ),
        sa.Column(
            "network_device_id",
            sa.Integer(),
            sa.ForeignKey("network_devices.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column(
            "vehicle_id", sa.Uuid(), sa.ForeignKey("vehicle.id", ondelete="RESTRICT"), unique=True
        ),
        sa.Column("notes", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            sa.ForeignKey("application_users.id"),
            nullable=False,
        ),
        sa.Column(
            "updated_by_user_id",
            sa.Integer(),
            sa.ForeignKey("application_users.id"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('available', 'maintenance', 'lost', 'damaged', 'retired')",
            name="ck_dotazioni_assets_status",
        ),
    )
    op.create_index(
        "ix_dotazioni_assets_asset_code", "dotazioni_assets", ["asset_code"], unique=True
    )
    for column in ("asset_type", "serial_number", "status", "assigned_org_unit_id"):
        op.create_index(f"ix_dotazioni_assets_{column}", "dotazioni_assets", [column])
    op.create_table(
        "dotazioni_custodies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "asset_id",
            sa.Uuid(),
            sa.ForeignKey("dotazioni_assets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "holder_user_id",
            sa.Integer(),
            sa.ForeignKey("application_users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True)),
        sa.Column("handover_from_user_id", sa.Integer(), sa.ForeignKey("application_users.id")),
        sa.Column(
            "recorded_by_user_id",
            sa.Integer(),
            sa.ForeignKey("application_users.id"),
            nullable=False,
        ),
        sa.Column("returned_by_user_id", sa.Integer(), sa.ForeignKey("application_users.id")),
        sa.Column("notes", sa.Text()),
        sa.Column("return_notes", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "returned_at IS NULL OR returned_at >= taken_at", name="ck_dotazioni_custody_time"
        ),
        sa.CheckConstraint(
            "(returned_at IS NULL AND returned_by_user_id IS NULL) OR (returned_at IS NOT NULL AND returned_by_user_id IS NOT NULL)",
            name="ck_dotazioni_custody_return_actor",
        ),
    )
    for column in ("asset_id", "holder_user_id"):
        op.create_index(f"ix_dotazioni_custodies_{column}", "dotazioni_custodies", [column])
    op.create_index(
        "uq_dotazioni_open_custody",
        "dotazioni_custodies",
        ["asset_id"],
        unique=True,
        postgresql_where=sa.text("returned_at IS NULL"),
        sqlite_where=sa.text("returned_at IS NULL"),
    )
    op.create_table(
        "dotazioni_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "asset_id",
            sa.Uuid(),
            sa.ForeignKey("dotazioni_assets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column(
            "actor_user_id", sa.Integer(), sa.ForeignKey("application_users.id"), nullable=False
        ),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_dotazioni_events_asset_id", "dotazioni_events", ["asset_id"])
    for action, label, role in (
        ("view", "Consultazione", "viewer"),
        ("manage", "Gestione beni", "admin"),
        ("assign", "Assegnazioni organizzative", "admin"),
        ("custody", "Custodia personale", "admin"),
        ("history", "Storico custodie", "viewer"),
    ):
        op.execute(
            sa.text(
                "INSERT INTO sections (module, key, label, min_role, is_active, sort_order) VALUES ('dotazioni', :key, :label, :role, true, 100) ON CONFLICT (key) DO NOTHING"
            ).bindparams(key=f"dotazioni.{action}", label=f"Dotazioni — {label}", role=role)
        )
    op.execute(
        sa.text(
            "INSERT INTO role_section_permissions (section_id, role, is_granted) SELECT id, 'operator', true FROM sections WHERE key = 'dotazioni.custody' ON CONFLICT (section_id, role) DO NOTHING"
        )
    )


def downgrade():
    op.execute(
        sa.text(
            "DELETE FROM sections WHERE module = 'dotazioni' AND key IN ('dotazioni.view', 'dotazioni.manage', 'dotazioni.assign', 'dotazioni.custody', 'dotazioni.history')"
        )
    )
    op.drop_table("dotazioni_events")
    op.drop_table("dotazioni_custodies")
    op.drop_table("dotazioni_assets")
    op.drop_column("application_users", "module_dotazioni")
