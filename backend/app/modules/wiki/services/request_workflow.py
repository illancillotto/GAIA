from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.models import WikiRequest, WikiRequestEvent
from app.modules.wiki.schemas import (
    WikiRequestCreate,
    WikiRequestDuplicateCandidateRead,
    WikiRequestFamilyRead,
    WikiRequestFeedbackUpdate,
    WikiRequestMakeCanonicalInput,
    WikiRequestReopenInput,
    WikiRequestStatusUpdate,
)

_TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9]+")
_REQUEST_STOPWORDS = {
    "a",
    "ad",
    "al",
    "alla",
    "allo",
    "anche",
    "che",
    "con",
    "come",
    "da",
    "dei",
    "del",
    "della",
    "delle",
    "di",
    "e",
    "ed",
    "gli",
    "ho",
    "il",
    "in",
    "la",
    "le",
    "lo",
    "ma",
    "mi",
    "nei",
    "nel",
    "nella",
    "non",
    "per",
    "piu",
    "su",
    "the",
    "to",
    "un",
    "una",
    "uno",
}


def derive_request_type_from_category(category: str) -> str:
    if category == "bug_report":
        return "bug_report"
    if category in {"question", "support_request"}:
        return "help_request"
    return "feature_request"


def legacy_status_to_workflow(status_value: str | None) -> str:
    if status_value == "pending":
        return "new"
    if status_value == "reviewed":
        return "triaged"
    if status_value == "done":
        return "resolved"
    return status_value or "new"


def normalize_request_text(value: str | None) -> str:
    normalized = _TOKEN_SPLIT_RE.sub(" ", (value or "").lower()).strip()
    return " ".join(normalized.split())


def request_tokens(*parts: str | None) -> set[str]:
    tokens: set[str] = set()
    for part in parts:
        normalized = normalize_request_text(part)
        for token in normalized.split():
            if len(token) < 3 or token in _REQUEST_STOPWORDS:
                continue
            tokens.add(token)
    return tokens


def build_request_dedupe_key(
    *,
    request_type: str | None,
    module_key: str | None,
    page_path: str | None,
    context_entity_key: str | None,
    user_question: str | None,
) -> str | None:
    question = normalize_request_text(user_question)
    if not question:
        return None
    page = normalize_request_text(page_path)
    if page.startswith("wiki requests "):
        page = ""
    return "|".join(
        [
            (request_type or "").strip().lower() or "unknown",
            (module_key or "").strip().lower() or "unknown",
            page or "unknown",
            normalize_request_text(context_entity_key) or "unknown",
            question,
        ]
    )


def request_similarity(source: WikiRequest, candidate: WikiRequest) -> tuple[float, str]:
    source_tokens = request_tokens(
        source.user_question,
        source.desired_outcome,
        source.observed_behavior,
        source.expected_behavior,
    )
    candidate_tokens = request_tokens(
        candidate.user_question,
        candidate.desired_outcome,
        candidate.observed_behavior,
        candidate.expected_behavior,
    )
    if not source_tokens or not candidate_tokens:
        return 0.0, "testo insufficiente"

    overlap = len(source_tokens & candidate_tokens)
    score = overlap / max(1, min(len(source_tokens), len(candidate_tokens)))
    if source.request_type == candidate.request_type:
        score += 0.12
    if source.module_key and source.module_key == candidate.module_key:
        score += 0.10
    if source.page_path and source.page_path == candidate.page_path:
        score += 0.08
    if source.context_entity_key and source.context_entity_key == candidate.context_entity_key:
        score += 0.16

    if source.dedupe_key and source.dedupe_key == candidate.dedupe_key:
        return 1.0, "contesto e testo quasi identici"
    if source.context_entity_key and source.context_entity_key == candidate.context_entity_key:
        return min(score, 0.98), "stessa entità e sintomi simili"
    if source.module_key and source.module_key == candidate.module_key and overlap >= 2:
        return min(score, 0.95), "stesso modulo con lessico sovrapponibile"
    if overlap >= 3:
        return min(score, 0.9), "descrizione molto simile"
    return score, "somiglianza debole"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def append_request_event(
    db: Session,
    *,
    request_id: uuid.UUID,
    event_type: str,
    actor_username: str | None,
    from_status: str | None = None,
    to_status: str | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    db.add(
        WikiRequestEvent(
            id=uuid.uuid4(),
            request_id=request_id,
            event_type=event_type,
            actor_username=actor_username,
            from_status=from_status,
            to_status=to_status,
            payload_json=json.dumps(payload, ensure_ascii=True) if payload else None,
        )
    )


def build_request_from_payload(payload: WikiRequestCreate, *, current_user: ApplicationUser) -> WikiRequest:
    request_type = payload.request_type or derive_request_type_from_category(payload.category)
    return WikiRequest(
        id=uuid.uuid4(),
        user_question=payload.user_question,
        agent_response=payload.agent_response,
        category=payload.category,
        request_type=request_type,
        status="new",
        priority="medium",
        severity=payload.severity,
        created_by=current_user.username,
        module_key=payload.module_key,
        page_path=payload.page_path,
        source_channel=payload.source_channel,
        impact_scope=payload.impact_scope,
        conversation_id=payload.conversation_id,
        context_article=payload.context_article,
        context_entity_key=payload.context_entity_key,
        dedupe_key=build_request_dedupe_key(
            request_type=request_type,
            module_key=payload.module_key,
            page_path=payload.page_path,
            context_entity_key=payload.context_entity_key,
            user_question=payload.user_question,
        ),
        desired_outcome=payload.desired_outcome,
        observed_behavior=payload.observed_behavior,
        expected_behavior=payload.expected_behavior,
    )


def append_created_event(db: Session, *, req: WikiRequest, payload: WikiRequestCreate, actor_username: str) -> None:
    append_request_event(
        db,
        request_id=req.id,
        event_type="created",
        actor_username=actor_username,
        to_status="new",
        payload={
            "category": payload.category,
            "request_type": payload.request_type or derive_request_type_from_category(payload.category),
            "source_channel": payload.source_channel,
            "module_key": payload.module_key,
            "severity": payload.severity,
        },
    )


def linked_duplicate_candidates(
    db: Session,
    canonical_request_id: uuid.UUID,
    *,
    serialize_duplicate_candidate: Callable[[Session, WikiRequest, float, str], WikiRequestDuplicateCandidateRead],
) -> list[WikiRequestDuplicateCandidateRead]:
    linked = (
        db.query(WikiRequest)
        .filter(WikiRequest.canonical_request_id == canonical_request_id)
        .order_by(WikiRequest.updated_at.desc(), WikiRequest.created_at.desc())
        .all()
    )
    return [
        serialize_duplicate_candidate(db, item, 1.0, "collegata a questo caso canonico")
        for item in linked
    ]


def resolve_family_canonical(db: Session, req: WikiRequest) -> WikiRequest:
    if req.canonical_request_id is None:
        return req
    canonical = db.query(WikiRequest).filter(WikiRequest.id == req.canonical_request_id).first()
    return canonical or req


def build_request_family(
    db: Session,
    req: WikiRequest,
    *,
    serialize_request: Callable[[Session, WikiRequest], object],
    serialize_duplicate_candidate: Callable[[Session, WikiRequest, float, str], WikiRequestDuplicateCandidateRead],
) -> WikiRequestFamilyRead:
    canonical = resolve_family_canonical(db, req)
    linked = linked_duplicate_candidates(db, canonical.id, serialize_duplicate_candidate=serialize_duplicate_candidate)
    created_timestamps = [canonical.created_at, *[item.created_at for item in linked]]
    affected_users = len({value for value in [canonical.created_by, *[item.created_by for item in linked]] if value})
    latest_created_at = max(created_timestamps) if created_timestamps else None
    return WikiRequestFamilyRead(
        canonical_request=serialize_request(db, canonical),
        linked_duplicates=linked,
        family_size=1 + len(linked),
        affected_users=affected_users,
        latest_created_at=latest_created_at,
    )


def reopen_request_for_user(
    db: Session,
    *,
    req: WikiRequest,
    payload: WikiRequestReopenInput,
    current_user: ApplicationUser,
) -> None:
    current_status = legacy_status_to_workflow(req.status)
    if current_status not in {"resolved", "duplicate", "rejected", "planned", "waiting_user"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Lo stato attuale non consente la riapertura.")

    previous_canonical_id = req.canonical_request_id
    req.status = "investigating"
    req.canonical_request_id = None
    req.user_feedback_rating = "not_helpful"
    req.user_feedback_notes = payload.reason or req.user_feedback_notes
    req.user_feedback_submitted_at = now_utc()
    req.user_last_viewed_at = req.user_feedback_submitted_at
    req.last_admin_update_at = req.user_feedback_submitted_at
    append_request_event(
        db,
        request_id=req.id,
        event_type="reopened_by_user",
        actor_username=current_user.username,
        from_status=current_status,
        to_status="investigating",
        payload={
            "reason": payload.reason,
            "previous_canonical_request_id": str(previous_canonical_id) if previous_canonical_id else None,
        },
    )


def mark_request_duplicate(
    db: Session,
    *,
    req: WikiRequest,
    canonical: WikiRequest,
    admin_notes: str | None,
    current_user: ApplicationUser,
) -> None:
    if canonical.id == req.id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Una richiesta non può essere duplicata di se stessa.")

    previous_status = legacy_status_to_workflow(req.status)
    previous_canonical_id = req.canonical_request_id
    req.status = "duplicate"
    req.canonical_request_id = canonical.id
    if admin_notes is not None:
        req.admin_notes = admin_notes
    req.last_admin_update_at = now_utc()
    if req.dedupe_key is None:
        req.dedupe_key = build_request_dedupe_key(
            request_type=req.request_type,
            module_key=req.module_key,
            page_path=req.page_path,
            context_entity_key=req.context_entity_key,
            user_question=req.user_question,
        )

    if previous_status != "duplicate":
        append_request_event(
            db,
            request_id=req.id,
            event_type="status_changed",
            actor_username=current_user.username,
            from_status=previous_status,
            to_status="duplicate",
        )
    append_request_event(
        db,
        request_id=req.id,
        event_type="marked_duplicate",
        actor_username=current_user.username,
        payload={
            "from_canonical_request_id": str(previous_canonical_id) if previous_canonical_id else None,
            "canonical_request_id": str(canonical.id),
            "canonical_request_question": canonical.user_question,
        },
    )
    append_request_event(
        db,
        request_id=canonical.id,
        event_type="duplicate_linked",
        actor_username=current_user.username,
        payload={
            "duplicate_request_id": str(req.id),
            "duplicate_request_question": req.user_question,
        },
    )


def unlink_request_duplicate(
    db: Session,
    *,
    req: WikiRequest,
    current_user: ApplicationUser,
) -> None:
    if req.canonical_request_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La richiesta non è collegata a un caso canonico.")

    previous_canonical_id = req.canonical_request_id
    current_status = legacy_status_to_workflow(req.status)
    req.canonical_request_id = None
    if current_status == "duplicate":
        req.status = "triaged"
        append_request_event(
            db,
            request_id=req.id,
            event_type="status_changed",
            actor_username=current_user.username,
            from_status="duplicate",
            to_status="triaged",
        )
    append_request_event(
        db,
        request_id=req.id,
        event_type="duplicate_unlinked",
        actor_username=current_user.username,
        payload={"previous_canonical_request_id": str(previous_canonical_id)},
    )
    req.last_admin_update_at = now_utc()


def make_request_canonical(
    db: Session,
    *,
    target: WikiRequest,
    payload: WikiRequestMakeCanonicalInput,
    current_user: ApplicationUser,
) -> None:
    current_canonical = resolve_family_canonical(db, target)
    if current_canonical.id == target.id and target.canonical_request_id is None:
        return

    family_duplicates = db.query(WikiRequest).filter(WikiRequest.canonical_request_id == current_canonical.id).all()
    for item in family_duplicates:
        if item.id == target.id:
            continue
        item.canonical_request_id = target.id
        append_request_event(
            db,
            request_id=item.id,
            event_type="canonical_reassigned",
            actor_username=current_user.username,
            payload={
                "from_canonical_request_id": str(current_canonical.id),
                "to_canonical_request_id": str(target.id),
            },
        )

    previous_target_status = legacy_status_to_workflow(target.status)
    previous_target_canonical = target.canonical_request_id
    target.canonical_request_id = None
    if previous_target_status == "duplicate":
        target.status = "triaged"
        append_request_event(
            db,
            request_id=target.id,
            event_type="status_changed",
            actor_username=current_user.username,
            from_status="duplicate",
            to_status="triaged",
        )
    if payload.admin_notes is not None:
        target.admin_notes = payload.admin_notes
    target.last_admin_update_at = now_utc()
    append_request_event(
        db,
        request_id=target.id,
        event_type="canonical_promoted",
        actor_username=current_user.username,
        payload={
            "from_canonical_request_id": str(previous_target_canonical) if previous_target_canonical else None,
        },
    )

    if current_canonical.id != target.id:
        previous_canonical_status = legacy_status_to_workflow(current_canonical.status)
        current_canonical.canonical_request_id = target.id
        current_canonical.status = "duplicate"
        current_canonical.last_admin_update_at = now_utc()
        if previous_canonical_status != "duplicate":
            append_request_event(
                db,
                request_id=current_canonical.id,
                event_type="status_changed",
                actor_username=current_user.username,
                from_status=previous_canonical_status,
                to_status="duplicate",
            )
        append_request_event(
            db,
            request_id=current_canonical.id,
            event_type="canonical_demoted",
            actor_username=current_user.username,
            payload={
                "new_canonical_request_id": str(target.id),
                "new_canonical_request_question": target.user_question,
            },
        )


def update_request_feedback_fields(
    db: Session,
    *,
    req: WikiRequest,
    payload: WikiRequestFeedbackUpdate,
    current_user: ApplicationUser,
) -> None:
    req.user_feedback_rating = payload.rating
    req.user_feedback_notes = payload.notes
    req.user_feedback_submitted_at = now_utc()
    req.user_last_viewed_at = req.user_feedback_submitted_at
    append_request_event(
        db,
        request_id=req.id,
        event_type="user_feedback_submitted",
        actor_username=current_user.username,
        payload={"rating": payload.rating},
    )


def apply_request_status_update(
    db: Session,
    *,
    req: WikiRequest,
    payload: WikiRequestStatusUpdate,
    current_user: ApplicationUser,
) -> None:
    current_status = legacy_status_to_workflow(req.status)

    if payload.status is not None and payload.status != current_status:
        if payload.status == "duplicate" and req.canonical_request_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Per marcare una richiesta come duplicata usa il caso canonico dedicato.",
            )
        req.status = payload.status
        if payload.status != "duplicate" and req.canonical_request_id is not None:
            previous_canonical = req.canonical_request_id
            req.canonical_request_id = None
            append_request_event(
                db,
                request_id=req.id,
                event_type="duplicate_cleared",
                actor_username=current_user.username,
                payload={"previous_canonical_request_id": str(previous_canonical)},
            )
        append_request_event(
            db,
            request_id=req.id,
            event_type="status_changed",
            actor_username=current_user.username,
            from_status=current_status,
            to_status=payload.status,
        )
    if payload.priority is not None:
        old_priority = req.priority
        req.priority = payload.priority
        if payload.priority != old_priority:
            append_request_event(
                db,
                request_id=req.id,
                event_type="priority_changed",
                actor_username=current_user.username,
                payload={"from": old_priority, "to": payload.priority},
            )
    if payload.severity is not None:
        old_severity = req.severity
        req.severity = payload.severity
        if payload.severity != old_severity:
            append_request_event(
                db,
                request_id=req.id,
                event_type="severity_changed",
                actor_username=current_user.username,
                payload={"from": old_severity, "to": payload.severity},
            )
    if payload.assigned_to is not None:
        old_assigned_to = req.assigned_to
        assigned_to = payload.assigned_to.strip()
        if assigned_to:
            assignee = db.query(ApplicationUser).filter(ApplicationUser.username == assigned_to).first()
            if not assignee:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Assegnatario non valido.")
            req.assigned_to = assignee.username
        else:
            req.assigned_to = None
        if req.assigned_to != old_assigned_to:
            append_request_event(
                db,
                request_id=req.id,
                event_type="assignee_changed",
                actor_username=current_user.username,
                payload={"from": old_assigned_to, "to": req.assigned_to},
            )
    if payload.resolution_message is not None:
        old_resolution_message = req.resolution_message or ""
        req.resolution_message = payload.resolution_message
        if (payload.resolution_message or "") != old_resolution_message:
            append_request_event(db, request_id=req.id, event_type="resolution_message_updated", actor_username=current_user.username)
    if payload.admin_notes is not None:
        old_notes = req.admin_notes or ""
        req.admin_notes = payload.admin_notes
        if (payload.admin_notes or "") != old_notes:
            append_request_event(db, request_id=req.id, event_type="notes_updated", actor_username=current_user.username)
    if payload.external_ticket_key is not None:
        old_ticket_key = req.external_ticket_key or ""
        req.external_ticket_key = payload.external_ticket_key or None
        if (req.external_ticket_key or "") != old_ticket_key:
            append_request_event(
                db,
                request_id=req.id,
                event_type="external_ticket_key_updated",
                actor_username=current_user.username,
                payload={"from": old_ticket_key or None, "to": req.external_ticket_key},
            )
    if payload.external_ticket_url is not None:
        old_ticket_url = req.external_ticket_url or ""
        req.external_ticket_url = payload.external_ticket_url or None
        if (req.external_ticket_url or "") != old_ticket_url:
            append_request_event(db, request_id=req.id, event_type="external_ticket_url_updated", actor_username=current_user.username)
    if payload.delivery_status is not None:
        old_delivery_status = req.delivery_status
        req.delivery_status = payload.delivery_status
        if req.delivery_status != old_delivery_status:
            append_request_event(
                db,
                request_id=req.id,
                event_type="delivery_status_changed",
                actor_username=current_user.username,
                payload={"from": old_delivery_status, "to": req.delivery_status},
            )
    if payload.delivery_notes is not None:
        old_delivery_notes = req.delivery_notes or ""
        req.delivery_notes = payload.delivery_notes
        if (payload.delivery_notes or "") != old_delivery_notes:
            append_request_event(db, request_id=req.id, event_type="delivery_notes_updated", actor_username=current_user.username)
    req.last_admin_update_at = now_utc()
