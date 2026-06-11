import logging
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.wiki.models import WikiRequest, WikiRequestArtifact, WikiRequestEvent
from app.modules.wiki.schemas import (
    WikiMyRequestsSummaryRead,
    WikiRequestAssigneeRead,
    WikiRequestArtifactRead,
    WikiRequestCreate,
    WikiRequestDuplicateCandidateRead,
    WikiRequestFamilyRead,
    WikiRequestDuplicateMarkInput,
    WikiRequestEventRead,
    WikiRequestFeedbackUpdate,
    WikiRequestMakeCanonicalInput,
    WikiRequestReopenInput,
    WikiRequestRead,
    WikiRequestStatusUpdate,
)
from app.modules.wiki.services.request_artifacts import create_request_artifacts
from app.modules.wiki.services.request_workflow import (
    append_created_event,
    append_request_event,
    apply_request_status_update,
    build_request_dedupe_key,
    build_request_family,
    build_request_from_payload,
    derive_request_type_from_category,
    legacy_status_to_workflow,
    linked_duplicate_candidates,
    make_request_canonical,
    mark_request_duplicate,
    now_utc,
    reopen_request_for_user,
    request_similarity,
    resolve_family_canonical,
    update_request_feedback_fields,
    unlink_request_duplicate,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Wiki"])


def _require_wiki_admin(current_user: ApplicationUser) -> None:
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso negato.")


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
            canonical_request_status = legacy_status_to_workflow(canonical.status)
    has_unread_update = False
    if req.last_admin_update_at is not None:
        has_unread_update = req.user_last_viewed_at is None or req.last_admin_update_at > req.user_last_viewed_at
    return WikiRequestRead(
        id=req.id,
        user_question=req.user_question,
        agent_response=req.agent_response,
        category=req.category,
        request_type=req.request_type,
        status=legacy_status_to_workflow(req.status),
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
        external_ticket_key=req.external_ticket_key,
        external_ticket_url=req.external_ticket_url,
        delivery_status=req.delivery_status,
        delivery_notes=req.delivery_notes,
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
        status=legacy_status_to_workflow(req.status),
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


def _get_request_artifact_or_404(db: Session, artifact_id: uuid.UUID) -> WikiRequestArtifact:
    artifact = db.query(WikiRequestArtifact).filter(WikiRequestArtifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact richiesta non trovato.")
    return artifact


def _require_request_access(req: WikiRequest, current_user: ApplicationUser) -> None:
    if current_user.role not in ("admin", "super_admin") and req.created_by != current_user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso negato.")


def _safe_json_loads(raw_value: str | None, *, field_name: str) -> dict[str, object] | None:
    if raw_value is None or not raw_value.strip():
        return None
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Formato JSON non valido per {field_name}.",
        ) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} deve essere un oggetto JSON.",
        )
    return parsed


def _coerce_request_form_payload(payload_json: str) -> WikiRequestCreate:
    try:
        raw_payload = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Payload richiesta non valido.") from exc
    if not isinstance(raw_payload, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Payload richiesta non valido.")
    return WikiRequestCreate.model_validate(raw_payload)


def _serialize_wiki_request_artifact(item: WikiRequestArtifact) -> WikiRequestArtifactRead:
    payload: dict[str, object] | None = None
    if item.payload_json:
        try:
            parsed = json.loads(item.payload_json)
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError:
            payload = None
    return WikiRequestArtifactRead(
        id=item.id,
        request_id=item.request_id,
        artifact_type=item.artifact_type,
        filename=item.filename,
        mime_type=item.mime_type,
        payload=payload,
        created_by=item.created_by,
        created_at=item.created_at,
    )


@router.post("/requests", response_model=WikiRequestRead, status_code=status.HTTP_201_CREATED)
def create_wiki_request(
    payload: WikiRequestCreate,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestRead:
    """Salva una richiesta utente (feature non implementata o domanda senza risposta)."""
    req = build_request_from_payload(payload, current_user=current_user)
    db.add(req)
    append_created_event(db, req=req, payload=payload, actor_username=current_user.username)
    db.commit()
    db.refresh(req)
    logger.info("WikiRequest creata: id=%s user=%s", req.id, current_user.username)
    return _serialize_wiki_request_read(db, req)


@router.post("/requests/with-artifacts", response_model=WikiRequestRead, status_code=status.HTTP_201_CREATED)
def create_wiki_request_with_artifacts(
    payload_json: str = Form(...),
    screenshot_meta_json: str | None = Form(None),
    ui_snapshot_json: str | None = Form(None),
    screenshot: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestRead:
    payload = _coerce_request_form_payload(payload_json)
    screenshot_meta = _safe_json_loads(screenshot_meta_json, field_name="screenshot_meta_json")
    ui_snapshot = _safe_json_loads(ui_snapshot_json, field_name="ui_snapshot_json")

    req = build_request_from_payload(payload, current_user=current_user)
    db.add(req)
    append_created_event(db, req=req, payload=payload, actor_username=current_user.username)
    create_request_artifacts(
        db,
        req=req,
        current_user=current_user,
        screenshot=screenshot,
        screenshot_meta=screenshot_meta,
        ui_snapshot=ui_snapshot,
    )
    db.commit()
    db.refresh(req)
    logger.info("WikiRequest con artifact creata: id=%s user=%s", req.id, current_user.username)
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


@router.get("/requests/mine/summary", response_model=WikiMyRequestsSummaryRead)
def get_my_wiki_requests_summary(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiMyRequestsSummaryRead:
    base_query = db.query(WikiRequest).filter(WikiRequest.created_by == current_user.username)
    items = base_query.all()
    unread_updates = sum(
        1
        for item in items
        if item.last_admin_update_at is not None
        and (item.user_last_viewed_at is None or item.last_admin_update_at > item.user_last_viewed_at)
    )
    waiting_user_requests = sum(1 for item in items if legacy_status_to_workflow(item.status) == "waiting_user")
    resolved_feedback_pending = sum(
        1
        for item in items
        if legacy_status_to_workflow(item.status) == "resolved" and item.user_feedback_submitted_at is None
    )
    open_requests = sum(
        1
        for item in items
        if legacy_status_to_workflow(item.status) not in {"resolved", "duplicate", "rejected"}
    )
    return WikiMyRequestsSummaryRead(
        total_requests=len(items),
        open_requests=open_requests,
        unread_updates=unread_updates,
        waiting_user_requests=waiting_user_requests,
        resolved_feedback_pending=resolved_feedback_pending,
    )


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
        score, reason = request_similarity(req, candidate)
        if score < 0.45:
            continue
        seen_ids.add(candidate.id)
        scored.append((candidate, score, reason))

    scored.sort(key=lambda item: (item[1], item[0].created_at), reverse=True)
    return [_serialize_duplicate_candidate(db, item, similarity_score=score, match_reason=reason) for item, score, reason in scored[:5]]


@router.get("/requests/{request_id}/linked-duplicates", response_model=list[WikiRequestDuplicateCandidateRead])
def list_wiki_request_linked_duplicates(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> list[WikiRequestDuplicateCandidateRead]:
    _require_wiki_admin(current_user)
    req = _get_request_or_404(db, request_id)
    canonical_id = req.canonical_request_id or req.id
    return linked_duplicate_candidates(db, canonical_id, serialize_duplicate_candidate=lambda s, item, score, reason: _serialize_duplicate_candidate(s, item, similarity_score=score, match_reason=reason))


@router.get("/requests/{request_id}/family", response_model=WikiRequestFamilyRead)
def get_wiki_request_family(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestFamilyRead:
    _require_wiki_admin(current_user)
    req = _get_request_or_404(db, request_id)
    return build_request_family(
        db,
        req,
        serialize_request=_serialize_wiki_request_read,
        serialize_duplicate_candidate=lambda s, item, score, reason: _serialize_duplicate_candidate(s, item, similarity_score=score, match_reason=reason),
    )


@router.get("/requests/{request_id}", response_model=WikiRequestRead)
def get_wiki_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestRead:
    req = _get_request_or_404(db, request_id)
    _require_request_access(req, current_user)
    return _serialize_wiki_request_read(db, req)


@router.get("/requests/{request_id}/artifacts", response_model=list[WikiRequestArtifactRead])
def list_wiki_request_artifacts(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> list[WikiRequestArtifactRead]:
    req = _get_request_or_404(db, request_id)
    _require_request_access(req, current_user)
    items = (
        db.query(WikiRequestArtifact)
        .filter(WikiRequestArtifact.request_id == request_id)
        .order_by(WikiRequestArtifact.created_at.desc())
        .all()
    )
    return [_serialize_wiki_request_artifact(item) for item in items]


@router.get("/requests/{request_id}/artifacts/{artifact_id}/download")
def download_wiki_request_artifact(
    request_id: uuid.UUID,
    artifact_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
):
    req = _get_request_or_404(db, request_id)
    _require_request_access(req, current_user)
    artifact = _get_request_artifact_or_404(db, artifact_id)
    if artifact.request_id != request_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact richiesta non trovato.")
    if not artifact.storage_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact binario non disponibile.")
    path = Path(artifact.storage_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File artifact non trovato.")
    return FileResponse(path, media_type=artifact.mime_type or "application/octet-stream", filename=artifact.filename or path.name)


@router.post("/requests/{request_id}/mark-viewed", response_model=WikiRequestRead)
def mark_wiki_request_viewed(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestRead:
    req = _get_request_or_404(db, request_id)
    _require_request_access(req, current_user)

    req.user_last_viewed_at = now_utc()
    append_request_event(
        db,
        request_id=req.id,
        event_type="user_viewed_update",
        actor_username=current_user.username,
    )
    db.commit()
    db.refresh(req)
    return _serialize_wiki_request_read(db, req)


@router.post("/requests/{request_id}/reopen", response_model=WikiRequestRead)
def reopen_wiki_request(
    request_id: uuid.UUID,
    payload: WikiRequestReopenInput,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestRead:
    req = _get_request_or_404(db, request_id)
    _require_request_access(req, current_user)

    reopen_request_for_user(db, req=req, payload=payload, current_user=current_user)
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
    mark_request_duplicate(db, req=req, canonical=canonical, admin_notes=payload.admin_notes, current_user=current_user)
    db.commit()
    db.refresh(req)
    return _serialize_wiki_request_read(db, req)


@router.post("/requests/{request_id}/unlink-duplicate", response_model=WikiRequestRead)
def unlink_wiki_request_duplicate(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestRead:
    _require_wiki_admin(current_user)
    req = _get_request_or_404(db, request_id)
    unlink_request_duplicate(db, req=req, current_user=current_user)
    db.commit()
    db.refresh(req)
    return _serialize_wiki_request_read(db, req)


@router.post("/requests/{request_id}/make-canonical", response_model=WikiRequestFamilyRead)
def make_wiki_request_canonical(
    request_id: uuid.UUID,
    payload: WikiRequestMakeCanonicalInput,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestFamilyRead:
    _require_wiki_admin(current_user)
    target = _get_request_or_404(db, request_id)
    if resolve_family_canonical(db, target).id == target.id and target.canonical_request_id is None:
        return build_request_family(
            db,
            target,
            serialize_request=_serialize_wiki_request_read,
            serialize_duplicate_candidate=lambda s, item, score, reason: _serialize_duplicate_candidate(s, item, similarity_score=score, match_reason=reason),
        )
    make_request_canonical(db, target=target, payload=payload, current_user=current_user)

    db.commit()
    db.refresh(target)
    return build_request_family(
        db,
        target,
        serialize_request=_serialize_wiki_request_read,
        serialize_duplicate_candidate=lambda s, item, score, reason: _serialize_duplicate_candidate(s, item, similarity_score=score, match_reason=reason),
    )


@router.patch("/requests/{request_id}/feedback", response_model=WikiRequestRead)
def update_wiki_request_feedback(
    request_id: uuid.UUID,
    payload: WikiRequestFeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestRead:
    req = _get_request_or_404(db, request_id)
    _require_request_access(req, current_user)

    update_request_feedback_fields(db, req=req, payload=payload, current_user=current_user)
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

    apply_request_status_update(db, req=req, payload=payload, current_user=current_user)
    db.commit()
    db.refresh(req)
    return _serialize_wiki_request_read(db, req)
