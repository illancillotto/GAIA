from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.gis import artifact_storage
from app.services.nas_connector import NasConnectorError


class FakeNasClient:
    def __init__(self, *, exists: bool = True, downloaded: bytes | None = None) -> None:
        self.exists = exists
        self.downloaded = downloaded
        self.calls: list[tuple] = []

    def upload_local_file(self, source: str, destination: str) -> None:
        self.calls.append(("upload_local_file", source, destination))

    def move_file(self, source: str, destination: str) -> None:
        self.calls.append(("move_file", source, destination))

    def path_exists(self, path: str) -> bool:
        self.calls.append(("path_exists", path))
        return self.exists

    def run_command(self, command: str) -> str:
        self.calls.append(("run_command", command))
        return ""

    def ensure_directory(self, path: str) -> None:
        self.calls.append(("ensure_directory", path))

    def upload_file(self, path: str, content: bytes) -> None:
        self.calls.append(("upload_file", path, content))
        if self.downloaded is None:
            self.downloaded = content

    def download_file(self, path: str) -> bytes:
        self.calls.append(("download_file", path))
        return self.downloaded or b""

    def close(self) -> None:
        self.calls.append(("close",))


def configure_transport(monkeypatch: pytest.MonkeyPatch, transport: str) -> None:
    monkeypatch.setattr(artifact_storage.settings, "gis_nas_transport", transport)
    monkeypatch.setattr(
        artifact_storage.settings,
        "gis_nas_health_path",
        "/volume1/Backups/GAIA/gis",
    )


def test_publish_and_delete_local_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_transport(monkeypatch, "local")
    source = tmp_path / "source.zip"
    source.write_bytes(b"archive")
    destination = tmp_path / "nested" / "output.zip"

    artifact_storage.publish_artifact(source, str(destination))

    assert destination.read_bytes() == b"archive"
    assert artifact_storage.read_artifact(str(destination)) == b"archive"
    assert artifact_storage.delete_artifact(str(destination)) is True
    assert artifact_storage.delete_artifact(str(destination)) is False


def test_publish_and_delete_sftp_artifacts(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_transport(monkeypatch, "sftp")
    client = FakeNasClient()
    monkeypatch.setattr(artifact_storage, "get_nas_client", lambda: client)
    source = Path("/tmp/source.zip")
    destination = "/volume1/Backups/GAIA/gis/rete/export.zip"

    artifact_storage.publish_artifact(source, destination)
    assert artifact_storage.delete_artifact(destination) is True

    upload = next(call for call in client.calls if call[0] == "upload_local_file")
    move = next(call for call in client.calls if call[0] == "move_file")
    assert upload[1] == str(source)
    assert upload[2].startswith(f"{destination}.")
    assert upload[2].endswith(".tmp")
    assert move == ("move_file", upload[2], destination)
    assert any(call[0] == "run_command" and destination in call[1] for call in client.calls)
    assert client.calls.count(("close",)) == 2


def test_read_sftp_artifact_closes_client(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_transport(monkeypatch, "sftp")
    client = FakeNasClient(downloaded=b"pdf")
    monkeypatch.setattr(artifact_storage, "get_nas_client", lambda: client)
    path = "/volume1/Backups/GAIA/gis/sheet.pdf"
    assert artifact_storage.read_artifact(path) == b"pdf"
    assert client.calls == [("download_file", path), ("close",)]


def test_sftp_delete_returns_false_for_missing_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_transport(monkeypatch, "sftp")
    client = FakeNasClient(exists=False)
    monkeypatch.setattr(artifact_storage, "get_nas_client", lambda: client)

    assert (
        artifact_storage.delete_artifact(
            "/volume1/Backups/GAIA/gis/missing.zip"
        )
        is False
    )
    assert client.calls[-1] == ("close",)


def test_sftp_only_applies_inside_managed_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_transport(monkeypatch, "sftp")
    source = tmp_path / "source.zip"
    source.write_bytes(b"local")
    destination = tmp_path / "outside.zip"

    assert artifact_storage._uses_sftp("/volume1/Backups/GAIA/gis") is True
    assert artifact_storage._uses_sftp(str(destination)) is False
    artifact_storage.publish_artifact(source, str(destination))
    assert destination.read_bytes() == b"local"


def test_probe_local_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    configure_transport(monkeypatch, "")

    available = artifact_storage.probe_artifact_storage(str(tmp_path))
    missing = artifact_storage.probe_artifact_storage(str(tmp_path / "missing"))

    assert available.transport == "local"
    assert available.readable is True
    assert available.writable is True
    assert missing.readable is False
    assert missing.writable is False


def test_probe_sftp_storage_performs_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_transport(monkeypatch, "sftp")
    client = FakeNasClient()
    monkeypatch.setattr(artifact_storage, "get_nas_client", lambda: client)

    probe = artifact_storage.probe_artifact_storage(
        "/volume1/Backups/GAIA/gis"
    )

    assert probe.transport == "sftp"
    assert probe.readable is True
    assert probe.writable is True
    assert client.calls[0] == ("ensure_directory", "/volume1/Backups/GAIA/gis")
    assert client.calls[-1] == ("close",)


def test_sftp_client_is_closed_when_publish_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_transport(monkeypatch, "sftp")
    client = FakeNasClient()

    def fail_upload(source: str, destination: str) -> None:
        raise OSError("upload failed")

    client.upload_local_file = fail_upload  # type: ignore[method-assign]
    monkeypatch.setattr(artifact_storage, "get_nas_client", lambda: client)

    with pytest.raises(OSError, match="upload failed"):
        artifact_storage.publish_artifact(
            Path("/tmp/source.zip"),
            "/volume1/Backups/GAIA/gis/rete/export.zip",
        )
    assert client.calls == [("close",)]


def test_sftp_publish_retries_transient_connector_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_transport(monkeypatch, "sftp")
    failed_client = FakeNasClient()
    successful_client = FakeNasClient()

    def fail_upload(source: str, destination: str) -> None:
        raise NasConnectorError("temporary offline")

    failed_client.upload_local_file = fail_upload  # type: ignore[method-assign]
    clients = iter((failed_client, successful_client))
    delays: list[float] = []
    monkeypatch.setattr(artifact_storage, "get_nas_client", lambda: next(clients))
    monkeypatch.setattr(artifact_storage.time, "sleep", delays.append)

    artifact_storage.publish_artifact(
        Path("/tmp/source.zip"),
        "/volume1/Backups/GAIA/gis/rete/export.zip",
    )

    assert delays == [1.0]
    assert failed_client.calls == [("close",)]
    assert successful_client.calls[-1] == ("close",)


def test_sftp_publish_raises_after_retry_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_transport(monkeypatch, "sftp")
    clients: list[FakeNasClient] = []

    def client_factory() -> FakeNasClient:
        client = FakeNasClient()

        def fail_upload(source: str, destination: str) -> None:
            raise NasConnectorError("still offline")

        client.upload_local_file = fail_upload  # type: ignore[method-assign]
        clients.append(client)
        return client

    delays: list[float] = []
    monkeypatch.setattr(artifact_storage, "get_nas_client", client_factory)
    monkeypatch.setattr(artifact_storage.time, "sleep", delays.append)

    with pytest.raises(NasConnectorError, match="still offline"):
        artifact_storage.publish_artifact(
            Path("/tmp/source.zip"),
            "/volume1/Backups/GAIA/gis/rete/export.zip",
        )

    assert delays == [1.0, 3.0]
    assert len(clients) == 3
    assert all(client.calls == [("close",)] for client in clients)
