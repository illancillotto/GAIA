"""riordino module: 14 tables + 25 step templates seed

Revision ID: 20260407_0033
Revises: 20260405_0032
Create Date: 2026-04-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260407_0033"
down_revision: Union[str, None] = "20260405_0032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────
    # riordino_step_templates
    # ─────────────────────────────────────────────────────────
    op.create_table(
        "riordino_step_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phase_code", sa.String(20), nullable=False),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("sequence_no", sa.Integer, nullable=False),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("branch", sa.String(50), nullable=True),
        sa.Column("activation_condition", postgresql.JSONB, nullable=True),
        sa.Column("requires_document", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_decision", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("outcome_options", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_riordino_step_templates_phase_code", "riordino_step_templates", ["phase_code"])
    op.create_index("ix_riordino_step_templates_is_active", "riordino_step_templates", ["is_active"])

    # ─────────────────────────────────────────────────────────
    # riordino_practices
    # ─────────────────────────────────────────────────────────
    op.create_table(
        "riordino_practices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("municipality", sa.String(100), nullable=False),
        sa.Column("grid_code", sa.String(50), nullable=False),
        sa.Column("lot_code", sa.String(50), nullable=False),
        sa.Column("current_phase", sa.String(20), nullable=False, server_default="phase_1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("owner_user_id", sa.Integer, sa.ForeignKey("application_users.id"), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("application_users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_riordino_practices_status", "riordino_practices", ["status"])
    op.create_index("ix_riordino_practices_municipality", "riordino_practices", ["municipality"])
    op.create_index("ix_riordino_practices_owner_user_id", "riordino_practices", ["owner_user_id"])
    op.create_index("ix_riordino_practices_current_phase", "riordino_practices", ["current_phase"])
    op.create_index("ix_riordino_practices_deleted_at", "riordino_practices", ["deleted_at"])

    # ─────────────────────────────────────────────────────────
    # riordino_phases
    # ─────────────────────────────────────────────────────────
    op.create_table(
        "riordino_phases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_practices.id"), nullable=False),
        sa.Column("phase_code", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="not_started"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.Integer, sa.ForeignKey("application_users.id"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_riordino_phases_practice_id", "riordino_phases", ["practice_id"])
    op.create_unique_constraint("uq_riordino_phases_practice_phase", "riordino_phases", ["practice_id", "phase_code"])

    # ─────────────────────────────────────────────────────────
    # riordino_steps
    # ─────────────────────────────────────────────────────────
    op.create_table(
        "riordino_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_practices.id"), nullable=False),
        sa.Column("phase_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_phases.id"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_step_templates.id"), nullable=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("sequence_no", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="todo"),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("branch", sa.String(50), nullable=True),
        sa.Column("is_decision", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("outcome_code", sa.String(50), nullable=True),
        sa.Column("outcome_notes", sa.Text, nullable=True),
        sa.Column("skip_reason", sa.Text, nullable=True),
        sa.Column("requires_document", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("owner_user_id", sa.Integer, sa.ForeignKey("application_users.id"), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_riordino_steps_practice_phase", "riordino_steps", ["practice_id", "phase_id"])
    op.create_index("ix_riordino_steps_practice_status", "riordino_steps", ["practice_id", "status"])
    op.create_unique_constraint("uq_riordino_steps_practice_code", "riordino_steps", ["practice_id", "code"])

    # ─────────────────────────────────────────────────────────
    # riordino_tasks
    # ─────────────────────────────────────────────────────────
    op.create_table(
        "riordino_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_practices.id"), nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_steps.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(20), nullable=False, server_default="todo"),
        sa.Column("owner_user_id", sa.Integer, sa.ForeignKey("application_users.id"), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_riordino_tasks_practice_id", "riordino_tasks", ["practice_id"])
    op.create_index("ix_riordino_tasks_step_id", "riordino_tasks", ["step_id"])

    # ─────────────────────────────────────────────────────────
    # riordino_appeals
    # ─────────────────────────────────────────────────────────
    op.create_table(
        "riordino_appeals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_practices.id"), nullable=False),
        sa.Column("phase_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_phases.id"), nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_steps.id"), nullable=True),
        sa.Column("appellant_subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ana_subjects.id"), nullable=True),
        sa.Column("appellant_name", sa.String(200), nullable=False),
        sa.Column("filed_at", sa.Date, nullable=False),
        sa.Column("deadline_at", sa.Date, nullable=True),
        sa.Column("commission_name", sa.String(200), nullable=True),
        sa.Column("commission_date", sa.Date, nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("resolution_notes", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("application_users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_riordino_appeals_practice_id", "riordino_appeals", ["practice_id"])
    op.create_index("ix_riordino_appeals_practice_status", "riordino_appeals", ["practice_id", "status"])

    # ─────────────────────────────────────────────────────────
    # riordino_issues
    # ─────────────────────────────────────────────────────────
    op.create_table(
        "riordino_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_practices.id"), nullable=False),
        sa.Column("phase_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_phases.id"), nullable=True),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_steps.id"), nullable=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("opened_by", sa.Integer, sa.ForeignKey("application_users.id"), nullable=False),
        sa.Column("assigned_to", sa.Integer, sa.ForeignKey("application_users.id"), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_riordino_issues_practice_id", "riordino_issues", ["practice_id"])
    op.create_index("ix_riordino_issues_practice_severity_status", "riordino_issues", ["practice_id", "severity", "status"])
    op.create_index("ix_riordino_issues_assigned_to_status", "riordino_issues", ["assigned_to", "status"])

    # ─────────────────────────────────────────────────────────
    # riordino_documents
    # ─────────────────────────────────────────────────────────
    op.create_table(
        "riordino_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_practices.id"), nullable=False),
        sa.Column("phase_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_phases.id"), nullable=True),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_steps.id"), nullable=True),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_issues.id"), nullable=True),
        sa.Column("appeal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_appeals.id"), nullable=True),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("version_no", sa.Integer, nullable=False, server_default="1"),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(300), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("uploaded_by", sa.Integer, sa.ForeignKey("application_users.id"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_riordino_documents_practice_id", "riordino_documents", ["practice_id"])
    op.create_index("ix_riordino_documents_practice_type", "riordino_documents", ["practice_id", "document_type"])
    op.create_index("ix_riordino_documents_step_id", "riordino_documents", ["step_id"])
    op.create_index("ix_riordino_documents_appeal_id", "riordino_documents", ["appeal_id"])

    # ─────────────────────────────────────────────────────────
    # riordino_parcel_links
    # ─────────────────────────────────────────────────────────
    op.create_table(
        "riordino_parcel_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_practices.id"), nullable=False),
        sa.Column("foglio", sa.String(20), nullable=False),
        sa.Column("particella", sa.String(20), nullable=False),
        sa.Column("subalterno", sa.String(20), nullable=True),
        sa.Column("quality_class", sa.String(50), nullable=True),
        sa.Column("title_holder_name", sa.String(200), nullable=True),
        sa.Column("title_holder_subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ana_subjects.id"), nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_riordino_parcel_links_practice_id", "riordino_parcel_links", ["practice_id"])
    op.create_index("ix_riordino_parcel_links_practice_foglio_particella", "riordino_parcel_links", ["practice_id", "foglio", "particella"])

    # ─────────────────────────────────────────────────────────
    # riordino_party_links
    # ─────────────────────────────────────────────────────────
    op.create_table(
        "riordino_party_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_practices.id"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ana_subjects.id"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_riordino_party_links_practice_id", "riordino_party_links", ["practice_id"])
    op.create_unique_constraint("uq_riordino_party_links_practice_subject", "riordino_party_links", ["practice_id", "subject_id"])

    # ─────────────────────────────────────────────────────────
    # riordino_gis_links
    # ─────────────────────────────────────────────────────────
    op.create_table(
        "riordino_gis_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_practices.id"), nullable=False),
        sa.Column("layer_name", sa.String(100), nullable=False),
        sa.Column("feature_id", sa.String(100), nullable=True),
        sa.Column("geometry_ref", sa.Text, nullable=True),
        sa.Column("sync_status", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_riordino_gis_links_practice_id", "riordino_gis_links", ["practice_id"])

    # ─────────────────────────────────────────────────────────
    # riordino_events
    # ─────────────────────────────────────────────────────────
    op.create_table(
        "riordino_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_practices.id"), nullable=False),
        sa.Column("phase_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_phases.id"), nullable=True),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_steps.id"), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload_json", postgresql.JSONB, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("application_users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_riordino_events_practice_created", "riordino_events", ["practice_id", "created_at"])
    op.create_index("ix_riordino_events_event_type", "riordino_events", ["event_type"])

    # ─────────────────────────────────────────────────────────
    # riordino_checklist_items
    # ─────────────────────────────────────────────────────────
    op.create_table(
        "riordino_checklist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_steps.id"), nullable=False),
        sa.Column("label", sa.String(300), nullable=False),
        sa.Column("is_checked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_blocking", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("checked_by", sa.Integer, sa.ForeignKey("application_users.id"), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sequence_no", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_riordino_checklist_items_step_id", "riordino_checklist_items", ["step_id"])

    # ─────────────────────────────────────────────────────────
    # riordino_notifications
    # ─────────────────────────────────────────────────────────
    op.create_table(
        "riordino_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("application_users.id"), nullable=False),
        sa.Column("practice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("riordino_practices.id"), nullable=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_riordino_notifications_user_read_created", "riordino_notifications", ["user_id", "is_read", "created_at"])

    # ─────────────────────────────────────────────────────────
    # SEED: 25 step templates (13 Fase 1 + 12 Fase 2)
    # ─────────────────────────────────────────────────────────
    seed_templates()


def downgrade() -> None:
    op.drop_table("riordino_notifications")
    op.drop_table("riordino_checklist_items")
    op.drop_table("riordino_events")
    op.drop_table("riordino_gis_links")
    op.drop_table("riordino_party_links")
    op.drop_table("riordino_parcel_links")
    op.drop_table("riordino_documents")
    op.drop_table("riordino_appeals")
    op.drop_table("riordino_tasks")
    op.drop_table("riordino_steps")
    op.drop_table("riordino_phases")
    op.drop_table("riordino_practices")
    op.drop_table("riordino_step_templates")


def seed_templates():
    """Seed all 25 step templates. Uses INSERT ... ON CONFLICT for idempotency."""
    templates = [
        # ── Fase 1 ──
        ("phase_1", "F1_STUDIO_PIANO", "Studio del Piano", 1, True, None, None, False, False, None),
        ("phase_1", "F1_INDAGINE", "Indagine: raccolta dati utenti e identificazione lotto", 2, True, None, None, False, False, None),
        ("phase_1", "F1_ELABORAZIONE", "Elaborazione", 3, True, None, None, False, False, None),
        ("phase_1", "F1_PUBBLICAZIONE", "Pubblicazione Piano da parte del Comune", 4, True, None, None, True, False, None),
        ("phase_1", "F1_OSSERVAZIONI", "Periodo osservazioni e ricorsi (90gg)", 5, True, None, None, False, True, '["ricorsi_presenti","nessun_ricorso"]'),
        ("phase_1", "F1_RICORSI", "Gestione ricorsi", 6, False, None, "F1_OSSERVAZIONI.outcome='ricorsi_presenti'", True, False, None),
        ("phase_1", "F1_COMMISSIONE", "Nomina commissione regionale e verifiche", 7, False, None, "F1_RICORSI attivo", True, False, None),
        ("phase_1", "F1_RISOLUZIONE", "Risoluzione e pubblicazione Piano/Decreto", 8, True, None, None, True, False, None),
        ("phase_1", "F1_TRASCRIZIONE", "Trascrizione a cura del consorzio (entro 30gg)", 9, True, None, None, True, False, None),
        ("phase_1", "F1_CONSERVATORIA", "Note trascrizione in Conservatoria", 10, True, None, None, True, False, None),
        ("phase_1", "F1_VOLTURA", "Voltura catastale tramite AdE", 11, True, None, None, True, False, None),
        ("phase_1", "F1_CARICAMENTO", "Caricamento sistema e aggiornamento GIS/Mappa", 12, True, None, None, False, False, None),
        ("phase_1", "F1_OUTPUT", "Output Fase 1: dati validati e caricati", 13, True, None, None, False, False, None),
        # ── Fase 2 ──
        ("phase_2", "F2_SCARICO_DATI", "Scarico dati catastali particelle del lotto", 1, True, None, None, False, False, None),
        ("phase_2", "F2_CSV", "Disponibilità file CSV (particelle, lotti, proprietari)", 2, True, None, None, True, False, None),
        ("phase_2", "F2_VERIFICA", "Verifica qualità/coerenza, classe coltivazione, intestazioni", 3, True, None, None, False, True, '["conforme","non_conforme"]'),
        ("phase_2", "F2_ESTRATTO_MAPPA", "Richiesta estratto di mappa", 4, True, None, "F2_VERIFICA.outcome='conforme'", True, False, None),
        ("phase_2", "F2_FUSIONE", "Fusione porzioni: unione quote stessa qualità (istanza unica)", 5, False, "anomalia", "F2_VERIFICA.outcome='non_conforme' AND tipo='fusione'", True, False, None),
        ("phase_2", "F2_DOCTE", "Variazione porzioni tramite DOCTE", 6, False, "anomalia", "F2_VERIFICA.outcome='non_conforme' AND tipo='variazione'", True, False, None),
        ("phase_2", "F2_PREGEO", "PREGEO per gestione mappali e unificazione qualità", 7, True, None, None, True, False, None),
        ("phase_2", "F2_MAPPALE_UNITO", "Ottenimento Mappale Unito", 8, True, None, None, True, False, None),
        ("phase_2", "F2_RIPRISTINO", "Ripristino porzioni per colture originali", 9, False, "anomalia", "F2_VERIFICA.outcome='non_conforme' AND tipo='fusione'", False, False, None),
        ("phase_2", "F2_ATTI_RT", "Atti di aggiornamento RT (contestuali)", 10, True, None, None, True, False, None),
        ("phase_2", "F2_AGG_GIS", "Aggiornamento GIS/Mappa nei sistemi", 11, True, None, None, False, False, None),
        ("phase_2", "F2_DOCUMENTO_FINALE", "Generazione pratica, protocollo e documento finale", 12, True, None, None, True, False, None),
    ]

    conn = op.get_bind()
    import json as _json
    for phase_code, code, title, seq, is_required, branch, activation, requires_doc, is_decision, outcome_opts in templates:
        outcome_val = _json.loads(outcome_opts) if outcome_opts else None
        conn.execute(
            sa.text("""
                INSERT INTO riordino_step_templates
                    (id, phase_code, code, title, sequence_no, is_required, branch,
                     activation_condition, requires_document, is_decision, outcome_options)
                VALUES
                    (gen_random_uuid(), :p_pc, :p_code, :p_title,
                     :p_seq, :p_req, :p_branch,
                     :p_activation, :p_reqdoc, :p_isdec,
                     CAST(:p_outcome AS jsonb))
                ON CONFLICT (code) DO NOTHING
            """),
            {
                "p_pc": phase_code,
                "p_code": code,
                "p_title": title,
                "p_seq": seq,
                "p_req": is_required,
                "p_branch": branch,
                "p_activation": None,
                "p_reqdoc": requires_doc,
                "p_isdec": is_decision,
                "p_outcome": _json.dumps(outcome_val) if outcome_val else None,
            },
        )
