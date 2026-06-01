from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.models.wc_sync_job import WCSyncJob
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.logic_catalog import (
    CATALOG_OPERAZIONI_AUTODOC_SYNC_STATUS,
    CATALOG_OPERAZIONI_MOBILE_SYNC,
    CATALOG_OPERAZIONI_STORAGE_ALERTS,
)
from app.modules.wiki.services.response_composer import build_logic_response


def explain_operazioni_storage_alert_level(question: str) -> WikiChatResponse:
    normalized = question.lower()
    explanation_key = "quota_usage"
    if any(term in normalized for term in ("critical", "critico", "critica")):
        explanation_key = "critical"
    elif any(term in normalized for term in ("warning", "attenzione", "allerta")):
        explanation_key = "warning"

    explanation = CATALOG_OPERAZIONI_STORAGE_ALERTS[explanation_key]
    return build_logic_response(
        answer=explanation.answer_template,
        tool_name="explain_operazioni_storage_alert_level",
        evidence_label=explanation.label,
        source_key=explanation.source_key,
        excerpt=explanation.excerpt,
        payload={"explanation_key": explanation_key},
    )


def explain_operazioni_mobile_sync_flow(question: str) -> WikiChatResponse:
    normalized = question.lower()
    explanation_key = "handshake"
    if any(term in normalized for term in ("catalog", "cataloghi", "catalogo")):
        explanation_key = "catalogs"
    elif any(term in normalized for term in ("workset", "attivita assegnate", "veicoli disponibili", "operatori mobile")):
        explanation_key = "worksets"
    elif any(term in normalized for term in ("field report", "activity start", "activity stop", "writeback", "fault")):
        explanation_key = "writeback"

    explanation = CATALOG_OPERAZIONI_MOBILE_SYNC[explanation_key]
    return build_logic_response(
        answer=explanation.answer_template,
        tool_name="explain_operazioni_mobile_sync_flow",
        evidence_label=explanation.label,
        source_key=explanation.source_key,
        excerpt=explanation.excerpt,
        payload={"explanation_key": explanation_key},
    )


def explain_operazioni_autodoc_sync_status(db: Session, current_user: ApplicationUser, job_id: UUID) -> WikiChatResponse:
    job = db.get(WCSyncJob, job_id)
    if job is None or job.entity != "autodoc_vehicle_details":
        return build_logic_response(
            answer="Non ho trovato nessun job AUTODOC Operazioni con questo identificativo.",
            tool_name="explain_operazioni_autodoc_sync_status",
            evidence_label="Job AUTODOC non trovato",
            source_key=f"operazioni.autodoc-sync.{job_id}",
            excerpt=f"AUTODOC sync job {job_id} non presente nel dominio Operazioni.",
            payload={"job_id": str(job_id)},
        )

    explanation = CATALOG_OPERAZIONI_AUTODOC_SYNC_STATUS.get(job.status)
    base_rule = explanation.answer_template if explanation is not None else "Lo stato del job AUTODOC deriva dal ciclo di vita del worker asincrono di sincronizzazione."
    answer = (
        f"Il job AUTODOC {job.id} è nello stato {job.status}. {base_rule} "
        f"Record synced {job.records_synced or 0}, skip {job.records_skipped or 0}, errori {job.records_errors or 0}."
    )
    excerpt = (
        f"AUTODOC job {job.id}, status {job.status}, synced {job.records_synced or 0}, "
        f"skipped {job.records_skipped or 0}, errors {job.records_errors or 0}."
    )
    payload = {
        "job_id": str(job.id),
        "entity": job.entity,
        "status": job.status,
        "started_at": job.started_at.isoformat(),
        "finished_at": job.finished_at.isoformat() if job.finished_at is not None else None,
        "records_synced": job.records_synced,
        "records_skipped": job.records_skipped,
        "records_errors": job.records_errors,
        "error_detail": job.error_detail,
        "triggered_by": job.triggered_by,
        "params_json": job.params_json,
    }
    return build_logic_response(
        answer=answer,
        tool_name="explain_operazioni_autodoc_sync_status",
        evidence_label=explanation.label if explanation is not None else "Spiegazione job AUTODOC Operazioni",
        source_key=f"operazioni.autodoc-sync.logic.{job.id}",
        excerpt=explanation.excerpt if explanation is not None else excerpt,
        payload=payload,
    )
