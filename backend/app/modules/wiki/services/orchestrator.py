from __future__ import annotations

import logging
from time import monotonic
import uuid

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.audit import build_audit_context, persist_tool_audit_log
from app.modules.wiki.services.conversations import get_or_create_wiki_conversation, persist_wiki_conversation_turn
from app.modules.wiki.services.intent_classifier import classify_intent
from app.modules.wiki.services.openai_client import is_wiki_available
from app.modules.wiki.services.policy import evaluate_tool_access, sanitize_wiki_response
from app.modules.wiki.services.rag import answer_question
from app.modules.wiki.services.response_composer import build_hybrid_response, build_tool_denied_response
from app.modules.wiki.services.tool_registry import find_matching_tool

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


def _should_attempt_docs_enrichment(question: str, context_article: str | None) -> bool:
    normalized = question.strip().lower()
    return context_article is not None or any(hint in normalized for hint in _HYBRID_HINTS)


def answer_with_orchestration(
    db: Session,
    current_user: ApplicationUser,
    question: str,
    context_article: str | None = None,
    conversation_id: uuid.UUID | None = None,
) -> WikiChatResponse:
    started_at = monotonic()
    conversation = get_or_create_wiki_conversation(
        db,
        current_user=current_user,
        question=question,
        context_article=context_article,
        conversation_id=conversation_id,
    )
    intent = classify_intent(question)
    matched_tool = find_matching_tool(question, intent) if intent in {"live_data", "logic"} else None

    if matched_tool is not None:
        access = evaluate_tool_access(db, current_user, matched_tool.meta)
        if not access.allowed:
            elapsed_ms = round((monotonic() - started_at) * 1000, 2)
            persist_tool_audit_log(
                db,
                current_user=current_user,
                question=question,
                intent=intent,
                mode="live_data",
                tool_name=matched_tool.meta.name,
                module_key=matched_tool.meta.module_key,
                conversation_id=conversation.id,
                success=False,
                found=False,
                latency_ms=elapsed_ms,
                context_article=context_article,
                fallback_reason=access.reason_code or "tool_denied",
            )
            logger.info(
                "wiki_tool_call_denied user=%s role=%s intent=%s tool=%s module=%s reason=%s latency_ms=%s",
                current_user.username,
                current_user.role,
                intent,
                matched_tool.meta.name,
                matched_tool.meta.module_key or "-",
                access.reason_code or "tool_denied",
                elapsed_ms,
            )
            denied_response = build_tool_denied_response(
                tool_name=matched_tool.meta.name,
                reason=access.reason_message or "Non posso accedere a questi dati live con i permessi del tuo account.",
            )
            denied_response.conversation_id = conversation.id
            persist_wiki_conversation_turn(
                db,
                conversation=conversation,
                question=question,
                response=denied_response,
            )
            return denied_response
        response = sanitize_wiki_response(matched_tool.meta, matched_tool.handler(db, current_user, question))
        fallback_reason: str | None = None
        if (
            response.found
            and matched_tool.meta.name in _HYBRID_TOOLS
            and _should_attempt_docs_enrichment(question, context_article)
            and is_wiki_available()
        ):
            docs_response = answer_question(db, question, context_article)
            if docs_response.found:
                response = build_hybrid_response(tool_response=response, docs_response=docs_response)
                fallback_reason = "docs_enrichment"
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
            tool_name=matched_tool.meta.name,
            module_key=matched_tool.meta.module_key,
            conversation_id=conversation.id,
            success=True,
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
        logger.info(
            "wiki_tool_call user=%s role=%s intent=%s tool=%s module=%s found=%s latency_ms=%s",
            current_user.username,
            current_user.role,
            intent,
            matched_tool.meta.name,
            matched_tool.meta.module_key or "-",
            response.found,
            elapsed_ms,
        )
        return response

    if not is_wiki_available():
        raise RuntimeError("Wiki Agent non disponibile: codex-lb non raggiungibile su CODEX_LB_URL.")

    response = answer_question(db, question, context_article)
    response.mode = "docs_only"
    elapsed_ms = round((monotonic() - started_at) * 1000, 2)
    response.conversation_id = conversation.id
    persist_wiki_conversation_turn(
        db,
        conversation=conversation,
        question=question,
        response=response,
    )
    docs_audit_context = build_audit_context(response=response, fallback_reason="docs_only")
    persist_tool_audit_log(
        db,
        current_user=current_user,
        question=question,
        intent=intent,
        mode=response.mode,
        tool_name="docs_answer",
        module_key=None,
        conversation_id=conversation.id,
        success=True,
        found=response.found,
        latency_ms=elapsed_ms,
        context_article=context_article,
        entity_key=docs_audit_context.entity_key,
        entity_label=docs_audit_context.entity_label,
        response_excerpt=docs_audit_context.response_excerpt,
        fallback_reason=docs_audit_context.fallback_reason,
        docs_source_count=docs_audit_context.docs_source_count,
        evidence_count=docs_audit_context.evidence_count,
    )
    logger.info(
        "wiki_docs_answer user=%s role=%s intent=%s found=%s latency_ms=%s context_article=%s",
        current_user.username,
        current_user.role,
        intent,
        response.found,
        elapsed_ms,
        context_article or "-",
    )
    return response
