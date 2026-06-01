from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.logic_catalog import (
    CATALOG_OPERAZIONI_ANALYTICS_ANOMALY,
    CATALOG_OPERAZIONI_ANALYTICS_METRICS,
)
from app.modules.wiki.services.response_composer import build_logic_response


def explain_operazioni_analytics_metric(question: str) -> WikiChatResponse:
    normalized = question.lower()
    metric_key = "total_km"
    if any(term in normalized for term in ("km", "chilometri", "kilometri")):
        metric_key = "total_km"
        if any(term in normalized for term in ("operatori", "operatori km", "top operatori", "top operator")):
            metric_key = "top_operators_km"
    elif any(term in normalized for term in ("litri", "carburante", "fuel", "riforn")):
        metric_key = "total_liters"
    elif any(term in normalized for term in ("ore", "work hours", "lavoro", "attivita", "attività")):
        metric_key = "total_work_hours"
        if any(term in normalized for term in ("team", "squadra", "by team")):
            metric_key = "work_hours_by_team"
    elif any(term in normalized for term in ("sessioni attive", "sessioni aperte", "active sessions")):
        metric_key = "active_sessions"
    elif any(term in normalized for term in ("anomalie", "anomaly", "alert")):
        metric_key = "anomaly_count"

    explanation = CATALOG_OPERAZIONI_ANALYTICS_METRICS[metric_key]
    return build_logic_response(
        answer=explanation.answer_template,
        tool_name="explain_operazioni_analytics_metric",
        evidence_label=explanation.label,
        source_key=explanation.source_key,
        excerpt=explanation.excerpt,
        payload={"metric_key": metric_key},
    )


def explain_operazioni_analytics_anomaly(db: Session, current_user: ApplicationUser, anomaly_identifier: str) -> WikiChatResponse:
    from app.modules.operazioni.routes.analytics import anomalies_analytics

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
        return build_logic_response(
            answer="Non ho trovato nessuna anomalia analytics Operazioni con questo identificativo.",
            tool_name="explain_operazioni_analytics_anomaly",
            evidence_label="Anomalia analytics non trovata",
            source_key=f"operazioni.analytics.anomalies.{anomaly_identifier}",
            excerpt=f"Anomaly identifier {anomaly_identifier} non trovato nel set analytics corrente.",
            payload={"anomaly_identifier": anomaly_identifier},
        )

    explanation = CATALOG_OPERAZIONI_ANALYTICS_ANOMALY.get(item.type)
    base_rule = explanation.answer_template if explanation is not None else "L'anomalia deriva dalle regole analytics operative del modulo Operazioni."
    answer = (
        f"L'anomalia analytics {item.id} è di tipo {item.type} con severità {item.severity}. "
        f"{base_rule} Descrizione: {item.description}."
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
    return build_logic_response(
        answer=answer,
        tool_name="explain_operazioni_analytics_anomaly",
        evidence_label=explanation.label if explanation is not None else "Spiegazione anomalia analytics Operazioni",
        source_key=f"operazioni.analytics.anomalies.logic.{item.id}",
        excerpt=explanation.excerpt if explanation is not None else item.description,
        payload=payload,
    )
