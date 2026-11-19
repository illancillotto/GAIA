"""A bulk sync owns one database lease across its audit and domain commits."""

import fcntl
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import Engine, select, text, update
from sqlalchemy.orm import Session

from app.modules.operazioni.models.gate_mobile_sync_run import GateMobileSyncRun

GATE_MOBILE_SYNC_LOCK = 760031019


class GateMobileSyncBusy(HTTPException):
    """Another process owns the outbound cycle."""

    def __init__(self) -> None:
        super().__init__(409, "Gate mobile sync già in esecuzione")


@contextmanager
def outbound_lease(db: Session) -> Iterator[int | None]:
    engine = db.get_bind().engine
    if engine.dialect.name == "sqlite":
        # SQLite fixtures have no PostgreSQL lock, so never mark them as leased.
        if db.scalar(
            select(GateMobileSyncRun.id).where(GateMobileSyncRun.status == "running").limit(1)
        ):
            raise GateMobileSyncBusy
        yield None
        return

    with _host_lock(), _postgres_lease(engine) as owner:
        # The retained PID is diagnostic only. Exclusive acquisition proves
        # that the previous lease ended, even when PostgreSQL reuses a PID.
        db.execute(
            update(GateMobileSyncRun)
            .where(
                GateMobileSyncRun.status == "running",
                GateMobileSyncRun.lease_backend_pid.is_not(None),
            )
            .values(
                status="failed",
                finished_at=datetime.now(UTC),
                error_kind="worker_interrupted",
                error_message="Previous outbound lease ended before finalization",
            )
        )
        yield owner


@contextmanager
def _postgres_lease(engine: Engine) -> Iterator[int]:
    # A session lock needs no open transaction while HTTP or the gateway are
    # busy. Discard the physical session on exit to release the lock even if
    # the socket died independently and to prevent pooling a locked session.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as lease:
        try:
            owner = lease.scalar(
                text("SELECT pg_backend_pid() WHERE pg_try_advisory_lock(:key)"),
                {"key": GATE_MOBILE_SYNC_LOCK},
            )
            if owner is None:
                raise GateMobileSyncBusy
            yield owner
        finally:
            lease.invalidate()


@contextmanager
def _host_lock() -> Iterator[None]:
    # Every CED producer mounts the same runtime directory. A separate local
    # descriptor still fences a live process if only its database socket dies.
    path = Path(os.environ.get("GATE_MOBILE_SYNC_LOCK_PATH", "/tmp/gaia-gate-mobile-sync.lock"))
    with path.open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise GateMobileSyncBusy from exc
        yield
