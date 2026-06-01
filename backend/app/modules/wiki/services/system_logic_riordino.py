from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.riordino.enums import AppealStatus, IssueSeverity, StepStatus, PracticeStatus
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.response_composer import build_logic_response


def explain_riordino_practice_state(db: Session, current_user: ApplicationUser, practice_id: UUID) -> WikiChatResponse:
    from app.modules.riordino.services.practice_service import get_practice_detail

    practice, counts = get_practice_detail(db, practice_id)
    issues_count, appeals_count, documents_count = counts
    required_open_steps = [
        step for step in practice.steps
        if step.is_required and step.status not in {StepStatus.done.value, StepStatus.skipped.value}
    ]
    blocking_issues = [issue for issue in practice.issues if issue.severity == IssueSeverity.blocking.value and issue.status != "closed"]
    open_appeals = [appeal for appeal in practice.appeals if appeal.status in {AppealStatus.open.value, AppealStatus.under_review.value}]
    current_phase = next((phase for phase in practice.phases if phase.phase_code == practice.current_phase), None)

    if practice.status == PracticeStatus.draft.value:
        rule = "La pratica e ancora in bozza: il workflow non e stato ancora avviato."
    elif practice.status == PracticeStatus.open.value:
        rule = "La pratica e aperta: almeno una fase o uno step operativo e in lavorazione."
    elif practice.status == PracticeStatus.in_review.value:
        rule = "La pratica e in review: la fase 1 risulta completata e il workflow e passato alla fase 2."
    elif practice.status == PracticeStatus.blocked.value or blocking_issues:
        rule = "La pratica risulta bloccata da issue blocking o da vincoli workflow non ancora risolti."
    elif practice.status == PracticeStatus.completed.value:
        rule = "La pratica e completata: non ci sono issue o appeal aperti e la fase finale e chiusa."
    elif practice.status == PracticeStatus.archived.value:
        rule = "La pratica e archiviata: il workflow e terminato e la pratica e stata portata fuori dal ciclo operativo."
    else:
        rule = "Lo stato pratica deriva dalla combinazione di fase corrente, step completati e vincoli aperti."

    answer = (
        f"La pratica {practice.code} e nello stato {practice.status} in {practice.current_phase}. "
        f"{rule} Step richiesti ancora aperti: {len(required_open_steps)}, "
        f"issue blocking aperte: {len(blocking_issues)}, ricorsi aperti: {len(open_appeals)}, "
        f"documenti: {documents_count}."
    )
    excerpt = (
        f"Pratica {practice.code}, stato {practice.status}, fase {practice.current_phase}, "
        f"required_open_steps {len(required_open_steps)}, blocking_issues {len(blocking_issues)}, open_appeals {len(open_appeals)}."
    )
    payload = {
        "practice_id": str(practice.id),
        "practice_code": practice.code,
        "status": practice.status,
        "current_phase": practice.current_phase,
        "current_phase_status": current_phase.status if current_phase is not None else None,
        "required_open_steps": [{"code": step.code, "title": step.title, "status": step.status} for step in required_open_steps[:5]],
        "blocking_issues": [{"id": str(issue.id), "title": issue.title, "status": issue.status} for issue in blocking_issues[:5]],
        "open_appeals": [{"id": str(appeal.id), "status": appeal.status} for appeal in open_appeals[:5]],
        "issues_count": issues_count,
        "appeals_count": appeals_count,
        "documents_count": documents_count,
    }
    return build_logic_response(
        answer=answer,
        tool_name="explain_riordino_practice_state",
        evidence_label="Spiegazione stato pratica Riordino",
        source_key=f"riordino.practice.logic.{practice.id}",
        excerpt=excerpt,
        payload=payload,
    )
