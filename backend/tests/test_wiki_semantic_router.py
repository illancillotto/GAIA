from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.modules.wiki.services.semantic_router import _extract_json, route_wiki_question


def test_extract_json_handles_empty_and_invalid_payloads() -> None:
    assert _extract_json("") is None
    assert _extract_json("   ") is None
    assert _extract_json("not-json") is None
    assert _extract_json("prefix {invalid} suffix") is None


def test_extract_json_extracts_embedded_json_block() -> None:
    payload = 'noise before {"language":"it","intent":"docs_only"} trailing'
    parsed = _extract_json(payload)
    assert parsed == {"language": "it", "intent": "docs_only"}


def test_route_wiki_question_returns_none_when_wiki_unavailable() -> None:
    with patch("app.modules.wiki.services.semantic_router.is_wiki_available", return_value=False):
        assert route_wiki_question("ciao") is None


def test_route_wiki_question_returns_none_when_client_raises() -> None:
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("boom")

    with (
        patch("app.modules.wiki.services.semantic_router.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.semantic_router.get_openai_client", return_value=client),
    ):
        assert route_wiki_question("ciao") is None


def test_route_wiki_question_returns_none_on_non_json_completion() -> None:
    completion = MagicMock()
    completion.choices[0].message.content = "plain text only"
    client = MagicMock()
    client.chat.completions.create.return_value = completion

    with (
        patch("app.modules.wiki.services.semantic_router.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.semantic_router.get_openai_client", return_value=client),
    ):
        assert route_wiki_question("ciao") is None


def test_route_wiki_question_parses_json_payload() -> None:
    completion = MagicMock()
    completion.choices[0].message.content = """
    {
      "language": "fr",
      "normalized_query": "come funziona il modulo wiki",
      "intent": "docs_only",
      "capability": "docs_supported",
      "module_hint": "wiki",
      "user_reply": null
    }
    """
    client = MagicMock()
    client.chat.completions.create.return_value = completion

    with (
        patch("app.modules.wiki.services.semantic_router.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.semantic_router.get_openai_client", return_value=client),
    ):
        route = route_wiki_question("Comment fonctionne le module wiki ?")

    assert route is not None
    assert route.language == "fr"
    assert route.normalized_query == "come funziona il modulo wiki"
    assert route.intent == "docs_only"
    assert route.capability == "docs_supported"
    assert route.module_hint == "wiki"


def test_route_wiki_question_normalizes_invalid_fields_to_safe_defaults() -> None:
    completion = MagicMock()
    completion.choices[0].message.content = """
    {
      "language": "EN",
      "normalized_query": "",
      "intent": "unsupported_value",
      "capability": "unknown_capability",
      "module_hint": "unknown_module",
      "user_reply": " "
    }
    """
    client = MagicMock()
    client.chat.completions.create.return_value = completion

    with (
        patch("app.modules.wiki.services.semantic_router.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.semantic_router.get_openai_client", return_value=client),
    ):
        route = route_wiki_question("Show me something")

    assert route is not None
    assert route.language == "en"
    assert route.normalized_query == "Show me something"
    assert route.intent == "docs_only"
    assert route.capability == "out_of_scope"
    assert route.module_hint is None
    assert route.user_reply is None
    assert route.is_blocking is True


def test_route_wiki_question_handles_blocking_response() -> None:
    completion = MagicMock()
    completion.choices[0].message.content = """
    {
      "language": "ru",
      "normalized_query": "dammi accesso alla cartella progetti",
      "intent": "docs_only",
      "capability": "unsupported_access_request",
      "module_hint": "accessi",
      "user_reply": "Я не могу выдавать доступ к ресурсам из этого чата."
    }
    """
    client = MagicMock()
    client.chat.completions.create.return_value = completion

    with (
        patch("app.modules.wiki.services.semantic_router.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.semantic_router.get_openai_client", return_value=client),
    ):
        route = route_wiki_question("Дай мне доступ к папке проектов")

    assert route is not None
    assert route.is_blocking is True
    assert route.user_reply is not None


def test_route_wiki_question_normalizes_network_module_hint_to_rete() -> None:
    completion = MagicMock()
    completion.choices[0].message.content = """
    {
      "language": "en",
      "normalized_query": "mostrami il riepilogo rete",
      "intent": "live_data",
      "capability": "internal_live_data",
      "module_hint": "network",
      "user_reply": null
    }
    """
    client = MagicMock()
    client.chat.completions.create.return_value = completion

    with (
        patch("app.modules.wiki.services.semantic_router.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.semantic_router.get_openai_client", return_value=client),
    ):
        route = route_wiki_question("Show me the network summary")

    assert route is not None
    assert route.module_hint == "rete"


def test_route_wiki_question_accepts_embedded_json_and_missing_optional_fields() -> None:
    completion = MagicMock()
    completion.choices[0].message.content = """
    Here is the routing result:
    {
      "language": "it",
      "normalized_query": "spiegami il workflow accessi",
      "intent": "logic",
      "capability": "internal_explanation",
      "module_hint": "accessi"
    }
    """
    client = MagicMock()
    client.chat.completions.create.return_value = completion

    with (
        patch("app.modules.wiki.services.semantic_router.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.semantic_router.get_openai_client", return_value=client),
    ):
        route = route_wiki_question("Spiegami il workflow accessi")

    assert route is not None
    assert route.intent == "logic"
    assert route.capability == "internal_explanation"
    assert route.module_hint == "accessi"
    assert route.user_reply is None
