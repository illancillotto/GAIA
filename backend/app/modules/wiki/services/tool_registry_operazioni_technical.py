from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.policy import WikiToolMeta
from app.modules.wiki.services.response_composer import build_live_data_response
from app.modules.wiki.services.system_logic import (
    explain_operazioni_autodoc_sync_status,
    explain_operazioni_mobile_sync_flow,
    explain_operazioni_storage_alert_level,
)
from app.modules.wiki.services.tool_registry_common import WikiToolDefinition, contains_any, has_uuid, parse_uuid, score_terms


def _match_operazioni_storage_summary(question: str) -> int:
    if not contains_any(question, "storage", "quota", "spazio", "alert storage", "allerta storage"):
        return 0
    return 8 + score_terms(question, "storage", "quota", "spazio", "alert", "operazioni")


def _match_operazioni_storage_logic(question: str) -> int:
    if not contains_any(question, "storage", "quota", "spazio", "alert", "warning", "critical"):
        return 0
    if not contains_any(question, "spiega", "significa", "come funziona", "regola", "soglia"):
        return 0
    return 8 + score_terms(question, "storage", "quota", "spazio", "alert", "warning", "critical", "soglia")


def _match_operazioni_mobile_sync_summary(question: str) -> int:
    if not contains_any(question, "mobile sync", "sync mobile", "connettore mobile", "operatori mobile", "workset", "cataloghi mobile"):
        return 0
    return 8 + score_terms(question, "mobile sync", "sync mobile", "connettore", "operatori mobile", "workset", "cataloghi")


def _match_operazioni_mobile_sync_logic(question: str) -> int:
    if not contains_any(question, "mobile sync", "sync mobile", "connettore mobile", "workset", "cataloghi mobile", "field report"):
        return 0
    if not contains_any(question, "spiega", "significa", "come funziona", "regola", "writeback", "handshake"):
        return 0
    return 8 + score_terms(question, "mobile sync", "connettore", "workset", "cataloghi", "field report", "handshake")


def _match_operazioni_autodoc_sync(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "autodoc", "sync autodoc", "sincronizzazione autodoc", "job autodoc"):
        return 0
    return 11 + score_terms(question, "autodoc", "sync", "job", "operazioni")


def _match_operazioni_autodoc_sync_logic(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "autodoc", "sync autodoc", "sincronizzazione autodoc", "job autodoc"):
        return 0
    if not contains_any(question, "spiega", "perche", "perché", "significa", "stato"):
        return 0
    return 9 + score_terms(question, "autodoc", "sync", "job", "stato")


def _operazioni_storage_status(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.operazioni.routes.dashboard import latest_storage_metric, storage_alerts

    metric_payload = latest_storage_metric(current_user=current_user, db=db)
    alerts_payload = storage_alerts(current_user=current_user, db=db)
    highest_level = alerts_payload[0]["level"] if alerts_payload else "none"
    answer = (
        "Storage Operazioni: "
        f"{metric_payload['percentage_used']:.1f}% quota usata, "
        f"{len(alerts_payload)} alert attivi, livello più alto {highest_level}."
    )
    excerpt = (
        f"Quota {metric_payload['percentage_used']:.1f}%, alerts {len(alerts_payload)}, "
        f"highest_level {highest_level}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="get_operazioni_storage_status",
        evidence_label="Storage alerts Operazioni",
        source_key="operazioni.storage.summary",
        excerpt=excerpt,
        payload={
            "metric": metric_payload,
            "alerts": alerts_payload,
            "active_alert_count": len(alerts_payload),
            "highest_level": highest_level,
        },
    )


def _operazioni_mobile_sync_status(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.operazioni.routes.mobile_sync import (
        get_mobile_catalogs,
        get_mobile_operators,
        get_mobile_worksets,
        mobile_connector_handshake,
    )

    handshake = mobile_connector_handshake().model_dump(mode="json")
    operators = get_mobile_operators(db=db).model_dump(mode="json")
    catalogs = get_mobile_catalogs(db=db).model_dump(mode="json")
    worksets = get_mobile_worksets(db=db, operator_id=None).model_dump(mode="json")

    workset_type_counts: dict[str, int] = {}
    for item in worksets["worksets"]:
        workset_type = item["workset_type"]
        workset_type_counts[workset_type] = workset_type_counts.get(workset_type, 0) + 1

    answer = (
        "Mobile sync Operazioni: "
        f"{len(operators['operators'])} operatori esportati, {len(catalogs['catalogs'])} cataloghi, "
        f"{len(worksets['worksets'])} workset, capability {len(handshake['capabilities'])}."
    )
    excerpt = (
        f"Operators {len(operators['operators'])}, catalogs {len(catalogs['catalogs'])}, "
        f"worksets {len(worksets['worksets'])}, capabilities {len(handshake['capabilities'])}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="get_operazioni_mobile_sync_status",
        evidence_label="Stato mobile sync Operazioni",
        source_key="operazioni.mobile-sync.summary",
        excerpt=excerpt,
        payload={
            "handshake": handshake,
            "operators_count": len(operators["operators"]),
            "catalogs_count": len(catalogs["catalogs"]),
            "worksets_count": len(worksets["worksets"]),
            "workset_type_counts": workset_type_counts,
            "operator_synced_from": operators["synced_from_gaia_at"],
        },
    )


def _operazioni_autodoc_sync_status(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.operazioni.services.autodoc_sync import get_latest_autodoc_sync_job, serialize_autodoc_sync_job

    job = get_latest_autodoc_sync_job(db)
    if job is None:
        return build_live_data_response(
            answer="Non risultano job AUTODOC Operazioni eseguiti o in coda.",
            tool_name="get_operazioni_autodoc_sync_status",
            evidence_label="Stato sync AUTODOC non disponibile",
            source_key="operazioni.autodoc-sync.latest",
            excerpt="Nessun job AUTODOC presente.",
            payload={"job": None},
        )

    payload = serialize_autodoc_sync_job(job).model_dump(mode="json")
    answer = (
        "Stato sync AUTODOC Operazioni: "
        f"job {payload['job_id']}, stato {payload['status']}, "
        f"synced {payload['records_synced'] or 0}, skip {payload['records_skipped'] or 0}, errori {payload['records_errors'] or 0}."
    )
    excerpt = (
        f"AUTODOC job {payload['job_id']}, status {payload['status']}, "
        f"synced {payload['records_synced'] or 0}, errors {payload['records_errors'] or 0}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="get_operazioni_autodoc_sync_status",
        evidence_label="Ultimo job AUTODOC Operazioni",
        source_key=f"operazioni.autodoc-sync.{payload['job_id']}",
        excerpt=excerpt,
        payload=payload,
    )


def _explain_operazioni_storage_alert_level(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    return explain_operazioni_storage_alert_level(question)


def _explain_operazioni_mobile_sync_flow(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    return explain_operazioni_mobile_sync_flow(question)


def _explain_operazioni_autodoc_sync_status(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    job_id = parse_uuid(question)
    if job_id is None:
        return build_live_data_response(
            answer="Per spiegare un job AUTODOC Operazioni devo ricevere un UUID valido.",
            tool_name="explain_operazioni_autodoc_sync_status",
            evidence_label="Spiegazione job AUTODOC non eseguita",
            source_key="operazioni.autodoc-sync.logic.lookup",
            excerpt="UUID job AUTODOC non presente nella domanda.",
        )
    return explain_operazioni_autodoc_sync_status(db, current_user, job_id)


def _find_operazioni_autodoc_sync_job_by_id(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.models.wc_sync_job import WCSyncJob
    from app.modules.operazioni.services.autodoc_sync import serialize_autodoc_sync_job

    job_id = parse_uuid(question)
    if job_id is None:
        return build_live_data_response(
            answer="Per cercare un job AUTODOC Operazioni devo ricevere un UUID valido.",
            tool_name="find_operazioni_autodoc_sync_job_by_id",
            evidence_label="Lookup job AUTODOC non eseguito",
            source_key="operazioni.autodoc-sync.lookup",
            excerpt="UUID job AUTODOC non presente nella domanda.",
        )

    job = db.get(WCSyncJob, job_id)
    if job is None or job.entity != "autodoc_vehicle_details":
        return build_live_data_response(
            answer="Non ho trovato nessun job AUTODOC Operazioni con questo identificativo.",
            tool_name="find_operazioni_autodoc_sync_job_by_id",
            evidence_label="Job AUTODOC non trovato",
            source_key=f"operazioni.autodoc-sync.{job_id}",
            excerpt=f"AUTODOC sync job {job_id} non presente nel dominio Operazioni.",
        )

    payload = serialize_autodoc_sync_job(job).model_dump(mode="json")
    answer = (
        "Lookup job AUTODOC Operazioni: "
        f"stato {payload['status']}, synced {payload['records_synced'] or 0}, "
        f"skip {payload['records_skipped'] or 0}, errori {payload['records_errors'] or 0}."
    )
    excerpt = (
        f"AUTODOC job {payload['job_id']}, status {payload['status']}, "
        f"errors {payload['records_errors'] or 0}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_operazioni_autodoc_sync_job_by_id",
        evidence_label="Dettaglio job AUTODOC Operazioni",
        source_key=f"operazioni.autodoc-sync.{payload['job_id']}",
        excerpt=excerpt,
        payload=payload,
    )


OPERAZIONI_TECHNICAL_TOOLS: tuple[WikiToolDefinition, ...] = (
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_operazioni_autodoc_sync_job_by_id", module_key="operazioni"),
        intents=("live_data",),
        priority=104,
        matcher=_match_operazioni_autodoc_sync,
        handler=_find_operazioni_autodoc_sync_job_by_id,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="get_operazioni_storage_status", module_key="operazioni"),
        intents=("live_data",),
        priority=27,
        matcher=_match_operazioni_storage_summary,
        handler=_operazioni_storage_status,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="get_operazioni_mobile_sync_status", module_key="operazioni"),
        intents=("live_data",),
        priority=27,
        matcher=_match_operazioni_mobile_sync_summary,
        handler=_operazioni_mobile_sync_status,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="get_operazioni_autodoc_sync_status", module_key="operazioni"),
        intents=("live_data",),
        priority=25,
        matcher=lambda question: 5 if contains_any(question, "autodoc", "sync autodoc", "sincronizzazione autodoc", "job autodoc") else 0,
        handler=_operazioni_autodoc_sync_status,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_operazioni_storage_alert_level", module_key="operazioni"),
        intents=("logic",),
        priority=55,
        matcher=_match_operazioni_storage_logic,
        handler=_explain_operazioni_storage_alert_level,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_operazioni_mobile_sync_flow", module_key="operazioni"),
        intents=("logic",),
        priority=55,
        matcher=_match_operazioni_mobile_sync_logic,
        handler=_explain_operazioni_mobile_sync_flow,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_operazioni_autodoc_sync_status", module_key="operazioni"),
        intents=("logic",),
        priority=65,
        matcher=_match_operazioni_autodoc_sync_logic,
        handler=_explain_operazioni_autodoc_sync_status,
    ),
)
