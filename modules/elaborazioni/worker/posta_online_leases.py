"""Session locks survive job commits and are released when a worker disconnects."""

import hashlib

from sqlalchemy import text
from sqlalchemy.engine import Engine

_PORTAL_NAMESPACE = 187431
_ACCOUNT_NAMESPACE = 187432


class PortalLease:
    def __init__(self, engine: Engine) -> None:
        if engine.dialect.name != "postgresql":
            raise RuntimeError("Il pool Poste richiede lock PostgreSQL")
        self.connection = engine.connect()
        self.locks: list[tuple[int, int, bool]] = []

    def acquire(self, namespace: int, key: int, *, shared: bool = False) -> bool:
        function = "pg_try_advisory_lock_shared" if shared else "pg_try_advisory_lock"
        acquired = self.connection.scalar(
            text(f"SELECT {function}(:namespace, :key)"), {"namespace": namespace, "key": key}
        )
        if acquired:
            self.locks.append((namespace, key, shared))
        self.connection.commit()
        return bool(acquired)

    def close(self) -> None:
        if self.connection.closed:
            return
        try:
            for namespace, key, shared in reversed(self.locks):
                function = "pg_advisory_unlock_shared" if shared else "pg_advisory_unlock"
                self.connection.scalar(
                    text(f"SELECT {function}(:namespace, :key)"),
                    {"namespace": namespace, "key": key},
                )
            self.connection.commit()
        except BaseException:
            self.connection.invalidate()
            raise
        finally:
            self.connection.close()


def acquire_portal_lease(engine: Engine, username: str | None) -> PortalLease | None:
    """Dispatches share the portal gate; legacy sessions require exclusive access."""
    lease = PortalLease(engine)
    try:
        ready = lease.acquire(_PORTAL_NAMESPACE, 0, shared=username is not None)
        if ready and username is not None:
            digest = hashlib.blake2s(username.strip().casefold().encode(), digest_size=4).digest()
            ready = lease.acquire(_ACCOUNT_NAMESPACE, int.from_bytes(digest, "big", signed=True))
        if ready:
            return lease
    except BaseException:
        lease.close()
        raise
    lease.close()
    return None
