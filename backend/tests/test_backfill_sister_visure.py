from __future__ import annotations

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core import database
from scripts import backfill_sister_visure


class _Session:
    def __init__(self, documents: list[SimpleNamespace]) -> None:
        self.documents = documents
        self.statement = None
        self.commits = 0
        self.rollbacks = 0

    def __enter__(self) -> _Session:
        return self

    def __exit__(self, *_args: object) -> None:
        pass

    def scalars(self, statement: object) -> list[SimpleNamespace]:
        self.statement = statement
        return self.documents

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def test_backfill_selects_only_request_bound_sister_documents(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    session = _Session([])
    monkeypatch.setattr(backfill_sister_visure, "SessionLocal", lambda: session)
    monkeypatch.setattr(sys, "argv", ["backfill_sister_visure"])

    assert backfill_sister_visure.main() == 0

    sql = str(session.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "JOIN catasto_visure_requests" in sql
    assert "catasto_visure_requests.id = catasto_documents.request_id" in sql
    assert "'visura_pdf'" in sql
    assert "'perpetual_sync'" in sql
    assert "'ade_status_scan'" not in sql
    assert "catasto_sister_extractions.document_id" in sql
    assert capsys.readouterr().out == "processed=0 review_required=0 failed=0 missing=0\n"


def test_backfill_reports_results_and_can_reprocess_failed_extractions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pdf = tmp_path / "visura.pdf"
    pdf.write_bytes(b"pdf")
    text_file = tmp_path / "not-pdf.txt"
    text_file.write_text("not pdf")
    documents = [
        SimpleNamespace(id=index, filepath=str(path))
        for index, path in enumerate(
            [pdf, pdf, pdf, pdf, text_file, tmp_path / "missing.pdf"], start=1
        )
    ]
    session = _Session(documents)
    statuses = iter(["ok", "review_required", "failed"])

    def persist(_db: _Session, document: SimpleNamespace) -> SimpleNamespace:
        if document.id == 4:
            raise ValueError("parser failed")
        return SimpleNamespace(status=next(statuses))

    monkeypatch.setattr(backfill_sister_visure, "SessionLocal", lambda: session)
    monkeypatch.setattr(backfill_sister_visure, "persist_sister_visura", persist)
    monkeypatch.setattr(sys, "argv", ["backfill_sister_visure", "--include-failed", "--limit", "6"])

    assert backfill_sister_visure.main() == 1

    sql = str(session.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "catasto_sister_extractions.document_id" not in sql
    assert "LIMIT 6" in sql
    assert session.commits == 3
    assert session.rollbacks == 1
    assert capsys.readouterr().out == "processed=3 review_required=1 failed=2 missing=2\n"


def test_backfill_cli_exits_without_database_writes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    session = _Session([])
    monkeypatch.setattr(database, "SessionLocal", lambda: session)
    monkeypatch.setattr(sys, "argv", ["backfill_sister_visure"])

    with pytest.raises(SystemExit) as result:
        runpy.run_path(str(Path(backfill_sister_visure.__file__)), run_name="__main__")

    assert result.value.code == 0
    assert session.commits == 0
    assert capsys.readouterr().out == "processed=0 review_required=0 failed=0 missing=0\n"
