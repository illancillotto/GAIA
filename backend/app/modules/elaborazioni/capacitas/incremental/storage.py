"""Durable original artifacts and a PostgreSQL lease, independent of portal sessions."""

import hashlib
import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text


def save_original(root: Path, content: bytes) -> tuple[str, Path]:
    sha = hashlib.sha256(content).hexdigest()
    directory = root / "originals"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / f"{sha}.xlsx"
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise RuntimeError("artifact_integrity_failure")
        return sha, path
    temporary = directory / f".{uuid4().hex}.tmp"
    try:
        with temporary.open("xb") as stream:
            os.chmod(temporary, 0o600)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)
    return sha, path


@contextmanager
def pipeline_lease(engine):
    """Dedicated connection: transaction commits elsewhere cannot release this lease."""
    if engine.dialect.name != "postgresql":
        raise RuntimeError("incremental_worker_requires_postgresql")
    with engine.connect() as connection:
        acquired = connection.scalar(text("SELECT pg_try_advisory_lock(716314, 1)"))
        try:
            yield bool(acquired)
        finally:
            if acquired:
                connection.execute(text("SELECT pg_advisory_unlock(716314, 1)"))
                connection.commit()
