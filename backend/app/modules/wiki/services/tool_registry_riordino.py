from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.policy import WikiToolMeta
from app.modules.wiki.services.response_composer import build_live_data_response
from app.modules.wiki.services.system_logic import explain_riordino_practice_state
from app.modules.wiki.services.tool_registry_common import (
    WikiToolDefinition,
    contains_any,
    has_uuid,
    parse_uuid,
    score_terms,
)


def _match_riordino_practice(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "riordino", "pratica", "practice", "workflow"):
        return 0
    return 10 + score_terms(question, "riordino", "pratica", "practice", "workflow")


def _match_riordino_logic(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "riordino", "pratica", "workflow", "stato"):
        return 0
    if not contains_any(question, "perche", "perché", "spiega", "significa", "stato"):
        return 0
    return 8 + score_terms(question, "riordino", "pratica", "workflow", "stato", "spiega")


def _find_riordino_practice_by_id(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.riordino.schemas.practice import PracticeDetailResponse
    from app.modules.riordino.services.practice_service import get_practice_detail

    practice_id = parse_uuid(question)
    if practice_id is None:
        return build_live_data_response(
            answer="Per cercare una pratica Riordino devo ricevere un UUID valido.",
            tool_name="find_riordino_practice_by_id",
            evidence_label="Lookup pratica Riordino non eseguito",
            source_key="riordino.practices.lookup",
            excerpt="UUID pratica non presente nella domanda.",
        )

    practice, counts = get_practice_detail(db, practice_id)
    issues_count, appeals_count, documents_count = counts
    response = PracticeDetailResponse.model_validate(practice)
    payload = response.model_dump(mode="json")
    payload.update(
        {
            "issues_count": issues_count,
            "appeals_count": appeals_count,
            "documents_count": documents_count,
        }
    )
    answer = (
        "Lookup pratica Riordino: "
        f"{response.code} {response.title}, stato {response.status}, fase {response.current_phase}, "
        f"comune {response.municipality}, issue {issues_count}, ricorsi {appeals_count}, documenti {documents_count}."
    )
    excerpt = (
        f"Pratica {response.code}, stato {response.status}, fase {response.current_phase}, "
        f"issue {issues_count}, ricorsi {appeals_count}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_riordino_practice_by_id",
        evidence_label="Dettaglio pratica Riordino",
        source_key=f"riordino.practices.{response.id}",
        excerpt=excerpt,
        payload=payload,
    )


def _explain_riordino_practice_state(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    practice_id = parse_uuid(question)
    if practice_id is None:
        return build_live_data_response(
            answer="Per spiegare lo stato di una pratica Riordino devo ricevere un UUID valido.",
            tool_name="explain_riordino_practice_state",
            evidence_label="Spiegazione pratica Riordino non eseguita",
            source_key="riordino.practice.logic.lookup",
            excerpt="UUID pratica non presente nella domanda.",
        )
    return explain_riordino_practice_state(db, current_user, practice_id)


RIORDINO_TOOLS: tuple[WikiToolDefinition, ...] = (
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_riordino_practice_by_id", module_key="riordino", required_sections=("riordino.practices",)),
        intents=("live_data",),
        priority=100,
        matcher=_match_riordino_practice,
        handler=_find_riordino_practice_by_id,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_riordino_practice_state", module_key="riordino", required_sections=("riordino.workflow",)),
        intents=("logic",),
        priority=60,
        matcher=_match_riordino_logic,
        handler=_explain_riordino_practice_state,
    ),
)
