from pathlib import Path

import pytest

from app.services.nas_connector import NasConnectorError, NasSSHClient, get_sync_capabilities


def test_get_sync_capabilities_reflects_password_auth(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nas_connector.settings.nas_host", "nas.example.local")
    monkeypatch.setattr("app.services.nas_connector.settings.nas_username", "svc_sync")
    monkeypatch.setattr("app.services.nas_connector.settings.nas_password", "secret")
    monkeypatch.setattr("app.services.nas_connector.settings.nas_private_key_path", None)

    capabilities = get_sync_capabilities()

    assert capabilities.ssh_configured is True
    assert capabilities.supports_live_sync is True
    assert capabilities.auth_mode == "password"
    assert capabilities.retry_strategy == "fixed"
    assert capabilities.retry_jitter_enabled is False
    assert capabilities.retry_jitter_ratio == 0.2


def test_get_sync_capabilities_reflects_private_key_auth(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nas_connector.settings.nas_host", "nas.example.local")
    monkeypatch.setattr("app.services.nas_connector.settings.nas_username", "svc_sync")
    monkeypatch.setattr("app.services.nas_connector.settings.nas_password", "")
    monkeypatch.setattr("app.services.nas_connector.settings.nas_private_key_path", "/keys/nas.pem")

    capabilities = get_sync_capabilities()

    assert capabilities.ssh_configured is True
    assert capabilities.supports_live_sync is True
    assert capabilities.auth_mode == "private_key"


def test_get_sync_capabilities_reflects_missing_auth(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nas_connector.settings.nas_host", "nas.example.local")
    monkeypatch.setattr("app.services.nas_connector.settings.nas_username", "svc_sync")
    monkeypatch.setattr("app.services.nas_connector.settings.nas_password", "")
    monkeypatch.setattr("app.services.nas_connector.settings.nas_private_key_path", None)

    capabilities = get_sync_capabilities()

    assert capabilities.supports_live_sync is False


def test_get_nas_client_uses_settings(monkeypatch) -> None:
    monkeypatch.setattr("app.services.nas_connector.settings.nas_host", "nas.example.local")
    monkeypatch.setattr("app.services.nas_connector.settings.nas_port", 2200)
    monkeypatch.setattr("app.services.nas_connector.settings.nas_username", "svc_sync")
    monkeypatch.setattr("app.services.nas_connector.settings.nas_password", "secret")
    monkeypatch.setattr("app.services.nas_connector.settings.nas_private_key_path", "/keys/nas.pem")
    monkeypatch.setattr("app.services.nas_connector.settings.nas_timeout", 8)

    from app.services.nas_connector import get_nas_client

    client = get_nas_client()

    assert client.host == "nas.example.local"
    assert client.port == 2200
    assert client.username == "svc_sync"
    assert client.password == "secret"
    assert client.private_key_path == "/keys/nas.pem"
    assert client.timeout == 8


def test_run_command_raises_when_paramiko_missing(monkeypatch) -> None:
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "paramiko":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    client = NasSSHClient(
        host="nas.example.local",
        port=22,
        username="svc_sync",
        timeout=5,
        password="secret",
    )

    try:
        client.run_command("getent passwd")
    except NasConnectorError as exc:
        assert "Paramiko is not installed" in str(exc)
    else:
        raise AssertionError("Expected NasConnectorError when paramiko is missing")


def test_get_client_reuses_existing_client_without_transport() -> None:
    sentinel = object()
    client = NasSSHClient(host="nas.example.local", port=22, username="svc_sync", timeout=5, password="secret")
    client._client = sentinel

    assert client._get_client() is sentinel


def test_get_client_reconnects_when_transport_is_inactive(monkeypatch) -> None:
    closed = False

    class ExistingClient:
        def get_transport(self):
            class Transport:
                @staticmethod
                def is_active() -> bool:
                    return False

            return Transport()

        def close(self) -> None:
            nonlocal closed
            closed = True

    connect_kwargs_seen: dict[str, object] = {}

    class FakeConnectedClient:
        def set_missing_host_key_policy(self, policy) -> None:
            return None

        def connect(self, **kwargs) -> None:
            connect_kwargs_seen.update(kwargs)

    class FakeParamiko:
        class SSHClient(FakeConnectedClient):
            pass

        @staticmethod
        def AutoAddPolicy():
            return object()

    monkeypatch.setitem(__import__("sys").modules, "paramiko", FakeParamiko)

    client = NasSSHClient(host="nas.example.local", port=22, username="svc_sync", timeout=5, password="secret")
    client._client = ExistingClient()

    connected = client._get_client()

    assert closed is True
    assert isinstance(connected, FakeConnectedClient)
    assert connect_kwargs_seen["password"] == "secret"


def test_get_client_uses_private_key_and_wraps_connect_errors(monkeypatch) -> None:
    class FailingClient:
        def set_missing_host_key_policy(self, policy) -> None:
            return None

        def connect(self, **kwargs) -> None:
            raise RuntimeError("connect boom")

    class FakeParamiko:
        class SSHClient(FailingClient):
            pass

        @staticmethod
        def AutoAddPolicy():
            return object()

    monkeypatch.setitem(__import__("sys").modules, "paramiko", FakeParamiko)

    client = NasSSHClient(
        host="nas.example.local",
        port=22,
        username="svc_sync",
        timeout=5,
        private_key_path="/keys/nas.pem",
    )

    with pytest.raises(NasConnectorError):
        client._get_client()


def test_download_file_falls_back_to_shell_when_sftp_fails() -> None:
    class FakeChannel:
        def recv_exit_status(self) -> int:
            return 0

    class FakeStream:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload
            self.channel = FakeChannel()

        def read(self) -> bytes:
            return self._payload

    class FailingSFTP:
        def file(self, path: str, mode: str):
            raise OSError("sftp disabled")

        def close(self) -> None:
            return None

    class FakeClient:
        def open_sftp(self) -> FailingSFTP:
            return FailingSFTP()

        def exec_command(self, command: str, timeout: int):
            assert command == "cat '/volume1/test file.pdf'"
            return (None, FakeStream(b"%PDF-1.4 shell fallback"), FakeStream(b""))

    client = NasSSHClient(
        host="nas.example.local",
        port=22,
        username="svc_sync",
        timeout=5,
        password="secret",
    )
    client._client = FakeClient()

    payload = client.download_file("/volume1/test file.pdf")

    assert payload == b"%PDF-1.4 shell fallback"


def test_download_file_uses_sftp_when_available() -> None:
    class RemoteFile:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return b"sftp-payload"

    class FakeSFTP:
        def file(self, path: str, mode: str):
            assert path == "/volume1/ok.pdf"
            assert mode == "rb"
            return RemoteFile()

        def close(self) -> None:
            return None

    class FakeClient:
        def open_sftp(self) -> FakeSFTP:
            return FakeSFTP()

    client = NasSSHClient(host="nas.example.local", port=22, username="svc_sync", timeout=5, password="secret")
    client._client = FakeClient()

    assert client.download_file("/volume1/ok.pdf") == b"sftp-payload"


def test_download_file_raises_when_fallback_fails() -> None:
    class FailingSFTP:
        def file(self, path: str, mode: str):
            raise OSError("sftp disabled")

        def close(self) -> None:
            return None

    class FakeClient:
        def open_sftp(self) -> FailingSFTP:
            return FailingSFTP()

        def exec_command(self, command: str, timeout: int):
            raise RuntimeError("shell failed")

    client = NasSSHClient(host="nas.example.local", port=22, username="svc_sync", timeout=5, password="secret")
    client._client = FakeClient()

    with pytest.raises(NasConnectorError):
        client.download_file("/volume1/missing.pdf")


def test_upload_file_falls_back_to_shell_when_sftp_fails() -> None:
    class FakeTransport:
        def __init__(self) -> None:
            self.commands: list[str] = []
            self.payload = b""

        def is_active(self) -> bool:
            return True

        def open_session(self):
            transport = self

            class FakeChannel:
                def exec_command(self, command: str) -> None:
                    transport.commands.append(command)

                def sendall(self, content: bytes) -> None:
                    transport.payload += content

                def shutdown_write(self) -> None:
                    return None

                def recv_exit_status(self) -> int:
                    return 0

                def makefile_stderr(self, mode: str):
                    class FakeFile:
                        def read(self) -> bytes:
                            return b""

                    return FakeFile()

                def close(self) -> None:
                    return None

            return FakeChannel()

    class FailingSFTP:
        def file(self, path: str, mode: str):
            raise OSError("sftp upload disabled")

        def close(self) -> None:
            return None

    class FakeClient:
        def __init__(self) -> None:
            self.transport = FakeTransport()
            self.mkdir_commands: list[str] = []

        def open_sftp(self) -> FailingSFTP:
            return FailingSFTP()

        def exec_command(self, command: str, timeout: int):
            self.mkdir_commands.append(command)

            class FakeChannel:
                def recv_exit_status(self) -> int:
                    return 0

            class FakeStream:
                def __init__(self) -> None:
                    self.channel = FakeChannel()

                def read(self):
                    return b""

            return (None, FakeStream(), FakeStream())

        def get_transport(self) -> FakeTransport:
            return self.transport

    client = NasSSHClient(
        host="nas.example.local",
        port=22,
        username="svc_sync",
        timeout=5,
        password="secret",
    )
    fake_client = FakeClient()
    client._client = fake_client

    client.upload_file("/volume1/test folder/manuale.pdf", b"hello nas")

    assert fake_client.mkdir_commands == ["mkdir -p '/volume1/test folder'"]
    assert fake_client.transport.commands == ["cat > '/volume1/test folder/manuale.pdf'"]
    assert fake_client.transport.payload == b"hello nas"


def test_upload_file_uses_sftp_when_available() -> None:
    captured: dict[str, object] = {}

    class RemoteFile:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def write(self, payload: bytes) -> None:
            captured["payload"] = payload

        def flush(self) -> None:
            captured["flushed"] = True

    class FakeSFTP:
        def file(self, path: str, mode: str):
            captured["path"] = path
            captured["mode"] = mode
            return RemoteFile()

        def close(self) -> None:
            return None

    class FakeClient:
        def exec_command(self, command: str, timeout: int):
            class FakeChannel:
                def recv_exit_status(self) -> int:
                    return 0

            class FakeStream:
                def __init__(self) -> None:
                    self.channel = FakeChannel()

                def read(self):
                    return b""

            return (None, FakeStream(), FakeStream())

        def open_sftp(self) -> FakeSFTP:
            return FakeSFTP()

    client = NasSSHClient(host="nas.example.local", port=22, username="svc_sync", timeout=5, password="secret")
    client._client = FakeClient()

    client.upload_file("/volume1/test/manuale.pdf", b"hello")

    assert captured == {
        "path": "/volume1/test/manuale.pdf",
        "mode": "wb",
        "payload": b"hello",
        "flushed": True,
    }


def test_upload_file_raises_when_fallback_fails() -> None:
    class FailingSFTP:
        def file(self, path: str, mode: str):
            raise OSError("sftp disabled")

        def close(self) -> None:
            return None

    class FakeClient:
        def exec_command(self, command: str, timeout: int):
            class FakeChannel:
                def recv_exit_status(self) -> int:
                    return 0

            class FakeStream:
                def __init__(self) -> None:
                    self.channel = FakeChannel()

                def read(self):
                    return b""

            return (None, FakeStream(), FakeStream())

        def open_sftp(self) -> FailingSFTP:
            return FailingSFTP()

        def get_transport(self):
            class Transport:
                @staticmethod
                def is_active() -> bool:
                    return True

            return Transport()

        def close(self) -> None:
            return None

    client = NasSSHClient(host="nas.example.local", port=22, username="svc_sync", timeout=5, password="secret")
    client._client = FakeClient()

    with pytest.raises(NasConnectorError):
        client.upload_file("/volume1/test/manuale.pdf", b"hello")


def test_list_files_uses_find_command() -> None:
    class FakeChannel:
        def recv_exit_status(self) -> int:
            return 0

    class FakeStream:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload
            self.channel = FakeChannel()

        def read(self) -> bytes:
            return self._payload

    class FakeClient:
        def exec_command(self, command: str, timeout: int):
            assert command == "find '/volume1/pubblica condivisa/GAIA/Visure' -mindepth 1 -maxdepth 1 -type f -print"
            payload = b"/volume1/pubblica condivisa/GAIA/Visure/a.pdf\n/volume1/pubblica condivisa/GAIA/Visure/b.pdf\n"
            return (None, FakeStream(payload), FakeStream(b""))

    client = NasSSHClient(
        host="nas.example.local",
        port=22,
        username="svc_sync",
        timeout=5,
        password="secret",
    )
    client._client = FakeClient()

    files = client.list_files("/volume1/pubblica condivisa/GAIA/Visure")

    assert files == [
        "/volume1/pubblica condivisa/GAIA/Visure/a.pdf",
        "/volume1/pubblica condivisa/GAIA/Visure/b.pdf",
    ]


def test_run_command_wraps_nonzero_exit_and_exec_failures() -> None:
    class FakeChannel:
        def __init__(self, status: int) -> None:
            self._status = status

        def recv_exit_status(self) -> int:
            return self._status

    class FakeStream:
        def __init__(self, payload: bytes, status: int = 0) -> None:
            self._payload = payload
            self.channel = FakeChannel(status)

        def read(self):
            return self._payload

    class ErrorClient:
        def exec_command(self, command: str, timeout: int):
            return (None, FakeStream(b"", status=1), FakeStream(b"permission denied"))

    client = NasSSHClient(host="nas.example.local", port=22, username="svc_sync", timeout=5, password="secret")
    client._client = ErrorClient()

    with pytest.raises(NasConnectorError):
        client.run_command("ls")

    class ExplodingClient:
        def exec_command(self, command: str, timeout: int):
            raise RuntimeError("boom")

    client._client = ExplodingClient()
    with pytest.raises(NasConnectorError):
        client.run_command("ls")


def test_ensure_directory_path_exists_and_close() -> None:
    commands: list[str] = []

    class FakeChannel:
        def recv_exit_status(self) -> int:
            return 0

    class FakeStream:
        def __init__(self) -> None:
            self.channel = FakeChannel()

        def read(self):
            return b"1"

    class FakeClient:
        def exec_command(self, command: str, timeout: int):
            commands.append(command)
            return (None, FakeStream(), FakeStream())

        def close(self) -> None:
            commands.append("closed")

    client = NasSSHClient(host="nas.example.local", port=22, username="svc_sync", timeout=5, password="secret")
    client._client = FakeClient()

    client.ensure_directory("/volume1/shared")
    assert client.path_exists("/volume1/shared") is True
    client.close()
    assert commands == [
        "mkdir -p /volume1/shared",
        "if [ -e /volume1/shared ]; then printf '1'; else printf '0'; fi",
        "closed",
    ]
    assert client._client is None


def test_path_exists_false_and_upload_local_file_missing(tmp_path) -> None:
    class FakeChannel:
        def recv_exit_status(self) -> int:
            return 0

    class FakeStream:
        def __init__(self) -> None:
            self.channel = FakeChannel()

        def read(self):
            return b"0"

    class FakeClient:
        def exec_command(self, command: str, timeout: int):
            return (None, FakeStream(), FakeStream())

    client = NasSSHClient(host="nas.example.local", port=22, username="svc_sync", timeout=5, password="secret")
    client._client = FakeClient()

    assert client.path_exists("/missing") is False
    with pytest.raises(NasConnectorError):
        client.upload_local_file(str(tmp_path / "missing.dump"), "/volume1/backups/gaia.dump")


def test_move_file_creates_parent_and_renames() -> None:
    class FakeChannel:
        def recv_exit_status(self) -> int:
            return 0

    class FakeStream:
        def __init__(self) -> None:
            self.channel = FakeChannel()

        def read(self):
            return b""

    class FakeClient:
        def __init__(self) -> None:
            self.commands: list[str] = []

        def exec_command(self, command: str, timeout: int):
            self.commands.append(command)
            return (None, FakeStream(), FakeStream())

    client = NasSSHClient(
        host="nas.example.local",
        port=22,
        username="svc_sync",
        timeout=5,
        password="secret",
    )
    fake_client = FakeClient()
    client._client = fake_client

    client.move_file(
        "/volume1/pubblica condivisa/GAIA/Visure/source.pdf",
        "/volume1/Settore Catasto/ARCHIVIO/R/ROSSI_MARIO_RSSMRA80A01H501U/visure/source.pdf",
    )

    assert fake_client.commands == [
        "mkdir -p '/volume1/Settore Catasto/ARCHIVIO/R/ROSSI_MARIO_RSSMRA80A01H501U/visure'",
        "mv '/volume1/pubblica condivisa/GAIA/Visure/source.pdf' '/volume1/Settore Catasto/ARCHIVIO/R/ROSSI_MARIO_RSSMRA80A01H501U/visure/source.pdf'",
    ]


def test_download_to_local_falls_back_to_shell_when_sftp_fails(tmp_path) -> None:
    class FakeChannel:
        def recv_exit_status(self) -> int:
            return 0

    class FakeStream:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload
            self.channel = FakeChannel()

        def read(self, size: int = -1) -> bytes:
            if size < 0:
                data = self._payload
                self._payload = b""
                return data
            data = self._payload[:size]
            self._payload = self._payload[size:]
            return data

    class FailingSFTP:
        def get(self, remote_path: str, local_path: str) -> None:
            raise OSError("sftp disabled")

        def close(self) -> None:
            return None

    class FakeClient:
        def open_sftp(self) -> FailingSFTP:
            return FailingSFTP()

        def exec_command(self, command: str, timeout: int):
            assert command == "cat /volume1/backups/gaia.dump"
            return (None, FakeStream(b"dump-payload"), FakeStream(b""))

    client = NasSSHClient(
        host="nas.example.local",
        port=22,
        username="svc_sync",
        timeout=5,
        password="secret",
    )
    client._client = FakeClient()

    destination = tmp_path / "gaia.dump"
    client.download_to_local("/volume1/backups/gaia.dump", str(destination))

    assert destination.read_bytes() == b"dump-payload"


def test_download_to_local_uses_sftp_when_available(tmp_path) -> None:
    destination = tmp_path / "gaia.dump"

    class FakeSFTP:
        def get(self, remote_path: str, local_path: str) -> None:
            Path(local_path).write_bytes(b"sftp-dump")

        def close(self) -> None:
            return None

    class FakeClient:
        def open_sftp(self) -> FakeSFTP:
            return FakeSFTP()

    client = NasSSHClient(host="nas.example.local", port=22, username="svc_sync", timeout=5, password="secret")
    client._client = FakeClient()

    client.download_to_local("/volume1/backups/gaia.dump", str(destination))

    assert destination.read_bytes() == b"sftp-dump"


def test_download_to_local_raises_when_fallback_fails(tmp_path) -> None:
    destination = tmp_path / "gaia.dump"

    class FailingSFTP:
        def get(self, remote_path: str, local_path: str) -> None:
            raise OSError("sftp disabled")

        def close(self) -> None:
            return None

    class FakeClient:
        def open_sftp(self) -> FailingSFTP:
            return FailingSFTP()

        def exec_command(self, command: str, timeout: int):
            raise RuntimeError("shell broken")

    client = NasSSHClient(host="nas.example.local", port=22, username="svc_sync", timeout=5, password="secret")
    client._client = FakeClient()

    with pytest.raises(NasConnectorError):
        client.download_to_local("/volume1/backups/gaia.dump", str(destination))


def test_upload_local_file_falls_back_to_shell_when_sftp_fails(tmp_path) -> None:
    source = tmp_path / "gaia.dump"
    source.write_bytes(b"chunk-1chunk-2")

    class FakeTransport:
        def __init__(self) -> None:
            self.commands: list[str] = []
            self.payload = b""

        def is_active(self) -> bool:
            return True

        def open_session(self):
            transport = self

            class FakeChannel:
                def exec_command(self, command: str) -> None:
                    transport.commands.append(command)

                def sendall(self, content: bytes) -> None:
                    transport.payload += content

                def shutdown_write(self) -> None:
                    return None

                def recv_exit_status(self) -> int:
                    return 0

                def makefile_stderr(self, mode: str):
                    class FakeFile:
                        def read(self) -> bytes:
                            return b""

                    return FakeFile()

                def close(self) -> None:
                    return None

            return FakeChannel()

    class FailingSFTP:
        def put(self, local_path: str, remote_path: str) -> None:
            raise OSError("sftp upload disabled")

        def close(self) -> None:
            return None

    class FakeClient:
        def __init__(self) -> None:
            self.transport = FakeTransport()
            self.mkdir_commands: list[str] = []

        def open_sftp(self) -> FailingSFTP:
            return FailingSFTP()

        def exec_command(self, command: str, timeout: int):
            self.mkdir_commands.append(command)

            class FakeChannel:
                def recv_exit_status(self) -> int:
                    return 0

            class FakeStream:
                def __init__(self) -> None:
                    self.channel = FakeChannel()

                def read(self):
                    return b""

            return (None, FakeStream(), FakeStream())

        def get_transport(self) -> FakeTransport:
            return self.transport

    client = NasSSHClient(
        host="nas.example.local",
        port=22,
        username="svc_sync",
        timeout=5,
        password="secret",
    )
    fake_client = FakeClient()
    client._client = fake_client

    client.upload_local_file(str(source), "/volume1/backups/gaia.dump")

    assert fake_client.mkdir_commands == ["mkdir -p /volume1/backups"]
    assert fake_client.transport.commands == ["cat > /volume1/backups/gaia.dump"]
    assert fake_client.transport.payload == b"chunk-1chunk-2"


def test_upload_local_file_uses_sftp_when_available(tmp_path) -> None:
    source = tmp_path / "gaia.dump"
    source.write_bytes(b"dump-data")
    seen: dict[str, str] = {}

    class FakeSFTP:
        def put(self, local_path: str, remote_path: str) -> None:
            seen["local"] = local_path
            seen["remote"] = remote_path

        def close(self) -> None:
            return None

    class FakeClient:
        def exec_command(self, command: str, timeout: int):
            class FakeChannel:
                def recv_exit_status(self) -> int:
                    return 0

            class FakeStream:
                def __init__(self) -> None:
                    self.channel = FakeChannel()

                def read(self):
                    return b""

            return (None, FakeStream(), FakeStream())

        def open_sftp(self) -> FakeSFTP:
            return FakeSFTP()

    client = NasSSHClient(host="nas.example.local", port=22, username="svc_sync", timeout=5, password="secret")
    client._client = FakeClient()

    client.upload_local_file(str(source), "/volume1/backups/gaia.dump")

    assert seen == {"local": str(source), "remote": "/volume1/backups/gaia.dump"}


def test_upload_local_file_raises_when_fallback_fails(tmp_path) -> None:
    source = tmp_path / "gaia.dump"
    source.write_bytes(b"dump-data")

    class FailingSFTP:
        def put(self, local_path: str, remote_path: str) -> None:
            raise OSError("sftp upload disabled")

        def close(self) -> None:
            return None

    class FakeClient:
        def exec_command(self, command: str, timeout: int):
            class FakeChannel:
                def recv_exit_status(self) -> int:
                    return 0

            class FakeStream:
                def __init__(self) -> None:
                    self.channel = FakeChannel()

                def read(self):
                    return b""

            return (None, FakeStream(), FakeStream())

        def open_sftp(self) -> FailingSFTP:
            return FailingSFTP()

        def get_transport(self):
            class Transport:
                @staticmethod
                def is_active() -> bool:
                    return True

            return Transport()

        def close(self) -> None:
            return None

    client = NasSSHClient(host="nas.example.local", port=22, username="svc_sync", timeout=5, password="secret")
    client._client = FakeClient()

    with pytest.raises(NasConnectorError):
        client.upload_local_file(str(source), "/volume1/backups/gaia.dump")


def test_shell_helpers_raise_on_errors(tmp_path) -> None:
    class FakeChannel:
        def __init__(self, status: int) -> None:
            self._status = status

        def recv_exit_status(self) -> int:
            return self._status

        def exec_command(self, command: str) -> None:
            return None

        def sendall(self, content: bytes) -> None:
            return None

        def shutdown_write(self) -> None:
            return None

        def makefile_stderr(self, mode: str):
            class FakeFile:
                def read(self) -> bytes:
                    return b"stderr"

            return FakeFile()

        def close(self) -> None:
            return None

    class FakeStream:
        def __init__(self, payload: bytes, status: int) -> None:
            self._payload = payload
            self.channel = FakeChannel(status)

        def read(self, size: int = -1):
            if size == -1:
                return self._payload
            chunk = self._payload[:size]
            self._payload = self._payload[size:]
            return chunk

    class FakeTransport:
        def __init__(self, active: bool, status: int) -> None:
            self._active = active
            self._status = status

        def is_active(self) -> bool:
            return self._active

        def open_session(self):
            return FakeChannel(self._status)

    class FakeClient:
        def __init__(self, status: int) -> None:
            self.status = status

        def exec_command(self, command: str, timeout: int):
            return (None, FakeStream(b"payload", self.status), FakeStream(b"stderr", self.status))

        def get_transport(self):
            return FakeTransport(active=False, status=self.status)

    client = NasSSHClient(host="nas.example.local", port=22, username="svc_sync", timeout=5, password="secret")

    with pytest.raises(NasConnectorError):
        client._download_file_via_shell(FakeClient(status=1), "/volume1/a.pdf")

    with pytest.raises(NasConnectorError):
        client._download_to_local_via_shell(FakeClient(status=1), "/volume1/a.pdf", tmp_path / "a.pdf")

    with pytest.raises(NasConnectorError):
        client._upload_file_via_shell(FakeClient(status=0), "/volume1/a.pdf", b"payload")

    with pytest.raises(NasConnectorError):
        client._upload_local_file_via_shell(FakeClient(status=0), tmp_path / "missing.pdf", "/volume1/a.pdf")


def test_shell_upload_helpers_raise_on_nonzero_exit_and_close_is_noop_with_no_client(tmp_path) -> None:
    source = tmp_path / "gaia.dump"
    source.write_bytes(b"payload")

    class FakeChannel:
        def __init__(self, status: int) -> None:
            self._status = status

        def exec_command(self, command: str) -> None:
            return None

        def sendall(self, content: bytes) -> None:
            return None

        def shutdown_write(self) -> None:
            return None

        def recv_exit_status(self) -> int:
            return self._status

        def makefile_stderr(self, mode: str):
            class FakeFile:
                def read(self) -> bytes:
                    return b"stderr"

            return FakeFile()

        def close(self) -> None:
            return None

    class FakeTransport:
        @staticmethod
        def is_active() -> bool:
            return True

        def open_session(self):
            return FakeChannel(status=1)

    class FakeClient:
        def get_transport(self):
            return FakeTransport()

    client = NasSSHClient(host="nas.example.local", port=22, username="svc_sync", timeout=5, password="secret")

    with pytest.raises(NasConnectorError):
        client._upload_file_via_shell(FakeClient(), "/volume1/a.pdf", b"payload")

    with pytest.raises(NasConnectorError):
        client._upload_local_file_via_shell(FakeClient(), source, "/volume1/a.pdf")

    client.close()
