from __future__ import annotations

import os
import shlex
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.services.nas_connector import NasConnectorError, get_nas_client

SFTP_PUBLISH_RETRY_DELAYS_SECONDS = (1.0, 3.0)


@dataclass(frozen=True)
class GisArtifactStorageProbe:
    path: str
    transport: str
    readable: bool
    writable: bool


def _uses_sftp(path: str) -> bool:
    if settings.gis_nas_transport.strip().lower() != "sftp":
        return False
    root = Path(settings.gis_nas_health_path).as_posix().rstrip("/")
    candidate = Path(path).as_posix()
    return candidate == root or candidate.startswith(f"{root}/")


def _publish_sftp_once(source_path: Path, temporary_path: str, destination_path: str) -> None:
    client = get_nas_client()
    try:
        client.upload_local_file(str(source_path), temporary_path)
        client.move_file(temporary_path, destination_path)
    finally:
        client.close()


def _wait_before_sftp_retry(attempt: int, error: NasConnectorError) -> None:
    if attempt >= len(SFTP_PUBLISH_RETRY_DELAYS_SECONDS):
        raise error
    time.sleep(SFTP_PUBLISH_RETRY_DELAYS_SECONDS[attempt])


def _publish_sftp(source_path: Path, destination_path: str) -> None:
    temporary_path = f"{destination_path}.{uuid.uuid4().hex}.tmp"
    for attempt in range(len(SFTP_PUBLISH_RETRY_DELAYS_SECONDS) + 1):
        try:
            _publish_sftp_once(source_path, temporary_path, destination_path)
            return
        except NasConnectorError as exc:
            _wait_before_sftp_retry(attempt, exc)


def publish_artifact(source_path: Path, destination_path: str) -> None:
    if _uses_sftp(destination_path):
        _publish_sftp(source_path, destination_path)
        return

    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.parent / f".{destination.name}.{uuid.uuid4().hex}.tmp"
    shutil.copyfile(source_path, temporary)
    temporary.replace(destination)


def delete_artifact(path: str) -> bool:
    if _uses_sftp(path):
        client = get_nas_client()
        try:
            if not client.path_exists(path):
                return False
            client.run_command(f"rm -f -- {shlex.quote(path)}")
            return True
        finally:
            client.close()

    local_path = Path(path)
    if not local_path.is_file():
        return False
    local_path.unlink()
    return True


def probe_artifact_storage(path: str) -> GisArtifactStorageProbe:
    transport = settings.gis_nas_transport.strip().lower() or "local"
    if transport == "sftp":
        client = get_nas_client()
        marker_path = f"{path.rstrip('/')}/.gaia-health-{uuid.uuid4().hex}"
        marker = os.urandom(24)
        try:
            client.ensure_directory(path)
            client.upload_file(marker_path, marker)
            readable = client.download_file(marker_path) == marker
            client.run_command(f"rm -f -- {shlex.quote(marker_path)}")
        finally:
            client.close()
        return GisArtifactStorageProbe(
            path=path,
            transport=transport,
            readable=readable,
            writable=True,
        )

    local_path = Path(path)
    available = local_path.exists() and local_path.is_dir()
    return GisArtifactStorageProbe(
        path=path,
        transport=transport,
        readable=available and os.access(local_path, os.R_OK),
        writable=available and os.access(local_path, os.W_OK),
    )
