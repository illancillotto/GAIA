from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.wiki.models import WikiConversationMetricsBackfillJob
from app.modules.wiki.services.conversation_governance import update_wiki_conversation_governance_config
from app.modules.wiki.services.conversation_metrics import refresh_wiki_conversation_daily_metrics

ACTIVE_BACKFILL_STATUSES = {"pending", "running"}


@dataclass(slots=True, frozen=True)
class WikiConversationMetricsBackfillJobReadModel:
    id: uuid.UUID
    parent_job_id: uuid.UUID | None
    retry_count: int
    status: str
    requested_by: str
    start_date: str
    end_date: str
    data_complete_from: str | None
    progress_total_days: int
    progress_completed_days: int
    progress_percent: int
    progress_message: str | None
    error_detail: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    queue_position: int | None = None
    is_latest_attempt: bool = False


@dataclass(slots=True, frozen=True)
class WikiConversationMetricsBackfillJobChainReadModel:
    root_job_id: uuid.UUID
    chain_status: str
    retry_count_total: int
    has_active_retry: bool
    oldest_created_at: datetime
    latest_job: WikiConversationMetricsBackfillJobReadModel
    items: list[WikiConversationMetricsBackfillJobReadModel]


@dataclass(slots=True, frozen=True)
class WikiConversationMetricsBackfillJobChainSummaryReadModel:
    total_chains: int
    failed_chains: int
    chains_with_active_retry: int
    completed_chains: int
    avg_retries_per_chain: float
    oldest_active_chain_created_at: datetime | None


def _serialize_job(job: WikiConversationMetricsBackfillJob) -> WikiConversationMetricsBackfillJobReadModel:
    total_days = max(int(job.progress_total_days or 0), 0)
    completed_days = max(int(job.progress_completed_days or 0), 0)
    progress_percent = 0 if total_days <= 0 else min(int(round((completed_days / total_days) * 100)), 100)
    return WikiConversationMetricsBackfillJobReadModel(
        id=job.id,
        parent_job_id=job.parent_job_id,
        retry_count=int(job.retry_count or 0),
        status=job.status,
        requested_by=job.requested_by,
        start_date=job.start_date.isoformat(),
        end_date=job.end_date.isoformat(),
        data_complete_from=job.data_complete_from.isoformat() if job.data_complete_from else None,
        progress_total_days=total_days,
        progress_completed_days=completed_days,
        progress_percent=progress_percent,
        progress_message=job.progress_message,
        error_detail=job.error_detail,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


def _load_backfill_job_rows(db: Session) -> list[WikiConversationMetricsBackfillJob]:
    return db.scalars(
        select(WikiConversationMetricsBackfillJob).order_by(desc(WikiConversationMetricsBackfillJob.created_at))
    ).all()


def _serialize_jobs(rows: list[WikiConversationMetricsBackfillJob]) -> list[WikiConversationMetricsBackfillJobReadModel]:
    pending_rows = sorted(
        [row for row in rows if row.status == "pending"],
        key=lambda row: (row.created_at, str(row.id)),
    )
    pending_positions = {row.id: index + 1 for index, row in enumerate(pending_rows)}
    return [
        replace(
            _serialize_job(row),
            queue_position=pending_positions.get(row.id),
        )
        for row in rows
    ]


def _build_job_chains(
    items: list[WikiConversationMetricsBackfillJobReadModel],
) -> list[WikiConversationMetricsBackfillJobChainReadModel]:
    by_id = {item.id: item for item in items}

    def resolve_root_id(item: WikiConversationMetricsBackfillJobReadModel) -> uuid.UUID:
        current = item
        seen: set[uuid.UUID] = set()
        while current.parent_job_id and current.parent_job_id in by_id and current.parent_job_id not in seen:
            seen.add(current.id)
            current = by_id[current.parent_job_id]
        return current.id

    grouped: dict[uuid.UUID, list[WikiConversationMetricsBackfillJobReadModel]] = {}
    for item in items:
        root_id = resolve_root_id(item)
        grouped.setdefault(root_id, []).append(item)

    chains: list[WikiConversationMetricsBackfillJobChainReadModel] = []
    for root_id, chain_items in grouped.items():
        latest_job = max(chain_items, key=lambda item: (item.created_at, item.retry_count))
        sorted_items = sorted(
            (
                replace(item, is_latest_attempt=item.id == latest_job.id)
                for item in chain_items
            ),
            key=lambda item: (item.retry_count, item.created_at),
        )
        chains.append(
            WikiConversationMetricsBackfillJobChainReadModel(
                root_job_id=root_id,
                chain_status=latest_job.status,
                retry_count_total=max(len(sorted_items) - 1, 0),
                has_active_retry=any(item.status in ACTIVE_BACKFILL_STATUSES for item in sorted_items),
                oldest_created_at=min(item.created_at for item in sorted_items),
                latest_job=replace(latest_job, is_latest_attempt=True),
                items=sorted_items,
            )
        )
    chains.sort(key=lambda chain: chain.latest_job.created_at, reverse=True)
    return chains


def _filter_and_sort_job_chains(
    chains: list[WikiConversationMetricsBackfillJobChainReadModel],
    *,
    latest_status: str | None = None,
    requested_by: str | None = None,
    has_active_retry: bool | None = None,
    sort_by: str = "failed_first",
) -> list[WikiConversationMetricsBackfillJobChainReadModel]:
    filtered = chains
    if latest_status is not None:
        filtered = [chain for chain in filtered if chain.chain_status == latest_status]
    if requested_by is not None:
        filtered = [chain for chain in filtered if any(item.requested_by == requested_by for item in chain.items)]
    if has_active_retry is not None:
        filtered = [chain for chain in filtered if chain.has_active_retry == has_active_retry]

    if sort_by == "retry_count_desc":
        filtered.sort(key=lambda chain: (chain.retry_count_total, chain.latest_job.created_at), reverse=True)
    elif sort_by == "oldest_active_first":
        filtered.sort(
            key=lambda chain: (
                0 if chain.has_active_retry else 1,
                chain.oldest_created_at,
                -chain.latest_job.created_at.timestamp(),
            )
        )
    elif sort_by == "failed_first":
        filtered.sort(
            key=lambda chain: (
                0 if chain.chain_status == "failed" else 1,
                0 if chain.has_active_retry else 1,
                -chain.latest_job.created_at.timestamp(),
            )
        )
    else:
        filtered.sort(key=lambda chain: chain.latest_job.created_at, reverse=True)
    return filtered


def _list_filtered_job_chains(
    db: Session,
    *,
    latest_status: str | None = None,
    requested_by: str | None = None,
    has_active_retry: bool | None = None,
    sort_by: str = "failed_first",
) -> list[WikiConversationMetricsBackfillJobChainReadModel]:
    items = _serialize_jobs(_load_backfill_job_rows(db))
    chains = _build_job_chains(items)
    return _filter_and_sort_job_chains(
        chains,
        latest_status=latest_status,
        requested_by=requested_by,
        has_active_retry=has_active_retry,
        sort_by=sort_by,
    )


def _mark_job_failed(db: Session, job: WikiConversationMetricsBackfillJob, detail: str) -> None:
    job.status = "failed"
    job.finished_at = datetime.now(UTC)
    job.error_detail = detail
    job.progress_message = "Backfill fallito."
    db.add(job)


def _fail_inconsistent_active_jobs(db: Session) -> None:
    active_jobs = db.scalars(
        select(WikiConversationMetricsBackfillJob)
        .where(WikiConversationMetricsBackfillJob.status.in_(ACTIVE_BACKFILL_STATUSES))
        .order_by(WikiConversationMetricsBackfillJob.created_at.asc())
    ).all()
    if len(active_jobs) <= 1:
        return
    keeper = active_jobs[0]
    for job in active_jobs[1:]:
        _mark_job_failed(
            db,
            job,
            f"Job attivo inconsistente: esiste già un altro job attivo ({keeper.id}).",
        )
    db.commit()


def _validate_job_chain_state(db: Session, *, job: WikiConversationMetricsBackfillJob) -> None:
    if job.start_date > job.end_date:
        raise ValueError("Intervallo date non valido.")

    visited: set[uuid.UUID] = {job.id}
    parent_id = job.parent_job_id
    while parent_id is not None:
        if parent_id in visited:
            raise ValueError("Loop rilevato nella chain di retry.")
        visited.add(parent_id)
        parent_job = db.get(WikiConversationMetricsBackfillJob, parent_id)
        if parent_job is None:
            raise ValueError("Parent job non trovato.")
        parent_id = parent_job.parent_job_id


def _resolve_root_job_id(db: Session, *, job: WikiConversationMetricsBackfillJob) -> uuid.UUID:
    current = job
    seen: set[uuid.UUID] = {current.id}
    while current.parent_job_id is not None:
        parent_job = db.get(WikiConversationMetricsBackfillJob, current.parent_job_id)
        if parent_job is None or parent_job.id in seen:
            break
        seen.add(parent_job.id)
        current = parent_job
    return current.id


def get_active_wiki_conversation_metrics_backfill_job(db: Session) -> WikiConversationMetricsBackfillJob | None:
    _fail_inconsistent_active_jobs(db)
    return db.scalar(
        select(WikiConversationMetricsBackfillJob)
        .where(WikiConversationMetricsBackfillJob.status.in_(ACTIVE_BACKFILL_STATUSES))
        .order_by(desc(WikiConversationMetricsBackfillJob.created_at))
        .limit(1)
    )


def get_next_wiki_conversation_metrics_backfill_job(db: Session) -> WikiConversationMetricsBackfillJob | None:
    _fail_inconsistent_active_jobs(db)
    running_job = db.scalar(
        select(WikiConversationMetricsBackfillJob)
        .where(WikiConversationMetricsBackfillJob.status == "running")
        .order_by(desc(WikiConversationMetricsBackfillJob.started_at), desc(WikiConversationMetricsBackfillJob.created_at))
        .limit(1)
    )
    if running_job is not None:
        return running_job
    return db.scalar(
        select(WikiConversationMetricsBackfillJob)
        .where(WikiConversationMetricsBackfillJob.status == "pending")
        .order_by(WikiConversationMetricsBackfillJob.created_at.asc())
        .limit(1)
    )


def get_latest_wiki_conversation_metrics_backfill_job(
    db: Session,
) -> WikiConversationMetricsBackfillJobReadModel | None:
    job = db.scalar(
        select(WikiConversationMetricsBackfillJob)
        .order_by(desc(WikiConversationMetricsBackfillJob.created_at))
        .limit(1)
    )
    if job is None:
        return None
    return _serialize_job(job)


def list_wiki_conversation_metrics_backfill_jobs(
    db: Session,
    *,
    limit: int = 10,
) -> list[WikiConversationMetricsBackfillJobReadModel]:
    return _serialize_jobs(_load_backfill_job_rows(db))[:limit]


def list_wiki_conversation_metrics_backfill_job_chains(
    db: Session,
    *,
    limit: int = 10,
    latest_status: str | None = None,
    requested_by: str | None = None,
    has_active_retry: bool | None = None,
    sort_by: str = "latest_created_desc",
) -> list[WikiConversationMetricsBackfillJobChainReadModel]:
    return _list_filtered_job_chains(
        db,
        latest_status=latest_status,
        requested_by=requested_by,
        has_active_retry=has_active_retry,
        sort_by=sort_by,
    )[:limit]


def summarize_wiki_conversation_metrics_backfill_job_chains(
    db: Session,
    *,
    latest_status: str | None = None,
    requested_by: str | None = None,
    has_active_retry: bool | None = None,
    sort_by: str = "failed_first",
) -> WikiConversationMetricsBackfillJobChainSummaryReadModel:
    chains = _list_filtered_job_chains(
        db,
        latest_status=latest_status,
        requested_by=requested_by,
        has_active_retry=has_active_retry,
        sort_by=sort_by,
    )
    total_chains = len(chains)
    active_chains = [chain for chain in chains if chain.has_active_retry]
    avg_retries = round(sum(chain.retry_count_total for chain in chains) / total_chains, 2) if chains else 0
    return WikiConversationMetricsBackfillJobChainSummaryReadModel(
        total_chains=total_chains,
        failed_chains=sum(1 for chain in chains if chain.chain_status == "failed"),
        chains_with_active_retry=len(active_chains),
        completed_chains=sum(1 for chain in chains if chain.chain_status == "completed"),
        avg_retries_per_chain=avg_retries,
        oldest_active_chain_created_at=min((chain.oldest_created_at for chain in active_chains), default=None),
    )


def get_wiki_conversation_metrics_backfill_job_chain(
    db: Session,
    *,
    root_job_id: uuid.UUID,
) -> WikiConversationMetricsBackfillJobChainReadModel | None:
    chains = _build_job_chains(_serialize_jobs(_load_backfill_job_rows(db)))
    for chain in chains:
        if chain.root_job_id == root_job_id:
            return chain
    return None


def get_wiki_conversation_metrics_backfill_job(
    db: Session,
    *,
    job_id: uuid.UUID,
) -> WikiConversationMetricsBackfillJobReadModel | None:
    job = db.get(WikiConversationMetricsBackfillJob, job_id)
    if job is None:
        return None
    return _serialize_job(job)


def create_wiki_conversation_metrics_backfill_job(
    db: Session,
    *,
    current_user: ApplicationUser,
    start_date: date,
    end_date: date,
    data_complete_from: date | None,
    parent_job_id: uuid.UUID | None = None,
    retry_count: int = 0,
) -> WikiConversationMetricsBackfillJobReadModel:
    active_job = get_active_wiki_conversation_metrics_backfill_job(db)
    if active_job is not None:
        raise ValueError("Esiste già un backfill conversazioni in esecuzione.")
    total_days = ((end_date - start_date).days + 1)
    job = WikiConversationMetricsBackfillJob(
        parent_job_id=parent_job_id,
        retry_count=retry_count,
        requested_by=current_user.username,
        status="pending",
        start_date=start_date,
        end_date=end_date,
        data_complete_from=data_complete_from,
        progress_total_days=max(total_days, 0),
        progress_completed_days=0,
        progress_message="Backfill accodato.",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _serialize_job(job)


def retry_wiki_conversation_metrics_backfill_job(
    db: Session,
    *,
    current_user: ApplicationUser,
    job_id: uuid.UUID,
) -> WikiConversationMetricsBackfillJobReadModel | None:
    source_job = db.get(WikiConversationMetricsBackfillJob, job_id)
    if source_job is None:
        return None
    chain = get_wiki_conversation_metrics_backfill_job_chain(
        db,
        root_job_id=_resolve_root_job_id(db, job=source_job),
    )
    if source_job.status != "failed":
        raise ValueError("Solo i job falliti possono essere riaccodati.")
    if chain is None or chain.latest_job.id != source_job.id:
        raise ValueError("È possibile riaccodare solo il tentativo fallito più recente della chain.")
    return create_wiki_conversation_metrics_backfill_job(
        db,
        current_user=current_user,
        start_date=source_job.start_date,
        end_date=source_job.end_date,
        data_complete_from=source_job.data_complete_from,
        parent_job_id=source_job.id,
        retry_count=int(source_job.retry_count or 0) + 1,
    )


def run_wiki_conversation_metrics_backfill_job(db: Session, *, job_id: uuid.UUID) -> None:
    try:
        job = db.get(WikiConversationMetricsBackfillJob, job_id)
        if job is None or job.status not in ACTIVE_BACKFILL_STATUSES:
            return
        _validate_job_chain_state(db, job=job)
        if job.status == "pending":
            job.status = "running"
        if job.started_at is None:
            job.started_at = datetime.now(UTC)
        job.progress_message = "Preparazione backfill metriche conversazioni."
        job.error_detail = None
        db.add(job)
        db.commit()

        total_days = max((job.end_date - job.start_date).days + 1, 0)
        for offset in range(total_days):
            current_day = job.start_date + timedelta(days=offset)
            job = db.get(WikiConversationMetricsBackfillJob, job_id)
            if job is None:
                return
            job.progress_message = f"Ricalcolo snapshot del {current_day.isoformat()}."
            db.add(job)
            db.commit()

            refresh_wiki_conversation_daily_metrics(db, start_date=current_day, end_date=current_day)

            job = db.get(WikiConversationMetricsBackfillJob, job_id)
            if job is None:
                return
            job.progress_completed_days = offset + 1
            job.progress_message = f"Completati {offset + 1}/{total_days} giorni."
            db.add(job)
            db.commit()

        job = db.get(WikiConversationMetricsBackfillJob, job_id)
        if job is None:
            return
        update_wiki_conversation_governance_config(
            db,
            current_user=None,
            data_complete_from=job.data_complete_from or job.start_date,
            last_backfill_at=datetime.now(UTC),
            updated_by=job.requested_by,
        )
        job.status = "completed"
        job.finished_at = datetime.now(UTC)
        job.progress_completed_days = job.progress_total_days
        job.progress_message = "Backfill completato."
        db.add(job)
        db.commit()
    except Exception as exc:
        db.rollback()
        failed_job = db.get(WikiConversationMetricsBackfillJob, job_id)
        if failed_job is not None:
            _mark_job_failed(db, failed_job, str(exc))
            db.commit()
        raise


def process_next_wiki_conversation_metrics_backfill_job(db: Session) -> WikiConversationMetricsBackfillJobReadModel | None:
    job = get_next_wiki_conversation_metrics_backfill_job(db)
    if job is None:
        return None
    run_wiki_conversation_metrics_backfill_job(db, job_id=job.id)
    refreshed = db.get(WikiConversationMetricsBackfillJob, job.id)
    if refreshed is None:
        return None
    return _serialize_job(refreshed)


def prune_wiki_conversation_metrics_backfill_jobs(db: Session, *, retention_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=max(retention_days, 1))
    result = db.execute(
        delete(WikiConversationMetricsBackfillJob).where(
            WikiConversationMetricsBackfillJob.status.in_(("completed", "failed")),
            func.coalesce(WikiConversationMetricsBackfillJob.finished_at, WikiConversationMetricsBackfillJob.created_at) < cutoff,
        ),
        execution_options={"synchronize_session": False},
    )
    db.commit()
    return int(result.rowcount or 0)


def clear_wiki_conversation_metrics_backfill_job_history(db: Session) -> int:
    result = db.execute(
        delete(WikiConversationMetricsBackfillJob).where(
            WikiConversationMetricsBackfillJob.status.in_(("completed", "failed")),
        ),
        execution_options={"synchronize_session": False},
    )
    db.commit()
    return int(result.rowcount or 0)
