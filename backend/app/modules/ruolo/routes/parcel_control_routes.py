from contextlib import contextmanager
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo.parcel_control_schemas import ControlCommand, ControlFilters
from app.modules.ruolo.services import parcel_control_cases as cases
from app.modules.ruolo.services import parcel_control_index as index
from app.modules.ruolo.services import parcel_control_notices as notices
from app.modules.ruolo.services import parcel_control_proposals as proposals
from app.modules.ruolo.services import parcel_control_queries as queries
from app.modules.ruolo.services import parcel_control_spatial as spatial
from app.modules.ruolo.services import parcel_control_visure as visure
from app.services.elaborazioni_batches import BatchValidationError

router = APIRouter(
    prefix="/particelle/controllo",
    tags=["ruolo-controllo-particelle"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.avvisi"))],
)
Database = Annotated[Session, Depends(get_db)]
Editor = Annotated[ApplicationUser, Depends(require_section("ruolo.tributi.manage_status"))]


@contextmanager
def transaction(db):
    try:
        yield
        db.commit()
    except LookupError as exc:
        db.rollback()
        raise HTTPException(404, str(exc)) from exc
    except HTTPException:
        db.rollback()
        raise
    except (IntegrityError, StaleDataError) as exc:
        db.rollback()
        raise HTTPException(409, "Operazione concorrente: ricaricare e riprovare") from exc
    except (ValueError, KeyError, TypeError, BatchValidationError) as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.get("")
def matrix(db: Database, filters: Annotated[ControlFilters, Query()]):
    if filters.view == "proposals":
        return queries.proposal_queue(db, filters)
    if filters.view in {"cases", "closed", "visure", "recovered"}:
        return queries.list_cases(db, filters)
    return queries.list_index(db, filters)


@router.get("/avvisi")
def anomalous_headers(db: Database, filters: Annotated[ControlFilters, Query()]):
    page = notices.anomalous_notices(db, filters)
    return {"items": [], "notices": page["items"], "total": page["total"]}


@router.post("/avvisi/{notice_id}/pratica")
def open_notice_practice(notice_id: UUID, payload: ControlCommand, db: Database, user: Editor):
    with transaction(db):
        case = notices.open_notice_case(db, notice_id, user.id, payload)
    return queries.case_view(db, case)


@router.post("/analisi")
def analyze(payload: ControlCommand, db: Database, user: Editor):
    with transaction(db):
        if not cases.replay(db, None, user.id, "analysis", payload):
            index.refresh_index(db, user.id)
            cases.audit_command(db, None, user.id, "analysis", payload)
    return queries.list_index(db, ControlFilters())


@router.post("/annualita/{year}/certificazione")
def certify(year: int, payload: ControlCommand, db: Database, user: Editor):
    with transaction(db):
        if not cases.replay(db, None, user.id, f"coverage:{year}", payload):
            index.certify_year(db, year, user.id, payload.reason, payload.data.get("source", ""))
            cases.audit_command(db, None, user.id, f"coverage:{year}", payload)
    return queries.list_index(db, ControlFilters())


@router.post("/{parcel_id}/pratica")
def open_practice(parcel_id: UUID, payload: ControlCommand, db: Database, user: Editor):
    with transaction(db):
        case = cases.open_case(db, parcel_id, user.id, payload)
    return queries.case_view(db, case)


@router.get("/pratiche/{case_id}")
def detail(case_id: UUID, db: Database):
    with transaction(db):
        case = cases.require_case(db, case_id)
    return queries.case_view(db, case)


@router.post("/pratiche/{case_id}/{action}")
def change(
    case_id: UUID,
    action: Literal[
        "status",
        "evidence",
        "match",
        "link_visura",
        "proposal",
        "decision",
        "recover",
        "parcel_status",
        "spatial_check",
    ],
    payload: ControlCommand,
    db: Database,
    user: Editor,
):
    with transaction(db):
        case = cases.require_case(db, case_id)
        if not cases.replay(db, case_id, user.id, action, payload):
            if case.version != payload.expected_version:
                raise HTTPException(409, "Pratica modificata: ricaricare prima di salvare")
            mutate(db, case, action, payload.data, user.id)
            case.version += 1
            cases.audit_command(db, case_id, user.id, action, payload)
    return queries.case_view(db, case)


def mutate(db, case, action, data, actor_id):
    if action == "proposal":
        proposals.create_proposal(db, case, data)
    elif action == "decision":
        proposals.decide_proposal(db, case, data)
    elif action == "recover":
        visure.recover_parcel(db, case, data)
    elif action == "spatial_check":
        spatial.spatial_check(db, case, data, actor_id)
    else:
        cases.update_case(db, case, action, data, actor_id)


@router.post(
    "/pratiche/{case_id}/visura/richiesta", dependencies=[Depends(require_module("elaborazioni"))]
)
def request_visura(case_id: UUID, payload: ControlCommand, db: Database, user: Editor):
    with transaction(db):
        case = cases.require_case(db, case_id)
        if not cases.replay(db, case_id, user.id, "request_visura", payload):
            if case.version != payload.expected_version:
                raise HTTPException(409, "Pratica modificata: ricaricare prima di salvare")
            visure.queue_visura(db, case, payload.data, user.id)
            case.version += 1
            cases.audit_command(db, case_id, user.id, "request_visura", payload)
    return queries.case_view(db, case)
