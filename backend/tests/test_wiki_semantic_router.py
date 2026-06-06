from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.modules.wiki.services.semantic_router import route_wiki_question


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
