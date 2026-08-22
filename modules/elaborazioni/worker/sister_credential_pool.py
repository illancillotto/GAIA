from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoBatch, CatastoBatchStatus, CatastoCredential


_REJECTED_CREDENTIAL_MARKERS = (
    "credenziali sister rifiutate",
    "credenziali errate",
    "autenticazione fallita",
)
logger = logging.getLogger(__name__)


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
    rejected_ids: set[UUID] = field(default_factory=set)

    @property
    def available_ids(self) -> set[UUID]:
        return {credential.id for credential in self.credentials} - self.rejected_ids

    def reject(self, credential_id: UUID) -> int:
        self.rejected_ids.add(credential_id)
        return len(self.available_ids)

    def rejection_operation(self, credential: CatastoCredential) -> str:
        return (
            f"Credenziale {credential.sister_username} esclusa: autenticazione rifiutata; "
            f"pool sincronizzato con {len(self.available_ids)} credenziali disponibili"
        )


def load_active_credential_pool(db: Session, batch: CatastoBatch) -> ActiveSisterCredentialPool:
    if batch.credential_id is not None:
        credential = db.get(CatastoCredential, batch.credential_id)
        credentials = (
            (credential,)
            if credential is not None and credential.user_id == batch.user_id and credential.active
            else ()
        )
        return ActiveSisterCredentialPool(credentials)

    credentials = tuple(
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
    return ActiveSisterCredentialPool(credentials)


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
) -> bool:
    if stop_requested:
        return True
    if not release_requested():
        return False
    logger.info(
        "Batch %s arrestato dopo completamento checkpoint corrente, logout per %s",
        batch_id,
        username,
    )
    return True


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
            f"Nessuna delle {credential_count} credenziali SISTER disponibili e' autenticabile; "
            "aggiornare il pool e riprendere il batch"
        )
        db.commit()
