from __future__ import annotations

import sys
import types
import urllib.error
from unittest.mock import Mock, patch

import pytest

from app.modules.wiki.services import openai_client


def test_is_wiki_available_uses_authorization_header(monkeypatch) -> None:
    monkeypatch.setattr(openai_client.settings, "codex_lb_url", "http://wiki-proxy.local/v1")
    monkeypatch.setattr(openai_client.settings, "codex_lb_api_key", "test-api-key")

    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)

    with patch("app.modules.wiki.services.openai_client.urllib.request.urlopen", return_value=response) as mocked_urlopen:
        assert openai_client.is_wiki_available() is True

    request = mocked_urlopen.call_args.args[0]
    assert request.full_url == "http://wiki-proxy.local/v1/models"
    assert request.get_header("Authorization") == "Bearer test-api-key"


def test_is_wiki_provider_degraded_error_detects_no_accounts_message() -> None:
    exc = RuntimeError(
        "Error code: 503 - {'error': {'message': 'No available accounts. Service is operating in degraded mode: all upstream accounts are unavailable', 'code': 'no_accounts'}}"
    )

    assert openai_client.is_wiki_provider_degraded_error(exc) is True


def test_is_wiki_provider_degraded_error_ignores_other_errors() -> None:
    exc = RuntimeError("Error code: 503 - temporary upstream timeout")

    assert openai_client.is_wiki_provider_degraded_error(exc) is False


def test_get_openai_client_caches_client(monkeypatch) -> None:
    monkeypatch.setattr(openai_client.settings, "codex_lb_url", "http://wiki-proxy.local/v1")
    monkeypatch.setattr(openai_client.settings, "codex_lb_api_key", "test-api-key")
    openai_client._client = None

    created_clients: list[object] = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            created_clients.append(kwargs)

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    client_one = openai_client.get_openai_client()
    client_two = openai_client.get_openai_client()

    assert client_one is client_two
    assert created_clients == [{"base_url": "http://wiki-proxy.local/v1", "api_key": "test-api-key"}]
    openai_client._client = None


def test_is_wiki_available_treats_4xx_as_reachable(monkeypatch) -> None:
    monkeypatch.setattr(openai_client.settings, "codex_lb_url", "http://wiki-proxy.local/v1")
    monkeypatch.setattr(openai_client.settings, "codex_lb_api_key", "test-api-key")

    request = urllib.request.Request("http://wiki-proxy.local/v1/models")
    error = urllib.error.HTTPError(request.full_url, 401, "Unauthorized", hdrs=None, fp=None)

    with patch("app.modules.wiki.services.openai_client.urllib.request.urlopen", side_effect=error):
        assert openai_client.is_wiki_available() is True


def test_is_wiki_available_returns_false_on_5xx(monkeypatch) -> None:
    monkeypatch.setattr(openai_client.settings, "codex_lb_url", "http://wiki-proxy.local/v1")
    monkeypatch.setattr(openai_client.settings, "codex_lb_api_key", "test-api-key")

    request = urllib.request.Request("http://wiki-proxy.local/v1/models")
    error = urllib.error.HTTPError(request.full_url, 503, "Unavailable", hdrs=None, fp=None)

    with patch("app.modules.wiki.services.openai_client.urllib.request.urlopen", side_effect=error):
        assert openai_client.is_wiki_available() is False


def test_is_wiki_available_returns_false_on_generic_exception(monkeypatch) -> None:
    monkeypatch.setattr(openai_client.settings, "codex_lb_url", "http://wiki-proxy.local/v1")
    monkeypatch.setattr(openai_client.settings, "codex_lb_api_key", "test-api-key")

    with patch("app.modules.wiki.services.openai_client.urllib.request.urlopen", side_effect=OSError("boom")):
        assert openai_client.is_wiki_available() is False


def test_is_wiki_provider_degraded_error_uses_response_status_code() -> None:
    exc = RuntimeError("Proxy says no available accounts")
    exc.response = types.SimpleNamespace(status_code=503)

    assert openai_client.is_wiki_provider_degraded_error(exc) is True
