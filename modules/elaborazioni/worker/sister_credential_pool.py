from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

from app.models.catasto import CatastoBatch, CatastoBatchStatus, CatastoCredential
from app.services.elaborazioni_credential_schedule import (
    credential_is_available,
    next_credential_availability,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

_REJECTED_CREDENTIAL_MARKERS = (
    "credenziali sister rifiutate",
    "credenziali errate",
    "autenticazione fallita",
)
logger = logging.getLogger(__name__)
_SCHEDULED_BATCH_RESUME_AT: dict[UUID, datetime] = {}


class RejectedCredentialQuarantined(Exception):
    pass


class CredentialRejectionRepository(Protocol):
    def fail_unavailable_pinned_requests(self, batch_id: UUID, active_credential_ids: set[UUID]) -> int: ...

    def reset_for_retry(
        self,
        request_id: UUID,
        operation: str,
        retry_at: datetime | None = None,
        error_code: str | None = None,
        execution_token: UUID | None = None,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class CredentialRejectionContext:
    pool: ActiveSisterCredentialPool
    credential: CatastoCredential
    batch_id: UUID
    request_id: UUID
    execution_token: UUID | None
    repository: CredentialRejectionRepository
    set_batch_operation: Callable[[UUID, str], None]


@dataclass(slots=True)
class ActiveSisterCredentialPool:
    credentials: tuple[CatastoCredential, ...]
    active_credential_count: int | None = None
    next_availability: datetime | None = None
    rejected_ids: set[UUID] = field(default_factory=set)

    @property
    def available_ids(self) -> set[UUID]:
        return {credential.id for credential in self.credentials} - self.rejected_ids

    def reject(self, credential_id: UUID) -> int:
        self.rejected_ids.add(credential_id)
        return len(self.available_ids)

    def merge(self, refreshed: ActiveSisterCredentialPool) -> tuple[CatastoCredential, ...]:
        known_ids = {credential.id for credential in self.credentials}
        added = tuple(
            credential
            for credential in refreshed.credentials
            if credential.id not in known_ids and credential.id not in self.rejected_ids
        )
        if added:
            self.credentials += added
        self.active_credential_count = refreshed.active_credential_count
        self.next_availability = refreshed.next_availability
        return added

    def rejection_operation(self, credential: CatastoCredential) -> str:
        return (
            f"Credenziale {credential.sister_username} esclusa: autenticazione rifiutata; "
            f"pool sincronizzato con {len(self.available_ids)} credenziali disponibili"
        )


def _is_available(credential: CatastoCredential, now: datetime) -> bool:
    return credential_is_available(
        getattr(credential, "schedule_enabled", False),
        getattr(credential, "availability_schedule", None),
        now,
    )


def _next_availability(credential: CatastoCredential, now: datetime) -> datetime | None:
    return next_credential_availability(
        getattr(credential, "schedule_enabled", False),
        getattr(credential, "availability_schedule", None),
        now,
    )


def _finalize_loaded_pool(batch: CatastoBatch, pool: ActiveSisterCredentialPool) -> ActiveSisterCredentialPool:
    if pool.credentials:
        _SCHEDULED_BATCH_RESUME_AT.pop(getattr(batch, "id", None), None)
    return pool


def _load_pinned_pool(db: Session, batch: CatastoBatch, now: datetime) -> ActiveSisterCredentialPool:
    credential = db.get(CatastoCredential, batch.credential_id)
    is_active = credential is not None and credential.user_id == batch.user_id and credential.active
    is_available = is_active and _is_available(credential, now)
    next_availability = _next_availability(credential, now) if is_active and not is_available else None
    return _finalize_loaded_pool(
        batch,
        ActiveSisterCredentialPool((credential,) if is_available else (), int(is_active), next_availability),
    )


def _load_shared_pool(db: Session, batch: CatastoBatch, now: datetime) -> ActiveSisterCredentialPool:
    active_credentials = tuple(
        credential
        for credential in db.scalars(
            select(CatastoCredential)
            .where(
                CatastoCredential.user_id == batch.user_id,
                CatastoCredential.active.is_(True),
            )
            .order_by(
                CatastoCredential.is_default.desc(),
                CatastoCredential.updated_at.desc(),
            )
        ).all()
        if credential.active
    )
    credentials = tuple(
        credential
        for credential in active_credentials
        if _is_available(credential, now)
    )
    next_openings = [
        opening
        for credential in active_credentials
        if credential not in credentials
        for opening in [_next_availability(credential, now)]
        if opening is not None
    ]
    return _finalize_loaded_pool(
        batch,
        ActiveSisterCredentialPool(
            credentials,
            len(active_credentials),
            min(next_openings) if next_openings else None,
        ),
    )


def load_active_credential_pool(
    db: Session,
    batch: CatastoBatch,
    at: datetime | None = None,
) -> ActiveSisterCredentialPool:
    now = at or datetime.now(timezone.utc)
    if batch.credential_id is not None:
        return _load_pinned_pool(db, batch, now)
    return _load_shared_pool(db, batch, now)


def refresh_shared_credential_pool(
    session_factory: Callable[[], Session],
    batch_id: UUID,
    pool: ActiveSisterCredentialPool,
    started_ids: set[UUID],
) -> tuple[CatastoCredential, ...]:
    with session_factory() as db:
        batch = db.get(CatastoBatch, batch_id)
        if (
            batch is None
            or batch.status == CatastoBatchStatus.CANCELLED.value
            or batch.credential_id is not None
        ):
            return ()
        refreshed_pool = load_active_credential_pool(db, batch)
    return tuple(credential for credential in pool.merge(refreshed_pool) if credential.id not in started_ids)


async def run_dynamic_credential_pool(
    initial_credentials: tuple[CatastoCredential, ...],
    run_credential: Callable[[CatastoCredential], Awaitable[None]],
    refresh_credentials: Callable[[set[UUID]], tuple[CatastoCredential, ...]],
    has_open_requests: Callable[[], bool],
    on_credentials_added: Callable[[], None],
    refresh_interval_seconds: int,
) -> None:
    started_ids: set[UUID] = set()
    runner_tasks: dict[UUID, asyncio.Task[None]] = {}

    def start_runner(credential: CatastoCredential) -> None:
        started_ids.add(credential.id)
        runner_tasks[credential.id] = asyncio.create_task(run_credential(credential))

    for credential in initial_credentials:
        start_runner(credential)

    while runner_tasks:
        done, _pending = await asyncio.wait(
            runner_tasks.values(),
            timeout=max(refresh_interval_seconds, 1),
            return_when=asyncio.FIRST_EXCEPTION,
        )
        for task in done:
            if task.exception() is not None:
                await task
        if has_open_requests():
            added_credentials = refresh_credentials(started_ids)
            for credential in added_credentials:
                start_runner(credential)
            if added_credentials:
                on_credentials_added()
        if all(task.done() for task in runner_tasks.values()):
            break

    await asyncio.gather(*runner_tasks.values())


def announce_expanded_credential_pool(
    pool: ActiveSisterCredentialPool,
    batch_id: UUID,
    repository: CredentialRejectionRepository,
    set_batch_operation: Callable[[UUID, str], None],
) -> None:
    repository.fail_unavailable_pinned_requests(batch_id, pool.available_ids)
    set_batch_operation(
        batch_id,
        f"Pool visure aggiornato: {len(pool.available_ids)} credenziali disponibili",
    )


def next_processable_batch_id(db: Session, at: datetime | None = None) -> UUID | None:
    now = at or datetime.now(timezone.utc)
    batches = db.scalars(
        select(CatastoBatch)
        .where(CatastoBatch.status == CatastoBatchStatus.PROCESSING.value)
        .order_by(CatastoBatch.started_at.asc().nullsfirst(), CatastoBatch.created_at.asc())
    ).all()
    return next(
        (batch.id for batch in batches if _SCHEDULED_BATCH_RESUME_AT.get(batch.id, now) <= now),
        None,
    )


def mark_batch_waiting_for_schedule(
    batch: CatastoBatch,
    pool: ActiveSisterCredentialPool,
    at: datetime | None = None,
) -> None:
    now = at or datetime.now(timezone.utc)
    if pool.active_credential_count and pool.next_availability is not None:
        _SCHEDULED_BATCH_RESUME_AT[batch.id] = min(pool.next_availability, now + timedelta(minutes=1))
        resume_label = pool.next_availability.astimezone(ZoneInfo("Europe/Rome")).strftime("%d/%m alle %H:%M")
        batch.current_operation = f"In attesa della prossima fascia credenziali: {resume_label}"
        return
    batch.status = CatastoBatchStatus.FAILED.value
    batch.current_operation = "Credenziali SISTER attive mancanti"


def is_rejected_credential_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in _REJECTED_CREDENTIAL_MARKERS)


def quarantine_rejected_credential(
    exc: Exception,
    context: CredentialRejectionContext,
) -> None:
    if not is_rejected_credential_error(exc):
        return
    remaining_credentials = context.pool.reject(context.credential.id)
    operation = context.pool.rejection_operation(context.credential)
    context.repository.fail_unavailable_pinned_requests(context.batch_id, context.pool.available_ids)
    context.repository.reset_for_retry(
        context.request_id,
        operation,
        error_code="sister_credential_rejected",
        execution_token=context.execution_token,
    )
    context.set_batch_operation(context.batch_id, operation)
    logger.error(
        "Batch %s credenziale %s esclusa dopo rifiuto autenticazione; credenziali residue=%s",
        context.batch_id,
        context.credential.sister_username,
        remaining_credentials,
    )
    raise RejectedCredentialQuarantined from exc


async def isolate_rejected_credential_runner(runner: Awaitable[None]) -> None:
    try:
        await runner
    except RejectedCredentialQuarantined:
        return


def should_stop_credential_runner(
    stop_requested: bool,
    batch_id: UUID,
    username: str,
    release_requested: Callable[[], bool],
    credential_release_requested: Callable[[], bool] | None = None,
) -> bool:
    if stop_requested:
        return True
    if release_requested():
        logger.info(
            "Batch %s arrestato dopo completamento checkpoint corrente, logout per %s",
            batch_id,
            username,
        )
        return True
    if credential_release_requested is None or not credential_release_requested():
        return False
    logger.info("Credenziale %s messa in pausa, logout della singola sessione SISTER", username)
    return True


def credential_is_active(session_factory: Callable[[], Session], credential_id: UUID) -> bool:
    with session_factory() as db:
        credential = db.get(CatastoCredential, credential_id)
        return credential is not None and credential.active


def finalize_credential_pool(
    pool: ActiveSisterCredentialPool,
    batch_id: UUID,
    has_open_requests: bool,
    session_factory: Callable[[], Session],
    finalize_batch: Callable[[UUID], None],
) -> None:
    if has_open_requests and not pool.available_ids:
        _pause_batch_for_rejected_credentials(session_factory, batch_id, len(pool.credentials))
        return
    finalize_batch(batch_id)


def _pause_batch_for_rejected_credentials(
    session_factory: Callable[[], Session],
    batch_id: UUID,
    credential_count: int,
) -> None:
    with session_factory() as db:
        batch = db.get(CatastoBatch, batch_id)
        if batch is None or batch.status == CatastoBatchStatus.CANCELLED.value:
            return
        batch.status = CatastoBatchStatus.FAILED.value
        batch.completed_at = datetime.now(timezone.utc)
        batch.current_operation = (
            f"Nessuna delle {credential_count} credenziali SISTER e' disponibile o autenticabile; "
            "riattivare o aggiornare il pool e riprendere il batch"
        )
        db.commit()
