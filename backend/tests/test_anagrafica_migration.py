from pathlib import Path


def find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / "docker-compose.yml").exists() and (candidate / "README.md").exists():
            return candidate
    raise RuntimeError("Repository root not found")


ROOT = find_repo_root()


def test_anagrafica_migration_creates_core_tables() -> None:
    migration = (
        ROOT
        / "backend"
        / "alembic"
        / "versions"
        / "20260327_0018_anagrafica_mvp_backend.py"
    ).read_text(encoding="utf-8")

    for table_name in [
        '"ana_subjects"',
        '"ana_persons"',
        '"ana_companies"',
        '"ana_documents"',
        '"ana_import_jobs"',
        '"ana_audit_log"',
    ]:
        assert table_name in migration


def test_anagrafica_migration_includes_expected_uniques() -> None:
    migration = (
        ROOT
        / "backend"
        / "alembic"
        / "versions"
        / "20260327_0018_anagrafica_mvp_backend.py"
    ).read_text(encoding="utf-8")

    assert '"uq_ana_subjects_nas_folder_path"' in migration
    assert '"uq_ana_persons_codice_fiscale"' in migration
    assert '"uq_ana_companies_partita_iva"' in migration


def test_person_snapshot_migration_creates_history_table() -> None:
    migration = (
        ROOT
        / "backend"
        / "alembic"
        / "versions"
        / "20260424_0060_add_anagrafica_person_snapshots.py"
    ).read_text(encoding="utf-8")

    assert '"ana_person_snapshots"' in migration
    assert '"ix_ana_person_snapshots_subject_id"' in migration
    assert '"ix_ana_person_snapshots_collected_at"' in migration
