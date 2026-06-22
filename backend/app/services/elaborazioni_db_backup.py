from __future__ import annotations

import fcntl
import hashlib
import logging
import os
from pathlib import Path
import subprocess
from urllib.parse import unquote

from sqlalchemy.engine import make_url

from app.core.config import settings
from app.services.backup_encryption import (
    BackupEncryptionError,
    encrypt_file,
)
from app.scripts.nas_db_transfer import export_dump

logger = logging.getLogger(__name__)
LOCK_FILENAME = ".gaia-elaborazioni-db-backup.lock"


def _build_pg_dump_command(output_path: Path) -> tuple[list[str], dict[str, str]]:
    url = make_url(settings.database_url)
    host = url.host or "postgres"
    port = str(url.port or 5432)
    username = unquote(url.username or "")
    database = url.database or "gaia"
    password = unquote(url.password or "")

    env = {
        "PGPASSWORD": password,
    }
    command = [
        "pg_dump",
        "-h",
        host,
        "-p",
        port,
        "-U",
        username,
        "-d",
        database,
        "-Fc",
        "--no-owner",
        "--no-privileges",
        "-f",
        str(output_path),
    ]
    return command, env


def _acquire_job_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def run_elaborazioni_db_backup_job() -> str | None:
    local_dir = Path(settings.elaborazioni_db_backup_local_dir).resolve()
    local_dir.mkdir(parents=True, exist_ok=True)
    lock_handle = _acquire_job_lock(local_dir / LOCK_FILENAME)
    if lock_handle is None:
        logger.info("Elaborazioni DB backup skipped: another worker already owns the backup lock")
        return None

    dump_filename = "gaia-nightly-elaborazioni.dump"
    dump_path = local_dir / dump_filename
    encrypted_dump_path = local_dir / f"{dump_filename}.enc"
    command, env_overrides = _build_pg_dump_command(dump_path)
    db_url = make_url(settings.database_url)
    db_name = db_url.database or "gaia"
    db_user = unquote(db_url.username or "")

    logger.info(
        "Elaborazioni DB backup avviato: cron=%s timezone=%s remote_root=%s retention=%s",
        settings.elaborazioni_db_backup_cron,
        settings.elaborazioni_db_backup_timezone,
        settings.elaborazioni_db_backup_remote_root,
        settings.elaborazioni_db_backup_retention_count,
    )

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, **env_overrides},
        )
        upload_path = dump_path
        encryption_metadata: dict[str, str] | None = None
        plaintext_sha256: str | None = None
        plaintext_size_bytes: int | None = None
        if settings.elaborazioni_db_backup_encryption_enabled:
            passphrase = settings.elaborazioni_db_backup_encryption_passphrase
            if not passphrase:
                raise RuntimeError("backup encryption enabled but passphrase is empty")
            plaintext_sha256 = _sha256_file(dump_path)
            plaintext_size_bytes = dump_path.stat().st_size
            encryption_metadata = encrypt_file(dump_path, encrypted_dump_path, passphrase)
            dump_path.unlink(missing_ok=True)
            upload_path = encrypted_dump_path
        export_kwargs: dict[str, object] = {
            "db_name": db_name,
            "db_user": db_user,
        }
        if encryption_metadata is not None:
            export_kwargs.update(
                {
                    "encryption": encryption_metadata,
                    "plaintext_dump_filename": dump_filename,
                    "plaintext_dump_format": "custom",
                    "plaintext_sha256": plaintext_sha256,
                    "plaintext_size_bytes": plaintext_size_bytes,
                }
            )
        manifest_path = export_dump(
            str(upload_path),
            settings.elaborazioni_db_backup_remote_root,
            ".env",
            "elaborazioni-nightly",
            settings.elaborazioni_db_backup_retention_count,
            **export_kwargs,
        )
        logger.info("Elaborazioni DB backup completato: manifest=%s", manifest_path)
        return manifest_path
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        details = stderr or stdout or str(exc)
        logger.exception("Elaborazioni DB backup fallito durante pg_dump: %s", details)
        raise RuntimeError(f"pg_dump failed: {details}") from exc
    except BackupEncryptionError as exc:
        logger.exception("Elaborazioni DB backup fallito durante cifratura: %s", exc)
        raise RuntimeError(f"backup encryption failed: {exc}") from exc
    finally:
        dump_path.unlink(missing_ok=True)
        encrypted_dump_path.unlink(missing_ok=True)
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()
