from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.models import WikiConversation, WikiConversationEvent, WikiConversationMessage, WikiToolAuditLog
from app.modules.wiki.services.conversation_governance import get_or_create_wiki_conversation_governance_config
from app.modules.wiki.services.review_rules import (
    WikiConversationReviewConfig,
    WikiConversationReviewSignals,
    assess_conversation_review,
)
from app.modules.wiki.schemas import (
    WikiChatResponse,
    WikiChunkSource,
    WikiConversationFlagUpdate,
    WikiConversationEventRead,
    WikiConversationMessageRead,
    WikiConversationRead,
    WikiConversationSummaryMetricsRead,
    WikiConversationSummaryRead,
    WikiConversationUpdate,
    WikiEvidence,
    WikiMetricCountRead,
    WikiToolCallSummary,
)

OPEN_STATUSES = {"open", "in_review", "waiting_user"}
STATUS_ORDER = {"open": 0, "in_review": 1, "waiting_user": 2, "resolved": 3}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass(slots=True)
class WikiConversationPersistResult:
    conversation_id: uuid.UUID
    user_message_id: uuid.UUID
    assistant_message_id: uuid.UUID


@dataclass(slots=True)
class _ConversationAuditStats:
    last_mode: dict[uuid.UUID, str]
    top_tool_name: dict[uuid.UUID, str]
    top_module: dict[uuid.UUID, str]
    top_intent: dict[uuid.UUID, str]
    latest_entity_key: dict[uuid.UUID, str]
    latest_context_article: dict[uuid.UUID, str]
    denied_count: dict[uuid.UUID, int]
    fallback_count: dict[uuid.UUID, int]
    no_match_count: dict[uuid.UUID, int]
    avg_latency_ms: dict[uuid.UUID, int]
    consecutive_no_match_count: dict[uuid.UUID, int]


@dataclass(slots=True)
class _ConversationEventStats:
    last_event_type: dict[uuid.UUID, str] = field(default_factory=dict)
    last_owner_change_at: dict[uuid.UUID, datetime] = field(default_factory=dict)
    reopen_count: dict[uuid.UUID, int] = field(default_factory=dict)


def _dump_json(value: object | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=True, default=str)


def _load_json_list(raw: str | None) -> list[dict[str, object]]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def _conversation_title(question: str) -> str:
    normalized = " ".join(question.strip().split())
    return normalized[:120] if normalized else "Nuova conversazione Wiki"


def _is_admin(user: ApplicationUser) -> bool:
    return user.role in {"admin", "super_admin"}


def _can_access_conversation(current_user: ApplicationUser, conversation: WikiConversation) -> bool:
    return _is_admin(current_user) or conversation.created_by == current_user.username


def _can_manage_conversation(current_user: ApplicationUser, conversation: WikiConversation) -> bool:
    return _is_admin(current_user) or conversation.created_by == current_user.username


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalize_owner_key(value: str | None) -> str:
    return value or "unassigned"


def _aging_bucket(now: datetime, created_at: datetime) -> str:
    age_hours = max((now - created_at.replace(tzinfo=UTC) if created_at.tzinfo is None else now - created_at).total_seconds() / 3600, 0)
    if age_hours < 24:
        return "lt_24h"
    if age_hours < 24 * 7:
        return "1d_7d"
    return "gt_7d"


def _hours_between(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    return max((end - start).total_seconds() / 3600, 0)


def _record_conversation_event(
    db: Session,
    *,
    conversation: WikiConversation,
    event_type: str,
    actor_username: str | None,
    from_status: str | None = None,
    to_status: str | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    db.add(
        WikiConversationEvent(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            event_type=event_type,
            actor_username=actor_username,
            from_status=from_status,
            to_status=to_status,
            payload_json=_dump_json(payload),
        )
    )


def _build_conversation_audit_stats(db: Session) -> _ConversationAuditStats:
    audit_rows = db.execute(
        select(
            WikiToolAuditLog.conversation_id,
            WikiToolAuditLog.mode,
            WikiToolAuditLog.tool_name,
            WikiToolAuditLog.module_key,
            WikiToolAuditLog.intent,
            WikiToolAuditLog.created_at,
            WikiToolAuditLog.success,
            WikiToolAuditLog.fallback_reason,
            WikiToolAuditLog.found,
            WikiToolAuditLog.latency_ms,
            WikiToolAuditLog.entity_key,
            WikiToolAuditLog.context_article,
        )
        .where(WikiToolAuditLog.conversation_id.is_not(None))
        .order_by(WikiToolAuditLog.created_at.desc())
    ).all()
    last_mode_map: dict[uuid.UUID, str] = {}
    top_tool_counts: dict[uuid.UUID, dict[str, int]] = {}
    top_module_counts: dict[uuid.UUID, dict[str, int]] = {}
    top_intent_counts: dict[uuid.UUID, dict[str, int]] = {}
    latest_entity_key: dict[uuid.UUID, str] = {}
    latest_context_article: dict[uuid.UUID, str] = {}
    denied_count_map: dict[uuid.UUID, int] = {}
    fallback_count_map: dict[uuid.UUID, int] = {}
    no_match_count_map: dict[uuid.UUID, int] = {}
    latency_totals: dict[uuid.UUID, int] = {}
    latency_samples: dict[uuid.UUID, int] = {}
    consecutive_no_match_count: dict[uuid.UUID, int] = {}
    tracking_latest_streak: set[uuid.UUID] = set()

    for row in audit_rows:
        conversation_id = row.conversation_id
        if conversation_id is None:
            continue
        if conversation_id not in last_mode_map:
            last_mode_map[conversation_id] = row.mode
            tracking_latest_streak.add(conversation_id)
        bucket = top_tool_counts.setdefault(conversation_id, {})
        bucket[row.tool_name] = bucket.get(row.tool_name, 0) + 1
        if row.module_key:
            module_bucket = top_module_counts.setdefault(conversation_id, {})
            module_bucket[row.module_key] = module_bucket.get(row.module_key, 0) + 1
        if row.intent:
            intent_bucket = top_intent_counts.setdefault(conversation_id, {})
            intent_bucket[row.intent] = intent_bucket.get(row.intent, 0) + 1
        if row.entity_key and conversation_id not in latest_entity_key:
            latest_entity_key[conversation_id] = row.entity_key
        if row.context_article and conversation_id not in latest_context_article:
            latest_context_article[conversation_id] = row.context_article
        if not bool(row.success):
            denied_count_map[conversation_id] = denied_count_map.get(conversation_id, 0) + 1
        if row.fallback_reason:
            fallback_count_map[conversation_id] = fallback_count_map.get(conversation_id, 0) + 1
        if not bool(row.found):
            no_match_count_map[conversation_id] = no_match_count_map.get(conversation_id, 0) + 1
            if conversation_id in tracking_latest_streak:
                consecutive_no_match_count[conversation_id] = consecutive_no_match_count.get(conversation_id, 0) + 1
        elif conversation_id in tracking_latest_streak:
            tracking_latest_streak.remove(conversation_id)
        latency_totals[conversation_id] = latency_totals.get(conversation_id, 0) + int(row.latency_ms or 0)
        latency_samples[conversation_id] = latency_samples.get(conversation_id, 0) + 1

    return _ConversationAuditStats(
        last_mode=last_mode_map,
        top_tool_name={
            conversation_id: sorted(tool_counts.items(), key=lambda pair: (-pair[1], pair[0]))[0][0]
            for conversation_id, tool_counts in top_tool_counts.items()
            if tool_counts
        },
        top_module={
            conversation_id: sorted(tool_counts.items(), key=lambda pair: (-pair[1], pair[0]))[0][0]
            for conversation_id, tool_counts in top_module_counts.items()
            if tool_counts
        },
        top_intent={
            conversation_id: sorted(tool_counts.items(), key=lambda pair: (-pair[1], pair[0]))[0][0]
            for conversation_id, tool_counts in top_intent_counts.items()
            if tool_counts
        },
        latest_entity_key=latest_entity_key,
        latest_context_article=latest_context_article,
        denied_count=denied_count_map,
        fallback_count=fallback_count_map,
        no_match_count=no_match_count_map,
        avg_latency_ms={
            conversation_id: int(round(latency_totals[conversation_id] / latency_samples[conversation_id]))
            for conversation_id in latency_totals
            if latency_samples.get(conversation_id)
        },
        consecutive_no_match_count=consecutive_no_match_count,
    )


def _build_conversation_event_stats(db: Session) -> _ConversationEventStats:
    rows = db.execute(
        select(
            WikiConversationEvent.conversation_id,
            WikiConversationEvent.event_type,
            WikiConversationEvent.created_at,
            WikiConversationEvent.from_status,
            WikiConversationEvent.to_status,
        )
        .order_by(WikiConversationEvent.created_at.desc())
    ).all()
    stats = _ConversationEventStats()
    for row in rows:
        conversation_id = row.conversation_id
        if conversation_id not in stats.last_event_type:
            stats.last_event_type[conversation_id] = row.event_type
        if row.event_type == "assignment_changed" and conversation_id not in stats.last_owner_change_at:
            stats.last_owner_change_at[conversation_id] = row.created_at
        if row.event_type == "status_changed" and row.from_status == "resolved" and row.to_status == "open":
            stats.reopen_count[conversation_id] = stats.reopen_count.get(conversation_id, 0) + 1
    return stats


def _derive_review_reason(conversation: WikiConversation, audit_stats: _ConversationAuditStats) -> str | None:
    review_config = None
    return _derive_review_reason_with_config(conversation, audit_stats, review_config=review_config)


def _derive_review_reason_with_config(
    conversation: WikiConversation,
    audit_stats: _ConversationAuditStats,
    *,
    review_config: WikiConversationReviewConfig | None,
) -> str | None:
    assessment = assess_conversation_review(
        WikiConversationReviewSignals(
            denied_count=audit_stats.denied_count.get(conversation.id, 0),
            fallback_count=audit_stats.fallback_count.get(conversation.id, 0),
            no_match_count=audit_stats.no_match_count.get(conversation.id, 0),
            consecutive_no_match_count=audit_stats.consecutive_no_match_count.get(conversation.id, 0),
            avg_latency_ms=audit_stats.avg_latency_ms.get(conversation.id, 0),
            manual_flag=conversation.review_reason == "manual_flag",
        ),
        priority=conversation.priority or "medium",
        status=conversation.status or "open",
        review_config=review_config,
    )
    return assessment.review_reason


def _needs_review(conversation: WikiConversation, audit_stats: _ConversationAuditStats) -> bool:
    return _needs_review_with_config(conversation, audit_stats, review_config=None)


def _needs_review_with_config(
    conversation: WikiConversation,
    audit_stats: _ConversationAuditStats,
    *,
    review_config: WikiConversationReviewConfig | None,
) -> bool:
    assessment = assess_conversation_review(
        WikiConversationReviewSignals(
            denied_count=audit_stats.denied_count.get(conversation.id, 0),
            fallback_count=audit_stats.fallback_count.get(conversation.id, 0),
            no_match_count=audit_stats.no_match_count.get(conversation.id, 0),
            consecutive_no_match_count=audit_stats.consecutive_no_match_count.get(conversation.id, 0),
            avg_latency_ms=audit_stats.avg_latency_ms.get(conversation.id, 0),
            manual_flag=conversation.review_reason == "manual_flag",
        ),
        priority=conversation.priority or "medium",
        status=conversation.status or "open",
        review_config=review_config,
    )
    return assessment.needs_review


def _review_score(conversation: WikiConversation, audit_stats: _ConversationAuditStats) -> int:
    return _review_score_with_config(conversation, audit_stats, review_config=None)


def _review_score_with_config(
    conversation: WikiConversation,
    audit_stats: _ConversationAuditStats,
    *,
    review_config: WikiConversationReviewConfig | None,
) -> int:
    assessment = assess_conversation_review(
        WikiConversationReviewSignals(
            denied_count=audit_stats.denied_count.get(conversation.id, 0),
            fallback_count=audit_stats.fallback_count.get(conversation.id, 0),
            no_match_count=audit_stats.no_match_count.get(conversation.id, 0),
            consecutive_no_match_count=audit_stats.consecutive_no_match_count.get(conversation.id, 0),
            avg_latency_ms=audit_stats.avg_latency_ms.get(conversation.id, 0),
            manual_flag=conversation.review_reason == "manual_flag",
        ),
        priority=conversation.priority or "medium",
        status=conversation.status or "open",
        review_config=review_config,
    )
    return assessment.review_score


def _serialize_message(message: WikiConversationMessage) -> WikiConversationMessageRead:
    return WikiConversationMessageRead(
        id=message.id,
        role=message.role,  # type: ignore[arg-type]
        content=message.content,
        sources=[WikiChunkSource.model_validate(item) for item in _load_json_list(message.sources_json)],
        evidences=[WikiEvidence.model_validate(item) for item in _load_json_list(message.evidences_json)],
        tool_calls=[WikiToolCallSummary.model_validate(item) for item in _load_json_list(message.tool_calls_json)],
        mode=message.mode,  # type: ignore[arg-type]
        found=None if message.found is None else bool(message.found),
        created_at=message.created_at,
    )


def _serialize_event(event: WikiConversationEvent) -> WikiConversationEventRead:
    payload = None
    if event.payload_json:
        try:
            decoded = json.loads(event.payload_json)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, dict):
            payload = decoded
    return WikiConversationEventRead(
        id=event.id,
        event_type=event.event_type,
        actor_username=event.actor_username,
        from_status=event.from_status,  # type: ignore[arg-type]
        to_status=event.to_status,  # type: ignore[arg-type]
        payload=payload,
        created_at=event.created_at,
    )


def _to_summary_read(
    conversation: WikiConversation,
    *,
    audit_stats: _ConversationAuditStats,
    event_stats: _ConversationEventStats,
    review_config: WikiConversationReviewConfig | None,
    message_count: int,
) -> WikiConversationSummaryRead:
    return WikiConversationSummaryRead(
        id=conversation.id,
        title=conversation.title,
        created_by=conversation.created_by,
        context_article=conversation.context_article,
        status=conversation.status,  # type: ignore[arg-type]
        priority=conversation.priority,  # type: ignore[arg-type]
        assigned_to=conversation.assigned_to,
        review_reason=_derive_review_reason_with_config(conversation, audit_stats, review_config=review_config),  # type: ignore[arg-type]
        last_reviewed_at=conversation.last_reviewed_at,
        resolved_by=conversation.resolved_by,
        resolved_at=conversation.resolved_at,
        last_mode=audit_stats.last_mode.get(conversation.id),  # type: ignore[arg-type]
        top_tool_name=audit_stats.top_tool_name.get(conversation.id),
        top_module=audit_stats.top_module.get(conversation.id),
        top_intent=audit_stats.top_intent.get(conversation.id),
        latest_entity_key=audit_stats.latest_entity_key.get(conversation.id),
        latest_context_article=audit_stats.latest_context_article.get(conversation.id) or conversation.context_article,
        denied_count=audit_stats.denied_count.get(conversation.id, 0),
        fallback_count=audit_stats.fallback_count.get(conversation.id, 0),
        no_match_count=audit_stats.no_match_count.get(conversation.id, 0),
        needs_review=_needs_review_with_config(conversation, audit_stats, review_config=review_config),
        review_score=_review_score_with_config(conversation, audit_stats, review_config=review_config),
        last_event_type=event_stats.last_event_type.get(conversation.id),
        last_owner_change_at=event_stats.last_owner_change_at.get(conversation.id),
        reopen_count=event_stats.reopen_count.get(conversation.id, 0),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=message_count,
    )


def _to_read(
    conversation: WikiConversation,
    *,
    audit_stats: _ConversationAuditStats,
    event_stats: _ConversationEventStats,
    review_config: WikiConversationReviewConfig | None,
    messages: list[WikiConversationMessage],
    events: list[WikiConversationEvent],
) -> WikiConversationRead:
    summary = _to_summary_read(
        conversation,
        audit_stats=audit_stats,
        event_stats=event_stats,
        review_config=review_config,
        message_count=len(messages),
    )
    return WikiConversationRead(
        **summary.model_dump(),
        messages=[_serialize_message(item) for item in messages],
        events=[_serialize_event(item) for item in events],
    )


def sync_conversation_review_state(
    db: Session,
    *,
    conversation: WikiConversation,
    audit_stats: _ConversationAuditStats | None = None,
) -> None:
    stats = audit_stats or _build_conversation_audit_stats(db)
    config = get_or_create_wiki_conversation_governance_config(db)
    review_config = WikiConversationReviewConfig(
        fallback_heavy_threshold=config.fallback_heavy_threshold,
        no_match_repeated_threshold=config.no_match_repeated_threshold,
        high_latency_ms_threshold=config.high_latency_ms_threshold,
    )
    derived_reason = _derive_review_reason_with_config(conversation, stats, review_config=review_config)
    if conversation.review_reason != "manual_flag":
        conversation.review_reason = derived_reason


def get_or_create_wiki_conversation(
    db: Session,
    *,
    current_user: ApplicationUser,
    question: str,
    context_article: str | None,
    conversation_id: uuid.UUID | None,
) -> WikiConversation:
    if conversation_id is not None:
        conversation = db.get(WikiConversation, conversation_id)
        if conversation is None or not _can_access_conversation(current_user, conversation):
            raise ValueError("Conversazione Wiki non trovata o non accessibile.")
        if context_article and not conversation.context_article:
            conversation.context_article = context_article
            db.commit()
            db.refresh(conversation)
        return conversation

    conversation = WikiConversation(
        id=uuid.uuid4(),
        title=_conversation_title(question),
        created_by=current_user.username,
        context_article=context_article,
        status="open",
        priority="medium",
    )
    db.add(conversation)
    _record_conversation_event(
        db,
        conversation=conversation,
        event_type="created",
        actor_username=current_user.username,
        to_status=conversation.status,
        payload={"priority": conversation.priority, "context_article": context_article or ""},
    )
    db.commit()
    db.refresh(conversation)
    return conversation


def persist_wiki_conversation_turn(
    db: Session,
    *,
    conversation: WikiConversation,
    question: str,
    response: WikiChatResponse,
) -> WikiConversationPersistResult:
    user_message = WikiConversationMessage(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role="user",
        content=question,
    )
    assistant_message = WikiConversationMessage(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role="assistant",
        content=response.answer,
        found=1 if response.found else 0,
        mode=response.mode,
        sources_json=_dump_json([item.model_dump(mode="json") for item in response.sources]),
        evidences_json=_dump_json([item.model_dump(mode="json") for item in response.evidences]),
        tool_calls_json=_dump_json([item.model_dump(mode="json") for item in response.tool_calls]),
    )
    db.add(user_message)
    db.add(assistant_message)
    conversation.updated_at = func.now()
    _record_conversation_event(
        db,
        conversation=conversation,
        event_type="message_appended",
        actor_username=conversation.created_by,
        to_status=conversation.status,
        payload={"mode": response.mode, "found": response.found},
    )
    if conversation.status == "resolved":
        previous_status = conversation.status
        conversation.status = "open"
        conversation.resolved_by = None
        conversation.resolved_at = None
        _record_conversation_event(
            db,
            conversation=conversation,
            event_type="status_changed",
            actor_username=conversation.created_by,
            from_status=previous_status,
            to_status="open",
            payload={"reason": "new_message"},
        )
    db.commit()
    return WikiConversationPersistResult(
        conversation_id=conversation.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
    )


def get_wiki_conversation(
    db: Session,
    *,
    conversation_id: uuid.UUID,
    current_user: ApplicationUser,
) -> WikiConversationRead | None:
    conversation = db.get(WikiConversation, conversation_id)
    if conversation is None or not _can_access_conversation(current_user, conversation):
        return None
    messages = db.scalars(
        select(WikiConversationMessage)
        .where(WikiConversationMessage.conversation_id == conversation.id)
        .order_by(WikiConversationMessage.created_at.asc())
    ).all()
    events = db.scalars(
        select(WikiConversationEvent)
        .where(WikiConversationEvent.conversation_id == conversation.id)
        .order_by(WikiConversationEvent.created_at.desc())
        .limit(20)
    ).all()
    audit_stats = _build_conversation_audit_stats(db)
    event_stats = _build_conversation_event_stats(db)
    config = get_or_create_wiki_conversation_governance_config(db)
    review_config = WikiConversationReviewConfig(
        fallback_heavy_threshold=config.fallback_heavy_threshold,
        no_match_repeated_threshold=config.no_match_repeated_threshold,
        high_latency_ms_threshold=config.high_latency_ms_threshold,
    )
    return _to_read(
        conversation,
        audit_stats=audit_stats,
        event_stats=event_stats,
        review_config=review_config,
        messages=messages,
        events=events,
    )


def list_wiki_conversations(
    db: Session,
    *,
    current_user: ApplicationUser,
    limit: int = 30,
    search: str | None = None,
    created_by: str | None = None,
    context_article: str | None = None,
    status: str | None = None,
    assigned_to: str | None = None,
    priority: str | None = None,
    needs_review: bool | None = None,
    review_reason: str | None = None,
) -> list[WikiConversationSummaryRead]:
    query = select(WikiConversation).order_by(WikiConversation.updated_at.desc())
    if not _is_admin(current_user):
        query = query.where(WikiConversation.created_by == current_user.username)
    elif created_by:
        query = query.where(WikiConversation.created_by == created_by)
    if context_article:
        query = query.where(WikiConversation.context_article == context_article)
    if status:
        query = query.where(WikiConversation.status == status)
    if assigned_to:
        query = query.where(WikiConversation.assigned_to == assigned_to)
    if priority:
        query = query.where(WikiConversation.priority == priority)
    if review_reason:
        query = query.where(WikiConversation.review_reason == review_reason)
    if search:
        normalized_search = f"%{search.strip()}%"
        matching_ids = select(WikiConversationMessage.conversation_id).where(
            WikiConversationMessage.content.ilike(normalized_search)
        )
        query = query.where(
            or_(
                WikiConversation.title.ilike(normalized_search),
                WikiConversation.context_article.ilike(normalized_search),
                WikiConversation.id.in_(matching_ids),
            )
        )

    conversations = db.scalars(query.limit(limit)).all()
    rows = db.execute(
        select(
            WikiConversationMessage.conversation_id,
            func.count().label("message_count"),
        )
        .group_by(WikiConversationMessage.conversation_id)
    ).all()
    count_map = {row.conversation_id: int(row.message_count or 0) for row in rows}
    audit_stats = _build_conversation_audit_stats(db)
    event_stats = _build_conversation_event_stats(db)
    config = get_or_create_wiki_conversation_governance_config(db)
    review_config = WikiConversationReviewConfig(
        fallback_heavy_threshold=config.fallback_heavy_threshold,
        no_match_repeated_threshold=config.no_match_repeated_threshold,
        high_latency_ms_threshold=config.high_latency_ms_threshold,
    )

    summaries = [
        _to_summary_read(
            item,
            audit_stats=audit_stats,
            event_stats=event_stats,
            review_config=review_config,
            message_count=count_map.get(item.id, 0),
        )
        for item in conversations
    ]
    if needs_review is not None:
        summaries = [item for item in summaries if item.needs_review is needs_review]
    if review_reason:
        summaries = [item for item in summaries if item.review_reason == review_reason]
    return sorted(
        summaries,
        key=lambda item: (
            0 if item.needs_review else 1,
            PRIORITY_ORDER.get(item.priority, 1),
            -item.review_score,
            STATUS_ORDER.get(item.status, 99),
            item.updated_at,
        ),
        reverse=False,
    )[:limit]


def summarize_wiki_conversations(
    db: Session,
    *,
    current_user: ApplicationUser,
    limit_review_items: int = 10,
) -> WikiConversationSummaryMetricsRead:
    query = select(WikiConversation).order_by(WikiConversation.updated_at.desc())
    if not _is_admin(current_user):
        query = query.where(WikiConversation.created_by == current_user.username)
    conversations = db.scalars(query).all()
    audit_stats = _build_conversation_audit_stats(db)
    event_stats = _build_conversation_event_stats(db)
    config = get_or_create_wiki_conversation_governance_config(db)
    review_config = WikiConversationReviewConfig(
        fallback_heavy_threshold=config.fallback_heavy_threshold,
        no_match_repeated_threshold=config.no_match_repeated_threshold,
        high_latency_ms_threshold=config.high_latency_ms_threshold,
    )
    summary_items = [
        _to_summary_read(item, audit_stats=audit_stats, event_stats=event_stats, review_config=review_config, message_count=0)
        for item in conversations
    ]
    open_items = [item for item in summary_items if item.status == "open"]
    review_items = [item for item in summary_items if item.needs_review]

    mode_counts: Counter[str] = Counter()
    tool_counts: Counter[str] = Counter()
    review_reason_counts: Counter[str] = Counter()
    backlog_by_status: Counter[str] = Counter()
    backlog_by_priority: Counter[str] = Counter()
    backlog_by_owner: Counter[str] = Counter()
    aging_buckets: Counter[str] = Counter()
    now = _utc_now()
    review_hours: list[float] = []
    resolve_hours: list[float] = []

    for item in summary_items:
        if item.last_mode:
            mode_counts[item.last_mode] += 1
        if item.top_tool_name:
            tool_counts[item.top_tool_name] += 1
        if item.review_reason:
            review_reason_counts[item.review_reason] += 1
        backlog_by_status[item.status] += 1
        backlog_by_priority[item.priority] += 1
        backlog_by_owner[_normalize_owner_key(item.assigned_to)] += 1
        aging_buckets[_aging_bucket(now, item.created_at)] += 1
        review_delta = _hours_between(item.created_at, item.last_reviewed_at)
        if review_delta is not None:
            review_hours.append(review_delta)
        resolve_delta = _hours_between(item.created_at, item.resolved_at)
        if resolve_delta is not None:
            resolve_hours.append(resolve_delta)

    def counts_to_reads(counter: Counter[str]) -> list[WikiMetricCountRead]:
        return [WikiMetricCountRead(key=key, count=count) for key, count in sorted(counter.items(), key=lambda pair: (-pair[1], pair[0]))]

    return WikiConversationSummaryMetricsRead(
        total=len(summary_items),
        open_count=sum(1 for item in summary_items if item.status == "open"),
        in_review_count=sum(1 for item in summary_items if item.status == "in_review"),
        waiting_user_count=sum(1 for item in summary_items if item.status == "waiting_user"),
        resolved_count=sum(1 for item in summary_items if item.status == "resolved"),
        needs_review_count=len(review_items),
        high_priority_count=sum(1 for item in summary_items if item.priority == "high"),
        unassigned_review_count=sum(1 for item in review_items if not item.assigned_to),
        open_denied_count=sum(1 for item in open_items if item.denied_count > 0),
        open_fallback_count=sum(1 for item in open_items if item.fallback_count > 0),
        avg_time_to_review_hours=round(sum(review_hours) / len(review_hours), 2) if review_hours else 0,
        avg_time_to_resolve_hours=round(sum(resolve_hours) / len(resolve_hours), 2) if resolve_hours else 0,
        top_mode=(mode_counts.most_common(1)[0][0] if mode_counts else None),
        top_tool=(tool_counts.most_common(1)[0][0] if tool_counts else None),
        top_review_reasons=counts_to_reads(review_reason_counts)[:5],
        backlog_by_status=counts_to_reads(backlog_by_status),
        backlog_by_priority=counts_to_reads(backlog_by_priority),
        backlog_by_owner=counts_to_reads(backlog_by_owner),
        aging_buckets=counts_to_reads(aging_buckets),
        items_needing_review=sorted(
            review_items,
            key=lambda item: (
                PRIORITY_ORDER.get(item.priority, 1),
                -item.review_score,
                item.assigned_to is not None,
                item.updated_at,
            ),
        )[:limit_review_items],
    )


def update_wiki_conversation(
    db: Session,
    *,
    conversation_id: uuid.UUID,
    current_user: ApplicationUser,
    payload: WikiConversationUpdate,
) -> WikiConversationRead | None:
    conversation = db.get(WikiConversation, conversation_id)
    if conversation is None:
        return None
    if not _can_manage_conversation(current_user, conversation):
        raise PermissionError("Permessi insufficienti per aggiornare la conversazione Wiki.")

    changes = payload.model_dump(exclude_unset=True)
    previous_status = conversation.status
    if "assigned_to" in changes:
        previous_assigned_to = conversation.assigned_to
        conversation.assigned_to = changes["assigned_to"]
        _record_conversation_event(
            db,
            conversation=conversation,
            event_type="assignment_changed",
            actor_username=current_user.username,
            to_status=conversation.status,
            payload={"from": previous_assigned_to or "", "to": changes["assigned_to"] or ""},
        )
    if "priority" in changes:
        previous_priority = conversation.priority
        conversation.priority = changes["priority"]
        _record_conversation_event(
            db,
            conversation=conversation,
            event_type="priority_changed",
            actor_username=current_user.username,
            to_status=conversation.status,
            payload={"from": previous_priority, "to": changes["priority"]},
        )
    if "status" in changes:
        conversation.status = changes["status"]
        if changes["status"] in {"in_review", "resolved"}:
            conversation.last_reviewed_at = func.now()
        if changes["status"] == "resolved":
            conversation.resolved_by = current_user.username
            conversation.resolved_at = func.now()
        else:
            conversation.resolved_by = None
            conversation.resolved_at = None
        _record_conversation_event(
            db,
            conversation=conversation,
            event_type="status_changed",
            actor_username=current_user.username,
            from_status=previous_status,
            to_status=changes["status"],
            payload={},
        )
    if changes and _is_admin(current_user):
        conversation.last_reviewed_at = func.now()
    sync_conversation_review_state(db, conversation=conversation)
    db.commit()
    return get_wiki_conversation(db, conversation_id=conversation_id, current_user=current_user)


def flag_wiki_conversation(
    db: Session,
    *,
    conversation_id: uuid.UUID,
    current_user: ApplicationUser,
    payload: WikiConversationFlagUpdate,
) -> WikiConversationRead | None:
    conversation = db.get(WikiConversation, conversation_id)
    if conversation is None:
        return None
    if not _is_admin(current_user):
        raise PermissionError("Solo admin e super_admin possono flaggare la conversazione Wiki.")
    previous_status = conversation.status
    conversation.review_reason = payload.review_reason
    conversation.last_reviewed_at = func.now()
    if conversation.status == "open":
        conversation.status = "in_review"
    _record_conversation_event(
        db,
        conversation=conversation,
        event_type="flagged",
        actor_username=current_user.username,
        from_status=previous_status,
        to_status=conversation.status,
        payload={"review_reason": payload.review_reason},
    )
    db.commit()
    return get_wiki_conversation(db, conversation_id=conversation_id, current_user=current_user)
