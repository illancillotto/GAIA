from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_alembic_env_references_application_metadata() -> None:
    env_py = (ROOT / "backend" / "alembic" / "env.py").read_text(encoding="utf-8")

    assert "settings.database_url" in env_py
    assert "target_metadata = Base.metadata" in env_py
    assert "context.run_migrations()" in env_py


def test_initial_migration_creates_snapshots_table() -> None:
    migration = (
        ROOT / "backend" / "alembic" / "versions" / "20260319_0001_initial_schema.py"
    ).read_text(encoding="utf-8")

    assert 'op.create_table(' in migration
    assert '"snapshots"' in migration
    assert '"status"' in migration
    assert 'op.create_index("ix_snapshots_id"' in migration
