from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import socket
import sys

from app.services.backup_encryption import (
    BackupEncryptionError,
    DEFAULT_PASSPHRASE_ENV_VAR,
    decrypt_file,
    strip_encrypted_suffix,
)
from app.services.nas_connector import NasConnectorError, get_nas_client

DEFAULT_REMOTE_ROOT = "/volume1/Backups/GAIA/db"
DEFAULT_RETENTION_COUNT = 14
LATEST_MANIFEST_NAME = "latest.json"
LOCK_DIR_NAME = ".locks/db-transfer.lock"


class TransferError(RuntimeError):
    """Raised when the NAS DB transfer flow cannot be completed safely."""


@dataclass
class BackupManifest:
    version: int
    backup_id: str
    project: str
    created_at: str
    created_by_host: str
    env_file: str
    db_name: str
    db_user: str
    dump_filename: str
    dump_format: str
    sha256: str
    size_bytes: int
    label: str | None
    remote_root: str
    remote_dump_path: str
    remote_manifest_path: str
    encryption: dict[str, str] | None = None
    plaintext_dump_filename: str | None = None
    plaintext_dump_format: str | None = None
    plaintext_sha256: str | None = None
    plaintext_size_bytes: int | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transfer GAIA PostgreSQL backups to and from the NAS.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Upload a local dump to the NAS.")
    export_parser.add_argument("--local-path", required=True, help="Local dump path produced by backup-gaia-db.sh.")
    export_parser.add_argument("--remote-root", default=os.getenv("NAS_DB_BACKUP_ROOT", DEFAULT_REMOTE_ROOT))
    export_parser.add_argument("--env-file", default=".env")
    export_parser.add_argument("--label", default="")
    export_parser.add_argument("--retention-count", type=int, default=_env_int("NAS_DB_BACKUP_RETENTION_COUNT", DEFAULT_RETENTION_COUNT))

    download_parser = subparsers.add_parser("download", help="Download a dump from the NAS.")
    download_parser.add_argument("--output-dir", required=True, help="Local directory where the dump will be downloaded.")
    download_parser.add_argument("--remote-root", default=os.getenv("NAS_DB_BACKUP_ROOT", DEFAULT_REMOTE_ROOT))
    download_parser.add_argument("--manifest-path", default="")

    return parser.parse_args()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise TransferError(f"Invalid integer for {name}: {raw}") from exc


def _read_env_value(env_file: str, key: str, fallback: str) -> str:
    env_path = Path(env_file)
    if not env_path.is_file():
        return fallback
    pattern = re.compile(rf"^{re.escape(key)}=(.*)$")
    value = fallback
    for line in env_path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        value = match.group(1).strip()
    return value or fallback


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _isoformat(timestamp: datetime) -> str:
    return timestamp.isoformat().replace("+00:00", "Z")


def _sanitize_label(label: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", label.strip())
    sanitized = sanitized.strip("-._")
    return sanitized


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _dump_format_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".dump":
        return "custom"
    if suffix == ".sql":
        return "plain"
    raise TransferError(f"Unsupported dump extension for {path}. Expected .dump or .sql.")


def _build_backup_id(timestamp: datetime, label: str) -> str:
    base = f"gaia-{timestamp.strftime('%Y%m%d-%H%M%S')}"
    safe_label = _sanitize_label(label)
    if safe_label:
        return f"{base}-{safe_label}"
    return base


def _normalize_remote_root(remote_root: str) -> str:
    normalized = remote_root.strip()
    if not normalized:
        raise TransferError("NAS remote root is empty. Set NAS_DB_BACKUP_ROOT or pass --remote-root.")
    return normalized.rstrip("/")


def _build_remote_paths(remote_root: str, backup_id: str, dump_filename: str, timestamp: datetime) -> dict[str, str]:
    year = timestamp.strftime("%Y")
    month = timestamp.strftime("%m")
    archive_root = f"{remote_root}/archives"
    archive_dir = f"{archive_root}/{year}/{month}"
    staging_dir = f"{remote_root}/.staging/{backup_id}"
    dump_path = f"{archive_dir}/{dump_filename}"
    manifest_path = f"{dump_path}.manifest.json"
    latest_path = f"{remote_root}/{LATEST_MANIFEST_NAME}"
    return {
        "archive_root": archive_root,
        "archive_dir": archive_dir,
        "staging_dir": staging_dir,
        "staging_dump_path": f"{staging_dir}/{dump_filename}",
        "staging_manifest_path": f"{staging_dir}/{dump_filename}.manifest.json",
        "staging_latest_path": f"{staging_dir}/{LATEST_MANIFEST_NAME}",
        "dump_path": dump_path,
        "manifest_path": manifest_path,
        "latest_path": latest_path,
        "lock_dir": f"{remote_root}/{LOCK_DIR_NAME}",
    }


def _remote_sha256_command(path: str) -> str:
    quoted_path = shlex.quote(path)
    return (
        "if command -v sha256sum >/dev/null 2>&1; then "
        f"sha256sum {quoted_path} | awk '{{print $1}}'; "
        "elif command -v shasum >/dev/null 2>&1; then "
        f"shasum -a 256 {quoted_path} | awk '{{print $1}}'; "
        "elif command -v openssl >/dev/null 2>&1; then "
        f"openssl dgst -sha256 {quoted_path} | awk '{{print $NF}}'; "
        "else echo 'missing-sha256-tool' >&2; exit 127; fi"
    )


def _acquire_lock(client, lock_dir: str) -> None:
    owner_payload = json.dumps(
        {
            "host": socket.gethostname(),
            "pid": os.getpid(),
            "created_at": _isoformat(_now_utc()),
        },
        indent=2,
    ).encode("utf-8")
    try:
        client.run_command(f"mkdir {shlex.quote(lock_dir)}")
    except NasConnectorError as exc:
        raise TransferError(f"Another NAS DB transfer is already running or lock directory exists: {lock_dir}") from exc
    try:
        client.upload_file(f"{lock_dir}/owner.json", owner_payload)
    except Exception:
        try:
            client.run_command(f"rm -rf {shlex.quote(lock_dir)}")
        finally:
            raise


def _release_lock(client, lock_dir: str) -> None:
    try:
        client.run_command(f"rm -rf {shlex.quote(lock_dir)}")
    except NasConnectorError:
        return


def _prune_remote_backups(client, archive_root: str, retention_count: int) -> None:
    if retention_count <= 0:
        return
    script = f"""
set -eu
archive_root={shlex.quote(archive_root)}
keep={retention_count}
find "$archive_root" -type f -name 'gaia-*.manifest.json' 2>/dev/null | sort -r | awk -v keep="$keep" 'NR > keep {{ print }}' | while IFS= read -r manifest; do
  [ -n "$manifest" ] || continue
  dump="${{manifest%.manifest.json}}"
  rm -f "$manifest" "$dump"
done
"""
    client.run_command(script)


def _load_manifest_from_bytes(payload: bytes, source: str) -> BackupManifest:
    try:
        data = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise TransferError(f"Invalid manifest JSON: {source}") from exc
    required_keys = {
        "version",
        "backup_id",
        "project",
        "created_at",
        "created_by_host",
        "env_file",
        "db_name",
        "db_user",
        "dump_filename",
        "dump_format",
        "sha256",
        "size_bytes",
        "remote_root",
        "remote_dump_path",
        "remote_manifest_path",
    }
    missing = sorted(required_keys - data.keys())
    if missing:
        raise TransferError(f"Manifest missing required keys: {', '.join(missing)}")
    return BackupManifest(**data)


def export_dump(
    local_path: str,
    remote_root: str,
    env_file: str,
    label: str,
    retention_count: int,
    *,
    db_name: str | None = None,
    db_user: str | None = None,
    encryption: dict[str, str] | None = None,
    plaintext_dump_filename: str | None = None,
    plaintext_dump_format: str | None = None,
    plaintext_sha256: str | None = None,
    plaintext_size_bytes: int | None = None,
) -> str:
    local_dump_path = Path(local_path).resolve()
    if not local_dump_path.is_file():
        raise TransferError(f"Local dump not found: {local_dump_path}")

    timestamp = _now_utc()
    backup_id = _build_backup_id(timestamp, label)
    normalized_remote_root = _normalize_remote_root(remote_root)
    dump_filename = local_dump_path.name
    remote_paths = _build_remote_paths(normalized_remote_root, backup_id, dump_filename, timestamp)
    manifest = BackupManifest(
        version=1,
        backup_id=backup_id,
        project="GAIA",
        created_at=_isoformat(timestamp),
        created_by_host=socket.gethostname(),
        env_file=env_file,
        db_name=db_name or _read_env_value(env_file, "POSTGRES_DB", "gaia"),
        db_user=db_user or _read_env_value(env_file, "POSTGRES_USER", "gaia_app"),
        dump_filename=dump_filename,
        dump_format=plaintext_dump_format or _dump_format_from_path(local_dump_path),
        sha256=_sha256_file(local_dump_path),
        size_bytes=local_dump_path.stat().st_size,
        label=_sanitize_label(label) or None,
        remote_root=normalized_remote_root,
        remote_dump_path=remote_paths["dump_path"],
        remote_manifest_path=remote_paths["manifest_path"],
        encryption=encryption,
        plaintext_dump_filename=plaintext_dump_filename,
        plaintext_dump_format=plaintext_dump_format,
        plaintext_sha256=plaintext_sha256,
        plaintext_size_bytes=plaintext_size_bytes,
    )
    manifest_bytes = (json.dumps(asdict(manifest), indent=2) + "\n").encode("utf-8")

    client = get_nas_client()
    try:
        _acquire_lock(client, remote_paths["lock_dir"])
        client.ensure_directory(remote_paths["staging_dir"])
        client.ensure_directory(remote_paths["archive_dir"])

        print(f"==> Upload dump verso NAS: {remote_paths['staging_dump_path']}", file=sys.stderr)
        client.upload_local_file(str(local_dump_path), remote_paths["staging_dump_path"])
        client.upload_file(remote_paths["staging_manifest_path"], manifest_bytes)

        remote_sha256 = client.run_command(_remote_sha256_command(remote_paths["staging_dump_path"])).strip()
        if remote_sha256 != manifest.sha256:
            raise TransferError(
                f"SHA256 remoto non coerente dopo upload: atteso {manifest.sha256}, ottenuto {remote_sha256}"
            )

        client.move_file(remote_paths["staging_dump_path"], remote_paths["dump_path"])
        client.move_file(remote_paths["staging_manifest_path"], remote_paths["manifest_path"])
        client.upload_file(remote_paths["staging_latest_path"], manifest_bytes)
        client.move_file(remote_paths["staging_latest_path"], remote_paths["latest_path"])
        _prune_remote_backups(client, remote_paths["archive_root"], retention_count)
    finally:
        _release_lock(client, remote_paths["lock_dir"])
        client.close()

    print(f"==> Export NAS completato: {remote_paths['dump_path']}", file=sys.stderr)
    print(remote_paths["manifest_path"])
    return remote_paths["manifest_path"]


def _resolve_manifest_path(client, remote_root: str, manifest_path: str) -> str:
    if manifest_path.strip():
        return manifest_path.strip()
    latest_path = f"{remote_root}/{LATEST_MANIFEST_NAME}"
    if not client.path_exists(latest_path):
        raise TransferError(f"Nessun latest manifest presente sul NAS: {latest_path}")
    return latest_path


def _unique_local_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return directory / f"{stem}-{timestamp}{suffix}"


def _resolve_decryption_passphrase(manifest: BackupManifest) -> str:
    env_var = DEFAULT_PASSPHRASE_ENV_VAR
    if manifest.encryption and manifest.encryption.get("passphrase_env_var"):
        env_var = manifest.encryption["passphrase_env_var"]
    passphrase = os.getenv(env_var, "").strip()
    if not passphrase and env_var != "NAS_DB_BACKUP_PASSPHRASE":
        passphrase = os.getenv("NAS_DB_BACKUP_PASSPHRASE", "").strip()
    if not passphrase:
        raise TransferError(f"Missing backup decryption passphrase in environment variable: {env_var}")
    return passphrase


def download_dump(output_dir: str, remote_root: str, manifest_path: str) -> str:
    local_output_dir = Path(output_dir).resolve()
    local_output_dir.mkdir(parents=True, exist_ok=True)

    normalized_remote_root = _normalize_remote_root(remote_root)
    client = get_nas_client()
    try:
        resolved_manifest_path = _resolve_manifest_path(client, normalized_remote_root, manifest_path)
        print(f"==> Download manifest da NAS: {resolved_manifest_path}", file=sys.stderr)
        manifest = _load_manifest_from_bytes(client.download_file(resolved_manifest_path), resolved_manifest_path)
        local_manifest_path = _unique_local_path(local_output_dir, f"{manifest.dump_filename}.manifest.json")
        local_dump_path = _unique_local_path(local_output_dir, manifest.dump_filename)
        local_manifest_path.write_text(json.dumps(asdict(manifest), indent=2) + "\n", encoding="utf-8")

        print(f"==> Download dump da NAS: {manifest.remote_dump_path}", file=sys.stderr)
        client.download_to_local(manifest.remote_dump_path, str(local_dump_path))
    finally:
        client.close()

    local_sha256 = _sha256_file(local_dump_path)
    if local_sha256 != manifest.sha256:
        raise TransferError(f"SHA256 locale non coerente: atteso {manifest.sha256}, ottenuto {local_sha256}")
    if local_dump_path.stat().st_size != manifest.size_bytes:
        raise TransferError(
            f"Dimensione locale non coerente: atteso {manifest.size_bytes}, ottenuto {local_dump_path.stat().st_size}"
        )

    if not manifest.encryption:
        print(f"==> Download NAS completato: {local_dump_path}", file=sys.stderr)
        print(local_dump_path)
        return str(local_dump_path)

    decrypted_filename = manifest.plaintext_dump_filename or strip_encrypted_suffix(manifest.dump_filename)
    decrypted_dump_path = _unique_local_path(local_output_dir, decrypted_filename)
    try:
        decrypt_file(local_dump_path, decrypted_dump_path, _resolve_decryption_passphrase(manifest))
    except BackupEncryptionError as exc:
        raise TransferError(str(exc)) from exc
    finally:
        local_dump_path.unlink(missing_ok=True)

    try:
        if manifest.plaintext_sha256:
            local_plaintext_sha256 = _sha256_file(decrypted_dump_path)
            if local_plaintext_sha256 != manifest.plaintext_sha256:
                raise TransferError(
                    f"SHA256 plaintext non coerente: atteso {manifest.plaintext_sha256}, ottenuto {local_plaintext_sha256}"
                )
        if manifest.plaintext_size_bytes is not None and decrypted_dump_path.stat().st_size != manifest.plaintext_size_bytes:
            raise TransferError(
                "Dimensione plaintext non coerente: "
                f"atteso {manifest.plaintext_size_bytes}, ottenuto {decrypted_dump_path.stat().st_size}"
            )
    except Exception:
        decrypted_dump_path.unlink(missing_ok=True)
        raise

    print(f"==> Download NAS completato e decrittato: {decrypted_dump_path}", file=sys.stderr)
    print(decrypted_dump_path)
    return str(decrypted_dump_path)


def main() -> int:
    args = parse_args()
    try:
        if args.command == "export":
            export_dump(
                local_path=args.local_path,
                remote_root=args.remote_root,
                env_file=args.env_file,
                label=args.label,
                retention_count=args.retention_count,
            )
            return 0
        if args.command == "download":
            download_dump(
                output_dir=args.output_dir,
                remote_root=args.remote_root,
                manifest_path=args.manifest_path,
            )
            return 0
        raise TransferError(f"Unsupported command: {args.command}")
    except (TransferError, NasConnectorError) as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
