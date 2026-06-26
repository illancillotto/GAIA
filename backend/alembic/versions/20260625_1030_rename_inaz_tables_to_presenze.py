"""rename presenze domain tables from inaz_* to presenze_*

Revision ID: 20260625_1030
Revises: 20260625_0900
Create Date: 2026-06-25
"""

from alembic import op


revision = "20260625_1030"
down_revision = "20260625_0900"
branch_labels = None
depends_on = None


TABLE_RENAMES: tuple[tuple[str, str], ...] = (
    ("inaz_credentials", "presenze_credentials"),
    ("inaz_supervisor_assignments", "presenze_supervisor_assignments"),
    ("inaz_holidays", "presenze_holidays"),
    ("inaz_schedule_templates", "presenze_schedule_templates"),
    ("inaz_schedule_rules", "presenze_schedule_rules"),
    ("inaz_collaborators", "presenze_collaborators"),
    ("inaz_collaborator_schedule_assignments", "presenze_collaborator_schedule_assignments"),
    ("inaz_import_jobs", "presenze_import_jobs"),
    ("inaz_sync_jobs", "presenze_sync_jobs"),
    ("inaz_auto_sync_config", "presenze_auto_sync_config"),
    ("inaz_bank_hours_guidance_config", "presenze_bank_hours_guidance_config"),
    ("inaz_bank_hours_guidance_config_revisions", "presenze_bank_hours_guidance_config_revisions"),
    ("inaz_daily_records", "presenze_daily_records"),
    ("inaz_daily_punches", "presenze_daily_punches"),
    ("inaz_event_summaries", "presenze_event_summaries"),
    ("inaz_recovery_adjustments", "presenze_recovery_adjustments"),
    ("inaz_bank_hours_adjustments", "presenze_bank_hours_adjustments"),
)


def _rename_tables(table_renames: tuple[tuple[str, str], ...]) -> None:
    for old_name, new_name in table_renames:
        op.rename_table(old_name, new_name)


def _rename_postgres_objects(old_prefix: str, new_prefix: str) -> None:
    op.execute(
        f"""
DO $$
DECLARE
    rec record;
    new_name text;
BEGIN
    FOR rec IN
        SELECT n.nspname AS schema_name, c.relname AS relation_name
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = current_schema()
          AND c.relkind IN ('S', 'i')
          AND c.relname LIKE '%{old_prefix}%'
        ORDER BY c.relkind, c.relname
    LOOP
        new_name := replace(rec.relation_name, '{old_prefix}', '{new_prefix}');
        IF new_name <> rec.relation_name THEN
            EXECUTE format(
                'ALTER %s %I.%I RENAME TO %I',
                CASE WHEN EXISTS (
                    SELECT 1 FROM pg_class c2
                    WHERE c2.relname = rec.relation_name
                      AND c2.relkind = 'S'
                      AND c2.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = rec.schema_name)
                ) THEN 'SEQUENCE' ELSE 'INDEX' END,
                rec.schema_name,
                rec.relation_name,
                new_name
            );
        END IF;
    END LOOP;

    FOR rec IN
        SELECT n.nspname AS schema_name, t.relname AS table_name, con.conname AS constraint_name
        FROM pg_constraint con
        JOIN pg_class t ON t.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = current_schema()
          AND con.conname LIKE '%{old_prefix}%'
        ORDER BY t.relname, con.conname
    LOOP
        new_name := replace(rec.constraint_name, '{old_prefix}', '{new_prefix}');
        IF new_name <> rec.constraint_name THEN
            EXECUTE format(
                'ALTER TABLE %I.%I RENAME CONSTRAINT %I TO %I',
                rec.schema_name,
                rec.table_name,
                rec.constraint_name,
                new_name
            );
        END IF;
    END LOOP;
END
$$;
"""
    )


def upgrade() -> None:
    _rename_tables(TABLE_RENAMES)
    _rename_postgres_objects("inaz_", "presenze_")


def downgrade() -> None:
    _rename_tables(tuple((new_name, old_name) for old_name, new_name in reversed(TABLE_RENAMES)))
    _rename_postgres_objects("presenze_", "inaz_")
