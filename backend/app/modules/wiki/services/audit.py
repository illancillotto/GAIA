from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.models import WikiToolAuditLog
from app.modules.wiki.schemas import WikiChatResponse


@dataclass(frozen=True)
class WikiAuditContext:
    entity_key: str | None = None
    entity_label: str | None = None
    response_excerpt: str | None = None
    fallback_reason: str | None = None
    docs_source_count: int = 0
    evidence_count: int = 0


def build_audit_context(
    *,
    response: WikiChatResponse,
    fallback_reason: str | None = None,
) -> WikiAuditContext:
    primary_evidence = response.evidences[0] if response.evidences else None
    excerpt = response.answer.strip()[:300] if response.answer else None
    return WikiAuditContext(
        entity_key=primary_evidence.source_key if primary_evidence is not None else None,
        entity_label=primary_evidence.label if primary_evidence is not None else None,
        response_excerpt=excerpt,
        fallback_reason=fallback_reason,
        docs_source_count=len(response.sources),
        evidence_count=len(response.evidences),
    )


def persist_tool_audit_log(
    db: Session,
    *,
    current_user: ApplicationUser,
    question: str,
    intent: str,
    mode: str,
    tool_name: str,
    module_key: str | None,
    conversation_id=None,
    success: bool,
    found: bool,
    latency_ms: float,
    context_article: str | None = None,
    entity_key: str | None = None,
    entity_label: str | None = None,
    response_excerpt: str | None = None,
    fallback_reason: str | None = None,
    docs_source_count: int = 0,
    evidence_count: int = 0,
) -> None:
    normalized_question = question.strip()
    db.add(
        WikiToolAuditLog(
            username=current_user.username,
            role=current_user.role,
            intent=intent,
            mode=mode,
            tool_name=tool_name,
            module_key=module_key,
            conversation_id=conversation_id,
            question_hash=hashlib.sha256(normalized_question.encode("utf-8")).hexdigest(),
            question_preview=normalized_question[:200],
            context_article=context_article,
            entity_key=entity_key,
            entity_label=entity_label,
            response_excerpt=response_excerpt[:300] if response_excerpt else None,
            fallback_reason=fallback_reason,
            success=1 if success else 0,
            found=1 if found else 0,
            latency_ms=int(latency_ms),
            docs_source_count=docs_source_count,
            evidence_count=evidence_count,
        )
    )
    db.commit()
    from app.modules.wiki.services.telemetry import refresh_wiki_daily_metrics
    from app.modules.wiki.services.conversation_metrics import refresh_wiki_conversation_daily_metrics
    from app.modules.wiki.services.conversations import _build_conversation_audit_stats, sync_conversation_review_state

    if conversation_id is not None:
        from app.modules.wiki.models import WikiConversation

        conversation = db.get(WikiConversation, conversation_id)
        if conversation is not None:
            sync_conversation_review_state(db, conversation=conversation, audit_stats=_build_conversation_audit_stats(db))
            db.commit()

    refresh_wiki_daily_metrics(db, start_date=date.today(), end_date=date.today())
    refresh_wiki_conversation_daily_metrics(db, start_date=date.today(), end_date=date.today())
