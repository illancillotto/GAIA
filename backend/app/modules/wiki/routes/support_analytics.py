from __future__ import annotations

import re
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.wiki.models import WikiRequest, WikiRequestEvent, WikiToolAuditLog
from app.modules.wiki.schemas import (
    WikiSupportAnalyticsCountRead,
    WikiSupportClusterRead,
    WikiSupportClustersResponse,
    WikiSupportInsightRead,
    WikiSupportInsightsResponse,
    WikiSupportAnalyticsSeriesPointRead,
    WikiSupportAnalyticsSeriesResponse,
    WikiSupportAnalyticsSummaryRead,
)

router = APIRouter(tags=["Wiki"])
_TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9]+")
_STOPWORDS = {
    "a", "ad", "al", "alla", "allo", "anche", "che", "con", "come", "da", "dei", "del", "della", "delle",
    "di", "e", "ed", "gli", "ho", "il", "in", "la", "le", "lo", "ma", "mi", "nei", "nel", "nella", "non",
    "per", "piu", "su", "the", "to", "un", "una", "uno",
}


def _require_wiki_admin(current_user: ApplicationUser) -> None:
    if current_user.role not in ("admin", "super_admin"):
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso negato.")


def _normalize(value: str | None) -> str:
    normalized = _TOKEN_SPLIT_RE.sub(" ", (value or "").lower()).strip()
    return " ".join(normalized.split())


def _tokens(*parts: str | None) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for part in parts:
        normalized = _normalize(part)
        for token in normalized.split():
            if len(token) < 3 or token in _STOPWORDS or token in seen:
                continue
            seen.add(token)
            tokens.append(token)
    return tokens


def _semantic_cluster_key(request: WikiRequest, canonical_ids: set[uuid.UUID]) -> str:
    if request.canonical_request_id:
        return f"canonical:{request.canonical_request_id}"
    if request.id in canonical_ids:
        return f"canonical:{request.id}"
    base_tokens = _tokens(request.user_question, request.desired_outcome, request.observed_behavior, request.expected_behavior)[:4]
    module_key = _normalize(request.module_key) or "unknown"
    page_key = _normalize(request.page_path) or "unknown"
    token_key = "-".join(base_tokens) or "generic"
    return f"semantic:{request.request_type}:{module_key}:{page_key}:{token_key}"


def _cluster_title(requests: list[WikiRequest]) -> str:
    first = requests[0]
    module = first.module_key or "modulo non dichiarato"
    request_type = first.request_type.replace("_", " ")
    page = first.page_path or "contesto generico"
    tokens = _tokens(first.user_question, first.desired_outcome, first.observed_behavior, first.expected_behavior)[:3]
    if tokens:
        return f"{module} · {request_type} · {' / '.join(tokens)}"
    return f"{module} · {request_type} · {page}"


def _support_window_requests(db: Session, *, start_date: date) -> list[WikiRequest]:
    return (
        db.query(WikiRequest)
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .order_by(WikiRequest.created_at.desc())
        .all()
    )


def _origin_signal_counts(db: Session, requests: list[WikiRequest]) -> tuple[int, int, int]:
    conversation_ids = [item.conversation_id for item in requests if item.conversation_id]
    if not conversation_ids:
        return 0, 0, 0

    rows = (
        db.query(
            WikiToolAuditLog.conversation_id.label("conversation_id"),
            func.max(case((WikiToolAuditLog.found == 0, 1), else_=0)).label("has_no_match"),
            func.max(case((WikiToolAuditLog.tool_name == "guardrail", 1), else_=0)).label("has_guardrail"),
            func.max(case((WikiToolAuditLog.mode == "docs_only", 1), else_=0)).label("has_docs_only"),
        )
        .filter(WikiToolAuditLog.conversation_id.in_(conversation_ids))
        .group_by(WikiToolAuditLog.conversation_id)
        .all()
    )
    by_conversation = {
        row.conversation_id: (
            int(row.has_no_match or 0),
            int(row.has_guardrail or 0),
            int(row.has_docs_only or 0),
        )
        for row in rows
    }
    no_match_count = 0
    guardrail_count = 0
    docs_only_count = 0
    seen_no_match: set[uuid.UUID] = set()
    seen_guardrail: set[uuid.UUID] = set()
    seen_docs: set[uuid.UUID] = set()
    for item in requests:
        if not item.conversation_id or item.conversation_id not in by_conversation:
            continue
        has_no_match, has_guardrail, has_docs_only = by_conversation[item.conversation_id]
        if has_no_match and item.id not in seen_no_match:
            no_match_count += 1
            seen_no_match.add(item.id)
        if has_guardrail and item.id not in seen_guardrail:
            guardrail_count += 1
            seen_guardrail.add(item.id)
        if has_docs_only and item.id not in seen_docs:
            docs_only_count += 1
            seen_docs.add(item.id)
    return no_match_count, guardrail_count, docs_only_count


def _reopened_requests_count(db: Session, requests: list[WikiRequest]) -> int:
    request_ids = [item.id for item in requests]
    if not request_ids:
        return 0
    rows = (
        db.query(func.count(func.distinct(WikiRequestEvent.request_id)))
        .filter(WikiRequestEvent.request_id.in_(request_ids))
        .filter(WikiRequestEvent.event_type == "reopened_by_user")
        .scalar()
    )
    return int(rows or 0)


def _cluster_requests(requests: list[WikiRequest], *, limit: int) -> list[WikiSupportClusterRead]:
    canonical_ids = {item.canonical_request_id for item in requests if item.canonical_request_id is not None}
    buckets: dict[str, list[WikiRequest]] = {}
    for item in requests:
        key = _semantic_cluster_key(item, canonical_ids=canonical_ids)
        buckets.setdefault(key, []).append(item)

    clusters: list[WikiSupportClusterRead] = []
    for key, items in buckets.items():
        ordered = sorted(items, key=lambda item: item.created_at, reverse=True)
        open_requests = sum(1 for item in items if item.status not in {"resolved", "duplicate", "rejected"})
        duplicate_requests = sum(1 for item in items if item.status == "duplicate")
        affected_users = len({item.created_by for item in items if item.created_by})
        canonical_case_count = sum(1 for item in items if item.id in canonical_ids and item.canonical_request_id is None)
        first = ordered[0]
        clusters.append(
            WikiSupportClusterRead(
                cluster_key=key,
                title=_cluster_title(ordered),
                request_type=first.request_type,
                module_key=first.module_key,
                page_path=first.page_path,
                total_requests=len(items),
                open_requests=open_requests,
                duplicate_requests=duplicate_requests,
                affected_users=affected_users,
                canonical_case_count=canonical_case_count,
                latest_created_at=first.created_at,
                sample_questions=[item.user_question for item in ordered[:3]],
            )
        )
    clusters.sort(
        key=lambda item: (
            item.total_requests,
            item.duplicate_requests,
            item.affected_users,
            item.latest_created_at,
        ),
        reverse=True,
    )
    return clusters[:limit]


def _build_support_insights(
    *,
    total_requests: int,
    clusters: list[WikiSupportClusterRead],
    top_modules: list[WikiSupportAnalyticsCountRead],
    top_pages: list[WikiSupportAnalyticsCountRead],
    duplicate_requests: int,
    reopened_requests: int,
    no_match_origin_requests: int,
    guardrail_origin_requests: int,
    docs_only_origin_requests: int,
    feature_requests: int,
    bug_reports: int,
) -> list[WikiSupportInsightRead]:
    insights: list[WikiSupportInsightRead] = []
    if total_requests <= 0:
        return insights

    duplicate_rate = duplicate_requests / total_requests
    no_match_rate = no_match_origin_requests / total_requests
    docs_only_rate = docs_only_origin_requests / total_requests
    guardrail_rate = guardrail_origin_requests / total_requests
    feature_rate = feature_requests / total_requests
    bug_rate = bug_reports / total_requests

    if duplicate_rate >= 0.25:
        insights.append(
            WikiSupportInsightRead(
                insight_type="duplicate_pressure",
                severity="critical" if duplicate_rate >= 0.4 else "warning",
                title="Pressione duplicati elevata",
                description="Molte richieste supporto vengono accorpate a casi già esistenti: il bisogno si ripete e il triage rischia di saturarsi.",
                metric_value=f"{round(duplicate_rate * 100)}%",
                action_hint="Verifica i cluster principali e valuta documentazione, fix prodotto o messaggi in-app per ridurre i casi ripetuti.",
            )
        )

    if no_match_rate >= 0.2:
        insights.append(
            WikiSupportInsightRead(
                insight_type="wiki_coverage_gap",
                severity="critical" if no_match_rate >= 0.35 else "warning",
                title="Gap di copertura documentale del Wiki",
                description="Una quota rilevante delle richieste nasce dopo un no-match del Wiki, segnale che l’assistente non trova contesto utile.",
                metric_value=f"{round(no_match_rate * 100)}%",
                action_hint="Rivedi le aree top per modulo e pagina; priorità a documentazione o tool live mancanti.",
            )
        )

    if docs_only_rate >= 0.3:
        insights.append(
            WikiSupportInsightRead(
                insight_type="docs_only_pressure",
                severity="warning",
                title="Pressione elevata su risposte solo documentali",
                description="Molti casi arrivano da conversazioni in cui il Wiki ha risposto solo con documentazione, senza risolvere il problema operativo.",
                metric_value=f"{round(docs_only_rate * 100)}%",
                action_hint="Valuta nuovi tool live o guide più operative nei moduli più colpiti.",
            )
        )

    if guardrail_rate >= 0.12:
        insights.append(
            WikiSupportInsightRead(
                insight_type="guardrail_pressure",
                severity="warning",
                title="Molte richieste bloccate dai guardrail",
                description="Gli utenti stanno tentando azioni o accessi che il Wiki non può eseguire: serve chiarire il perimetro o migliorare i percorsi di supporto.",
                metric_value=f"{round(guardrail_rate * 100)}%",
                action_hint="Controlla se i casi riguardano accessi, azioni o richieste live esterne e definisci un flusso più chiaro.",
            )
        )

    if reopened_requests >= max(3, total_requests // 8):
        insights.append(
            WikiSupportInsightRead(
                insight_type="negative_feedback_loop",
                severity="critical" if reopened_requests >= max(5, total_requests // 5) else "warning",
                title="Molti casi vengono riaperti dagli utenti",
                description="Le richieste chiuse non stanno sempre portando a una soluzione percepita come valida.",
                metric_value=reopened_requests,
                action_hint="Analizza le richieste riaperte e il feedback non helpful per capire dove il workflow di chiusura è debole.",
            )
        )

    if feature_rate >= 0.35:
        module = top_modules[0].key if top_modules else None
        insights.append(
            WikiSupportInsightRead(
                insight_type="feature_demand",
                severity="info",
                title="Domanda di prodotto alta",
                description="Le feature request rappresentano una quota importante del backlog supporto.",
                metric_value=f"{round(feature_rate * 100)}%",
                action_hint="Usa i cluster e il modulo dominante per trasformare il backlog utenti in roadmap di prodotto.",
                related_key=module,
            )
        )

    if bug_rate >= 0.3:
        page = top_pages[0].key if top_pages else None
        insights.append(
            WikiSupportInsightRead(
                insight_type="bug_hotspot",
                severity="warning",
                title="Hotspot di anomalie ricorrenti",
                description="Le segnalazioni di problemi e anomalie hanno un peso rilevante sul supporto nel periodo osservato.",
                metric_value=f"{round(bug_rate * 100)}%",
                action_hint="Parti dalla pagina o dal modulo più segnalato per isolare i problemi con maggiore impatto operativo.",
                related_key=page,
            )
        )

    if clusters:
        lead_cluster = clusters[0]
        insights.append(
            WikiSupportInsightRead(
                insight_type="top_cluster",
                severity="info" if lead_cluster.total_requests < 4 else "warning",
                title="Cluster dominante da monitorare",
                description=f"Il cluster più denso raccoglie {lead_cluster.total_requests} richieste e {lead_cluster.affected_users} utenti diversi.",
                metric_value=lead_cluster.total_requests,
                action_hint="Usalo come candidato principale per un fix strutturale o una comunicazione dedicata.",
                related_key=lead_cluster.title,
            )
        )

    return insights[:6]


def _count_rows(
    db: Session,
    *,
    start_date: date,
    column,
    limit: int = 6,
    include_null_label: str | None = None,
) -> list[WikiSupportAnalyticsCountRead]:
    if include_null_label:
        key_expr = func.coalesce(func.nullif(column, ""), include_null_label)
    else:
        key_expr = column
    rows = (
        db.query(key_expr.label("key"), func.count(WikiRequest.id).label("count"))
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .group_by(key_expr)
        .order_by(func.count(WikiRequest.id).desc(), key_expr.asc())
        .limit(limit)
        .all()
    )
    return [WikiSupportAnalyticsCountRead(key=str(row.key), count=int(row.count)) for row in rows if row.key]


@router.get("/support/analytics/summary", response_model=WikiSupportAnalyticsSummaryRead)
def get_wiki_support_analytics_summary(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiSupportAnalyticsSummaryRead:
    _require_wiki_admin(current_user)

    start_date = date.today() - timedelta(days=days - 1)
    window_requests = _support_window_requests(db, start_date=start_date)

    total_requests = (
        db.query(func.count(WikiRequest.id))
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .scalar()
        or 0
    )
    open_requests = (
        db.query(func.count(WikiRequest.id))
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .filter(WikiRequest.status.notin_(("resolved", "duplicate", "rejected")))
        .scalar()
        or 0
    )
    assigned_requests = (
        db.query(func.count(WikiRequest.id))
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .filter(WikiRequest.assigned_to.isnot(None))
        .filter(WikiRequest.assigned_to != "")
        .scalar()
        or 0
    )
    resolved_requests = (
        db.query(func.count(WikiRequest.id))
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .filter(WikiRequest.status == "resolved")
        .scalar()
        or 0
    )
    urgent_requests = (
        db.query(func.count(WikiRequest.id))
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .filter(WikiRequest.priority == "urgent")
        .scalar()
        or 0
    )
    high_severity_requests = (
        db.query(func.count(WikiRequest.id))
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .filter(WikiRequest.severity.in_(("high", "critical")))
        .scalar()
        or 0
    )

    def _count_type(request_type: str) -> int:
        return (
            db.query(func.count(WikiRequest.id))
            .filter(func.date(WikiRequest.created_at) >= start_date)
            .filter(WikiRequest.request_type == request_type)
            .scalar()
            or 0
        )

    duplicate_requests = (
        db.query(func.count(WikiRequest.id))
        .filter(func.date(WikiRequest.created_at) >= start_date)
        .filter(WikiRequest.status == "duplicate")
        .scalar()
        or 0
    )
    canonical_ids = {item.canonical_request_id for item in window_requests if item.canonical_request_id}
    canonical_ids.discard(None)
    canonical_cases = sum(1 for item in window_requests if item.id in canonical_ids)
    reopened_requests = _reopened_requests_count(db, window_requests)
    no_match_origin_requests, guardrail_origin_requests, docs_only_origin_requests = _origin_signal_counts(db, window_requests)

    return WikiSupportAnalyticsSummaryRead(
        total_requests=int(total_requests),
        open_requests=int(open_requests),
        assigned_requests=int(assigned_requests),
        resolved_requests=int(resolved_requests),
        urgent_requests=int(urgent_requests),
        high_severity_requests=int(high_severity_requests),
        feature_requests=int(_count_type("feature_request")),
        bug_reports=int(_count_type("bug_report")),
        access_issues=int(_count_type("access_issue")),
        data_issues=int(_count_type("data_issue")),
        help_requests=int(_count_type("help_request")),
        duplicate_requests=int(duplicate_requests),
        canonical_cases=int(canonical_cases),
        reopened_requests=int(reopened_requests),
        no_match_origin_requests=int(no_match_origin_requests),
        guardrail_origin_requests=int(guardrail_origin_requests),
        docs_only_origin_requests=int(docs_only_origin_requests),
        top_request_types=_count_rows(db, start_date=start_date, column=WikiRequest.request_type, include_null_label="n/d"),
        top_modules=_count_rows(db, start_date=start_date, column=WikiRequest.module_key, include_null_label="Modulo non dichiarato"),
        top_statuses=_count_rows(db, start_date=start_date, column=WikiRequest.status, include_null_label="n/d"),
        top_priorities=_count_rows(db, start_date=start_date, column=WikiRequest.priority, include_null_label="n/d"),
        top_severities=_count_rows(db, start_date=start_date, column=WikiRequest.severity, include_null_label="n/d"),
        top_pages=_count_rows(db, start_date=start_date, column=WikiRequest.page_path, include_null_label="Pagina non dichiarata"),
        top_assignees=_count_rows(db, start_date=start_date, column=WikiRequest.assigned_to, include_null_label="Non assegnata"),
        top_creators=_count_rows(db, start_date=start_date, column=WikiRequest.created_by, include_null_label="Autore non dichiarato"),
        top_impact_scopes=_count_rows(db, start_date=start_date, column=WikiRequest.impact_scope, include_null_label="Impatto non dichiarato"),
        top_source_channels=_count_rows(db, start_date=start_date, column=WikiRequest.source_channel, include_null_label="Canale non dichiarato"),
    )


@router.get("/support/analytics/series", response_model=WikiSupportAnalyticsSeriesResponse)
def get_wiki_support_analytics_series(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiSupportAnalyticsSeriesResponse:
    _require_wiki_admin(current_user)

    start_date = date.today() - timedelta(days=days - 1)
    metric_date = func.date(WikiRequest.created_at)
    rows = (
        db.query(
            metric_date.label("metric_date"),
            func.count(WikiRequest.id).label("created_count"),
            func.sum(case((WikiRequest.status == "resolved", 1), else_=0)).label("resolved_count"),
            func.sum(case((WikiRequest.status.notin_(("resolved", "duplicate", "rejected")), 1), else_=0)).label("open_count"),
            func.sum(case((WikiRequest.request_type == "feature_request", 1), else_=0)).label("feature_request_count"),
            func.sum(case((WikiRequest.request_type == "bug_report", 1), else_=0)).label("bug_report_count"),
            func.sum(case((WikiRequest.request_type == "help_request", 1), else_=0)).label("help_request_count"),
            func.sum(case((WikiRequest.request_type == "access_issue", 1), else_=0)).label("access_issue_count"),
            func.sum(case((WikiRequest.request_type == "data_issue", 1), else_=0)).label("data_issue_count"),
            func.sum(case((WikiRequest.priority == "urgent", 1), else_=0)).label("urgent_count"),
            func.sum(case((WikiRequest.severity.in_(("high", "critical")), 1), else_=0)).label("high_severity_count"),
        )
        .filter(metric_date >= start_date)
        .group_by(metric_date)
        .order_by(metric_date.asc())
        .all()
    )
    items: list[WikiSupportAnalyticsSeriesPointRead] = []
    for row in rows:
        metric_date_value = row.metric_date if isinstance(row.metric_date, date) else date.fromisoformat(str(row.metric_date))
        items.append(
            WikiSupportAnalyticsSeriesPointRead(
                metric_date=metric_date_value,
                period_label=metric_date_value.strftime("%d/%m"),
                created_count=int(row.created_count or 0),
                resolved_count=int(row.resolved_count or 0),
                open_count=int(row.open_count or 0),
                feature_request_count=int(row.feature_request_count or 0),
                bug_report_count=int(row.bug_report_count or 0),
                help_request_count=int(row.help_request_count or 0),
                access_issue_count=int(row.access_issue_count or 0),
                data_issue_count=int(row.data_issue_count or 0),
                urgent_count=int(row.urgent_count or 0),
                high_severity_count=int(row.high_severity_count or 0),
            )
        )
    return WikiSupportAnalyticsSeriesResponse(days=days, items=items)


@router.get("/support/analytics/clusters", response_model=WikiSupportClustersResponse)
def get_wiki_support_analytics_clusters(
    days: int = Query(30, ge=7, le=365),
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiSupportClustersResponse:
    _require_wiki_admin(current_user)
    start_date = date.today() - timedelta(days=days - 1)
    requests = _support_window_requests(db, start_date=start_date)
    items = _cluster_requests(requests, limit=limit)
    return WikiSupportClustersResponse(days=days, items=items)


@router.get("/support/analytics/insights", response_model=WikiSupportInsightsResponse)
def get_wiki_support_analytics_insights(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiSupportInsightsResponse:
    _require_wiki_admin(current_user)
    start_date = date.today() - timedelta(days=days - 1)
    requests = _support_window_requests(db, start_date=start_date)
    clusters = _cluster_requests(requests, limit=8)
    top_modules = _count_rows(db, start_date=start_date, column=WikiRequest.module_key, include_null_label="Modulo non dichiarato")
    top_pages = _count_rows(db, start_date=start_date, column=WikiRequest.page_path, include_null_label="Pagina non dichiarata")
    duplicate_requests = sum(1 for item in requests if item.status == "duplicate")
    reopened_requests = _reopened_requests_count(db, requests)
    no_match_origin_requests, guardrail_origin_requests, docs_only_origin_requests = _origin_signal_counts(db, requests)
    feature_requests = sum(1 for item in requests if item.request_type == "feature_request")
    bug_reports = sum(1 for item in requests if item.request_type == "bug_report")
    items = _build_support_insights(
        total_requests=len(requests),
        clusters=clusters,
        top_modules=top_modules,
        top_pages=top_pages,
        duplicate_requests=duplicate_requests,
        reopened_requests=reopened_requests,
        no_match_origin_requests=no_match_origin_requests,
        guardrail_origin_requests=guardrail_origin_requests,
        docs_only_origin_requests=docs_only_origin_requests,
        feature_requests=feature_requests,
        bug_reports=bug_reports,
    )
    return WikiSupportInsightsResponse(days=days, items=items)
