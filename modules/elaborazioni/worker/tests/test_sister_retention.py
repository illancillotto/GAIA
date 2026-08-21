from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys

import pytest


WORKER_ROOT = Path(__file__).resolve().parents[1]
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))


import sister_retention as retention_module
from sister_retention import (
    ArtifactRetentionPolicy,
    SisterRetentionConfig,
    SisterRetentionManager,
    purge_artifacts,
)


def _age(path: Path, days: int) -> None:
    timestamp = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
    os.utime(path, (timestamp, timestamp))


def test_purge_artifacts_enforces_roots_and_retention(tmp_path) -> None:
    debug_root = tmp_path / "debug"
    report_root = tmp_path / "reports"
    debug_root.mkdir()
    report_root.mkdir()
    old_dir = debug_root / "old"
    old_dir.mkdir()
    old_file = old_dir / "trace.html"
    old_file.write_bytes(b"old")
    _age(old_file, 20)
    empty_dir = debug_root / "empty"
    empty_dir.mkdir()
    fresh_file = debug_root / "fresh.png"
    fresh_file.write_bytes(b"fresh")
    symlink = debug_root / "external-link"
    symlink.symlink_to(tmp_path / "outside")

    with pytest.raises(ValueError, match="non autorizzata"):
        purge_artifacts(
            tmp_path,
            ArtifactRetentionPolicy((debug_root, report_root), 14, False),
        )

    dry = purge_artifacts(
        debug_root,
        ArtifactRetentionPolicy((debug_root, report_root), 14, True),
    )
    assert dry.deleted_files == 1
    assert dry.deleted_directories == 1
    assert dry.reclaimed_bytes == 3
    assert old_file.exists()
    assert empty_dir.exists()

    result = purge_artifacts(
        debug_root,
        ArtifactRetentionPolicy((debug_root, report_root), 14, False),
    )
    assert result.deleted_files == 1
    assert result.deleted_directories == 2
    assert not old_dir.exists()
    assert fresh_file.exists()
    assert symlink.is_symlink()

    assert purge_artifacts(
        report_root,
        ArtifactRetentionPolicy((debug_root, report_root), 0, False),
    ).deleted_files == 0
    assert purge_artifacts(
        tmp_path / "missing",
        ArtifactRetentionPolicy((tmp_path / "missing",), 14, False),
    ).deleted_files == 0


def test_retention_manager_schedules_dry_run_and_is_fail_open(tmp_path, monkeypatch) -> None:
    debug_root = tmp_path / "debug"
    report_root = tmp_path / "reports"
    debug_root.mkdir()
    report_root.mkdir()
    deleted = []
    ticks = iter([100.0, 101.0, 200.0, 300.0, 400.0])
    monkeypatch.setattr(retention_module, "monotonic", lambda: next(ticks))
    manager = SisterRetentionManager(
        SisterRetentionConfig(debug_root, report_root, 14, 30, False, 10),
        lambda days: deleted.append(days) or 4,
    )
    assert manager.run_if_due() is True
    assert manager.run_if_due() is False
    assert manager.run_if_due(force=True) is True
    assert deleted == [30, 30]

    dry_manager = SisterRetentionManager(
        SisterRetentionConfig(debug_root, report_root, 14, 30, True),
        lambda _days: pytest.fail("dry-run must not purge DB"),
    )
    assert dry_manager.run_if_due(force=True) is True

    failing_manager = SisterRetentionManager(
        SisterRetentionConfig(debug_root, report_root, 14, 30, False),
        lambda _days: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert failing_manager.run_if_due(force=True) is True
