from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def test_alembic_env_references_application_metadata() -> None:
    env_py = (
        ROOT / "modules" / "accessi" / "backend" / "alembic" / "env.py"
    ).read_text(encoding="utf-8")

    assert "settings.database_url" in env_py
    assert "target_metadata = Base.metadata" in env_py
    assert "context.run_migrations()" in env_py


def test_initial_migration_creates_snapshots_table() -> None:
    migration = (
        ROOT
        / "modules"
        / "accessi"
        / "backend"
        / "alembic"
        / "versions"
        / "20260319_0001_initial_schema.py"
    ).read_text(encoding="utf-8")

    assert 'op.create_table(' in migration
    assert '"snapshots"' in migration
    assert '"status"' in migration
    assert 'op.create_index("ix_snapshots_id"' in migration


def test_audit_domain_migration_creates_core_tables() -> None:
    migration = (
        ROOT
        / "modules"
        / "accessi"
        / "backend"
        / "alembic"
        / "versions"
        / "20260320_0003_audit_domain_minimum.py"
    ).read_text(encoding="utf-8")

    for table_name in ['"nas_users"', '"nas_groups"', '"shares"', '"reviews"']:
        assert table_name in migration


def test_permission_engine_migration_creates_permission_tables() -> None:
    migration = (
        ROOT
        / "modules"
        / "accessi"
        / "backend"
        / "alembic"
        / "versions"
        / "20260320_0004_permission_engine_mvp.py"
    ).read_text(encoding="utf-8")

    for table_name in ['"permission_entries"', '"effective_permissions"']:
        assert table_name in migration


def test_sync_runs_migration_creates_audit_table() -> None:
    migration = (
        ROOT
        / "modules"
        / "accessi"
        / "backend"
        / "alembic"
        / "versions"
        / "20260323_0005_sync_runs_audit.py"
    ).read_text(encoding="utf-8")

    assert '"sync_runs"' in migration
    assert '"mode"' in migration
    assert '"status"' in migration
    assert '"attempts_used"' in migration


def test_sync_runs_metadata_migration_extends_audit_table() -> None:
    migration = (
        ROOT
        / "modules"
        / "accessi"
        / "backend"
        / "alembic"
        / "versions"
        / "20260323_0006_sync_runs_metadata.py"
    ).read_text(encoding="utf-8")

    assert 'op.add_column("sync_runs"' in migration
    assert '"duration_ms"' in migration
    assert '"initiated_by"' in migration
    assert '"source_label"' in migration
