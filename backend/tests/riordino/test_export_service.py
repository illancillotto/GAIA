from __future__ import annotations

import csv
import json
import zipfile
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.modules.riordino.services import export_service

PRACTICE_ID = UUID(int=1)
PHASE_ID = UUID(int=2)
STEP_ID = UUID(int=3)
UNKNOWN_ID = UUID(int=4)
APPEAL_ID = UUID(int=5)
ISSUE_ID = UUID(int=6)


@pytest.fixture
def practice(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    step = SimpleNamespace(
        id=STEP_ID,
        code="STEP",
        title="Istruttoria",
        status="open",
        is_required=True,
        branch=None,
        is_decision=False,
        outcome_code=None,
        skip_reason=None,
        documents=[],
        checklist_items=[],
        started_at=None,
        completed_at=None,
    )
    phase = SimpleNamespace(id=PHASE_ID, phase_code="PHASE", status="open", steps=[step])
    result = SimpleNamespace(
        id=PRACTICE_ID,
        code="PR-001",
        title="Pratica à",
        municipality="Comune",
        grid_code="G1",
        lot_code="L1",
        status="open",
        current_phase="PHASE",
        phases=[phase],
        documents=[],
        issues=[],
        appeals=[],
    )
    monkeypatch.setattr(export_service.PracticeRepository, "get", lambda self, key: result)
    return result


@pytest.mark.parametrize(
    ("step_id", "appeal_id", "issue_id", "phase_id"),
    list(
        product(
            [None, UNKNOWN_ID, STEP_ID],
            [None, APPEAL_ID],
            [None, ISSUE_ID],
            [None, UNKNOWN_ID, PHASE_ID],
        )
    ),
)
def test_dossier_document_precedence_and_contents(
    practice: SimpleNamespace,
    tmp_path: Path,
    step_id: UUID | None,
    appeal_id: UUID | None,
    issue_id: UUID | None,
    phase_id: UUID | None,
) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"document content")
    practice.documents = [
        SimpleNamespace(
            step_id=step_id,
            appeal_id=appeal_id,
            issue_id=issue_id,
            phase_id=phase_id,
            original_filename="original.pdf",
            storage_path=str(source),
            deleted_at=None,
        )
    ]
    if step_id == STEP_ID:
        directory = "PHASE/STEP"
    elif appeal_id is not None:
        directory = f"appeals/{APPEAL_ID}"
    elif issue_id is not None:
        directory = f"issues/{ISSUE_ID}"
    elif phase_id == PHASE_ID:
        directory = "PHASE/_general"
    else:
        directory = "_general"
    buffer, filename = export_service.export_practice_dossier_zip(Mock(), PRACTICE_ID)
    assert filename == "pr-001-dossier.zip"
    assert buffer.tell() == 0
    with zipfile.ZipFile(buffer) as archive:
        entry = f"documents/{directory}/original.pdf"
        assert archive.namelist() == ["manifest.json", "summary/practice-summary.csv", entry]
        assert archive.read(entry) == b"document content"
        assert json.loads(archive.read("manifest.json")) == {
            "practice": {
                "id": str(PRACTICE_ID),
                "code": "PR-001",
                "title": "Pratica à",
                "municipality": "Comune",
                "grid_code": "G1",
                "lot_code": "L1",
                "status": "open",
                "current_phase": "PHASE",
            },
            "counts": {"phases": 1, "steps": 1, "documents": 1, "issues": 0, "appeals": 0},
        }
        assert b"Pratica \xc3\xa0" in archive.read("manifest.json")
        csv_content, csv_filename = export_service.export_practice_summary_csv(Mock(), PRACTICE_ID)
        assert csv_filename == "pr-001-summary.csv"
        assert archive.read("summary/practice-summary.csv") == csv_content


def test_dossier_excludes_deleted_and_missing_files_but_counts_missing(
    practice: SimpleNamespace, tmp_path: Path
) -> None:
    practice.documents = [
        SimpleNamespace(deleted_at=datetime.now(UTC)),
        SimpleNamespace(deleted_at=None, storage_path=str(tmp_path / "missing.pdf")),
    ]
    buffer, _ = export_service.export_practice_dossier_zip(Mock(), PRACTICE_ID)
    with zipfile.ZipFile(buffer) as archive:
        assert archive.namelist() == ["manifest.json", "summary/practice-summary.csv"]
        assert json.loads(archive.read("manifest.json"))["counts"]["documents"] == 1


def test_summary_preserves_step_order_and_optional_values(practice: SimpleNamespace) -> None:
    step = practice.phases[0].steps[0]
    step.documents = [
        SimpleNamespace(deleted_at=None),
        SimpleNamespace(deleted_at=datetime.now(UTC)),
    ]
    step.checklist_items = [SimpleNamespace(is_checked=True), SimpleNamespace(is_checked=False)]
    step.branch = "branch"
    step.outcome_code = "accepted"
    step.skip_reason = "reason"
    step.started_at = datetime(2026, 10, 1, tzinfo=UTC)
    step.completed_at = datetime(2026, 10, 2, tzinfo=UTC)
    rows = export_service.build_practice_summary_rows(practice)
    assert rows == [
        {
            "practice_code": "PR-001",
            "practice_title": "Pratica à",
            "municipality": "Comune",
            "grid_code": "G1",
            "lot_code": "L1",
            "practice_status": "open",
            "phase_code": "PHASE",
            "phase_status": "open",
            "step_code": "STEP",
            "step_title": "Istruttoria",
            "step_status": "open",
            "is_required": True,
            "branch": "branch",
            "is_decision": False,
            "outcome_code": "accepted",
            "skip_reason": "reason",
            "documents_count": 1,
            "checklist_total": 2,
            "checklist_checked": 1,
            "started_at": "2026-10-01T00:00:00+00:00",
            "completed_at": "2026-10-02T00:00:00+00:00",
        }
    ]
    step.branch = step.outcome_code = step.skip_reason = None
    step.started_at = step.completed_at = None
    practice.phases.append(SimpleNamespace(phase_code="SECOND", status="closed", steps=[step]))
    content, _ = export_service.export_practice_summary_csv(Mock(), PRACTICE_ID)
    exported = list(csv.DictReader(content.decode("utf-8").splitlines()))
    assert [row["phase_code"] for row in exported] == ["PHASE", "SECOND"]
    assert all(row["started_at"] == row["completed_at"] == "" for row in exported)
    assert all(row["branch"] == row["outcome_code"] == row["skip_reason"] == "" for row in exported)


def test_summary_empty_practice_keeps_csv_header(practice: SimpleNamespace) -> None:
    expected_header = list(export_service.build_practice_summary_rows(practice)[0])
    practice.phases = []
    content, filename = export_service.export_practice_summary_csv(Mock(), PRACTICE_ID)
    assert filename == "pr-001-summary.csv"
    assert list(csv.reader(content.decode("utf-8").splitlines())) == [expected_header]


@pytest.mark.parametrize(
    "exporter",
    [export_service.export_practice_summary_csv, export_service.export_practice_dossier_zip],
)
def test_export_missing_practice_is_404(monkeypatch: pytest.MonkeyPatch, exporter) -> None:
    monkeypatch.setattr(export_service.PracticeRepository, "get", lambda self, key: None)
    with pytest.raises(HTTPException) as error:
        exporter(Mock(), PRACTICE_ID)
    assert error.value.status_code == 404
    assert error.value.detail == "Practice not found"
