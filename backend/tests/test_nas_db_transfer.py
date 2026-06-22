from __future__ import annotations

from argparse import Namespace
from datetime import UTC, datetime
import json
from pathlib import Path
import runpy

import pytest

from app.scripts import nas_db_transfer
from app.scripts.nas_db_transfer import (
    BackupManifest,
    TransferError,
    _acquire_lock,
    _build_backup_id,
    _build_remote_paths,
    _dump_format_from_path,
    _env_int,
    _load_manifest_from_bytes,
    _normalize_remote_root,
    _prune_remote_backups,
    _read_env_value,
    _release_lock,
    _remote_sha256_command,
    _resolve_manifest_path,
    _sanitize_label,
    _unique_local_path,
    download_dump,
    export_dump,
    main,
    parse_args,
)
from app.services.nas_connector import NasConnectorError


def test_parse_args_export(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "nas_db_transfer.py",
            "export",
            "--local-path",
            "/tmp/gaia.dump",
            "--remote-root",
            "/volume1/Backups/GAIA/db",
            "--env-file",
            ".env.test",
            "--label",
            "manuale",
            "--retention-count",
            "5",
        ],
    )

    args = parse_args()

    assert args == Namespace(
        command="export",
        local_path="/tmp/gaia.dump",
        remote_root="/volume1/Backups/GAIA/db",
        env_file=".env.test",
        label="manuale",
        retention_count=5,
    )


def test_parse_args_download(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "nas_db_transfer.py",
            "download",
            "--output-dir",
            "/tmp/downloads",
            "--manifest-path",
            "/volume1/Backups/GAIA/db/latest.json",
        ],
    )

    args = parse_args()

    assert args.command == "download"
    assert args.output_dir == "/tmp/downloads"
    assert args.manifest_path == "/volume1/Backups/GAIA/db/latest.json"


def test_env_int_uses_default_and_validates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NAS_DB_BACKUP_RETENTION_COUNT", raising=False)
    assert _env_int("NAS_DB_BACKUP_RETENTION_COUNT", 14) == 14

    monkeypatch.setenv("NAS_DB_BACKUP_RETENTION_COUNT", "7")
    assert _env_int("NAS_DB_BACKUP_RETENTION_COUNT", 14) == 7

    monkeypatch.setenv("NAS_DB_BACKUP_RETENTION_COUNT", "bad")
    with pytest.raises(TransferError):
        _env_int("NAS_DB_BACKUP_RETENTION_COUNT", 14)


def test_read_env_value_uses_file_when_present(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OTHER_KEY=x\nPOSTGRES_DB=gaia\nPOSTGRES_DB=naap\n", encoding="utf-8")

    assert _read_env_value(str(env_path), "POSTGRES_DB", "fallback") == "naap"
    assert _read_env_value(str(tmp_path / "missing.env"), "POSTGRES_DB", "fallback") == "fallback"


def test_sanitize_label_replaces_unsafe_characters() -> None:
    assert _sanitize_label(" pre push / manuale : 01 ") == "pre-push-manuale-01"


def test_dump_format_and_backup_id() -> None:
    timestamp = datetime(2026, 6, 19, 10, 11, 12, tzinfo=UTC)
    assert _build_backup_id(timestamp, "manuale") == "gaia-20260619-101112-manuale"
    assert _build_backup_id(timestamp, "") == "gaia-20260619-101112"
    assert _dump_format_from_path(Path("/tmp/gaia.dump")) == "custom"
    assert _dump_format_from_path(Path("/tmp/gaia.sql")) == "plain"
    with pytest.raises(TransferError):
        _dump_format_from_path(Path("/tmp/gaia.txt"))


def test_normalize_remote_root_rejects_empty_string() -> None:
    with pytest.raises(TransferError):
        _normalize_remote_root("   ")


def test_build_remote_paths_keeps_archives_staging_and_latest_separate() -> None:
    timestamp = datetime(2026, 6, 19, 10, 11, 12, tzinfo=UTC)
    paths = _build_remote_paths("/volume1/Backups/GAIA/db", "gaia-20260619-101112", "gaia.dump", timestamp)

    assert paths["archive_dir"] == "/volume1/Backups/GAIA/db/archives/2026/06"
    assert paths["staging_dump_path"] == "/volume1/Backups/GAIA/db/.staging/gaia-20260619-101112/gaia.dump"
    assert paths["manifest_path"] == "/volume1/Backups/GAIA/db/archives/2026/06/gaia.dump.manifest.json"
    assert paths["latest_path"] == "/volume1/Backups/GAIA/db/latest.json"


def test_remote_sha256_command_contains_supported_tools() -> None:
    command = _remote_sha256_command("/volume1/Backups/GAIA/db/gaia.dump")
    assert "sha256sum" in command
    assert "shasum -a 256" in command
    assert "openssl dgst -sha256" in command


def test_acquire_lock_writes_owner_and_release_lock_ignores_failure() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.commands: list[str] = []
            self.uploads: list[tuple[str, bytes]] = []

        def run_command(self, command: str) -> str:
            self.commands.append(command)
            return ""

        def upload_file(self, path: str, payload: bytes) -> None:
            self.uploads.append((path, payload))

    client = FakeClient()
    _acquire_lock(client, "/locks/db-transfer.lock")
    assert client.commands == ["mkdir /locks/db-transfer.lock"]
    assert client.uploads[0][0] == "/locks/db-transfer.lock/owner.json"

    class FailingReleaseClient:
        def run_command(self, command: str) -> str:
            raise NasConnectorError("cannot release")

    _release_lock(FailingReleaseClient(), "/locks/db-transfer.lock")


def test_acquire_lock_cleanup_runs_when_owner_upload_fails() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.commands: list[str] = []

        def run_command(self, command: str) -> str:
            self.commands.append(command)
            return ""

        def upload_file(self, path: str, payload: bytes) -> None:
            raise RuntimeError("upload failed")

    client = FakeClient()
    with pytest.raises(RuntimeError):
        _acquire_lock(client, "/locks/db-transfer.lock")

    assert client.commands == ["mkdir /locks/db-transfer.lock", "rm -rf /locks/db-transfer.lock"]


def test_acquire_lock_translates_existing_remote_lock() -> None:
    class FakeClient:
        def run_command(self, command: str) -> str:
            raise NasConnectorError("exists")

        def upload_file(self, path: str, payload: bytes) -> None:
            raise AssertionError("should not upload")

    with pytest.raises(TransferError):
        _acquire_lock(FakeClient(), "/locks/db-transfer.lock")


def test_prune_remote_backups_noop_and_script() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.commands: list[str] = []

        def run_command(self, command: str) -> str:
            self.commands.append(command)
            return ""

    client = FakeClient()
    _prune_remote_backups(client, "/volume1/Backups/GAIA/db/archives", 0)
    assert client.commands == []

    _prune_remote_backups(client, "/volume1/Backups/GAIA/db/archives", 5)
    assert "gaia-*.manifest.json" in client.commands[0]


def test_load_manifest_from_bytes_validates_required_fields_and_json() -> None:
    with pytest.raises(TransferError):
        _load_manifest_from_bytes(b"not-json", "memory")

    payload = b'{"backup_id":"gaia-20260619-101112"}'
    with pytest.raises(TransferError):
        _load_manifest_from_bytes(payload, "memory")


def test_load_manifest_from_bytes_returns_manifest() -> None:
    manifest = BackupManifest(
        version=1,
        backup_id="gaia-20260619-101112",
        project="GAIA",
        created_at="2026-06-19T10:11:12Z",
        created_by_host="gaia-dev",
        env_file=".env",
        db_name="gaia",
        db_user="gaia_app",
        dump_filename="gaia-20260619-101112.dump",
        dump_format="custom",
        sha256="abc123",
        size_bytes=1234,
        label="manuale",
        remote_root="/volume1/Backups/GAIA/db",
        remote_dump_path="/volume1/Backups/GAIA/db/archives/2026/06/gaia-20260619-101112.dump",
        remote_manifest_path="/volume1/Backups/GAIA/db/archives/2026/06/gaia-20260619-101112.dump.manifest.json",
    )

    loaded = _load_manifest_from_bytes(json.dumps(manifest.__dict__).encode("utf-8"), "memory")

    assert loaded == manifest


def test_export_dump_handles_success_checksum_mismatch_and_missing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timestamp = datetime(2026, 6, 19, 10, 11, 12, tzinfo=UTC)
    monkeypatch.setattr(nas_db_transfer, "_now_utc", lambda: timestamp)
    monkeypatch.setattr("app.scripts.nas_db_transfer.socket.gethostname", lambda: "gaia-host")

    dump_path = tmp_path / "gaia.dump"
    dump_path.write_bytes(b"gaia-backup")
    sha = nas_db_transfer._sha256_file(dump_path)

    class FakeClient:
        def __init__(self, remote_sha: str) -> None:
            self.remote_sha = remote_sha
            self.ensure_dirs: list[str] = []
            self.upload_local_calls: list[tuple[str, str]] = []
            self.upload_calls: list[str] = []
            self.move_calls: list[tuple[str, str]] = []
            self.commands: list[str] = []
            self.closed = False

        def ensure_directory(self, path: str) -> None:
            self.ensure_dirs.append(path)

        def upload_local_file(self, local_path: str, remote_path: str) -> None:
            self.upload_local_calls.append((local_path, remote_path))

        def upload_file(self, path: str, content: bytes) -> None:
            self.upload_calls.append(path)

        def move_file(self, source_path: str, destination_path: str) -> None:
            self.move_calls.append((source_path, destination_path))

        def run_command(self, command: str) -> str:
            self.commands.append(command)
            if command.startswith("mkdir "):
                return ""
            if "sha256sum" in command:
                return self.remote_sha
            if command.startswith("rm -rf "):
                return ""
            return ""

        def close(self) -> None:
            self.closed = True

    success_client = FakeClient(remote_sha=sha)
    monkeypatch.setattr("app.scripts.nas_db_transfer.get_nas_client", lambda: success_client)

    manifest_path = export_dump(str(dump_path), "/volume1/Backups/GAIA/db", ".env", "manuale", 5)

    assert manifest_path.endswith(".manifest.json")
    assert success_client.ensure_dirs == [
        "/volume1/Backups/GAIA/db/.staging/gaia-20260619-101112-manuale",
        "/volume1/Backups/GAIA/db/archives/2026/06",
    ]
    assert success_client.upload_local_calls
    assert success_client.upload_calls[-1].endswith("/latest.json")
    assert success_client.move_calls[-1][1] == "/volume1/Backups/GAIA/db/latest.json"
    assert success_client.closed is True
    assert success_client.commands[-1] == "rm -rf /volume1/Backups/GAIA/db/.locks/db-transfer.lock"

    mismatch_client = FakeClient(remote_sha="wrong")
    monkeypatch.setattr("app.scripts.nas_db_transfer.get_nas_client", lambda: mismatch_client)
    with pytest.raises(TransferError):
        export_dump(str(dump_path), "/volume1/Backups/GAIA/db", ".env", "manuale", 5)
    assert mismatch_client.closed is True

    with pytest.raises(TransferError):
        export_dump(str(tmp_path / "missing.dump"), "/volume1/Backups/GAIA/db", ".env", "manuale", 5)


def test_export_dump_uses_db_name_and_user_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dump_path = tmp_path / "gaia.dump"
    dump_path.write_bytes(b"gaia")
    monkeypatch.setattr(nas_db_transfer, "_now_utc", lambda: datetime(2026, 6, 19, 10, 11, 12, tzinfo=UTC))
    monkeypatch.setattr("app.scripts.nas_db_transfer.socket.gethostname", lambda: "gaia-host")

    class FakeClient:
        def ensure_directory(self, path: str) -> None:
            return None

        def upload_local_file(self, local_path: str, remote_path: str) -> None:
            return None

        def upload_file(self, path: str, content: bytes) -> None:
            self.content = content

        def move_file(self, source_path: str, destination_path: str) -> None:
            return None

        def run_command(self, command: str) -> str:
            if "sha256sum" in command:
                return nas_db_transfer._sha256_file(dump_path)
            return ""

        def close(self) -> None:
            return None

    client = FakeClient()
    monkeypatch.setattr("app.scripts.nas_db_transfer.get_nas_client", lambda: client)
    export_dump(
        str(dump_path),
        "/volume1/Backups/GAIA/db",
        ".env",
        "manuale",
        5,
        db_name="override_db",
        db_user="override_user",
    )
    payload = json.loads(client.content.decode("utf-8"))
    assert payload["db_name"] == "override_db"
    assert payload["db_user"] == "override_user"


def test_export_dump_persists_encryption_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dump_path = tmp_path / "gaia.dump.enc"
    dump_path.write_bytes(b"encrypted-payload")
    monkeypatch.setattr(nas_db_transfer, "_now_utc", lambda: datetime(2026, 6, 19, 10, 11, 12, tzinfo=UTC))
    monkeypatch.setattr("app.scripts.nas_db_transfer.socket.gethostname", lambda: "gaia-host")

    class FakeClient:
        def ensure_directory(self, path: str) -> None:
            return None

        def upload_local_file(self, local_path: str, remote_path: str) -> None:
            return None

        def upload_file(self, path: str, content: bytes) -> None:
            if path.endswith(".manifest.json") or path.endswith("/latest.json"):
                self.content = content

        def move_file(self, source_path: str, destination_path: str) -> None:
            return None

        def run_command(self, command: str) -> str:
            if "sha256sum" in command:
                return nas_db_transfer._sha256_file(dump_path)
            return ""

        def close(self) -> None:
            return None

    client = FakeClient()
    monkeypatch.setattr("app.scripts.nas_db_transfer.get_nas_client", lambda: client)
    export_dump(
        str(dump_path),
        "/volume1/Backups/GAIA/db",
        ".env",
        "manuale",
        5,
        encryption={"scheme": "aes-256-ctr+hmac-sha256", "kdf": "scrypt"},
        plaintext_dump_filename="gaia.dump",
        plaintext_dump_format="custom",
        plaintext_sha256="plain-sha",
        plaintext_size_bytes=42,
    )
    payload = json.loads(client.content.decode("utf-8"))
    assert payload["encryption"] == {"scheme": "aes-256-ctr+hmac-sha256", "kdf": "scrypt"}
    assert payload["plaintext_dump_filename"] == "gaia.dump"
    assert payload["plaintext_sha256"] == "plain-sha"
    assert payload["plaintext_size_bytes"] == 42


def test_resolve_manifest_and_unique_local_path(tmp_path: Path) -> None:
    class FakeClient:
        def __init__(self, exists: bool) -> None:
            self.exists = exists

        def path_exists(self, path: str) -> bool:
            return self.exists

    assert _resolve_manifest_path(FakeClient(True), "/volume1/Backups/GAIA/db", "") == "/volume1/Backups/GAIA/db/latest.json"
    assert _resolve_manifest_path(FakeClient(False), "/volume1/Backups/GAIA/db", "/other/manifest.json") == "/other/manifest.json"
    with pytest.raises(TransferError):
        _resolve_manifest_path(FakeClient(False), "/volume1/Backups/GAIA/db", "")

    candidate = tmp_path / "gaia.dump"
    assert _unique_local_path(tmp_path, "gaia.dump") == candidate
    candidate.write_bytes(b"existing")
    assert _unique_local_path(tmp_path, "gaia.dump") != candidate


def test_download_dump_success_and_validation_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = BackupManifest(
        version=1,
        backup_id="gaia-20260619-101112",
        project="GAIA",
        created_at="2026-06-19T10:11:12Z",
        created_by_host="gaia-dev",
        env_file=".env",
        db_name="gaia",
        db_user="gaia_app",
        dump_filename="gaia.dump",
        dump_format="custom",
        sha256="",
        size_bytes=4,
        label="manuale",
        remote_root="/volume1/Backups/GAIA/db",
        remote_dump_path="/volume1/Backups/GAIA/db/archives/2026/06/gaia.dump",
        remote_manifest_path="/volume1/Backups/GAIA/db/archives/2026/06/gaia.dump.manifest.json",
    )
    local_payload = b"data"
    manifest.sha256 = json.loads(json.dumps({"sha": nas_db_transfer.hashlib.sha256(local_payload).hexdigest()}))["sha"]

    class FakeClient:
        def __init__(self, payload: bytes) -> None:
            self.payload = payload
            self.closed = False

        def path_exists(self, path: str) -> bool:
            return True

        def download_file(self, path: str) -> bytes:
            return json.dumps(manifest.__dict__).encode("utf-8")

        def download_to_local(self, remote_path: str, local_path: str) -> None:
            Path(local_path).write_bytes(self.payload)

        def close(self) -> None:
            self.closed = True

    success_client = FakeClient(local_payload)
    monkeypatch.setattr("app.scripts.nas_db_transfer.get_nas_client", lambda: success_client)
    downloaded = download_dump(str(tmp_path), "/volume1/Backups/GAIA/db", "")
    assert Path(downloaded).read_bytes() == local_payload
    assert success_client.closed is True

    mismatch_client = FakeClient(b"bad!")
    monkeypatch.setattr("app.scripts.nas_db_transfer.get_nas_client", lambda: mismatch_client)
    with pytest.raises(TransferError):
        download_dump(str(tmp_path), "/volume1/Backups/GAIA/db", "")

    wrong_size_manifest = BackupManifest(**{**manifest.__dict__, "size_bytes": 999})

    class WrongSizeClient(FakeClient):
        def download_file(self, path: str) -> bytes:
            return json.dumps(wrong_size_manifest.__dict__).encode("utf-8")

    monkeypatch.setattr("app.scripts.nas_db_transfer.get_nas_client", lambda: WrongSizeClient(local_payload))
    with pytest.raises(TransferError):
        download_dump(str(tmp_path), "/volume1/Backups/GAIA/db", "")


def test_download_dump_decrypts_encrypted_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plaintext_payload = b"plaintext-backup"
    plaintext_source = tmp_path / "gaia.dump"
    encrypted_source = tmp_path / "gaia.dump.enc"
    plaintext_source.write_bytes(plaintext_payload)
    from app.services.backup_encryption import encrypt_file

    encrypt_file(plaintext_source, encrypted_source, "super-secret-passphrase")
    encrypted_payload = encrypted_source.read_bytes()
    manifest = BackupManifest(
        version=1,
        backup_id="gaia-20260619-101112",
        project="GAIA",
        created_at="2026-06-19T10:11:12Z",
        created_by_host="gaia-dev",
        env_file=".env",
        db_name="gaia",
        db_user="gaia_app",
        dump_filename="gaia.dump.enc",
        dump_format="custom",
        sha256=nas_db_transfer.hashlib.sha256(encrypted_payload).hexdigest(),
        size_bytes=len(encrypted_payload),
        label="manuale",
        remote_root="/volume1/Backups/GAIA/db",
        remote_dump_path="/volume1/Backups/GAIA/db/archives/2026/06/gaia.dump.enc",
        remote_manifest_path="/volume1/Backups/GAIA/db/archives/2026/06/gaia.dump.enc.manifest.json",
        encryption={
            "scheme": "aes-256-ctr+hmac-sha256",
            "kdf": "scrypt",
            "passphrase_env_var": "ELABORAZIONI_DB_BACKUP_ENCRYPTION_PASSPHRASE",
        },
        plaintext_dump_filename="gaia.dump",
        plaintext_dump_format="custom",
        plaintext_sha256=nas_db_transfer.hashlib.sha256(plaintext_payload).hexdigest(),
        plaintext_size_bytes=len(plaintext_payload),
    )

    class FakeClient:
        def __init__(self) -> None:
            self.closed = False

        def path_exists(self, path: str) -> bool:
            return True

        def download_file(self, path: str) -> bytes:
            return json.dumps(manifest.__dict__).encode("utf-8")

        def download_to_local(self, remote_path: str, local_path: str) -> None:
            Path(local_path).write_bytes(encrypted_payload)

        def close(self) -> None:
            self.closed = True

    monkeypatch.setenv("ELABORAZIONI_DB_BACKUP_ENCRYPTION_PASSPHRASE", "super-secret-passphrase")
    monkeypatch.setattr("app.scripts.nas_db_transfer.get_nas_client", lambda: FakeClient())

    downloaded = download_dump(str(tmp_path / "downloads"), "/volume1/Backups/GAIA/db", "")

    assert Path(downloaded).name == "gaia.dump"
    assert Path(downloaded).read_bytes() == plaintext_payload
    assert not Path(str(tmp_path / "downloads" / "gaia.dump.enc")).exists()


def test_main_dispatches_export_download_and_errors(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        "app.scripts.nas_db_transfer.parse_args",
        lambda: Namespace(
            command="export",
            local_path="/tmp/gaia.dump",
            remote_root="/volume1/Backups/GAIA/db",
            env_file=".env",
            label="manuale",
            retention_count=5,
        ),
    )
    monkeypatch.setattr("app.scripts.nas_db_transfer.export_dump", lambda **kwargs: "/manifest.json")
    assert main() == 0

    monkeypatch.setattr(
        "app.scripts.nas_db_transfer.parse_args",
        lambda: Namespace(
            command="download",
            output_dir="/tmp/downloads",
            remote_root="/volume1/Backups/GAIA/db",
            manifest_path="/manifest.json",
        ),
    )
    monkeypatch.setattr("app.scripts.nas_db_transfer.download_dump", lambda **kwargs: "/tmp/downloads/gaia.dump")
    assert main() == 0

    monkeypatch.setattr("app.scripts.nas_db_transfer.parse_args", lambda: Namespace(command="weird"))
    assert main() == 1
    assert "Unsupported command: weird" in capsys.readouterr().err

    monkeypatch.setattr(
        "app.scripts.nas_db_transfer.parse_args",
        lambda: Namespace(
            command="export",
            local_path="/tmp/gaia.dump",
            remote_root="/volume1/Backups/GAIA/db",
            env_file=".env",
            label="manuale",
            retention_count=5,
        ),
    )
    monkeypatch.setattr("app.scripts.nas_db_transfer.export_dump", lambda **kwargs: (_ for _ in ()).throw(TransferError("boom")))
    assert main() == 1
    assert "Errore: boom" in capsys.readouterr().err


def test_module_main_entrypoint_executes_under___main__(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dump_path = tmp_path / "gaia.dump"
    dump_path.write_bytes(b"gaia")

    class FakeClient:
        def ensure_directory(self, path: str) -> None:
            return None

        def upload_local_file(self, local_path: str, remote_path: str) -> None:
            return None

        def upload_file(self, path: str, content: bytes) -> None:
            return None

        def move_file(self, source_path: str, destination_path: str) -> None:
            return None

        def run_command(self, command: str) -> str:
            if "sha256sum" in command:
                return nas_db_transfer._sha256_file(dump_path)
            return ""

        def close(self) -> None:
            return None

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "app.services.nas_connector.get_nas_client",
        lambda: FakeClient(),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "nas_db_transfer.py",
            "export",
            "--local-path",
            str(dump_path),
            "--remote-root",
            "/volume1/Backups/GAIA/db",
            "--retention-count",
            "5",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("app.scripts.nas_db_transfer", run_name="__main__")

    assert exc_info.value.code == 0
