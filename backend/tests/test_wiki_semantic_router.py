from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.modules.wiki.services.semantic_router import (
    WikiSemanticRoute,
    _build_routing_prompt,
    _extract_json,
    route_wiki_question,
)


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
      "task_type": "docs_lookup",
      "extracted_slots": {},
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
    assert route.task_type == "docs_lookup"
    assert route.module_hint == "wiki"
    assert route.extracted_slots == {}


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
    assert route.task_type == "blocked_request"
    assert route.module_hint is None
    assert route.user_reply is None
    assert route.is_blocking is True


def test_semantic_route_marks_new_conversational_capabilities_as_preflight() -> None:
    route = WikiSemanticRoute(
        language="it",
        normalized_query="ciao",
        intent="docs_only",
        capability="greeting",
        module_hint=None,
        user_reply="Ciao",
    )

    assert route.should_preflight_reply is True
    assert route.is_blocking is False


def test_route_wiki_question_returns_none_when_payload_normalization_raises() -> None:
    completion = MagicMock()
    completion.choices[0].message.content = "{}"
    client = MagicMock()
    client.chat.completions.create.return_value = completion

    class BrokenPayload:
        def get(self, *args, **kwargs):
            raise RuntimeError("bad payload")

    with (
        patch("app.modules.wiki.services.semantic_router.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.semantic_router.get_openai_client", return_value=client),
        patch("app.modules.wiki.services.semantic_router._extract_json", return_value=BrokenPayload()),
    ):
        assert route_wiki_question("ciao") is None


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
      "task_type": "entity_lookup",
      "extracted_slots": {"uuid": null},
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
    assert route.task_type == "entity_lookup"


def test_route_wiki_question_accepts_owner_lookup_task_type_and_slots() -> None:
    completion = MagicMock()
    completion.choices[0].message.content = """
    Here is the routing result:
    {
      "language": "it",
      "normalized_query": "trova proprietario terreno comune Oristano foglio 24 particella 191",
      "intent": "live_data",
      "capability": "internal_live_data",
      "module_hint": "catasto",
      "task_type": "owner_lookup",
      "extracted_slots": {
        "comune": "Oristano",
        "foglio": "24",
        "particella": "191",
        "codice_fiscale": null
      }
    }
    """
    client = MagicMock()
    client.chat.completions.create.return_value = completion

    with (
        patch("app.modules.wiki.services.semantic_router.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.semantic_router.get_openai_client", return_value=client),
    ):
        route = route_wiki_question("Trova il proprietario del terreno comune Oristano foglio 24 particella 191")

    assert route is not None
    assert route.intent == "live_data"
    assert route.capability == "internal_live_data"
    assert route.task_type == "owner_lookup"
    assert route.module_hint == "catasto"
    assert route.extracted_slots["comune"] == "Oristano"
    assert route.extracted_slots["foglio"] == "24"
    assert route.extracted_slots["particella"] == "191"


def test_route_wiki_question_accepts_embedded_json_and_missing_optional_fields_for_logic() -> None:
    completion = MagicMock()
    completion.choices[0].message.content = """
    Here is the routing result:
    {
      "language": "it",
      "normalized_query": "spiegami il workflow accessi",
      "intent": "logic",
      "capability": "internal_explanation",
      "module_hint": "accessi",
      "task_type": "workflow_explanation"
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
    assert route.task_type == "workflow_explanation"
    assert route.module_hint == "accessi"
    assert route.user_reply is None


def test_build_routing_prompt_includes_context_and_navigation_catalog() -> None:
    prompt = _build_routing_prompt(
        "dove trovo le particelle?",
        module_key="catasto",
        page_path="/catasto/gis",
    )

    assert "current_module: catasto" in prompt
    assert "current_page_path: /catasto/gis" in prompt
    assert '/catasto/particelle' in prompt
    assert '/ruolo/particelle' in prompt
    assert '"giornaliere" => /inaz/giornaliere' in prompt


def test_route_wiki_question_parses_navigation_resolution_fields() -> None:
    completion = MagicMock()
    completion.choices[0].message.content = """
    {
      "language": "it",
      "normalized_query": "dove trovo le particelle",
      "intent": "docs_only",
      "capability": "navigation_help",
      "module_hint": "catasto",
      "page_path": "/catasto/particelle",
      "confidence": 0.91,
      "disambiguation_needed": false,
      "disambiguation_question": null,
      "task_type": "navigation_help",
      "extracted_slots": {},
      "user_reply": "Trovi la funzione in Particelle Catasto (`/catasto/particelle`)."
    }
    """
    client = MagicMock()
    client.chat.completions.create.return_value = completion

    with (
        patch("app.modules.wiki.services.semantic_router.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.semantic_router.get_openai_client", return_value=client),
    ):
        route = route_wiki_question(
            "dove trovo le particelle?",
            module_key="catasto",
            page_path="/catasto/gis",
        )

    assert route is not None
    assert route.capability == "navigation_help"
    assert route.module_hint == "catasto"
    assert route.resolved_page_path == "/catasto/particelle"
    assert route.confidence == 0.91
    assert route.disambiguation_needed is False
    assert route.disambiguation_question is None
