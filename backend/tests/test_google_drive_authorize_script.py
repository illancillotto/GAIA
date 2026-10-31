from __future__ import annotations

import importlib.util
import runpy
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "google_drive_authorize.py"


def load_script():
    spec = importlib.util.spec_from_file_location("google_drive_authorize", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script(monkeypatch):
    module = load_script()
    monkeypatch.setattr(module.settings, "google_drive_client_id", "drive-id")
    monkeypatch.setattr(module.settings, "google_drive_client_secret", "drive-secret")
    return module


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_authorization_url_requests_offline_drive_scope(script):
    query = parse_qs(urlparse(script.authorization_url("drive-id")).query)
    assert query["scope"] == [script.DRIVE_SCOPE]
    assert query["access_type"] == ["offline"] and query["prompt"] == ["consent"]
    assert query["redirect_uri"] == ["http://localhost"]


def test_client_credentials_fallback_and_missing(script, monkeypatch):
    assert script.client_credentials() == ("drive-id", "drive-secret")
    for name in (
        "google_drive_client_id",
        "google_drive_client_secret",
        "google_oauth_client_id",
        "google_oauth_client_secret",
    ):
        monkeypatch.setattr(script.settings, name, "")
    with pytest.raises(SystemExit, match="Configurare"):
        script.client_credentials()


def test_code_from_redirect(script):
    assert script.code_from_redirect(" http://localhost/?code=4%2Fabc&scope=x ") == "4/abc"
    with pytest.raises(SystemExit, match="Nessun parametro code"):
        script.code_from_redirect("http://localhost/?error=access_denied")


def test_exchange_code_requires_refresh_token(script):
    sent = {}

    def post(url, data, timeout):
        sent.update(data)
        return FakeResponse({"refresh_token": "rt"})

    assert script.exchange_code("id", "secret", "code", post) == "rt"
    assert sent["grant_type"] == "authorization_code" and sent["code"] == "code"
    with pytest.raises(SystemExit, match="refresh token"):
        script.exchange_code("id", "secret", "code", lambda url, data, timeout: FakeResponse({}))


def test_main_prints_refresh_token(script, capsys):
    result = script.main(
        read_line=lambda prompt: "http://localhost/?code=c1",
        post=lambda url, data, timeout: FakeResponse({"refresh_token": "rt-1"}),
    )
    assert result == 0
    assert "GOOGLE_DRIVE_REFRESH_TOKEN=rt-1" in capsys.readouterr().out


def test_script_entrypoint_exits_with_main_result(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "http://localhost/?code=c1")
    monkeypatch.setattr(
        "httpx.post", lambda url, data, timeout: FakeResponse({"refresh_token": "rt"})
    )
    monkeypatch.setattr("app.core.config.settings.google_drive_client_id", "id")
    monkeypatch.setattr("app.core.config.settings.google_drive_client_secret", "secret")
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(SCRIPT_PATH), run_name="__main__")
    assert excinfo.value.code == 0
