from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.services.elaborazioni_db_backup import (
    _build_pg_dump_command,
    run_elaborazioni_db_backup_job,
)


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


# --- R124 characterization: upload artifact preparation and error routing ---


def _configure_backup_settings(
    monkeypatch, local_dir: Path, *, encryption_enabled: bool, passphrase: str
) -> None:
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_local_dir", str(local_dir))
    monkeypatch.setattr(
        "app.core.config.settings.elaborazioni_db_backup_remote_root", "/volume1/Backups/GAIA/db"
    )
    monkeypatch.setattr("app.core.config.settings.elaborazioni_db_backup_retention_count", 3)
    monkeypatch.setattr(
        "app.core.config.settings.elaborazioni_db_backup_encryption_enabled", encryption_enabled
    )
    monkeypatch.setattr(
        "app.core.config.settings.elaborazioni_db_backup_encryption_passphrase", passphrase
    )
    monkeypatch.setattr(
        "app.core.config.settings.database_url",
        "postgresql+psycopg://naap_app:secret@postgres:5432/naap",
    )


def _install_fake_pg_dump(monkeypatch, run_calls: list[dict[str, object]] | None = None) -> None:
    def fake_subprocess_run(command, **kwargs):
        if run_calls is not None:
            run_calls.append({"command": command, "kwargs": kwargs})
        Path(command[-1]).write_bytes(b"fake-pg-dump")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("app.services.elaborazioni_db_backup.subprocess.run", fake_subprocess_run)


def _install_failing_export(monkeypatch, export_calls: list[object]) -> None:
    def fake_export_dump(*args, **kwargs):
        export_calls.append((args, kwargs))
        raise AssertionError("export_dump must not be called")

    monkeypatch.setattr("app.services.elaborazioni_db_backup.export_dump", fake_export_dump)


def _assert_lock_released(local_dir: Path) -> None:
    import fcntl

    with (local_dir / ".gaia-elaborazioni-db-backup.lock").open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _assert_artifacts_removed(local_dir: Path) -> None:
    assert not (local_dir / "gaia-nightly-elaborazioni.dump").exists()
    assert not (local_dir / "gaia-nightly-elaborazioni.dump.enc").exists()


def test_run_backup_job_rejects_empty_passphrase_when_encryption_enabled(
    tmp_path, monkeypatch
) -> None:
    local_dir = tmp_path / "db-backups"
    _configure_backup_settings(monkeypatch, local_dir, encryption_enabled=True, passphrase="")
    _install_fake_pg_dump(monkeypatch)
    export_calls: list[object] = []
    _install_failing_export(monkeypatch, export_calls)

    with pytest.raises(RuntimeError) as exc_info:
        run_elaborazioni_db_backup_job()

    assert type(exc_info.value) is RuntimeError
    assert str(exc_info.value) == "backup encryption enabled but passphrase is empty"
    assert exc_info.value.__cause__ is None
    assert export_calls == []
    _assert_artifacts_removed(local_dir)
    _assert_lock_released(local_dir)


def test_run_backup_job_wraps_backup_encryption_error(tmp_path, monkeypatch) -> None:
    from app.services.backup_encryption import BackupEncryptionError

    local_dir = tmp_path / "db-backups"
    _configure_backup_settings(monkeypatch, local_dir, encryption_enabled=True, passphrase="pw")
    _install_fake_pg_dump(monkeypatch)
    export_calls: list[object] = []
    _install_failing_export(monkeypatch, export_calls)
    original = BackupEncryptionError("cipher exploded")
    encrypt_calls: list[tuple[Path, Path, str]] = []

    def fake_encrypt_file(input_path, output_path, passphrase):
        encrypt_calls.append((input_path, output_path, passphrase))
        Path(output_path).write_bytes(b"partial")
        raise original

    monkeypatch.setattr("app.services.elaborazioni_db_backup.encrypt_file", fake_encrypt_file)

    with pytest.raises(RuntimeError) as exc_info:
        run_elaborazioni_db_backup_job()

    assert type(exc_info.value) is RuntimeError
    assert str(exc_info.value) == "backup encryption failed: cipher exploded"
    assert exc_info.value.__cause__ is original
    assert encrypt_calls == [
        (
            local_dir.resolve() / "gaia-nightly-elaborazioni.dump",
            local_dir.resolve() / "gaia-nightly-elaborazioni.dump.enc",
            "pw",
        )
    ]
    assert export_calls == []
    _assert_artifacts_removed(local_dir)
    _assert_lock_released(local_dir)


def test_run_backup_job_reports_stdout_when_pg_dump_stderr_is_empty(tmp_path, monkeypatch) -> None:
    local_dir = tmp_path / "db-backups"
    _configure_backup_settings(monkeypatch, local_dir, encryption_enabled=False, passphrase="")
    export_calls: list[object] = []
    _install_failing_export(monkeypatch, export_calls)
    raised: list[subprocess.CalledProcessError] = []

    def fake_subprocess_run(command, **kwargs):
        exc = subprocess.CalledProcessError(
            returncode=2, cmd=command, output="  only stdout  ", stderr="   "
        )
        raised.append(exc)
        raise exc

    monkeypatch.setattr("app.services.elaborazioni_db_backup.subprocess.run", fake_subprocess_run)

    with pytest.raises(RuntimeError) as exc_info:
        run_elaborazioni_db_backup_job()

    assert str(exc_info.value) == "pg_dump failed: only stdout"
    assert exc_info.value.__cause__ is raised[0]
    assert export_calls == []
    _assert_artifacts_removed(local_dir)
    _assert_lock_released(local_dir)


def test_run_backup_job_falls_back_to_exception_text_without_pg_dump_output(
    tmp_path, monkeypatch
) -> None:
    local_dir = tmp_path / "db-backups"
    _configure_backup_settings(monkeypatch, local_dir, encryption_enabled=False, passphrase="")
    export_calls: list[object] = []
    _install_failing_export(monkeypatch, export_calls)
    raised: list[subprocess.CalledProcessError] = []

    def fake_subprocess_run(command, **kwargs):
        exc = subprocess.CalledProcessError(returncode=3, cmd=["pg_dump"], output=None, stderr=None)
        raised.append(exc)
        raise exc

    monkeypatch.setattr("app.services.elaborazioni_db_backup.subprocess.run", fake_subprocess_run)

    with pytest.raises(RuntimeError) as exc_info:
        run_elaborazioni_db_backup_job()

    assert str(exc_info.value) == f"pg_dump failed: {raised[0]}"
    assert "returned non-zero exit status 3" in str(exc_info.value)
    assert exc_info.value.__cause__ is raised[0]
    _assert_artifacts_removed(local_dir)
    _assert_lock_released(local_dir)


def test_run_backup_job_plain_upload_passes_exact_export_arguments(tmp_path, monkeypatch) -> None:
    local_dir = tmp_path / "db-backups"
    _configure_backup_settings(
        monkeypatch, local_dir, encryption_enabled=False, passphrase="ignored"
    )
    run_calls: list[dict[str, object]] = []
    _install_fake_pg_dump(monkeypatch, run_calls)
    encrypt_calls: list[object] = []
    monkeypatch.setattr(
        "app.services.elaborazioni_db_backup.encrypt_file",
        lambda *args, **kwargs: encrypt_calls.append(args),
    )
    export_calls: list[tuple[tuple[object, ...], dict[str, object], bool]] = []

    def fake_export_dump(*args, **kwargs):
        export_calls.append((args, kwargs, Path(args[0]).read_bytes() == b"fake-pg-dump"))
        return "manifest.json"

    monkeypatch.setattr("app.services.elaborazioni_db_backup.export_dump", fake_export_dump)

    assert run_elaborazioni_db_backup_job() == "manifest.json"

    dump_path = local_dir.resolve() / "gaia-nightly-elaborazioni.dump"
    assert encrypt_calls == []
    assert export_calls == [
        (
            (str(dump_path), "/volume1/Backups/GAIA/db", ".env", "elaborazioni-nightly", 3),
            {"db_name": "naap", "db_user": "naap_app"},
            True,
        )
    ]
    assert len(run_calls) == 1
    assert run_calls[0]["command"][-1] == str(dump_path)
    run_kwargs = run_calls[0]["kwargs"]
    assert run_kwargs["check"] is True
    assert run_kwargs["capture_output"] is True
    assert run_kwargs["text"] is True
    assert run_kwargs["env"]["PGPASSWORD"] == "secret"
    _assert_artifacts_removed(local_dir)
    _assert_lock_released(local_dir)


def test_run_backup_job_encrypted_upload_removes_plain_dump_before_export(
    tmp_path, monkeypatch
) -> None:
    local_dir = tmp_path / "db-backups"
    _configure_backup_settings(monkeypatch, local_dir, encryption_enabled=True, passphrase="pw")
    _install_fake_pg_dump(monkeypatch)
    observed: list[dict[str, object]] = []

    def fake_export_dump(*args, **kwargs):
        resolved = local_dir.resolve()
        observed.append(
            {
                "args": args,
                "kwargs": kwargs,
                "plain_exists": (resolved / "gaia-nightly-elaborazioni.dump").exists(),
                "enc_exists": (resolved / "gaia-nightly-elaborazioni.dump.enc").exists(),
            }
        )
        return "manifest.json"

    monkeypatch.setattr("app.services.elaborazioni_db_backup.export_dump", fake_export_dump)

    assert run_elaborazioni_db_backup_job() == "manifest.json"

    assert len(observed) == 1
    call = observed[0]
    assert call["args"] == (
        str(local_dir.resolve() / "gaia-nightly-elaborazioni.dump.enc"),
        "/volume1/Backups/GAIA/db",
        ".env",
        "elaborazioni-nightly",
        3,
    )
    assert list(call["kwargs"]) == [
        "db_name",
        "db_user",
        "encryption",
        "plaintext_dump_filename",
        "plaintext_dump_format",
        "plaintext_sha256",
        "plaintext_size_bytes",
    ]
    assert call["plain_exists"] is False
    assert call["enc_exists"] is True
    _assert_artifacts_removed(local_dir)
    _assert_lock_released(local_dir)


def test_run_backup_job_propagates_export_failure_and_cleans_up(tmp_path, monkeypatch) -> None:
    local_dir = tmp_path / "db-backups"
    _configure_backup_settings(monkeypatch, local_dir, encryption_enabled=True, passphrase="pw")
    _install_fake_pg_dump(monkeypatch)
    failure = OSError("nas unreachable")

    def fake_export_dump(*args, **kwargs):
        raise failure

    monkeypatch.setattr("app.services.elaborazioni_db_backup.export_dump", fake_export_dump)

    with pytest.raises(OSError) as exc_info:
        run_elaborazioni_db_backup_job()

    assert exc_info.value is failure
    _assert_artifacts_removed(local_dir)
    _assert_lock_released(local_dir)
