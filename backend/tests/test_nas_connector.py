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
