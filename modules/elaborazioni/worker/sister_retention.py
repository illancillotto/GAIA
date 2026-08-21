from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
from time import monotonic
from typing import Callable


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RetentionResult:
    deleted_files: int = 0
    deleted_directories: int = 0
    reclaimed_bytes: int = 0
    dry_run: bool = False

    def add(self, other: "RetentionResult") -> "RetentionResult":
        return RetentionResult(
            self.deleted_files + other.deleted_files,
            self.deleted_directories + other.deleted_directories,
            self.reclaimed_bytes + other.reclaimed_bytes,
            self.dry_run,
        )


@dataclass(frozen=True, slots=True)
class ArtifactRetentionPolicy:
    allowed_roots: tuple[Path, ...]
    retention_days: int
    dry_run: bool


@dataclass(frozen=True, slots=True)
class SisterRetentionConfig:
    debug_root: Path
    report_root: Path
    artifact_retention_days: int
    event_retention_days: int
    dry_run: bool
    interval_seconds: int = 86_400


def purge_artifacts(
    root: Path,
    policy: ArtifactRetentionPolicy,
    *,
    now: datetime | None = None,
) -> RetentionResult:
    resolved_root = _validated_root(root, policy.allowed_roots)
    if not resolved_root.exists() or policy.retention_days <= 0:
        return RetentionResult(dry_run=policy.dry_run)
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=policy.retention_days)
    result = RetentionResult(dry_run=policy.dry_run)
    paths = sorted(resolved_root.rglob("*"), key=lambda item: len(item.parts), reverse=True)
    for path in paths:
        result = result.add(_purge_path(path, cutoff, policy.dry_run))
    return result


def _validated_root(root: Path, allowed_roots: tuple[Path, ...]) -> Path:
    resolved_root = root.resolve()
    allowed = {candidate.resolve() for candidate in allowed_roots}
    if resolved_root not in allowed:
        raise ValueError(f"Retention root non autorizzata: {resolved_root}")
    return resolved_root


def _purge_path(path: Path, cutoff: datetime, dry_run: bool) -> RetentionResult:
    if path.is_symlink():
        return RetentionResult(dry_run=dry_run)
    if path.is_file():
        return _purge_file(path, cutoff, dry_run)
    if path.is_dir() and not any(path.iterdir()):
        if not dry_run:
            path.rmdir()
        return RetentionResult(deleted_directories=1, dry_run=dry_run)
    return RetentionResult(dry_run=dry_run)


def _purge_file(path: Path, cutoff: datetime, dry_run: bool) -> RetentionResult:
    stat = path.stat()
    if datetime.fromtimestamp(stat.st_mtime, timezone.utc) >= cutoff:
        return RetentionResult(dry_run=dry_run)
    if not dry_run:
        path.unlink(missing_ok=True)
    return RetentionResult(deleted_files=1, reclaimed_bytes=stat.st_size, dry_run=dry_run)


class SisterRetentionManager:
    def __init__(self, config: SisterRetentionConfig, purge_events: Callable[[int], int]) -> None:
        self.config = config
        self.purge_events = purge_events
        self._next_run = 0.0

    def run_if_due(self, *, force: bool = False) -> bool:
        now_monotonic = monotonic()
        if not force and now_monotonic < self._next_run:
            return False
        self._next_run = now_monotonic + max(self.config.interval_seconds, 60)
        self._run()
        return True

    def _run(self) -> None:
        try:
            artifact_result = self._purge_artifacts()
            deleted_events = 0 if self.config.dry_run else self.purge_events(self.config.event_retention_days)
            logger.info(
                "Retention SISTER completata dry_run=%s files=%s dirs=%s bytes=%s events=%s",
                self.config.dry_run,
                artifact_result.deleted_files,
                artifact_result.deleted_directories,
                artifact_result.reclaimed_bytes,
                deleted_events,
            )
        except Exception:
            logger.warning("Retention SISTER ignorata per non interrompere il worker", exc_info=True)

    def _purge_artifacts(self) -> RetentionResult:
        roots = (self.config.debug_root, self.config.report_root)
        policy = ArtifactRetentionPolicy(
            allowed_roots=roots,
            retention_days=self.config.artifact_retention_days,
            dry_run=self.config.dry_run,
        )
        result = RetentionResult(dry_run=self.config.dry_run)
        for root in roots:
            result = result.add(purge_artifacts(root, policy))
        return result


__all__ = [
    "ArtifactRetentionPolicy",
    "RetentionResult",
    "SisterRetentionConfig",
    "SisterRetentionManager",
    "purge_artifacts",
]
