import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.wiki.models import WikiRequest
from app.modules.wiki.schemas import WikiRequestAssigneeRead, WikiRequestCreate, WikiRequestRead, WikiRequestStatusUpdate

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Wiki"])


def _require_wiki_admin(current_user: ApplicationUser) -> None:
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso negato.")


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
        status=req.status,
        priority=req.priority,
        created_by=req.created_by,
        assigned_to=req.assigned_to,
        assigned_to_name=assigned_to_name,
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
        status="pending",
        priority="medium",
        created_by=current_user.username,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    logger.info("WikiRequest creata: id=%s user=%s", req.id, current_user.username)
    return _serialize_wiki_request_read(db, req)


@router.get("/requests", response_model=list[WikiRequestRead])
def list_wiki_requests(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> list[WikiRequestRead]:
    """Lista richieste utente. Solo admin e super_admin."""
    _require_wiki_admin(current_user)
    items = db.query(WikiRequest).order_by(WikiRequest.created_at.desc()).all()
    return [_serialize_wiki_request_read(db, item) for item in items]


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

    if payload.status is not None:
        req.status = payload.status
    if payload.priority is not None:
        req.priority = payload.priority
    if payload.assigned_to is not None:
        assigned_to = payload.assigned_to.strip()
        if assigned_to:
            assignee = db.query(ApplicationUser).filter(ApplicationUser.username == assigned_to).first()
            if not assignee:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Assegnatario non valido.")
            req.assigned_to = assignee.username
        else:
            req.assigned_to = None
    if payload.admin_notes is not None:
        req.admin_notes = payload.admin_notes
    db.commit()
    db.refresh(req)
    return _serialize_wiki_request_read(db, req)
