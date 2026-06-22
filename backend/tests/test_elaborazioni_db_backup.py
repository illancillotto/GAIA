from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from app.services.elaborazioni_db_backup import _build_pg_dump_command, run_elaborazioni_db_backup_job


def test_build_pg_dump_command_uses_database_url(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.core.config.settings.database_url",
        "postgresql+psycopg://naap_app:secret%402024@postgres:5432/naap",
    )
    command, env = _build_pg_dump_command(Path("/tmp/gaia.dump"))

    assert command[:10] == [
        "pg_dump",
        "-h",
        "postgres",
        "-p",
        "5432",
        "-U",
        "naap_app",
        "-d",
        "naap",
        "-Fc",
    ]
    assert env["PGPASSWORD"] == "secret@2024"


def test_run_elaborazioni_db_backup_job_exports_dump_and_cleans_local_file(tmp_path, monkeypatch) -> None:
    local_dir = tmp_path / "db-backups"
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_local_dir", str(local_dir))
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_remote_root", "/volume1/Backups/GAIA/db")
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_retention_count", 5)
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_encryption_enabled", False)
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_encryption_passphrase", "")
    monkeypatch.setattr(
        "app.core.config.settings.database_url",
        "postgresql+psycopg://naap_app:secret@postgres:5432/naap",
    )

    dump_calls: list[list[str]] = []

    def fake_subprocess_run(command, **kwargs):
        dump_calls.append(command)
        output_path = Path(command[-1])
        output_path.write_bytes(b"fake-pg-dump")
        return subprocess.CompletedProcess(command, 0, "", "")

    export_calls: list[dict[str, object]] = []

    def fake_export_dump(local_path: str, remote_root: str, env_file: str, label: str, retention_count: int, **kwargs):
        export_calls.append(
            {
                "local_path": local_path,
                "remote_root": remote_root,
                "env_file": env_file,
                "label": label,
                "retention_count": retention_count,
                "kwargs": kwargs,
            }
        )
        return "/volume1/Backups/GAIA/db/latest.json"

    monkeypatch.setattr("app.services.elaborazioni_db_backup.subprocess.run", fake_subprocess_run)
    monkeypatch.setattr("app.services.elaborazioni_db_backup.export_dump", fake_export_dump)

    manifest_path = run_elaborazioni_db_backup_job()

    assert manifest_path == "/volume1/Backups/GAIA/db/latest.json"
    assert dump_calls
    assert export_calls == [
        {
            "local_path": str(local_dir / "gaia-nightly-elaborazioni.dump"),
            "remote_root": "/volume1/Backups/GAIA/db",
            "env_file": ".env",
            "label": "elaborazioni-nightly",
            "retention_count": 5,
            "kwargs": {"db_name": "naap", "db_user": "naap_app"},
        }
    ]
    assert not (local_dir / "gaia-nightly-elaborazioni.dump").exists()


def test_run_elaborazioni_db_backup_job_encrypts_dump_before_upload(tmp_path, monkeypatch) -> None:
    local_dir = tmp_path / "db-backups"
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_local_dir", str(local_dir))
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_remote_root", "/volume1/Backups/GAIA/db")
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_retention_count", 5)
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_encryption_enabled", True)
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_encryption_passphrase", "super-secret-passphrase")
    monkeypatch.setattr(
        "app.core.config.settings.database_url",
        "postgresql+psycopg://naap_app:secret@postgres:5432/naap",
    )

    def fake_subprocess_run(command, **kwargs):
        output_path = Path(command[-1])
        output_path.write_bytes(b"fake-pg-dump")
        return subprocess.CompletedProcess(command, 0, "", "")

    export_calls: list[dict[str, object]] = []

    def fake_export_dump(local_path: str, remote_root: str, env_file: str, label: str, retention_count: int, **kwargs):
        export_calls.append(
            {
                "local_path": local_path,
                "remote_root": remote_root,
                "env_file": env_file,
                "label": label,
                "retention_count": retention_count,
                "kwargs": kwargs,
            }
        )
        return "/volume1/Backups/GAIA/db/latest.json"

    monkeypatch.setattr("app.services.elaborazioni_db_backup.subprocess.run", fake_subprocess_run)
    monkeypatch.setattr("app.services.elaborazioni_db_backup.export_dump", fake_export_dump)

    manifest_path = run_elaborazioni_db_backup_job()

    assert manifest_path == "/volume1/Backups/GAIA/db/latest.json"
    assert export_calls == [
        {
            "local_path": str(local_dir / "gaia-nightly-elaborazioni.dump.enc"),
            "remote_root": "/volume1/Backups/GAIA/db",
            "env_file": ".env",
            "label": "elaborazioni-nightly",
            "retention_count": 5,
            "kwargs": {
                "db_name": "naap",
                "db_user": "naap_app",
                "encryption": {
                    "scheme": "aes-256-ctr+hmac-sha256",
                    "kdf": "scrypt",
                    "passphrase_env_var": "ELABORAZIONI_DB_BACKUP_ENCRYPTION_PASSPHRASE",
                },
                "plaintext_dump_filename": "gaia-nightly-elaborazioni.dump",
                "plaintext_dump_format": "custom",
                "plaintext_sha256": "d6d8d84b025ce1e7c95232a2a02bacc3acfef0582076e6869205fb732d0e0792",
                "plaintext_size_bytes": 12,
            },
        }
    ]
    assert not (local_dir / "gaia-nightly-elaborazioni.dump").exists()
    assert not (local_dir / "gaia-nightly-elaborazioni.dump.enc").exists()


def test_run_elaborazioni_db_backup_job_raises_runtime_error_on_pg_dump_failure(tmp_path, monkeypatch) -> None:
    local_dir = tmp_path / "db-backups"
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_local_dir", str(local_dir))
    monkeypatch.setattr(
        "app.core.config.settings.database_url",
        "postgresql+psycopg://naap_app:secret@postgres:5432/naap",
    )

    def fake_subprocess_run(command, **kwargs):
        output_path = Path(command[-1])
        output_path.write_bytes(b"stale-dump")
        raise subprocess.CalledProcessError(returncode=1, cmd=command, stderr="broken dump", output="")

    monkeypatch.setattr("app.services.elaborazioni_db_backup.subprocess.run", fake_subprocess_run)

    with pytest.raises(RuntimeError) as exc_info:
        run_elaborazioni_db_backup_job()

    assert "pg_dump failed: broken dump" in str(exc_info.value)
    assert not (local_dir / "gaia-nightly-elaborazioni.dump").exists()


def test_run_elaborazioni_db_backup_job_skips_when_lock_is_already_held(tmp_path, monkeypatch) -> None:
    local_dir = tmp_path / "db-backups"
    local_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_local_dir", str(local_dir))
    monkeypatch.setattr(
        "app.core.config.settings.database_url",
        "postgresql+psycopg://naap_app:secret@postgres:5432/naap",
    )

    lock_path = local_dir / ".gaia-elaborazioni-db-backup.lock"
    lock_path.write_text("", encoding="utf-8")
    held_lock = lock_path.open("a+", encoding="utf-8")
    try:
        import fcntl

        fcntl.flock(held_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        subprocess_mock = pytest.MonkeyPatch()
        subprocess_mock.setattr("app.services.elaborazioni_db_backup.subprocess.run", lambda *args, **kwargs: None)
        try:
            assert run_elaborazioni_db_backup_job() is None
        finally:
            subprocess_mock.undo()
    finally:
        import fcntl

        fcntl.flock(held_lock.fileno(), fcntl.LOCK_UN)
        held_lock.close()
