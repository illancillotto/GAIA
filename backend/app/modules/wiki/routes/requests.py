import logging
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.wiki.models import WikiRequest, WikiRequestEvent
from app.modules.wiki.schemas import (
    WikiRequestAssigneeRead,
    WikiRequestCreate,
    WikiRequestEventRead,
    WikiRequestRead,
    WikiRequestStatusUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Wiki"])


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
    if req.assigned_to:
        assignee = db.query(ApplicationUser).filter(ApplicationUser.username == req.assigned_to).first()
        if assignee:
            assigned_to_name = assignee.full_name or assignee.username
        else:
            assigned_to_name = req.assigned_to
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
        desired_outcome=req.desired_outcome,
        observed_behavior=req.observed_behavior,
        expected_behavior=req.expected_behavior,
        admin_notes=req.admin_notes,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


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
    req = db.query(WikiRequest).filter(WikiRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Richiesta non trovata.")
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


@router.get("/requests/{request_id}", response_model=WikiRequestRead)
def get_wiki_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiRequestRead:
    req = db.query(WikiRequest).filter(WikiRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Richiesta non trovata.")
    if current_user.role not in ("admin", "super_admin") and req.created_by != current_user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso negato.")
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

    req = db.query(WikiRequest).filter(WikiRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Richiesta non trovata.")

    current_status = _legacy_status_to_workflow(req.status)

    if payload.status is not None and payload.status != current_status:
        req.status = payload.status
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
    db.commit()
    db.refresh(req)
    return _serialize_wiki_request_read(db, req)
