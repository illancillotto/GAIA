"""Workflow routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.riordino.schemas import PhaseCompleteRequest, PhaseResponse, StepAdvanceRequest, StepResponse, StepSkipRequest
from app.modules.riordino.services import advance_step, complete_phase, reopen_step, skip_step, start_phase

router = APIRouter(dependencies=[Depends(require_module("riordino")), Depends(require_section("riordino.workflow"))])


@router.post("/{practice_id}/steps/{step_id}/advance", response_model=StepResponse)
def advance_step_endpoint(
    practice_id: UUID,
    step_id: UUID,
    payload: StepAdvanceRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    step = advance_step(db, practice_id, step_id, current_user, outcome_code=payload.outcome_code, outcome_notes=payload.outcome_notes)
    db.commit()
    db.refresh(step)
    return step


@router.post("/{practice_id}/steps/{step_id}/skip", response_model=StepResponse)
def skip_step_endpoint(
    practice_id: UUID,
    step_id: UUID,
    payload: StepSkipRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    step = skip_step(db, practice_id, step_id, current_user, payload.skip_reason)
    db.commit()
    db.refresh(step)
    return step


@router.post("/{practice_id}/steps/{step_id}/reopen", response_model=StepResponse)
def reopen_step_endpoint(
    practice_id: UUID,
    step_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    step = reopen_step(db, practice_id, step_id, current_user)
    db.commit()
    db.refresh(step)
    return step


@router.post("/{practice_id}/phases/{phase_id}/start", response_model=PhaseResponse)
def start_phase_endpoint(
    practice_id: UUID,
    phase_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    phase = start_phase(db, practice_id, phase_id, current_user)
    db.commit()
    db.refresh(phase)
    return phase


@router.post("/{practice_id}/phases/{phase_id}/complete", response_model=PhaseResponse)
def complete_phase_endpoint(
    practice_id: UUID,
    phase_id: UUID,
    payload: PhaseCompleteRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    phase = complete_phase(db, practice_id, phase_id, current_user, notes=payload.notes)
    db.commit()
    db.refresh(phase)
    return phase
