from __future__ import annotations

from app.modules.wiki.schemas import WikiChatResponse, WikiChunkSource, WikiEvidence, WikiToolCallSummary


def _infer_payload_kind(source_key: str) -> str | None:
    if source_key == "accessi.dashboard.summary":
        return "accessi_dashboard_summary"
    if source_key.startswith("accessi.nas-users."):
        return "accessi_nas_user_detail"
    if source_key.startswith("accessi.shares."):
        return "accessi_share_detail"
    if source_key == "catasto.dashboard.summary":
        return "catasto_dashboard_summary"
    if source_key.startswith("catasto.particelle."):
        return "catasto_particella_detail"
    if source_key == "ruolo.stats":
        return "ruolo_dashboard_summary"
    if source_key.startswith("ruolo.subjects."):
        return "ruolo_subject_detail"
    if source_key == "utenze.stats":
        return "utenze_stats"
    if source_key.startswith("utenze.subjects."):
        return "utenze_subject_detail"
    if source_key.startswith("riordino.practices."):
        return "riordino_practice_detail"
    if source_key == "operazioni.analytics.summary":
        return "operazioni_analytics_summary"
    if source_key == "operazioni.dashboard.summary":
        return "operazioni_dashboard_summary"
    if source_key == "operazioni.dashboard.pending-approvals":
        return "operazioni_pending_approvals"
    if source_key == "operazioni.analytics.fuel.top-vehicles":
        return "operazioni_analytics_top_fuel_vehicles"
    if source_key == "operazioni.analytics.km.top-operators":
        return "operazioni_analytics_top_km_operators"
    if source_key == "operazioni.analytics.work-hours.by-team":
        return "operazioni_analytics_work_hours_by_team"
    if source_key == "operazioni.storage.summary":
        return "operazioni_storage_status"
    if source_key == "operazioni.mobile-sync.summary":
        return "operazioni_mobile_sync_status"
    if source_key.startswith("operazioni.cases."):
        return "operazioni_case_detail"
    if source_key.startswith("operazioni.assignments."):
        return "operazioni_assignment_detail"
    if source_key.startswith("operazioni.maintenances."):
        return "operazioni_maintenance_detail"
    if source_key.startswith("operazioni.usage-sessions."):
        return "operazioni_usage_session_detail"
    if source_key.startswith("operazioni.activities."):
        return "operazioni_activity_detail"
    if source_key.startswith("operazioni.activity-approvals."):
        return "operazioni_activity_approval_detail"
    if source_key.startswith("operazioni.fuel-logs."):
        return "operazioni_fuel_log_detail"
    if source_key.startswith("operazioni.unresolved-transactions."):
        return "operazioni_unresolved_transaction_detail"
    if source_key.startswith("operazioni.autodoc-sync."):
        return "operazioni_autodoc_sync_status"
    return None


def build_live_data_response(
    *,
    answer: str,
    tool_name: str,
    evidence_label: str,
    source_key: str,
    excerpt: str,
    payload_kind: str | None = None,
    payload: dict[str, object] | None = None,
) -> WikiChatResponse:
    return WikiChatResponse(
        answer=answer,
        sources=[],
        found=True,
        mode="live_data",
        evidences=[
            WikiEvidence(
                type="live_data",
                label=evidence_label,
                source_key=source_key,
                excerpt=excerpt,
                payload_kind=payload_kind or _infer_payload_kind(source_key),
                payload=payload,
            )
        ],
        tool_calls=[WikiToolCallSummary(tool_name=tool_name, success=True, redacted=False)],
    )


def build_logic_response(
    *,
    answer: str,
    tool_name: str,
    evidence_label: str,
    source_key: str,
    excerpt: str,
    payload_kind: str | None = None,
    payload: dict[str, object] | None = None,
) -> WikiChatResponse:
    return WikiChatResponse(
        answer=answer,
        sources=[],
        found=True,
        mode="logic",
        evidences=[
            WikiEvidence(
                type="logic",
                label=evidence_label,
                source_key=source_key,
                excerpt=excerpt,
                payload_kind=payload_kind or _infer_payload_kind(source_key),
                payload=payload,
            )
        ],
        tool_calls=[WikiToolCallSummary(tool_name=tool_name, success=True, redacted=False)],
    )


def build_docs_evidences(sources: list[WikiChunkSource]) -> list[WikiEvidence]:
    evidences: list[WikiEvidence] = []
    for source in sources:
        label = source.section_title or source.source_file.split("/")[-1]
        evidences.append(
            WikiEvidence(
                type="docs",
                label=label,
                source_key=source.source_file,
                excerpt=source.excerpt,
                payload_kind="docs_chunk",
            )
        )
    return evidences


def build_hybrid_response(
    *,
    tool_response: WikiChatResponse,
    docs_response: WikiChatResponse,
) -> WikiChatResponse:
    answer_parts = [tool_response.answer.strip()]
    if docs_response.answer.strip():
        answer_parts.append(f"Contesto documentale: {docs_response.answer.strip()}")

    return WikiChatResponse(
        answer="\n\n".join(part for part in answer_parts if part),
        sources=docs_response.sources,
        found=tool_response.found or docs_response.found,
        mode="hybrid",
        evidences=[
            *tool_response.evidences,
            *build_docs_evidences(docs_response.sources),
            *docs_response.evidences,
        ],
        tool_calls=tool_response.tool_calls,
    )


def build_tool_denied_response(*, tool_name: str, reason: str) -> WikiChatResponse:
    return WikiChatResponse(
        answer=reason,
        sources=[],
        found=False,
        mode="live_data",
        tool_calls=[WikiToolCallSummary(tool_name=tool_name, success=False, redacted=True)],
    )
