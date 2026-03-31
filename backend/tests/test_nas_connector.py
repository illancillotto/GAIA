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
