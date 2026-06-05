from __future__ import annotations

from unittest.mock import Mock, patch

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
