from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.operazioni_analytics_read_models import (
    get_operazioni_analytics_summary_read_model,
    get_operazioni_analytics_top_fuel_read_model,
    get_operazioni_analytics_top_km_operators_read_model,
    get_operazioni_analytics_work_hours_by_team_read_model,
)
from app.modules.wiki.services.policy import WikiToolMeta
from app.modules.wiki.services.response_composer import build_live_data_response
from app.modules.wiki.services.system_logic import (
    explain_operazioni_analytics_anomaly,
    explain_operazioni_analytics_metric,
)
from app.modules.wiki.services.tool_registry_common import WikiToolDefinition, contains_any, has_uuid, parse_uuid, score_terms


def _match_operazioni_analytics_summary(question: str) -> int:
    if not contains_any(question, "analytics", "analisi", "summary analisi", "cruscotto analisi"):
        return 0
    return 7 + score_terms(question, "analytics", "analisi", "summary", "operazioni", "km", "litri", "ore", "anomalie")


def _match_operazioni_analytics_top_fuel(question: str) -> int:
    if not contains_any(question, "analytics", "analisi", "carburante", "fuel", "consumi"):
        return 0
    if not contains_any(question, "top mezzi", "top veicoli", "top", "carburante", "fuel", "consumi"):
        return 0
    return 8 + score_terms(question, "analytics", "analisi", "top", "mezzi", "veicoli", "carburante", "fuel", "consumi")


def _match_operazioni_analytics_top_km_operators(question: str) -> int:
    if not contains_any(question, "analytics", "analisi", "km", "chilometri"):
        return 0
    if not contains_any(question, "top operatori", "top operator", "operatori", "conducenti"):
        return 0
    return 8 + score_terms(question, "analytics", "analisi", "km", "top", "operatori", "operator")


def _match_operazioni_analytics_work_hours_team(question: str) -> int:
    if not contains_any(question, "analytics", "analisi", "ore", "work hours"):
        return 0
    if not contains_any(question, "team", "squadra", "ore per team", "by team"):
        return 0
    return 8 + score_terms(question, "analytics", "analisi", "ore", "work hours", "team", "squadra")


def _match_operazioni_analytics_logic(question: str) -> int:
    if not contains_any(question, "analytics", "analisi"):
        return 0
    if not contains_any(question, "km", "litri", "ore", "anomalie", "sessioni attive"):
        return 0
    if not contains_any(question, "spiega", "significa", "come viene calcolato", "come si calcola", "indicatore", "metrica"):
        return 0
    return 8 + score_terms(question, "analytics", "analisi", "km", "litri", "ore", "anomalie", "indicatore", "metrica")


def _match_operazioni_analytics_anomaly(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "anomalia", "anomalie", "analytics", "analisi"):
        return 0
    return 11 + score_terms(question, "anomalia", "anomalie", "analytics", "analisi", "operazioni")


def _match_operazioni_analytics_anomaly_logic(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "anomalia", "anomalie", "analytics", "analisi"):
        return 0
    if not contains_any(question, "spiega", "perche", "perché", "significa", "motivo"):
        return 0
    return 9 + score_terms(question, "anomalia", "anomalie", "analytics", "analisi", "spiega", "motivo", "significa")


def _operazioni_analytics_summary(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    payload = get_operazioni_analytics_summary_read_model(db, current_user)
    answer = (
        "Analytics Operazioni: "
        f"{float(payload['total_km']):.1f} km, {float(payload['total_liters']):.2f} litri, "
        f"{float(payload['total_work_hours']):.1f} ore lavoro, {int(payload['active_sessions'])} sessioni attive, "
        f"{int(payload['anomaly_count'])} anomalie."
    )
    excerpt = (
        f"Periodo {payload['period_label']}, km {float(payload['total_km']):.1f}, litri {float(payload['total_liters']):.2f}, "
        f"ore {float(payload['total_work_hours']):.1f}, anomalie {int(payload['anomaly_count'])}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="get_operazioni_analytics_summary",
        evidence_label="Summary analytics Operazioni",
        source_key="operazioni.analytics.summary",
        excerpt=excerpt,
        payload=payload,
    )


def _operazioni_analytics_top_fuel(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    payload = get_operazioni_analytics_top_fuel_read_model(db, current_user)
    top = payload.get("top_vehicles", [])[:3]
    if not top:
        answer = "Non ci sono ancora mezzi con consumi carburante aggregati nelle analytics Operazioni."
        excerpt = "Top veicoli carburante non disponibile."
    else:
        summary = "; ".join(f"{item['label']}: {float(item['total_liters']):.2f} L" for item in top)
        answer = f"Top mezzi carburante Operazioni: {summary}."
        excerpt = summary
    return build_live_data_response(
        answer=answer,
        tool_name="get_operazioni_analytics_top_fuel_vehicles",
        evidence_label="Top mezzi carburante Operazioni",
        source_key="operazioni.analytics.fuel.top-vehicles",
        excerpt=excerpt,
        payload=payload,
    )


def _operazioni_analytics_top_km_operators(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    payload = get_operazioni_analytics_top_km_operators_read_model(db, current_user)
    top = payload.get("top_operators", [])[:3]
    if not top:
        answer = "Non ci sono ancora operatori con km aggregati nelle analytics Operazioni."
        excerpt = "Top operatori km non disponibile."
    else:
        summary = "; ".join(f"{item['label']}: {float(item['total_km']):.1f} km" for item in top)
        answer = f"Top operatori km Operazioni: {summary}."
        excerpt = summary
    return build_live_data_response(
        answer=answer,
        tool_name="get_operazioni_analytics_top_km_operators",
        evidence_label="Top operatori km Operazioni",
        source_key="operazioni.analytics.km.top-operators",
        excerpt=excerpt,
        payload=payload,
    )


def _operazioni_analytics_work_hours_by_team(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    payload = get_operazioni_analytics_work_hours_by_team_read_model(db, current_user)
    teams = payload.get("by_team", [])[:3]
    if not teams:
        answer = "Non ci sono ancora team con ore attività aggregate nelle analytics Operazioni."
        excerpt = "Ore per team non disponibili."
    else:
        summary = "; ".join(f"{item['team_name']}: {float(item['total_hours']):.1f} h" for item in teams)
        answer = f"Ore per team Operazioni: {summary}."
        excerpt = summary
    return build_live_data_response(
        answer=answer,
        tool_name="get_operazioni_analytics_work_hours_by_team",
        evidence_label="Ore per team Operazioni",
        source_key="operazioni.analytics.work-hours.by-team",
        excerpt=excerpt,
        payload=payload,
    )


def _explain_operazioni_analytics_metric(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    return explain_operazioni_analytics_metric(question)


def _find_operazioni_analytics_anomaly_by_id(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.operazioni.routes.analytics import anomalies_analytics

    anomaly_id = parse_uuid(question)
    if anomaly_id is None:
        return build_live_data_response(
            answer="Per cercare un'anomalia analytics Operazioni devo ricevere un UUID valido.",
            tool_name="find_operazioni_analytics_anomaly_by_id",
            evidence_label="Lookup anomalia analytics non eseguito",
            source_key="operazioni.analytics.anomalies.lookup",
            excerpt="UUID anomalia analytics non presente nella domanda.",
        )

    anomaly_identifier = str(anomaly_id)
    response = anomalies_analytics(current_user=current_user, db=db, from_date=None, to_date=None, anomaly_type=None)
    item = next(
        (
            candidate
            for candidate in response.items
            if candidate.id == anomaly_identifier
            or candidate.entity_id == anomaly_identifier
            or candidate.id.endswith(anomaly_identifier)
        ),
        None,
    )
    if item is None:
        return build_live_data_response(
            answer="Non ho trovato nessuna anomalia analytics Operazioni con questo identificativo.",
            tool_name="find_operazioni_analytics_anomaly_by_id",
            evidence_label="Anomalia analytics non trovata",
            source_key=f"operazioni.analytics.anomalies.{anomaly_identifier}",
            excerpt=f"Anomaly identifier {anomaly_identifier} non trovato nel set analytics corrente.",
        )

    payload = {
        "id": item.id,
        "type": item.type,
        "severity": item.severity,
        "description": item.description,
        "entity_id": item.entity_id,
        "entity_label": item.entity_label,
        "detected_at": item.detected_at,
        "details": item.details,
    }
    answer = (
        "Lookup anomalia analytics Operazioni: "
        f"{item.type}, severità {item.severity}, entità {item.entity_label or item.entity_id or 'n/d'}, "
        f"rilevata {item.detected_at}."
    )
    excerpt = f"Anomaly {item.id}, type {item.type}, severity {item.severity}."
    return build_live_data_response(
        answer=answer,
        tool_name="find_operazioni_analytics_anomaly_by_id",
        evidence_label="Dettaglio anomalia analytics Operazioni",
        source_key=f"operazioni.analytics.anomalies.{item.id}",
        excerpt=excerpt,
        payload=payload,
    )


def _explain_operazioni_analytics_anomaly(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    anomaly_id = parse_uuid(question)
    if anomaly_id is None:
        return build_live_data_response(
            answer="Per spiegare un'anomalia analytics Operazioni devo ricevere un UUID valido.",
            tool_name="explain_operazioni_analytics_anomaly",
            evidence_label="Spiegazione anomalia analytics non eseguita",
            source_key="operazioni.analytics.anomaly.logic.lookup",
            excerpt="UUID anomalia analytics non presente nella domanda.",
        )
    return explain_operazioni_analytics_anomaly(db, current_user, str(anomaly_id))


OPERAZIONI_ANALYTICS_TOOLS: tuple[WikiToolDefinition, ...] = (
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_operazioni_analytics_anomaly_by_id", module_key="operazioni"),
        intents=("live_data",),
        priority=105,
        matcher=_match_operazioni_analytics_anomaly,
        handler=_find_operazioni_analytics_anomaly_by_id,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="get_operazioni_analytics_summary", module_key="operazioni"),
        intents=("live_data",),
        priority=30,
        matcher=_match_operazioni_analytics_summary,
        handler=_operazioni_analytics_summary,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="get_operazioni_analytics_top_fuel_vehicles", module_key="operazioni"),
        intents=("live_data",),
        priority=31,
        matcher=_match_operazioni_analytics_top_fuel,
        handler=_operazioni_analytics_top_fuel,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="get_operazioni_analytics_top_km_operators", module_key="operazioni"),
        intents=("live_data",),
        priority=31,
        matcher=_match_operazioni_analytics_top_km_operators,
        handler=_operazioni_analytics_top_km_operators,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="get_operazioni_analytics_work_hours_by_team", module_key="operazioni"),
        intents=("live_data",),
        priority=31,
        matcher=_match_operazioni_analytics_work_hours_team,
        handler=_operazioni_analytics_work_hours_by_team,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_operazioni_analytics_metric", module_key="operazioni"),
        intents=("logic",),
        priority=55,
        matcher=_match_operazioni_analytics_logic,
        handler=_explain_operazioni_analytics_metric,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_operazioni_analytics_anomaly", module_key="operazioni"),
        intents=("logic",),
        priority=65,
        matcher=_match_operazioni_analytics_anomaly_logic,
        handler=_explain_operazioni_analytics_anomaly,
    ),
)
