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
