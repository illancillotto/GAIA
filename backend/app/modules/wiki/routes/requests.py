import logging
import json
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.wiki.models import WikiRequest, WikiRequestEvent
from app.modules.wiki.schemas import (
    WikiRequestAssigneeRead,
    WikiRequestCreate,
    WikiRequestDuplicateCandidateRead,
    WikiRequestDuplicateMarkInput,
    WikiRequestEventRead,
    WikiRequestFeedbackUpdate,
    WikiRequestRead,
    WikiRequestStatusUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Wiki"])
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


def _derive_request_type_from_category(category: str) -> str:
    if category == "bug_report":
        return "bug_report"
    if category == "question":
        return "help_request"
    if category == "support_request":
        return "help_request"
    return "feature_request"


def _legacy_status_to_workflow(status_value: str | None) -> str:
    if status_value == "pending":
        return "new"
    if status_value == "reviewed":
        return "triaged"
    if status_value == "done":
        return "resolved"
    return status_value or "new"


def _normalize_request_text(value: str | None) -> str:
    normalized = _TOKEN_SPLIT_RE.sub(" ", (value or "").lower()).strip()
    return " ".join(normalized.split())


def _request_tokens(*parts: str | None) -> set[str]:
    tokens: set[str] = set()
    for part in parts:
        normalized = _normalize_request_text(part)
        for token in normalized.split():
            if len(token) < 3 or token in _REQUEST_STOPWORDS:
                continue
            tokens.add(token)
    return tokens


def _build_request_dedupe_key(
    *,
    request_type: str | None,
    module_key: str | None,
    page_path: str | None,
    context_entity_key: str | None,
    user_question: str | None,
) -> str | None:
    question = _normalize_request_text(user_question)
    if not question:
        return None
    page = _normalize_request_text(page_path)
    if page.startswith("wiki requests "):
        page = ""
    return "|".join(
        [
            (request_type or "").strip().lower() or "unknown",
            (module_key or "").strip().lower() or "unknown",
            page or "unknown",
            _normalize_request_text(context_entity_key) or "unknown",
            question,
        ]
    )


def _request_similarity(source: WikiRequest, candidate: WikiRequest) -> tuple[float, str]:
    source_tokens = _request_tokens(
        source.user_question,
        source.desired_outcome,
        source.observed_behavior,
        source.expected_behavior,
    )
    candidate_tokens = _request_tokens(
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


def _require_wiki_admin(current_user: ApplicationUser) -> None:
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso negato.")


def _append_request_event(
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


def _serialize_request_event(item: WikiRequestEvent) -> WikiRequestEventRead:
    payload: dict[str, object] | None = None
    if item.payload_json:
        try:
            parsed = json.loads(item.payload_json)
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError:
            payload = None
    return WikiRequestEventRead(
        id=item.id,
        request_id=item.request_id,
        event_type=item.event_type,
        actor_username=item.actor_username,
        from_status=item.from_status,
        to_status=item.to_status,
        payload=payload,
        created_at=item.created_at,
    )


def _serialize_wiki_request_read(db: Session, req: WikiRequest) -> WikiRequestRead:
    assigned_to_name: str | None = None
    canonical_request_question: str | None = None
    canonical_request_status: str | None = None
    if req.assigned_to:
        assignee = db.query(ApplicationUser).filter(ApplicationUser.username == req.assigned_to).first()
        if assignee:
            assigned_to_name = assignee.full_name or assignee.username
        else:
            assigned_to_name = req.assigned_to
    if req.canonical_request_id:
        canonical = db.query(WikiRequest).filter(WikiRequest.id == req.canonical_request_id).first()
        if canonical:
            canonical_request_question = canonical.user_question
            canonical_request_status = _legacy_status_to_workflow(canonical.status)
    has_unread_update = False
    if req.last_admin_update_at is not None:
        has_unread_update = req.user_last_viewed_at is None or req.last_admin_update_at > req.user_last_viewed_at
    return WikiRequestRead(
        id=req.id,
        user_question=req.user_question,
        agent_response=req.agent_response,
        category=req.category,
        request_type=req.request_type,
        status=_legacy_status_to_workflow(req.status),
        priority=req.priority,
        severity=req.severity,
        created_by=req.created_by,
        assigned_to=req.assigned_to,
        assigned_to_name=assigned_to_name,
        module_key=req.module_key,
        page_path=req.page_path,
        source_channel=req.source_channel,
        impact_scope=req.impact_scope,
        conversation_id=req.conversation_id,
        context_article=req.context_article,
        context_entity_key=req.context_entity_key,
        dedupe_key=req.dedupe_key,
        canonical_request_id=req.canonical_request_id,
        canonical_request_question=canonical_request_question,
        canonical_request_status=canonical_request_status,
        desired_outcome=req.desired_outcome,
        observed_behavior=req.observed_behavior,
        expected_behavior=req.expected_behavior,
        resolution_message=req.resolution_message,
        last_admin_update_at=req.last_admin_update_at,
        user_last_viewed_at=req.user_last_viewed_at,
        has_unread_update=has_unread_update,
        user_feedback_rating=req.user_feedback_rating,
        user_feedback_notes=req.user_feedback_notes,
        user_feedback_submitted_at=req.user_feedback_submitted_at,
        admin_notes=req.admin_notes,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


def _serialize_duplicate_candidate(db: Session, req: WikiRequest, *, similarity_score: float, match_reason: str) -> WikiRequestDuplicateCandidateRead:
    assigned_to_name: str | None = None
    if req.assigned_to:
        assignee = db.query(ApplicationUser).filter(ApplicationUser.username == req.assigned_to).first()
        assigned_to_name = assignee.full_name or assignee.username if assignee else req.assigned_to
    return WikiRequestDuplicateCandidateRead(
        id=req.id,
        user_question=req.user_question,
        request_type=req.request_type,
        status=_legacy_status_to_workflow(req.status),
        module_key=req.module_key,
        page_path=req.page_path,
        created_by=req.created_by,
        assigned_to_name=assigned_to_name,
        created_at=req.created_at,
        similarity_score=round(similarity_score, 3),
        match_reason=match_reason,
    )


def _get_request_or_404(db: Session, request_id: uuid.UUID) -> WikiRequest:
    req = db.query(WikiRequest).filter(WikiRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Richiesta non trovata.")
    return req


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@router.post("/requests", response_model=WikiRequestRead, status_code=status.HTTP_201_CREATED)
def create_wiki_request(
    payload: WikiRequestCreate,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestRead:
    """Salva una richiesta utente (feature non implementata o domanda senza risposta)."""
    req = WikiRequest(
        id=uuid.uuid4(),
        user_question=payload.user_question,
        agent_response=payload.agent_response,
        category=payload.category,
        request_type=payload.request_type or _derive_request_type_from_category(payload.category),
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
        dedupe_key=_build_request_dedupe_key(
            request_type=payload.request_type or _derive_request_type_from_category(payload.category),
            module_key=payload.module_key,
            page_path=payload.page_path,
            context_entity_key=payload.context_entity_key,
            user_question=payload.user_question,
        ),
        desired_outcome=payload.desired_outcome,
        observed_behavior=payload.observed_behavior,
        expected_behavior=payload.expected_behavior,
    )
    db.add(req)
    _append_request_event(
        db,
        request_id=req.id,
        event_type="created",
        actor_username=current_user.username,
        to_status="new",
        payload={
            "category": payload.category,
            "request_type": payload.request_type or _derive_request_type_from_category(payload.category),
            "source_channel": payload.source_channel,
            "module_key": payload.module_key,
            "severity": payload.severity,
        },
    )
    db.commit()
    db.refresh(req)
    logger.info("WikiRequest creata: id=%s user=%s", req.id, current_user.username)
    return _serialize_wiki_request_read(db, req)


@router.get("/requests/mine", response_model=list[WikiRequestRead])
def list_my_wiki_requests(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> list[WikiRequestRead]:
    items = (
        db.query(WikiRequest)
        .filter(WikiRequest.created_by == current_user.username)
        .order_by(WikiRequest.created_at.desc())
        .all()
    )
    return [_serialize_wiki_request_read(db, item) for item in items]


@router.get("/requests", response_model=list[WikiRequestRead])
def list_wiki_requests(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> list[WikiRequestRead]:
    """Lista richieste utente. Solo admin e super_admin."""
    _require_wiki_admin(current_user)
    items = db.query(WikiRequest).order_by(WikiRequest.created_at.desc()).all()
    return [_serialize_wiki_request_read(db, item) for item in items]


@router.get("/requests/{request_id}/events", response_model=list[WikiRequestEventRead])
def list_wiki_request_events(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> list[WikiRequestEventRead]:
    _require_wiki_admin(current_user)
    _get_request_or_404(db, request_id)
    items = (
        db.query(WikiRequestEvent)
        .filter(WikiRequestEvent.request_id == request_id)
        .order_by(WikiRequestEvent.created_at.desc())
        .all()
    )
    return [_serialize_request_event(item) for item in items]


@router.get("/requests/assignees", response_model=list[WikiRequestAssigneeRead])
def list_wiki_request_assignees(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> list[WikiRequestAssigneeRead]:
    _require_wiki_admin(current_user)
    users = (
        db.query(ApplicationUser)
        .filter(ApplicationUser.is_active.is_(True))
        .order_by(ApplicationUser.full_name.asc(), ApplicationUser.username.asc())
        .all()
    )
    return [
        WikiRequestAssigneeRead(
            username=user.username,
            full_name=user.full_name,
            role=user.role,
        )
        for user in users
    ]


@router.get("/requests/{request_id}/duplicates", response_model=list[WikiRequestDuplicateCandidateRead])
def list_wiki_request_duplicates(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> list[WikiRequestDuplicateCandidateRead]:
    _require_wiki_admin(current_user)
    req = _get_request_or_404(db, request_id)
    candidates = (
        db.query(WikiRequest)
        .filter(WikiRequest.id != request_id)
        .filter(WikiRequest.status != "rejected")
        .order_by(WikiRequest.created_at.desc())
        .all()
    )

    scored: list[tuple[WikiRequest, float, str]] = []
    seen_ids: set[uuid.UUID] = set()
    if req.canonical_request_id:
        canonical = db.query(WikiRequest).filter(WikiRequest.id == req.canonical_request_id).first()
        if canonical:
            seen_ids.add(canonical.id)
            scored.append((canonical, 1.0, "caso canonico già associato"))

    for candidate in candidates:
        if candidate.id in seen_ids:
            continue
        score, reason = _request_similarity(req, candidate)
        if score < 0.45:
            continue
        seen_ids.add(candidate.id)
        scored.append((candidate, score, reason))

    scored.sort(key=lambda item: (item[1], item[0].created_at), reverse=True)
    return [_serialize_duplicate_candidate(db, item, similarity_score=score, match_reason=reason) for item, score, reason in scored[:5]]


@router.get("/requests/{request_id}", response_model=WikiRequestRead)
def get_wiki_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestRead:
    req = _get_request_or_404(db, request_id)
    if current_user.role not in ("admin", "super_admin") and req.created_by != current_user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso negato.")
    return _serialize_wiki_request_read(db, req)


@router.post("/requests/{request_id}/mark-viewed", response_model=WikiRequestRead)
def mark_wiki_request_viewed(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestRead:
    req = _get_request_or_404(db, request_id)
    if current_user.role not in ("admin", "super_admin") and req.created_by != current_user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso negato.")

    req.user_last_viewed_at = _now_utc()
    _append_request_event(
        db,
        request_id=req.id,
        event_type="user_viewed_update",
        actor_username=current_user.username,
    )
    db.commit()
    db.refresh(req)
    return _serialize_wiki_request_read(db, req)


@router.post("/requests/{request_id}/mark-duplicate", response_model=WikiRequestRead)
def mark_wiki_request_duplicate(
    request_id: uuid.UUID,
    payload: WikiRequestDuplicateMarkInput,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestRead:
    _require_wiki_admin(current_user)

    req = _get_request_or_404(db, request_id)
    canonical = _get_request_or_404(db, payload.canonical_request_id)
    if canonical.id == req.id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Una richiesta non può essere duplicata di se stessa.")

    previous_status = _legacy_status_to_workflow(req.status)
    previous_canonical_id = req.canonical_request_id
    req.status = "duplicate"
    req.canonical_request_id = canonical.id
    if payload.admin_notes is not None:
        req.admin_notes = payload.admin_notes
    req.last_admin_update_at = _now_utc()
    if req.dedupe_key is None:
        req.dedupe_key = _build_request_dedupe_key(
            request_type=req.request_type,
            module_key=req.module_key,
            page_path=req.page_path,
            context_entity_key=req.context_entity_key,
            user_question=req.user_question,
        )

    if previous_status != "duplicate":
        _append_request_event(
            db,
            request_id=req.id,
            event_type="status_changed",
            actor_username=current_user.username,
            from_status=previous_status,
            to_status="duplicate",
        )
    _append_request_event(
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
    _append_request_event(
        db,
        request_id=canonical.id,
        event_type="duplicate_linked",
        actor_username=current_user.username,
        payload={
            "duplicate_request_id": str(req.id),
            "duplicate_request_question": req.user_question,
        },
    )
    db.commit()
    db.refresh(req)
    return _serialize_wiki_request_read(db, req)


@router.patch("/requests/{request_id}/feedback", response_model=WikiRequestRead)
def update_wiki_request_feedback(
    request_id: uuid.UUID,
    payload: WikiRequestFeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestRead:
    req = _get_request_or_404(db, request_id)
    if current_user.role not in ("admin", "super_admin") and req.created_by != current_user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso negato.")

    req.user_feedback_rating = payload.rating
    req.user_feedback_notes = payload.notes
    req.user_feedback_submitted_at = _now_utc()
    req.user_last_viewed_at = req.user_feedback_submitted_at
    _append_request_event(
        db,
        request_id=req.id,
        event_type="user_feedback_submitted",
        actor_username=current_user.username,
        payload={"rating": payload.rating},
    )
    db.commit()
    db.refresh(req)
    return _serialize_wiki_request_read(db, req)


@router.patch("/requests/{request_id}", response_model=WikiRequestRead)
def update_wiki_request_status(
    request_id: uuid.UUID,
    payload: WikiRequestStatusUpdate,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestRead:
    """Aggiorna stato, priorita, assegnazione e note di una richiesta. Solo admin e super_admin."""
    _require_wiki_admin(current_user)

    req = _get_request_or_404(db, request_id)

    current_status = _legacy_status_to_workflow(req.status)

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
            _append_request_event(
                db,
                request_id=req.id,
                event_type="duplicate_cleared",
                actor_username=current_user.username,
                payload={"previous_canonical_request_id": str(previous_canonical)},
            )
        _append_request_event(
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
            _append_request_event(
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
            _append_request_event(
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
            _append_request_event(
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
            _append_request_event(
                db,
                request_id=req.id,
                event_type="resolution_message_updated",
                actor_username=current_user.username,
            )
    if payload.admin_notes is not None:
        old_notes = req.admin_notes or ""
        req.admin_notes = payload.admin_notes
        if (payload.admin_notes or "") != old_notes:
            _append_request_event(
                db,
                request_id=req.id,
                event_type="notes_updated",
                actor_username=current_user.username,
            )
    req.last_admin_update_at = _now_utc()
    db.commit()
    db.refresh(req)
    return _serialize_wiki_request_read(db, req)
