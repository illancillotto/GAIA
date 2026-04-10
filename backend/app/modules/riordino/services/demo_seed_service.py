"""Demo seed helpers for the Riordino module."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.riordino.enums import PHASE_1, PHASE_2, PhaseStatus, PracticeStatus, StepStatus
from app.modules.riordino.models import RiordinoPractice
from app.modules.riordino.services.common import create_event, utcnow
from app.modules.riordino.services.practice_service import create_practice


DEMO_PRACTICES = [
    {
        "title": "DEMO Riordino - Draft",
        "description": "Pratica demo non ancora avviata.",
        "municipality": "Comune Demo",
        "grid_code": "DM1",
        "lot_code": "LOT-001",
        "state": "draft",
    },
    {
        "title": "DEMO Riordino - Fase 1 in corso",
        "description": "Pratica demo con prime attività di fase 1 avviate.",
        "municipality": "Comune Demo",
        "grid_code": "DM2",
        "lot_code": "LOT-002",
        "state": "phase_1_in_progress",
    },
    {
        "title": "DEMO Riordino - Fase 2 pronta",
        "description": "Pratica demo con fase 1 completata e fase 2 pronta alla lavorazione.",
        "municipality": "Comune Demo",
        "grid_code": "DM3",
        "lot_code": "LOT-003",
        "state": "phase_2_ready",
    },
    {
        "title": "DEMO Riordino - Completata",
        "description": "Pratica demo interamente completata.",
        "municipality": "Comune Demo",
        "grid_code": "DM4",
        "lot_code": "LOT-004",
        "state": "completed",
    },
    {
        "title": "DEMO Riordino - Archiviata",
        "description": "Pratica demo completata e archiviata.",
        "municipality": "Comune Demo",
        "grid_code": "DM5",
        "lot_code": "LOT-005",
        "state": "archived",
    },
]


def _resolve_owner_user_id(db: Session, owner_user_id: int | None) -> int:
    if owner_user_id is not None:
        user = db.get(ApplicationUser, owner_user_id)
        if user and user.is_active:
            return user.id

    fallback = db.scalar(
        select(ApplicationUser)
        .where(ApplicationUser.is_active.is_(True))
        .order_by(ApplicationUser.id.asc())
    )
    if not fallback:
        raise ValueError("No active application user available for riordino demo seed")
    return fallback.id


def _apply_demo_state(db: Session, practice: RiordinoPractice, state: str, actor_id: int) -> None:
    now = utcnow()
    phase_1 = next((phase for phase in practice.phases if phase.phase_code == PHASE_1), None)
    phase_2 = next((phase for phase in practice.phases if phase.phase_code == PHASE_2), None)

    if state == "draft":
        return

    if state == "phase_1_in_progress" and phase_1:
        practice.status = PracticeStatus.open.value
        practice.opened_at = now
        phase_1.status = PhaseStatus.in_progress.value
        phase_1.started_at = now
        first_step = min(phase_1.steps, key=lambda item: item.sequence_no)
        first_step.status = StepStatus.done.value
        first_step.started_at = now
        first_step.completed_at = now
        create_event(db, practice_id=practice.id, phase_id=phase_1.id, created_by=actor_id, event_type="phase_started")
        create_event(db, practice_id=practice.id, phase_id=phase_1.id, step_id=first_step.id, created_by=actor_id, event_type="step_completed")
        return

    if state == "phase_2_ready" and phase_1 and phase_2:
        practice.status = PracticeStatus.in_review.value
        practice.opened_at = now
        practice.current_phase = PHASE_2
        phase_1.status = PhaseStatus.completed.value
        phase_1.started_at = now
        phase_1.completed_at = now
        phase_1.approved_by = actor_id
        for step in phase_1.steps:
            if step.is_required:
                step.status = StepStatus.done.value
                step.started_at = now
                step.completed_at = now
        create_event(db, practice_id=practice.id, phase_id=phase_1.id, created_by=actor_id, event_type="phase_completed")
        return

    if state in {"completed", "archived"} and phase_1 and phase_2:
        practice.status = PracticeStatus.completed.value if state == "completed" else PracticeStatus.archived.value
        practice.opened_at = now
        practice.current_phase = PHASE_2
        practice.completed_at = now
        if state == "archived":
            practice.archived_at = now

        for phase in (phase_1, phase_2):
            phase.status = PhaseStatus.completed.value
            phase.started_at = now
            phase.completed_at = now
            phase.approved_by = actor_id
            for step in phase.steps:
                if step.is_required:
                    step.status = StepStatus.done.value
                    step.started_at = now
                    step.completed_at = now

        create_event(db, practice_id=practice.id, phase_id=phase_1.id, created_by=actor_id, event_type="phase_completed")
        create_event(db, practice_id=practice.id, phase_id=phase_2.id, created_by=actor_id, event_type="phase_completed")
        create_event(
            db,
            practice_id=practice.id,
            created_by=actor_id,
            event_type="status_changed",
            payload_json={"status": practice.status},
        )
        return


def ensure_demo_practices(db: Session, owner_user_id: int | None = None, created_by_user_id: int | None = None) -> dict[str, int]:
    actor_id = _resolve_owner_user_id(db, created_by_user_id or owner_user_id)
    owner_id = _resolve_owner_user_id(db, owner_user_id or created_by_user_id)

    created = 0
    skipped = 0

    for payload in DEMO_PRACTICES:
        existing = db.scalar(
            select(RiordinoPractice).where(
                RiordinoPractice.title == payload["title"],
                RiordinoPractice.deleted_at.is_(None),
            )
        )
        if existing:
            skipped += 1
            continue

        practice = create_practice(
            db,
            {
                "title": payload["title"],
                "description": payload["description"],
                "municipality": payload["municipality"],
                "grid_code": payload["grid_code"],
                "lot_code": payload["lot_code"],
                "owner_user_id": owner_id,
            },
            actor_id,
        )
        _apply_demo_state(db, practice, payload["state"], actor_id)
        created += 1

    db.commit()
    return {"created": created, "skipped": skipped, "total": len(DEMO_PRACTICES)}
