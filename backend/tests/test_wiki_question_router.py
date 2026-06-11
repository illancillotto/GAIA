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
    assert route.capability == "docs_supported"
    assert route.module_hint == "operazioni"


def test_fast_router_returns_none_for_non_latin_question() -> None:
    route = route_wiki_question_fast("Покажи мне сводку по сети")

    assert route is None


def test_fast_router_returns_none_for_english_question_to_preserve_semantic_normalization() -> None:
    route = route_wiki_question_fast("Show me the current network summary")

    assert route is None
