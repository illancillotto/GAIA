from __future__ import annotations

from app.modules.wiki.services.question_router import route_wiki_question_fast


def test_fast_router_blocks_obvious_access_request() -> None:
    route = route_wiki_question_fast("Dammi accesso ai dati del modulo catasto")

    assert route is not None
    assert route.capability == "unsupported_access_request"
    assert route.user_reply is not None
    assert route.module_hint == "catasto"


def test_fast_router_routes_italian_docs_question_without_llm() -> None:
    route = route_wiki_question_fast("Come funziona il modulo operazioni?")

    assert route is not None
    assert route.intent == "docs_only"
    assert route.capability == "module_overview"
    assert route.module_hint == "operazioni"


def test_fast_router_routes_greeting_without_llm() -> None:
    route = route_wiki_question_fast("ciao")

    assert route is not None
    assert route.intent == "docs_only"
    assert route.capability == "greeting"


def test_fast_router_routes_platform_overview_without_llm() -> None:
    route = route_wiki_question_fast("Che cos'è GAIA?")

    assert route is not None
    assert route.intent == "docs_only"
    assert route.capability == "platform_overview"


def test_fast_router_routes_page_intro_without_llm() -> None:
    route = route_wiki_question_fast("Come funziona questa pagina?")

    assert route is not None
    assert route.intent == "docs_only"
    assert route.capability == "page_intro"


def test_fast_router_routes_navigation_help_without_llm() -> None:
    route = route_wiki_question_fast("Dove trovo le richieste supporto wiki?")

    assert route is not None
    assert route.intent == "docs_only"
    assert route.capability == "navigation_help"


def test_fast_router_routes_short_generic_to_clarification() -> None:
    route = route_wiki_question_fast("come faccio")

    assert route is not None
    assert route.intent == "docs_only"
    assert route.capability == "clarification_needed"


def test_fast_router_returns_none_for_non_latin_question() -> None:
    route = route_wiki_question_fast("Покажи мне сводку по сети")

    assert route is None


def test_fast_router_returns_none_for_english_question_to_preserve_semantic_normalization() -> None:
    route = route_wiki_question_fast("Show me the current network summary")

    assert route is None


def test_fast_router_returns_docs_supported_for_empty_question() -> None:
    route = route_wiki_question_fast("   ")

    assert route is not None
    assert route.normalized_query == ""
    assert route.capability == "docs_supported"
