from __future__ import annotations

from dataclasses import dataclass
import logging
from time import monotonic
import uuid
from typing import Iterator

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.capabilities import CapabilityDefinition, select_capability
from app.modules.wiki.models import WikiConversation
from app.modules.wiki.schemas import WikiChatResponse, WikiChatStreamChunk
from app.modules.wiki.services.audit import build_audit_context, persist_tool_audit_log
from app.modules.wiki.services.conversations import get_or_create_wiki_conversation, persist_wiki_conversation_turn
from app.modules.wiki.services.guardrails import (
    build_contextual_preflight_response,
    build_operational_preflight_response,
    build_widget_preflight_response,
    has_platform_scope,
    is_widget_context,
    postflight_docs_guardrail,
    preflight_capability_guardrail,
)
from app.modules.wiki.services.intent_classifier import classify_intent
from app.modules.wiki.services.openai_client import is_wiki_available
from app.modules.wiki.services.policy import evaluate_tool_access, sanitize_wiki_response
from app.modules.wiki.services.question_router import route_wiki_question_fast
from app.modules.wiki.services.rag import (
    answer_question,
    build_docs_response_from_prepared,
    prepare_docs_answer,
    stream_answer_from_prepared,
)
from app.modules.wiki.services.response_composer import build_hybrid_response, build_tool_denied_response
from app.modules.wiki.services.semantic_router import route_wiki_question
from app.modules.wiki.services.tool_registry import find_matching_tool, find_tool_by_name

logger = logging.getLogger(__name__)

_HYBRID_HINTS = (
    "spiega",
    "significa",
    "come funziona",
    "come viene calcolato",
    "come si calcola",
    "perche",
    "perché",
)

_HYBRID_TOOLS = {
    "find_ruolo_subject",
    "find_share_by_name",
    "find_particella_by_id",
    "find_riordino_practice_by_id",
    "find_operazioni_case_by_id",
    "find_operazioni_assignment_by_id",
    "find_operazioni_maintenance_by_id",
    "find_operazioni_usage_session_by_id",
    "find_operazioni_activity_by_id",
    "find_operazioni_activity_approval_by_id",
    "find_operazioni_autodoc_sync_job_by_id",
    "find_operazioni_fuel_log_by_id",
    "find_operazioni_unresolved_transaction_by_id",
    "find_operazioni_analytics_anomaly_by_id",
    "get_operazioni_storage_status",
    "get_operazioni_mobile_sync_status",
    "explain_catasto_metric",
    "explain_ruolo_metric",
    "explain_operazioni_analytics_metric",
    "explain_operazioni_storage_alert_level",
    "explain_operazioni_mobile_sync_flow",
    "explain_riordino_practice_state",
    "explain_operazioni_case_status",
    "explain_operazioni_assignment_status",
    "explain_operazioni_maintenance_status",
    "explain_operazioni_usage_session_status",
    "explain_operazioni_activity_status",
    "explain_operazioni_activity_approval_decision",
    "explain_operazioni_autodoc_sync_status",
    "explain_operazioni_fuel_log_status",
    "explain_operazioni_unresolved_transaction_reason",
    "explain_operazioni_analytics_anomaly",
}

_DOCS_GUIDED_PREFLIGHT_REASONS = {
    "missing_parameters",
    "owner_lookup_clarification",
    "page_intro",
    "module_overview",
    "platform_overview",
    "clarification_needed",
}

_WIKI_UNAVAILABLE_ANSWER_MARKERS = (
    "wiki non e operativo",
    "non riesce a sintetizzarli",
)

_SEMANTIC_ROUTER_REPLY_ONLY_CAPABILITIES = {
    "unsupported_external_live",
    "unsupported_access_request",
    "unsupported_action_request",
    "out_of_scope",
}


def _is_usable_docs_enrichment(docs_response: WikiChatResponse) -> bool:
    if not docs_response.found:
        return False
    normalized = docs_response.answer.strip().lower()
    return not any(marker in normalized for marker in _WIKI_UNAVAILABLE_ANSWER_MARKERS)


@dataclass(slots=True)
class WikiOrchestrationPlan:
    conversation: WikiConversation
    intent: str
    normalized_question: str
    matched_tool: object | None
    selected_capability: CapabilityDefinition | None
    preflight_response: WikiChatResponse | None
    preflight_reason: str | None
    preflight_tool_name: str | None


def _resolve_context_article(plan: WikiOrchestrationPlan, context_article: str | None) -> str | None:
    if context_article is not None:
        return context_article
    if plan.selected_capability is None or not plan.selected_capability.docs_pages:
        return None
    return f"domain-docs/wiki/operational/{plan.selected_capability.docs_pages[0]}"


def _serialize_stream_chunk(event: str, data: dict[str, object]) -> WikiChatStreamChunk:
    return WikiChatStreamChunk(event=event, data=data)


def _chunk_answer(answer: str, *, chunk_words: int = 40) -> list[str]:
    words = answer.split()
    if not words:
        return [""]
    return [" ".join(words[index:index + chunk_words]) for index in range(0, len(words), chunk_words)]


def _build_orchestration_plan(
    db: Session,
    current_user: ApplicationUser,
    question: str,
    context_article: str | None,
    conversation_id: uuid.UUID | None,
    module_key: str | None,
    page_path: str | None,
) -> WikiOrchestrationPlan:
    conversation = get_or_create_wiki_conversation(
        db,
        current_user=current_user,
        question=question,
        context_article=context_article,
        conversation_id=conversation_id,
    )
    fast_route = route_wiki_question_fast(question)
    semantic_route = None
    if fast_route is None or fast_route.capability in {
        "navigation_help",
        "page_intro",
        "module_overview",
        "platform_overview",
        "clarification_needed",
    }:
        semantic_route = route_wiki_question(
            question,
            module_key=module_key,
            page_path=page_path,
        )
    semantic_route = semantic_route or fast_route
    normalized_question = semantic_route.normalized_query if semantic_route is not None else question
    intent = semantic_route.intent if semantic_route is not None else classify_intent(question)
    preferred_module_key = semantic_route.module_hint if semantic_route is not None else None
    selected_capability = (
        select_capability(
            task_type=semantic_route.task_type,
            module_hint=preferred_module_key,
            extracted_slots=semantic_route.extracted_slots,
        )
        if semantic_route is not None
        else None
    )
    matched_tool = (
        find_matching_tool(normalized_question, intent, preferred_module_key=preferred_module_key)
        if intent in {"live_data", "logic"}
        else None
    )
    if matched_tool is None and selected_capability is not None and selected_capability.tool_name:
        matched_tool = find_tool_by_name(selected_capability.tool_name)

    preflight_response: WikiChatResponse | None = None
    preflight_reason: str | None = None
    preflight_tool_name: str | None = None
    if (
        semantic_route is not None
        and semantic_route.should_preflight_reply
        and semantic_route.user_reply
        and semantic_route.capability in _SEMANTIC_ROUTER_REPLY_ONLY_CAPABILITIES
    ):
        preflight_response = _build_guardrail_response(
            semantic_route.user_reply,
            found=semantic_route.capability not in {
                "unsupported_external_live",
                "unsupported_access_request",
                "unsupported_action_request",
                "out_of_scope",
            },
        )
        preflight_reason = semantic_route.capability
        preflight_tool_name = semantic_route.capability
    elif matched_tool is None:
        preflight_decision = preflight_capability_guardrail(question)
        if preflight_decision is not None:
            preflight_response = _build_guardrail_response(preflight_decision.answer, found=False)
            preflight_reason = preflight_decision.fallback_reason
            preflight_tool_name = preflight_decision.fallback_reason
        else:
            if selected_capability is not None:
                missing_slots = selected_capability.missing_slots(
                    semantic_route.extracted_slots if semantic_route is not None else {}
                )
                if missing_slots and selected_capability.clarification_prompt:
                    preflight_response = _build_guardrail_response(selected_capability.clarification_prompt, found=True)
                    preflight_reason = "missing_parameters"
                    preflight_tool_name = selected_capability.name
            if preflight_response is not None:
                return WikiOrchestrationPlan(
                    conversation=conversation,
                    intent=intent,
                    normalized_question=normalized_question,
                    matched_tool=matched_tool,
                    selected_capability=selected_capability,
                    preflight_response=preflight_response,
                    preflight_reason=preflight_reason,
                    preflight_tool_name=preflight_tool_name,
                )
            operational_preflight = build_operational_preflight_response(
                question,
                module_key=module_key,
                page_path=page_path,
            )
            if operational_preflight is not None:
                preflight_response = _build_guardrail_response(
                    operational_preflight.answer,
                    found=operational_preflight.found,
                )
                preflight_reason = operational_preflight.fallback_reason
                preflight_tool_name = operational_preflight.tool_name
            else:
                contextual_preflight = build_contextual_preflight_response(
                    question,
                    module_key=module_key,
                    page_path=page_path,
                )
                if contextual_preflight is not None:
                    preflight_response = _build_guardrail_response(
                        contextual_preflight.answer,
                        found=contextual_preflight.found,
                    )
                    preflight_reason = contextual_preflight.fallback_reason
                    preflight_tool_name = contextual_preflight.tool_name
                else:
                    widget_preflight = build_widget_preflight_response(
                        question,
                        module_key=module_key,
                        page_path=page_path,
                        has_active_conversation=conversation_id is not None,
                    )
                    if widget_preflight is not None:
                        preflight_response = _build_guardrail_response(
                            widget_preflight.answer,
                            found=widget_preflight.found,
                        )
                        preflight_reason = widget_preflight.fallback_reason
                        preflight_tool_name = widget_preflight.tool_name

    return WikiOrchestrationPlan(
        conversation=conversation,
        intent=intent,
        normalized_question=normalized_question,
        matched_tool=matched_tool,
        selected_capability=selected_capability,
        preflight_response=preflight_response,
        preflight_reason=preflight_reason,
        preflight_tool_name=preflight_tool_name,
    )


def _should_attempt_docs_enrichment(question: str, context_article: str | None) -> bool:
    normalized = question.strip().lower()
    return context_article is not None or any(hint in normalized for hint in _HYBRID_HINTS)


def _build_guardrail_response(answer: str, *, found: bool = False) -> WikiChatResponse:
    return WikiChatResponse(
        answer=answer,
        sources=[],
        found=found,
        mode="docs_only",
    )


def _build_stream_meta(
    response: WikiChatResponse,
    *,
    stream_mode: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "mode": response.mode,
        "found": response.found,
        "conversation_id": str(response.conversation_id) if response.conversation_id is not None else None,
        "tool_calls": [item.model_dump(mode="json") for item in response.tool_calls],
        "sources": [item.model_dump(mode="json") for item in response.sources],
        "evidences": [item.model_dump(mode="json") for item in response.evidences],
    }
    if stream_mode is not None:
        payload["stream_mode"] = stream_mode
    return payload


def _persist_response_and_audit(
    db: Session,
    *,
    current_user: ApplicationUser,
    conversation: WikiConversation,
    question: str,
    response: WikiChatResponse,
    intent: str,
    tool_name: str,
    module_key: str | None,
    started_at: float,
    context_article: str | None,
    fallback_reason: str | None = None,
    success: bool = True,
) -> WikiChatResponse:
    elapsed_ms = round((monotonic() - started_at) * 1000, 2)
    response.conversation_id = conversation.id
    persist_wiki_conversation_turn(
        db,
        conversation=conversation,
        question=question,
        response=response,
    )
    audit_context = build_audit_context(response=response, fallback_reason=fallback_reason)
    persist_tool_audit_log(
        db,
        current_user=current_user,
        question=question,
        intent=intent,
        mode=response.mode,
        tool_name=tool_name,
        module_key=module_key,
        conversation_id=conversation.id,
        success=success,
        found=response.found,
        latency_ms=elapsed_ms,
        context_article=context_article,
        entity_key=audit_context.entity_key,
        entity_label=audit_context.entity_label,
        response_excerpt=audit_context.response_excerpt,
        fallback_reason=audit_context.fallback_reason,
        docs_source_count=audit_context.docs_source_count,
        evidence_count=audit_context.evidence_count,
    )
    return response


def _execute_guardrail_plan(
    db: Session,
    *,
    current_user: ApplicationUser,
    plan: WikiOrchestrationPlan,
    question: str,
    context_article: str | None,
    started_at: float,
    module_key: str | None,
    page_path: str | None,
) -> WikiChatResponse:
    if plan.preflight_response is None:
        raise RuntimeError("Preflight plan richiesto senza risposta associata.")
    effective_context_article = _resolve_context_article(plan, context_article)
    response = plan.preflight_response
    fallback_reason = plan.preflight_reason
    tool_name = plan.preflight_tool_name or "guardrail"
    if (
        response.found
        and effective_context_article is not None
        and plan.preflight_reason in _DOCS_GUIDED_PREFLIGHT_REASONS
        and is_wiki_available()
    ):
        docs_response = answer_question(
            db,
            question,
            effective_context_article,
            retrieval_query=plan.normalized_question,
            module_key=module_key,
            page_path=page_path,
            operational_only=is_widget_context(page_path),
        )
        if docs_response.found and _is_usable_docs_enrichment(docs_response):
            response = docs_response
            response.mode = "docs_only"
            fallback_reason = f"docs_guided_{plan.preflight_reason}"
            tool_name = "docs_answer"
    return _persist_response_and_audit(
        db,
        current_user=current_user,
        conversation=plan.conversation,
        question=question,
        response=response,
        intent=plan.intent,
        tool_name=tool_name,
        module_key=None,
        started_at=started_at,
        context_article=effective_context_article,
        fallback_reason=fallback_reason,
    )


def _execute_tool_plan(
    db: Session,
    *,
    current_user: ApplicationUser,
    plan: WikiOrchestrationPlan,
    question: str,
    context_article: str | None,
    started_at: float,
    module_key: str | None,
    page_path: str | None,
) -> WikiChatResponse:
    if plan.matched_tool is None:
        raise RuntimeError("Tool plan richiesto senza tool associato.")
    effective_context_article = _resolve_context_article(plan, context_article)

    access = evaluate_tool_access(db, current_user, plan.matched_tool.meta)
    if not access.allowed:
        elapsed_ms = round((monotonic() - started_at) * 1000, 2)
        persist_tool_audit_log(
            db,
            current_user=current_user,
            question=question,
            intent=plan.intent,
            mode="live_data",
            tool_name=plan.matched_tool.meta.name,
            module_key=plan.matched_tool.meta.module_key,
            conversation_id=plan.conversation.id,
            success=False,
            found=False,
            latency_ms=elapsed_ms,
            context_article=effective_context_article,
            fallback_reason=access.reason_code or "tool_denied",
        )
        logger.info(
            "wiki_tool_call_denied user=%s role=%s intent=%s tool=%s module=%s reason=%s latency_ms=%s",
            current_user.username,
            current_user.role,
            plan.intent,
            plan.matched_tool.meta.name,
            plan.matched_tool.meta.module_key or "-",
            access.reason_code or "tool_denied",
            elapsed_ms,
        )
        denied_response = build_tool_denied_response(
            tool_name=plan.matched_tool.meta.name,
            reason=access.reason_message or "Non posso accedere a questi dati live con i permessi del tuo account.",
        )
        denied_response.conversation_id = plan.conversation.id
        persist_wiki_conversation_turn(
            db,
            conversation=plan.conversation,
            question=question,
            response=denied_response,
        )
        return denied_response

    response = sanitize_wiki_response(plan.matched_tool.meta, plan.matched_tool.handler(db, current_user, plan.normalized_question))
    fallback_reason: str | None = None
    operational_only = is_widget_context(page_path)
    if (
        response.found
        and plan.matched_tool.meta.name in _HYBRID_TOOLS
        and _should_attempt_docs_enrichment(question, effective_context_article)
        and is_wiki_available()
    ):
        docs_response = answer_question(
            db,
            question,
            effective_context_article,
            retrieval_query=plan.normalized_question,
            module_key=module_key,
            page_path=page_path,
            operational_only=operational_only,
        )
        if docs_response.found:
            response = build_hybrid_response(tool_response=response, docs_response=docs_response)
            fallback_reason = "docs_enrichment"

    response = _persist_response_and_audit(
        db,
        current_user=current_user,
        conversation=plan.conversation,
        question=question,
        response=response,
        intent=plan.intent,
        tool_name=plan.matched_tool.meta.name,
        module_key=plan.matched_tool.meta.module_key,
        started_at=started_at,
        context_article=effective_context_article,
        fallback_reason=fallback_reason,
    )
    elapsed_ms = round((monotonic() - started_at) * 1000, 2)
    logger.info(
        "wiki_tool_call user=%s role=%s intent=%s tool=%s module=%s found=%s latency_ms=%s",
        current_user.username,
        current_user.role,
        plan.intent,
        plan.matched_tool.meta.name,
        plan.matched_tool.meta.module_key or "-",
        response.found,
        elapsed_ms,
    )
    return response


def _execute_docs_plan(
    db: Session,
    *,
    current_user: ApplicationUser,
    plan: WikiOrchestrationPlan,
    question: str,
    context_article: str | None,
    started_at: float,
    module_key: str | None,
    page_path: str | None,
) -> WikiChatResponse:
    operational_only = is_widget_context(page_path)
    effective_context_article = _resolve_context_article(plan, context_article)
    response = answer_question(
        db,
        question,
        effective_context_article,
        retrieval_query=plan.normalized_question,
        module_key=module_key,
        page_path=page_path,
        operational_only=operational_only,
    )
    if not response.found and effective_context_article is not None and context_article is None:
        response = answer_question(
            db,
            question,
            None,
            retrieval_query=plan.normalized_question,
            module_key=module_key,
            page_path=page_path,
            operational_only=operational_only,
        )
        effective_context_article = None
    if not response.found and effective_context_article is None and has_platform_scope(question):
        response = answer_question(
            db,
            question,
            effective_context_article,
            allow_recent_fallback=True,
            retrieval_query=plan.normalized_question,
            module_key=module_key,
            page_path=page_path,
            operational_only=operational_only,
        )
    response.mode = "docs_only"
    postflight_decision = postflight_docs_guardrail(
        question=question,
        response=response,
        context_article=effective_context_article,
        module_key=module_key,
        page_path=page_path,
    )
    fallback_reason = "docs_only"
    if postflight_decision is not None:
        response = _build_guardrail_response(postflight_decision.answer, found=False)
        fallback_reason = postflight_decision.fallback_reason

    response = _persist_response_and_audit(
        db,
        current_user=current_user,
        conversation=plan.conversation,
        question=question,
        response=response,
        intent=plan.intent,
        tool_name="docs_answer",
        module_key=None,
        started_at=started_at,
        context_article=effective_context_article,
        fallback_reason=fallback_reason,
    )
    elapsed_ms = round((monotonic() - started_at) * 1000, 2)
    logger.info(
        "wiki_docs_answer user=%s role=%s intent=%s found=%s latency_ms=%s context_article=%s fallback_reason=%s",
        current_user.username,
        current_user.role,
        plan.intent,
        response.found,
        elapsed_ms,
        context_article or "-",
        fallback_reason,
    )
    return response


def _yield_synthetic_stream(response: WikiChatResponse) -> Iterator[WikiChatStreamChunk]:
    yield _serialize_stream_chunk("meta", _build_stream_meta(response))
    for piece in _chunk_answer(response.answer):
        yield _serialize_stream_chunk("delta", {"text": piece})
    yield _serialize_stream_chunk(
        "done",
        {"answer": response.answer, "conversation_id": str(response.conversation_id) if response.conversation_id is not None else None},
    )


def answer_with_orchestration(
    db: Session,
    current_user: ApplicationUser,
    question: str,
    context_article: str | None = None,
    conversation_id: uuid.UUID | None = None,
    module_key: str | None = None,
    page_path: str | None = None,
) -> WikiChatResponse:
    started_at = monotonic()
    plan = _build_orchestration_plan(db, current_user, question, context_article, conversation_id, module_key, page_path)
    if plan.preflight_response is not None:
        return _execute_guardrail_plan(
            db,
            current_user=current_user,
            plan=plan,
            question=question,
            context_article=context_article,
            started_at=started_at,
            module_key=module_key,
            page_path=page_path,
        )

    if plan.matched_tool is not None:
        return _execute_tool_plan(
            db,
            current_user=current_user,
            plan=plan,
            question=question,
            context_article=context_article,
            started_at=started_at,
            module_key=module_key,
            page_path=page_path,
        )

    if not is_wiki_available():
        raise RuntimeError("Wiki Agent non disponibile: codex-lb non raggiungibile su CODEX_LB_URL.")

    return _execute_docs_plan(
        db,
        current_user=current_user,
        plan=plan,
        question=question,
        context_article=context_article,
        started_at=started_at,
        module_key=module_key,
        page_path=page_path,
    )


def stream_with_orchestration(
    db: Session,
    current_user: ApplicationUser,
    question: str,
    context_article: str | None = None,
    conversation_id: uuid.UUID | None = None,
    module_key: str | None = None,
    page_path: str | None = None,
) -> Iterator[WikiChatStreamChunk]:
    started_at = monotonic()
    plan = _build_orchestration_plan(db, current_user, question, context_article, conversation_id, module_key, page_path)

    if plan.preflight_response is not None:
        response = answer_with_orchestration(db, current_user, question, context_article, plan.conversation.id, module_key, page_path)
        yield from _yield_synthetic_stream(response)
        return

    if plan.matched_tool is not None:
        response = answer_with_orchestration(db, current_user, question, context_article, plan.conversation.id, module_key, page_path)
        yield from _yield_synthetic_stream(response)
        return

    if not is_wiki_available():
        raise RuntimeError("Wiki Agent non disponibile: codex-lb non raggiungibile su CODEX_LB_URL.")

    operational_only = is_widget_context(page_path)
    effective_context_article = _resolve_context_article(plan, context_article)
    prepared = prepare_docs_answer(
        db,
        question,
        effective_context_article,
        retrieval_query=plan.normalized_question,
        operational_only=operational_only,
    )
    if not prepared.found and effective_context_article is not None and context_article is None:
        prepared = prepare_docs_answer(
            db,
            question,
            None,
            retrieval_query=plan.normalized_question,
            operational_only=operational_only,
        )
        effective_context_article = None
    if not prepared.found and effective_context_article is None and has_platform_scope(question):
        prepared = prepare_docs_answer(
            db,
            question,
            effective_context_article,
            allow_recent_fallback=True,
            retrieval_query=plan.normalized_question,
            operational_only=operational_only,
        )

    if not prepared.found:
        response = answer_with_orchestration(db, current_user, question, context_article, plan.conversation.id, module_key, page_path)
        yield _serialize_stream_chunk("meta", _build_stream_meta(response))
        yield _serialize_stream_chunk("done", {"answer": response.answer, "conversation_id": str(response.conversation_id) if response.conversation_id is not None else None})
        return

    sources = [item.model_dump(mode="json") for item in prepared.sources]
    yield _serialize_stream_chunk(
        "meta",
        {
            "mode": "docs_only",
            "found": True,
            "conversation_id": str(plan.conversation.id),
            "tool_calls": [],
            "sources": sources,
            "evidences": [],
            "stream_mode": "provider",
        },
    )

    answer_parts: list[str] = []
    for delta in stream_answer_from_prepared(prepared, question):
        answer_parts.append(delta)
        yield _serialize_stream_chunk("delta", {"text": delta})

    streamed_answer = "".join(answer_parts).strip()
    if streamed_answer:
        response = build_docs_response_from_prepared(prepared, streamed_answer, module_key=module_key, page_path=page_path)
    else:
        response = answer_question(
            db,
            question,
            effective_context_article,
            retrieval_query=plan.normalized_question,
            module_key=module_key,
            page_path=page_path,
            operational_only=operational_only,
        )
    response.mode = "docs_only"
    postflight_decision = postflight_docs_guardrail(
        question=question,
        response=response,
        context_article=effective_context_article,
        module_key=module_key,
        page_path=page_path,
    )
    fallback_reason = "docs_only"
    if postflight_decision is not None:
        response = _build_guardrail_response(postflight_decision.answer, found=False)
        fallback_reason = postflight_decision.fallback_reason
    response = _persist_response_and_audit(
        db,
        current_user=current_user,
        conversation=plan.conversation,
        question=question,
        response=response,
        intent=plan.intent,
        tool_name="docs_answer",
        module_key=None,
        started_at=started_at,
        context_article=effective_context_article,
        fallback_reason=fallback_reason,
    )
    yield _serialize_stream_chunk(
        "done",
        {"answer": response.answer, "conversation_id": str(response.conversation_id) if response.conversation_id is not None else None},
    )
