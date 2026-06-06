from __future__ import annotations

from app.modules.wiki.schemas import WikiChatResponse, WikiChunkSource
from app.modules.wiki.services.guardrails import (
    extract_requested_module,
    has_platform_scope,
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


def test_has_platform_scope_detects_gaia_questions() -> None:
    assert has_platform_scope("Che cosa fa il modulo wiki?") is True
    assert has_platform_scope("Dimmi le news di oggi") is False
    assert has_platform_scope("What does the wiki module do?") is True


def test_extract_requested_module_reads_known_modules() -> None:
    assert extract_requested_module("Come funziona il modulo accessi?") == "accessi"
    assert extract_requested_module("What does the wiki module do?") == "wiki"
