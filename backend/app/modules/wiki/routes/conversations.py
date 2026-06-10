from __future__ import annotations

import uuid
from urllib.parse import quote
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import (
    WikiConversationContextLinkRead,
    WikiConversationFlagUpdate,
    WikiConversationGovernanceConfigRead,
    WikiConversationGovernanceConfigUpdate,
    WikiConversationMetricsBackfillRequest,
    WikiConversationMetricsBackfillJobRead,
    WikiConversationMetricsBackfillJobListResponse,
    WikiConversationMetricsBackfillJobChainRead,
    WikiConversationMetricsBackfillJobChainDetailRead,
    WikiConversationMetricsBackfillJobChainListResponse,
    WikiConversationMetricsBackfillJobChainSummaryRead,
    WikiConversationMetricsBackfillJobPruneResponse,
    WikiConversationMetricsSeriesPointRead,
    WikiConversationMetricsSeriesResponse,
    WikiConversationMetricsSummaryRead,
    WikiConversationRead,
    WikiConversationSummaryMetricsRead,
    WikiConversationSummaryRead,
    WikiConversationUpdate,
)
from app.modules.wiki.services.accessi_read_models import get_nas_user_read_model, get_share_read_model
from app.modules.wiki.services.conversation_governance import (
    get_or_create_wiki_conversation_governance_config,
    update_wiki_conversation_governance_config,
)
from app.modules.wiki.services.conversation_backfill_jobs import (
    clear_wiki_conversation_metrics_backfill_job_history,
    create_wiki_conversation_metrics_backfill_job,
    get_latest_wiki_conversation_metrics_backfill_job,
    get_wiki_conversation_metrics_backfill_job_chain,
    get_wiki_conversation_metrics_backfill_job,
    list_wiki_conversation_metrics_backfill_job_chains,
    list_wiki_conversation_metrics_backfill_jobs,
    retry_wiki_conversation_metrics_backfill_job,
    summarize_wiki_conversation_metrics_backfill_job_chains,
)
from app.modules.wiki.services.conversation_metrics import (
    get_wiki_conversation_metrics_series,
    get_wiki_conversation_metrics_summary,
    refresh_wiki_conversation_daily_metrics,
    refresh_recent_wiki_conversation_daily_metrics,
)
from app.modules.wiki.services.conversations import (
    flag_wiki_conversation,
    get_wiki_conversation,
    list_wiki_conversations,
    summarize_wiki_conversations,
    update_wiki_conversation,
)
from app.modules.wiki.services.ruolo_utenze_read_models import get_ruolo_subject_by_reference_read_model

router = APIRouter(tags=["Wiki"])


def _require_wiki_admin(current_user: ApplicationUser) -> None:
    if current_user.role not in {"admin", "super_admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso riservato agli amministratori.")


def _serialize_governance_config_read(config: object) -> WikiConversationGovernanceConfigRead:
    return WikiConversationGovernanceConfigRead(
        fallback_heavy_threshold=config.fallback_heavy_threshold,
        no_match_repeated_threshold=config.no_match_repeated_threshold,
        high_latency_ms_threshold=config.high_latency_ms_threshold,
        data_complete_from=config.data_complete_from.isoformat() if config.data_complete_from else None,
        last_backfill_at=config.last_backfill_at,
        updated_by=config.updated_by,
        updated_at=config.updated_at,
    )


def _parse_backfill_request_dates(payload: WikiConversationMetricsBackfillRequest) -> tuple[date, date, date]:
    try:
        start_date = date.fromisoformat(payload.start_date)
        end_date = date.fromisoformat(payload.end_date)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Date backfill non valide.") from exc
    if start_date > end_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_date deve precedere end_date.")
    try:
        complete_from = date.fromisoformat(payload.data_complete_from) if payload.data_complete_from else start_date
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="data_complete_from non valida.") from exc
    return start_date, end_date, complete_from


def _serialize_backfill_job_read(job: object) -> WikiConversationMetricsBackfillJobRead:
    return WikiConversationMetricsBackfillJobRead(
        id=job.id,
        parent_job_id=job.parent_job_id,
        retry_count=job.retry_count,
        status=job.status,
        requested_by=job.requested_by,
        start_date=job.start_date,
        end_date=job.end_date,
        data_complete_from=job.data_complete_from,
        progress_total_days=job.progress_total_days,
        progress_completed_days=job.progress_completed_days,
        progress_percent=job.progress_percent,
        progress_message=job.progress_message,
        error_detail=job.error_detail,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        queue_position=getattr(job, "queue_position", None),
        is_latest_attempt=getattr(job, "is_latest_attempt", False),
    )


def _serialize_backfill_job_chain_read(job: object) -> WikiConversationMetricsBackfillJobChainRead:
    return WikiConversationMetricsBackfillJobChainRead(
        root_job_id=job.root_job_id,
        chain_status=job.chain_status,
        retry_count_total=job.retry_count_total,
        has_active_retry=job.has_active_retry,
        oldest_created_at=job.oldest_created_at,
        latest_job=_serialize_backfill_job_read(job.latest_job),
        items=[_serialize_backfill_job_read(item) for item in job.items],
    )


@router.get("/conversations/context-link", response_model=WikiConversationContextLinkRead)
def resolve_conversation_context_link(
    entity_key: str | None = Query(None),
    module_key: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiConversationContextLinkRead:
    if entity_key:
        if entity_key.startswith("accessi.nas-users."):
            username = entity_key.replace("accessi.nas-users.", "")
            if username != "lookup":
                payload = get_nas_user_read_model(db, current_user, username)
                if payload is not None:
                    return WikiConversationContextLinkRead(
                        href=f"/nas-control/users/{payload['id']}",
                        resolved=True,
                        resolution_kind="nas_user",
                    )
                return WikiConversationContextLinkRead(
                    href=f"/nas-control/users?q={quote(username)}",
                    resolved=False,
                    resolution_kind="nas_user_search",
                )
        if entity_key.startswith("accessi.shares.") or entity_key.startswith("accessi.share."):
            share_name = entity_key.split(".", 2)[2]
            if share_name != "lookup":
                payload = get_share_read_model(db, current_user, share_name)
                if payload is not None:
                    return WikiConversationContextLinkRead(
                        href=f"/nas-control/shares/{payload['id']}",
                        resolved=True,
                        resolution_kind="share",
                    )
                return WikiConversationContextLinkRead(
                    href=f"/nas-control/shares?q={quote(share_name)}",
                    resolved=False,
                    resolution_kind="share_search",
                )
        if entity_key.startswith("ruolo.subjects."):
            subject_ref = entity_key.replace("ruolo.subjects.", "")
            if subject_ref != "lookup":
                payload = get_ruolo_subject_by_reference_read_model(db, current_user, subject_ref)
                if payload is not None:
                    latest_items = payload.get("latest_items") if isinstance(payload, dict) else None
                    if isinstance(latest_items, list) and latest_items:
                        first_item = latest_items[0]
                        if isinstance(first_item, dict) and first_item.get("id"):
                            return WikiConversationContextLinkRead(
                                href=f"/ruolo/avvisi/{first_item['id']}",
                                resolved=True,
                                resolution_kind="ruolo_avviso",
                            )
                    if payload.get("subject_id"):
                        return WikiConversationContextLinkRead(
                            href=f"/ruolo/avvisi?subject_id={quote(str(payload['subject_id']))}",
                            resolved=True,
                            resolution_kind="ruolo_subject",
                        )
                return WikiConversationContextLinkRead(
                    href=f"/ruolo/avvisi?q={quote(subject_ref)}",
                    resolved=False,
                    resolution_kind="ruolo_search",
                )
    module_map = {
        "accessi": "/nas-control",
        "catasto": "/catasto",
        "operazioni": "/operazioni",
        "riordino": "/riordino",
        "ruolo": "/ruolo",
        "utenze": "/utenze",
    }
    href = module_map.get(module_key or "")
    if href:
        return WikiConversationContextLinkRead(href=href, resolved=False, resolution_kind="module")
    return WikiConversationContextLinkRead()


@router.get("/conversations/summary", response_model=WikiConversationSummaryMetricsRead)
def get_conversations_summary(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiConversationSummaryMetricsRead:
    return summarize_wiki_conversations(db, current_user=current_user)


@router.get("/conversations/governance-config", response_model=WikiConversationGovernanceConfigRead)
def get_conversations_governance_config(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiConversationGovernanceConfigRead:
    _require_wiki_admin(current_user)
    config = get_or_create_wiki_conversation_governance_config(db)
    return _serialize_governance_config_read(config)


@router.patch("/conversations/governance-config", response_model=WikiConversationGovernanceConfigRead)
def patch_conversations_governance_config(
    payload: WikiConversationGovernanceConfigUpdate,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiConversationGovernanceConfigRead:
    _require_wiki_admin(current_user)
    config = update_wiki_conversation_governance_config(
        db,
        current_user=current_user,
        fallback_heavy_threshold=payload.fallback_heavy_threshold,
        no_match_repeated_threshold=payload.no_match_repeated_threshold,
        high_latency_ms_threshold=payload.high_latency_ms_threshold,
    )
    refresh_recent_wiki_conversation_daily_metrics(db)
    return _serialize_governance_config_read(config)


@router.post("/conversations/metrics/backfill", response_model=WikiConversationGovernanceConfigRead)
def backfill_conversation_metrics(
    payload: WikiConversationMetricsBackfillRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiConversationGovernanceConfigRead:
    _require_wiki_admin(current_user)
    start_date, end_date, complete_from = _parse_backfill_request_dates(payload)
    refresh_wiki_conversation_daily_metrics(db, start_date=start_date, end_date=end_date)
    config = update_wiki_conversation_governance_config(
        db,
        current_user=current_user,
        data_complete_from=complete_from,
        last_backfill_at=datetime.now(UTC),
    )
    return _serialize_governance_config_read(config)


@router.post(
    "/conversations/metrics/backfill-jobs",
    response_model=WikiConversationMetricsBackfillJobRead,
    status_code=status.HTTP_201_CREATED,
)
def enqueue_conversation_metrics_backfill(
    payload: WikiConversationMetricsBackfillRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiConversationMetricsBackfillJobRead:
    _require_wiki_admin(current_user)
    start_date, end_date, complete_from = _parse_backfill_request_dates(payload)
    try:
        job = create_wiki_conversation_metrics_backfill_job(
            db,
            current_user=current_user,
            start_date=start_date,
            end_date=end_date,
            data_complete_from=complete_from,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _serialize_backfill_job_read(job)


@router.get(
    "/conversations/metrics/backfill-jobs/latest",
    response_model=WikiConversationMetricsBackfillJobRead | None,
)
def get_latest_conversation_metrics_backfill(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiConversationMetricsBackfillJobRead | None:
    _require_wiki_admin(current_user)
    job = get_latest_wiki_conversation_metrics_backfill_job(db)
    if job is None:
        return None
    return _serialize_backfill_job_read(job)


@router.get(
    "/conversations/metrics/backfill-jobs",
    response_model=WikiConversationMetricsBackfillJobListResponse,
)
def list_conversation_metrics_backfill_jobs(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50),
) -> WikiConversationMetricsBackfillJobListResponse:
    _require_wiki_admin(current_user)
    items = list_wiki_conversation_metrics_backfill_jobs(db, limit=limit)
    return WikiConversationMetricsBackfillJobListResponse(
        items=[_serialize_backfill_job_read(item) for item in items]
    )


@router.get(
    "/conversations/metrics/backfill-job-chains",
    response_model=WikiConversationMetricsBackfillJobChainListResponse,
)
def list_conversation_metrics_backfill_job_chains(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50),
    latest_status: str | None = Query(None, pattern="^(pending|running|completed|failed)$"),
    requested_by: str | None = Query(None),
    has_active_retry: bool | None = Query(None),
    sort_by: str = Query(
        "failed_first",
        pattern="^(latest_created_desc|retry_count_desc|failed_first|oldest_active_first)$",
    ),
) -> WikiConversationMetricsBackfillJobChainListResponse:
    _require_wiki_admin(current_user)
    items = list_wiki_conversation_metrics_backfill_job_chains(
        db,
        limit=limit,
        latest_status=latest_status,
        requested_by=requested_by,
        has_active_retry=has_active_retry,
        sort_by=sort_by,
    )
    return WikiConversationMetricsBackfillJobChainListResponse(
        items=[_serialize_backfill_job_chain_read(item) for item in items]
    )


@router.get(
    "/conversations/metrics/backfill-job-chains/summary",
    response_model=WikiConversationMetricsBackfillJobChainSummaryRead,
)
def summarize_conversation_metrics_backfill_job_chains(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
    latest_status: str | None = Query(None, pattern="^(pending|running|completed|failed)$"),
    requested_by: str | None = Query(None),
    has_active_retry: bool | None = Query(None),
    sort_by: str = Query(
        "failed_first",
        pattern="^(latest_created_desc|retry_count_desc|failed_first|oldest_active_first)$",
    ),
) -> WikiConversationMetricsBackfillJobChainSummaryRead:
    _require_wiki_admin(current_user)
    summary = summarize_wiki_conversation_metrics_backfill_job_chains(
        db,
        latest_status=latest_status,
        requested_by=requested_by,
        has_active_retry=has_active_retry,
        sort_by=sort_by,
    )
    return WikiConversationMetricsBackfillJobChainSummaryRead(
        total_chains=summary.total_chains,
        failed_chains=summary.failed_chains,
        chains_with_active_retry=summary.chains_with_active_retry,
        completed_chains=summary.completed_chains,
        avg_retries_per_chain=summary.avg_retries_per_chain,
        oldest_active_chain_created_at=summary.oldest_active_chain_created_at,
    )


@router.get(
    "/conversations/metrics/backfill-job-chains/{root_job_id}",
    response_model=WikiConversationMetricsBackfillJobChainDetailRead,
)
def get_conversation_metrics_backfill_job_chain(
    root_job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiConversationMetricsBackfillJobChainDetailRead:
    _require_wiki_admin(current_user)
    chain = get_wiki_conversation_metrics_backfill_job_chain(db, root_job_id=root_job_id)
    if chain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chain backfill non trovata.")
    return WikiConversationMetricsBackfillJobChainDetailRead(
        root_job_id=chain.root_job_id,
        chain_status=chain.chain_status,
        retry_count_total=chain.retry_count_total,
        has_active_retry=chain.has_active_retry,
        oldest_created_at=chain.oldest_created_at,
        latest_job=_serialize_backfill_job_read(chain.latest_job),
        items=[_serialize_backfill_job_read(item) for item in chain.items],
    )


@router.get(
    "/conversations/metrics/backfill-jobs/{job_id}",
    response_model=WikiConversationMetricsBackfillJobRead,
)
def get_conversation_metrics_backfill_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiConversationMetricsBackfillJobRead:
    if current_user.role not in {"admin", "super_admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso riservato agli amministratori.")
    job = get_wiki_conversation_metrics_backfill_job(db, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job backfill non trovato.")
    return _serialize_backfill_job_read(job)


@router.post(
    "/conversations/metrics/backfill-jobs/{job_id}/retry",
    response_model=WikiConversationMetricsBackfillJobRead,
    status_code=status.HTTP_201_CREATED,
)
def retry_conversation_metrics_backfill_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiConversationMetricsBackfillJobRead:
    _require_wiki_admin(current_user)
    try:
        job = retry_wiki_conversation_metrics_backfill_job(db, current_user=current_user, job_id=job_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job backfill non trovato.")
    return _serialize_backfill_job_read(job)


@router.delete(
    "/conversations/metrics/backfill-jobs",
    response_model=WikiConversationMetricsBackfillJobPruneResponse,
)
def clear_conversation_metrics_backfill_job_history(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiConversationMetricsBackfillJobPruneResponse:
    _require_wiki_admin(current_user)
    deleted_count = clear_wiki_conversation_metrics_backfill_job_history(db)
    return WikiConversationMetricsBackfillJobPruneResponse(deleted_count=deleted_count)


@router.get("/conversations/metrics/summary", response_model=WikiConversationMetricsSummaryRead)
def get_conversations_metrics_summary(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
    days: int = Query(30, ge=7, le=180),
) -> WikiConversationMetricsSummaryRead:
    _require_wiki_admin(current_user)
    summary = get_wiki_conversation_metrics_summary(db, days=days)
    return WikiConversationMetricsSummaryRead(
        total_threads=summary.total_threads,
        created_count=summary.created_count,
        closed_count=summary.closed_count,
        open_count=summary.open_count,
        in_review_count=summary.in_review_count,
        waiting_user_count=summary.waiting_user_count,
        resolved_count=summary.resolved_count,
        high_priority_count=summary.high_priority_count,
        needs_review_count=summary.needs_review_count,
        review_entered_count=summary.review_entered_count,
        reassigned_count=summary.reassigned_count,
        reopened_count=summary.reopened_count,
        avg_time_to_review_hours=summary.avg_time_to_review_hours,
        avg_time_to_resolve_hours=summary.avg_time_to_resolve_hours,
        avg_open_to_review_hours=summary.avg_open_to_review_hours,
        avg_review_to_resolve_hours=summary.avg_review_to_resolve_hours,
        avg_waiting_user_hours=summary.avg_waiting_user_hours,
        data_complete_from=summary.data_complete_from,
        last_backfill_at=summary.last_backfill_at,
        top_statuses=[{"key": item.key, "count": item.count} for item in summary.top_statuses],
        top_priorities=[{"key": item.key, "count": item.count} for item in summary.top_priorities],
        top_owners=[{"key": item.key, "count": item.count} for item in summary.top_owners],
        top_review_reasons=[{"key": item.key, "count": item.count} for item in summary.top_review_reasons],
        top_event_types=[{"key": item.key, "count": item.count} for item in summary.top_event_types],
    )


@router.get("/conversations/metrics/series", response_model=WikiConversationMetricsSeriesResponse)
def get_conversations_metrics_series(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
    dimension_type: str = Query("global", pattern="^(global|status|priority|assigned_to|review_reason)$"),
    dimension_key: str | None = Query(None),
    days: int = Query(30, ge=7, le=180),
    granularity: str = Query("day", pattern="^(day|week|month)$"),
) -> WikiConversationMetricsSeriesResponse:
    _require_wiki_admin(current_user)
    items = get_wiki_conversation_metrics_series(
        db,
        dimension_type=dimension_type,
        dimension_key=dimension_key,
        days=days,
        granularity=granularity,
    )
    return WikiConversationMetricsSeriesResponse(
        dimension_type=dimension_type,
        dimension_key=dimension_key,
        days=days,
        granularity=granularity,
        items=[
            WikiConversationMetricsSeriesPointRead(
                metric_date=item.metric_date,
                period_label=item.period_label,
                created_count=item.created_count,
                closed_count=item.closed_count,
                open_count=item.open_count,
                in_review_count=item.in_review_count,
                waiting_user_count=item.waiting_user_count,
                resolved_count=item.resolved_count,
                high_priority_count=item.high_priority_count,
                needs_review_count=item.needs_review_count,
                denied_threads_count=item.denied_threads_count,
                fallback_threads_count=item.fallback_threads_count,
                no_match_threads_count=item.no_match_threads_count,
                review_entered_count=item.review_entered_count,
                reassigned_count=item.reassigned_count,
                reopened_count=item.reopened_count,
                avg_time_to_review_hours=item.avg_time_to_review_hours,
                avg_time_to_resolve_hours=item.avg_time_to_resolve_hours,
                avg_open_to_review_hours=item.avg_open_to_review_hours,
                avg_review_to_resolve_hours=item.avg_review_to_resolve_hours,
                avg_waiting_user_hours=item.avg_waiting_user_hours,
            )
            for item in items
        ],
    )


@router.get("/conversations", response_model=list[WikiConversationSummaryRead])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
    limit: int = Query(30, ge=1, le=100),
    search: str | None = Query(None),
    created_by: str | None = Query(None),
    context_article: str | None = Query(None),
    status: str | None = Query(None, pattern="^(open|in_review|waiting_user|resolved)$"),
    assigned_to: str | None = Query(None),
    priority: str | None = Query(None, pattern="^(low|medium|high)$"),
    needs_review: bool | None = Query(None),
    review_reason: str | None = Query(None, pattern="^(denied_present|fallback_heavy|no_match_repeated|high_latency|manual_flag)$"),
) -> list[WikiConversationSummaryRead]:
    return list_wiki_conversations(
        db,
        current_user=current_user,
        limit=limit,
        search=search,
        created_by=created_by,
        context_article=context_article,
        status=status,
        assigned_to=assigned_to,
        priority=priority,
        needs_review=needs_review,
        review_reason=review_reason,
    )


@router.get("/conversations/{conversation_id}", response_model=WikiConversationRead)
def get_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiConversationRead:
    conversation = get_wiki_conversation(db, conversation_id=conversation_id, current_user=current_user)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversazione Wiki non trovata.")
    return conversation


@router.patch("/conversations/{conversation_id}", response_model=WikiConversationRead)
def update_conversation_status(
    conversation_id: uuid.UUID,
    payload: WikiConversationUpdate,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiConversationRead:
    try:
        conversation = update_wiki_conversation(
            db,
            conversation_id=conversation_id,
            current_user=current_user,
            payload=payload,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversazione Wiki non trovata.")
    return conversation


@router.post("/conversations/{conversation_id}/flag", response_model=WikiConversationRead)
def flag_conversation(
    conversation_id: uuid.UUID,
    payload: WikiConversationFlagUpdate,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user),
) -> WikiConversationRead:
    try:
        conversation = flag_wiki_conversation(
            db,
            conversation_id=conversation_id,
            current_user=current_user,
            payload=payload,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversazione Wiki non trovata.")
    return conversation
