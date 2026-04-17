from pathlib import Path


def test_ruolo_admin_backfill_migration_updates_existing_admins() -> None:
    migration = Path("backend/alembic/versions/20260417_0049_backfill_ruolo_module_for_admins.py").read_text()

    assert 'UPDATE application_users' in migration
    assert "SET module_ruolo = TRUE" in migration
    assert "role IN ('admin', 'super_admin')" in migration
