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
from app.modules.wiki.services.semantic_router import WikiSemanticRoute, extract_task_slots, infer_task_type

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
        task_type = "docs_lookup"
        return WikiSemanticRoute(
            language="it",
            normalized_query="",
            intent="docs_only",
            capability="docs_supported",
            module_hint=None,
            user_reply=None,
            task_type=task_type,
            extracted_slots=extract_task_slots(normalized, task_type),
        )

    guardrail_decision = preflight_capability_guardrail(normalized)
    if guardrail_decision is not None:
        module_hint = extract_requested_module(normalized)
        task_type = infer_task_type(
            question=normalized,
            capability=guardrail_decision.fallback_reason,
            intent="docs_only",
            module_hint=module_hint,
        )
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability=guardrail_decision.fallback_reason,
            module_hint=module_hint,
            user_reply=guardrail_decision.answer,
            task_type=task_type,
            extracted_slots=extract_task_slots(normalized, task_type),
        )

    lower_question = normalized.lower()
    if _NON_LATIN_RE.search(normalized):
        return None
    if any(hint in lower_question for hint in _ENGLISH_HINTS):
        return None

    if is_greeting_message(normalized):
        task_type = "greeting"
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability="greeting",
            module_hint=extract_requested_module(normalized),
            user_reply=None,
            task_type=task_type,
            extracted_slots=extract_task_slots(normalized, task_type),
        )

    if is_page_intro_request(normalized):
        task_type = "page_intro"
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability="page_intro",
            module_hint=extract_requested_module(normalized),
            user_reply=None,
            task_type=task_type,
            extracted_slots=extract_task_slots(normalized, task_type),
        )

    if is_module_overview_request(normalized):
        task_type = "module_overview"
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability="module_overview",
            module_hint=extract_requested_module(normalized),
            user_reply=None,
            task_type=task_type,
            extracted_slots=extract_task_slots(normalized, task_type),
        )

    if is_platform_overview_request(normalized):
        task_type = "platform_overview"
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability="platform_overview",
            module_hint=extract_requested_module(normalized),
            user_reply=None,
            task_type=task_type,
            extracted_slots=extract_task_slots(normalized, task_type),
        )

    if is_navigation_help_request(normalized):
        task_type = "navigation_help"
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability="navigation_help",
            module_hint=extract_requested_module(normalized),
            user_reply=None,
            task_type=task_type,
            extracted_slots=extract_task_slots(normalized, task_type),
        )

    if is_short_generic_request(normalized):
        task_type = "clarification"
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability="clarification_needed",
            module_hint=extract_requested_module(normalized),
            user_reply=None,
            task_type=task_type,
            extracted_slots=extract_task_slots(normalized, task_type),
        )

    intent = classify_intent(normalized)
    module_hint = extract_requested_module(normalized)
    capability = "docs_supported"
    if intent != "docs_only":
        capability = "internal_live_data" if intent == "live_data" else "internal_explanation"
    task_type = infer_task_type(
        question=normalized,
        capability=capability,
        intent=intent,
        module_hint=module_hint,
    )
    if intent == "docs_only":
        return WikiSemanticRoute(
            language="it",
            normalized_query=normalized,
            intent="docs_only",
            capability="docs_supported",
            module_hint=module_hint,
            user_reply=None,
            task_type=task_type,
            extracted_slots=extract_task_slots(normalized, task_type),
        )
    if module_hint is None:
        return None
    return WikiSemanticRoute(
        language="it",
        normalized_query=normalized,
        intent=intent,
        capability=capability,
        module_hint=module_hint,
        user_reply=None,
        task_type=task_type,
        extracted_slots=extract_task_slots(normalized, task_type),
    )
