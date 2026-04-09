"""Appeal services."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.riordino.enums import EventType, PHASE_1
from app.modules.riordino.models import RiordinoAppeal, RiordinoPhase, RiordinoStep
from app.modules.riordino.repositories import AppealRepository, PracticeRepository
from app.modules.riordino.services.common import create_event, utcnow


def _phase_and_step(db: Session, practice_id: UUID) -> tuple[RiordinoPhase, RiordinoStep | None]:
    phase = db.scalar(select(RiordinoPhase).where(RiordinoPhase.practice_id == practice_id, RiordinoPhase.phase_code == PHASE_1))
    if not phase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase 1 not found")
    step = db.scalar(select(RiordinoStep).where(RiordinoStep.practice_id == practice_id, RiordinoStep.code == "F1_RICORSI"))
    return phase, step


def create_appeal(db: Session, practice_id: UUID, data: dict, current_user) -> RiordinoAppeal:
    practice = PracticeRepository(db).get(practice_id)
    if not practice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice not found")
    phase, step = _phase_and_step(db, practice_id)
    appeal = RiordinoAppeal(
        practice_id=practice_id,
        phase_id=phase.id,
        step_id=step.id if step else None,
        created_by=current_user.id,
        **data,
    )
    AppealRepository(db).add(appeal)
    create_event(db, practice_id=practice_id, phase_id=phase.id, step_id=step.id if step else None, created_by=current_user.id, event_type=EventType.appeal_created)
    db.flush()
    return appeal


def update_appeal(db: Session, practice_id: UUID, appeal_id: UUID, data: dict) -> RiordinoAppeal:
    appeal = AppealRepository(db).get(practice_id, appeal_id)
    if not appeal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appeal not found")
    for key, value in data.items():
        if value is not None:
            setattr(appeal, key, value)
    db.flush()
    return appeal


def list_appeals(db: Session, practice_id: UUID, status_filter: str | None = None) -> list[RiordinoAppeal]:
    return AppealRepository(db).list(practice_id, status_filter)


def resolve_appeal(db: Session, practice_id: UUID, appeal_id: UUID, data: dict, current_user) -> RiordinoAppeal:
    appeal = AppealRepository(db).get(practice_id, appeal_id)
    if not appeal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appeal not found")
    appeal.status = data["status"]
    appeal.resolution_notes = data.get("resolution_notes")
    appeal.resolved_at = utcnow()
    create_event(db, practice_id=practice_id, phase_id=appeal.phase_id, step_id=appeal.step_id, created_by=current_user.id, event_type=EventType.appeal_resolved, payload_json={"status": appeal.status})
    db.flush()
    return appeal
