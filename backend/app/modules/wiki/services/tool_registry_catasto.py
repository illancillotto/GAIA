from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.catasto_read_models import (
    get_catasto_dashboard_summary_read_model,
    get_catasto_particella_read_model,
)
from app.modules.wiki.services.policy import WikiToolMeta
from app.modules.wiki.services.response_composer import build_live_data_response
from app.modules.wiki.services.system_logic import explain_catasto_metric
from app.modules.wiki.services.tool_registry_common import (
    WikiToolDefinition,
    contains_any,
    has_uuid,
    parse_uuid,
    score_terms,
)


def _match_particella(question: str) -> int:
    if not has_uuid(question):
        return 0
    return 10 + score_terms(question, "particella", "catasto")


def _match_catasto_logic(question: str) -> int:
    if not contains_any(question, "catasto", "anomalie", "particelle", "importi", "copertura"):
        return 0
    if not contains_any(
        question,
        "come viene calcolato",
        "come si calcola",
        "indicatore",
        "metrica",
        "significa",
        "spiega",
    ):
        return 0
    return 7 + score_terms(question, "catasto", "anomalie", "particelle", "importi", "copertura", "indicatore", "spiega")


def _catasto_summary(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    payload = get_catasto_dashboard_summary_read_model(db, current_user)
    excerpt = (
        f"Anno {payload['anno']}, particelle {payload['particelle']['totale_correnti']}, "
        f"utenze ruolo {payload['utenze']['totale_utenze']}, anomalie {payload['anomalie']['aperte']}."
    )
    answer = (
        "Dati live Catasto: "
        f"anno campagna {payload['anno'] or 'n/d'}, {payload['particelle']['totale_correnti']} particelle correnti, "
        f"{payload['utenze']['totale_utenze']} utenze ruolo, {payload['anomalie']['aperte']} anomalie aperte, "
        f"importi complessivi {payload['utenze']['importo_totale']:,.2f} euro."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="get_catasto_dashboard_summary",
        evidence_label="Dashboard Catasto",
        source_key="catasto.dashboard.summary",
        excerpt=excerpt,
        payload=payload,
    )


def _find_particella_by_id(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    particella_id = parse_uuid(question)
    if particella_id is None:
        return build_live_data_response(
            answer="Per cercare una particella devo ricevere un UUID valido.",
            tool_name="find_particella_by_id",
            evidence_label="Lookup particella non eseguito",
            source_key="catasto.particelle.lookup",
            excerpt="UUID particella non presente nella domanda.",
        )
    payload = get_catasto_particella_read_model(db, current_user, particella_id)
    answer = (
        "Lookup particella Catasto: "
        f"{payload['nome_comune'] or payload['codice_catastale'] or 'Comune n/d'} "
        f"foglio {payload['foglio']}, particella {payload['particella']}"
        f"{f' subalterno {payload['subalterno']}' if payload['subalterno'] else ''}. "
        f"Distretto {payload['num_distretto'] or 'n/d'}, anagrafica {'presente' if payload['ha_anagrafica'] else 'assente'}, "
        f"fuori distretto {'sì' if payload['fuori_distretto'] else 'no'}."
    )
    excerpt = (
        f"ID {payload['id']}, comune {payload['nome_comune'] or payload['codice_catastale']}, "
        f"foglio {payload['foglio']}, particella {payload['particella']}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_particella_by_id",
        evidence_label="Dettaglio particella Catasto",
        source_key=f"catasto.particelle.{payload['id']}",
        excerpt=excerpt,
        payload=payload,
    )


def _explain_catasto_metric(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    return explain_catasto_metric(question)


CATASTO_TOOLS: tuple[WikiToolDefinition, ...] = (
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_particella_by_id", module_key="catasto"),
        intents=("live_data",),
        priority=100,
        matcher=_match_particella,
        handler=_find_particella_by_id,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="get_catasto_dashboard_summary", module_key="catasto"),
        intents=("live_data",),
        priority=10,
        matcher=lambda question: 1 if contains_any(question, "catasto", "particelle", "distretti", "anomalie") else 0,
        handler=_catasto_summary,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_catasto_metric", module_key="catasto"),
        intents=("logic",),
        priority=50,
        matcher=_match_catasto_logic,
        handler=_explain_catasto_metric,
    ),
)
