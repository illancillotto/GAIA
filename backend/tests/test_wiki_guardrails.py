from __future__ import annotations

import pytest

from app.modules.wiki.schemas import WikiChatResponse, WikiChunkSource
from app.modules.wiki.services.guardrails import (
    build_module_overview_answer,
    build_clarification_answer,
    build_navigation_help_answer,
    build_page_intro_answer,
    build_platform_overview_answer,
    build_short_greeting_answer,
    build_page_capability_hint,
    build_widget_preflight_response,
    describe_page_scope,
    extract_requested_module,
    has_platform_scope,
    is_brief_platform_request,
    is_greeting_message,
    is_navigation_help_request,
    is_page_intro_request,
    is_platform_overview_request,
    is_short_generic_request,
    is_widget_context,
    postflight_docs_guardrail,
    preflight_capability_guardrail,
)


def test_preflight_guardrail_blocks_external_live_questions() -> None:
    decision = preflight_capability_guardrail("Dimmi le news di oggi")

    assert decision is not None
    assert decision.fallback_reason == "unsupported_external_live"
    assert "fonti esterne" in decision.answer


def test_preflight_guardrail_blocks_action_requests() -> None:
    decision = preflight_capability_guardrail("Aggiorna il record e chiudi la pratica")

    assert decision is not None
    assert decision.fallback_reason == "unsupported_action_request"
    assert "non eseguire azioni" in decision.answer


def test_preflight_guardrail_blocks_access_requests() -> None:
    decision = preflight_capability_guardrail("Dammi accesso alla cartella progetti")

    assert decision is not None
    assert decision.fallback_reason == "unsupported_access_request"
    assert "accessi a risorse" in decision.answer


def test_preflight_guardrail_blocks_access_requests_in_english() -> None:
    decision = preflight_capability_guardrail("Give me access to the projects folder")

    assert decision is not None
    assert decision.fallback_reason == "unsupported_access_request"


def test_widget_context_detects_non_wiki_pages() -> None:
    assert is_widget_context("/operazioni/pratiche") is True
    assert is_widget_context("/wiki") is False
    assert is_widget_context("   ") is False


def test_greeting_and_generic_detectors_cover_widget_cases() -> None:
    assert is_greeting_message("ciao") is True
    assert is_short_generic_request("come faccio") is True
    assert is_brief_platform_request("gaia") is True
    assert is_page_intro_request("cosa posso fare qui?") is True
    assert is_platform_overview_request("Che cos'è GAIA?") is True
    assert is_navigation_help_request("Dove trovo le richieste supporto wiki?") is True


def test_build_page_intro_answer_is_contextual() -> None:
    answer = build_page_intro_answer("operazioni", "/operazioni/pratiche")

    assert "Pratiche Operazioni" in answer
    assert "funzionalita operative" in answer


def test_describe_page_scope_falls_back_to_page_segment_and_section() -> None:
    assert describe_page_scope(None, "/pagina-generica") == "In questa pagina Pagina Generica"
    assert describe_page_scope("catasto", None) == "In questo modulo Catasto"
    assert describe_page_scope(None, "/") == "In questa pagina"
    assert describe_page_scope(None, None) == "In questa sezione"


def test_build_short_greeting_answer_is_contextual() -> None:
    answer = build_short_greeting_answer("utenze", "/utenze/visure-routing-anomalies")

    assert "dimmi pure cosa ti serve" in answer.lower()
    assert "Anomalie visure Utenze" in answer


def test_build_platform_overview_answer_stays_operational() -> None:
    answer = build_platform_overview_answer("accessi", "/nas-control/shares")

    assert "piattaforma interna" in answer
    assert "Cartelle condivise NAS Control" in answer


def test_build_module_overview_answer_falls_back_to_page_intro_without_module_hint() -> None:
    answer = build_module_overview_answer(None, "/pagina-generica")

    assert "In questa pagina Pagina Generica" in answer


def test_build_navigation_help_answer_falls_back_to_generic_navigation() -> None:
    answer = build_navigation_help_answer("Dove trovo questa funzione?", module_key="catasto", page_path="/catasto/particelle")

    assert "orientarti meglio nella navigazione" in answer


def test_build_navigation_help_answer_points_to_wiki_support() -> None:
    answer = build_navigation_help_answer("Dove trovo le richieste supporto wiki?")

    assert "/wiki/support" in answer


def test_build_clarification_answer_guides_the_user() -> None:
    answer = build_clarification_answer("catasto", "/catasto/letture-contatori")

    assert "indica il modulo" in answer
    assert "Contatori irrigui" in answer


def test_widget_preflight_returns_page_intro_for_first_greeting() -> None:
    decision = build_widget_preflight_response(
        "ciao",
        module_key="operazioni",
        page_path="/operazioni/pratiche",
        has_active_conversation=False,
    )

    assert decision is not None
    assert decision.tool_name == "page_intro"
    assert "Pratiche Operazioni" in decision.answer


def test_widget_preflight_returns_short_greeting_for_existing_conversation() -> None:
    decision = build_widget_preflight_response(
        "ciao",
        module_key="operazioni",
        page_path="/operazioni/pratiche",
        has_active_conversation=True,
    )

    assert decision is not None
    assert decision.tool_name == "greeting"
    assert "dimmi pure cosa ti serve" in decision.answer.lower()


def test_widget_preflight_returns_module_overview() -> None:
    decision = build_widget_preflight_response(
        "Come funziona il modulo accessi?",
        module_key="wiki",
        page_path="/nas-control/shares",
        has_active_conversation=False,
    )

    assert decision is not None
    assert decision.tool_name == "module_overview"
    assert "modulo Accessi" in decision.answer


def test_widget_preflight_returns_navigation_help() -> None:
    decision = build_widget_preflight_response(
        "Dove trovo le richieste supporto wiki?",
        module_key="wiki",
        page_path="/operazioni/pratiche",
        has_active_conversation=False,
    )

    assert decision is not None
    assert decision.tool_name == "navigation_help"
    assert "/wiki/support" in decision.answer


def test_widget_preflight_returns_platform_overview() -> None:
    decision = build_widget_preflight_response(
        "Che cos'è GAIA?",
        module_key="accessi",
        page_path="/nas-control/shares",
        has_active_conversation=False,
    )

    assert decision is not None
    assert decision.tool_name == "platform_overview"
    assert "piattaforma interna" in decision.answer


def test_widget_preflight_returns_clarification_for_platform_scoped_generic_request() -> None:
    decision = build_widget_preflight_response(
        "gaia",
        module_key="catasto",
        page_path="/catasto/particelle",
        has_active_conversation=True,
    )

    assert decision is not None
    assert decision.tool_name == "clarification_needed"
    assert "indica il modulo" in decision.answer


def test_widget_preflight_returns_none_for_specific_non_generic_request() -> None:
    decision = build_widget_preflight_response(
        "Elenca le particelle associate al fascicolo 123",
        module_key="catasto",
        page_path="/catasto/particelle",
        has_active_conversation=True,
    )

    assert decision is None


def test_postflight_guardrail_returns_none_with_context_article_or_empty_tokens() -> None:
    response = WikiChatResponse(
        answer="Risposta",
        sources=[WikiChunkSource(source_file="docs/wiki.md", section_title="Intro", excerpt="wiki gaia")],
        found=True,
    )

    assert postflight_docs_guardrail(question="ciao", response=response, context_article="docs/wiki.md") is None
    assert postflight_docs_guardrail(question="...", response=response) is None


def test_postflight_guardrail_rejects_out_of_scope_docs_answer() -> None:
    response = WikiChatResponse(
        answer="Ti parlo del milestone interno della wiki.",
        sources=[
            WikiChunkSource(
                source_file="docs/wiki-progress.md",
                section_title="Milestone 9",
                excerpt="Backend e frontend wiki risultano implementati.",
            )
        ],
        found=True,
    )

    decision = postflight_docs_guardrail(question="Dimmi le news di oggi", response=response)

    assert decision is not None
    assert decision.fallback_reason == "question_out_of_scope"


def test_postflight_guardrail_keeps_platform_scoped_docs_answer() -> None:
    response = WikiChatResponse(
        answer="Il modulo wiki espone la chat documentale.",
        sources=[
            WikiChunkSource(
                source_file="docs/wiki.md",
                section_title="Modulo Wiki",
                excerpt="La documentazione wiki descrive chat, articoli e richieste.",
            )
        ],
        found=True,
    )

    decision = postflight_docs_guardrail(question="Che cosa fa il modulo wiki?", response=response)

    assert decision is None


def test_postflight_guardrail_rejects_wrong_module_docs_answer() -> None:
    response = WikiChatResponse(
        answer="Il modulo wiki espone la chat documentale.",
        sources=[
            WikiChunkSource(
                source_file="docs/wiki.md",
                section_title="Modulo Wiki",
                excerpt="La documentazione wiki descrive chat, articoli e richieste.",
            )
        ],
        found=True,
    )

    decision = postflight_docs_guardrail(question="Come funziona il modulo accessi?", response=response)

    assert decision is not None
    assert decision.fallback_reason == "module_docs_missing"
    assert "modulo" in decision.answer.lower() or "sezione" in decision.answer.lower()


def test_postflight_guardrail_not_found_describes_current_page_capabilities() -> None:
    response = WikiChatResponse(
        answer="",
        sources=[],
        found=False,
    )

    decision = postflight_docs_guardrail(question="Domanda generica", response=response)

    assert decision is not None
    assert decision.fallback_reason == "docs_insufficient_context"
    assert "pagina" in decision.answer.lower() or "sezione" in decision.answer.lower()
    assert "per esempio:" in decision.answer.lower()


def test_build_page_capability_hint_uses_module_examples() -> None:
    hint = build_page_capability_hint("inaz", "/inaz/organigramma")

    assert "In questa pagina Organigramma Inaz" in hint
    assert "come leggere l'organigramma corrente" in hint
    assert "responsabili, diretti e sotto-alberi" in hint


def test_describe_page_scope_prefers_known_page_label() -> None:
    assert describe_page_scope("inaz", "/inaz/organigramma") == "In questa pagina Organigramma Inaz"


def test_build_page_capability_hint_prefers_known_page_over_module() -> None:
    hint = build_page_capability_hint("operazioni", "/operazioni/pratiche")

    assert "In questa pagina Pratiche Operazioni" in hint
    assert "come leggere una pratica" in hint
    assert "stati e campi" in hint


def test_has_platform_scope_detects_gaia_questions() -> None:
    assert has_platform_scope("Che cosa fa il modulo wiki?") is True
    assert has_platform_scope("Dimmi le news di oggi") is False
    assert has_platform_scope("What does the wiki module do?") is True


def test_extract_requested_module_reads_known_modules() -> None:
    assert extract_requested_module("Come funziona il modulo accessi?") == "accessi"
    assert extract_requested_module("What does the wiki module do?") == "wiki"


def test_describe_page_scope_uses_module_label_when_page_is_generic() -> None:
    assert describe_page_scope("inaz", "/inaz") == "In questa pagina Inaz"


def test_describe_page_scope_supports_organigramma_root_page() -> None:
    assert describe_page_scope("organigramma", "/organigramma") == "In questa pagina Organigramma"

@pytest.mark.parametrize(
    ("module_key", "page_path", "expected_scope", "expected_snippet"),
    [
        ("accessi", "/nas-control/shares", "In questa pagina Cartelle condivise NAS Control", "quali utenti o gruppi hanno accesso"),
        ("rete", "/network/devices", "In questa pagina Dispositivi Rete", "come leggere un dispositivo di rete"),
        ("catasto", "/catasto/particelle", "In questa pagina Particelle Catasto", "quali dati catastali sono più rilevanti"),
        ("utenze", "/utenze/visure-routing-anomalies", "In questa pagina Anomalie visure Utenze", "instradamento della visura"),
        ("riordino", "/riordino/pratiche", "In questa pagina Pratiche Riordino", "timeline e passaggi successivi"),
        ("ruolo", "/ruolo/avvisi", "In questa pagina Avvisi Ruolo", "contesto tributario"),
        ("elaborazioni", "/elaborazioni/batches", "In questa pagina Batch elaborazioni", "quali stati aiutano a capire l'avanzamento"),
        ("inventario", "/inventory", "In questa pagina Inventario", "scheda bene o asset"),
    ],
)
def test_page_hint_supports_registered_routes(
    module_key: str,
    page_path: str,
    expected_scope: str,
    expected_snippet: str,
) -> None:
    hint = build_page_capability_hint(module_key, page_path)

    assert expected_scope in hint
    assert expected_snippet in hint
