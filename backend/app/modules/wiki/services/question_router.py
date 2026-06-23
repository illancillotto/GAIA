from __future__ import annotations

import re

from app.modules.wiki.services.guardrails import (
    extract_requested_module,
    is_greeting_message,
    is_module_overview_request,
    is_navigation_help_request,
    is_page_intro_request,
    is_platform_overview_request,
    is_short_generic_request,
    preflight_capability_guardrail,
)
from app.modules.wiki.services.intent_classifier import classify_intent
from app.modules.wiki.services.semantic_router import WikiSemanticRoute

_NON_LATIN_RE = re.compile(r"[^\u0000-\u024F\s]")
_ENGLISH_HINTS = (
    "what is",
    "what does",
    "how does",
    "show me",
    "find ",
    "details",
    "current status",
)


def route_wiki_question_fast(question: str) -> WikiSemanticRoute | None:
    normalized = question.strip()
    if not normalized:
        return WikiSemanticRoute(
            language="it",
            normalized_query="",
            intent="docs_only",
            capability="docs_supported",
            module_hint=None,
            user_reply=None,
        )

    guardrail_decision = preflight_capability_guardrail(normalized)
    if guardrail_decision is not None:
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability=guardrail_decision.fallback_reason,
            module_hint=extract_requested_module(normalized),
            user_reply=guardrail_decision.answer,
        )

    lower_question = normalized.lower()
    if _NON_LATIN_RE.search(normalized):
        return None
    if any(hint in lower_question for hint in _ENGLISH_HINTS):
        return None

    if is_greeting_message(normalized):
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability="greeting",
            module_hint=extract_requested_module(normalized),
            user_reply=None,
        )

    if is_page_intro_request(normalized):
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability="page_intro",
            module_hint=extract_requested_module(normalized),
            user_reply=None,
        )

    if is_module_overview_request(normalized):
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability="module_overview",
            module_hint=extract_requested_module(normalized),
            user_reply=None,
        )

    if is_platform_overview_request(normalized):
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability="platform_overview",
            module_hint=extract_requested_module(normalized),
            user_reply=None,
        )

    if is_navigation_help_request(normalized):
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability="navigation_help",
            module_hint=extract_requested_module(normalized),
            user_reply=None,
        )

    if is_short_generic_request(normalized):
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability="clarification_needed",
            module_hint=extract_requested_module(normalized),
            user_reply=None,
        )

    intent = classify_intent(normalized)
    module_hint = extract_requested_module(normalized)
    if intent == "docs_only":
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability="docs_supported",
            module_hint=module_hint,
            user_reply=None,
        )
    if module_hint is None:
        return None
    capability = "internal_live_data" if intent == "live_data" else "internal_explanation"
    return WikiSemanticRoute(
        language="it",
        normalized_query=normalized,
        intent=intent,
        capability=capability,
        module_hint=module_hint,
        user_reply=None,
    )
