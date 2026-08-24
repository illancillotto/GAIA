from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.catasto.services import ade_document_audit_backfill as backfill_module
from app.modules.catasto.services.ade_document_audit_backfill import backfill_document_audits


class _Scalars:
    def __init__(self, documents):
        self.documents = documents

    def all(self):
        return self.documents


class _Db:
    def __init__(self, documents):
        self.documents = documents
        self.commits = 0
        self.rollbacks = 0
        self.statement = None

    def scalars(self, statement):
        self.statement = statement
        return _Scalars(self.documents)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def _document(path: Path, request_type: str | None = None):
    return SimpleNamespace(filepath=str(path), request_type=request_type, tipo_visura="Sintetica")


def test_backfill_dry_run_counts_results_without_writes(tmp_path, monkeypatch) -> None:
    current = tmp_path / "current.pdf"
    missing = tmp_path / "missing.pdf"
    broken = tmp_path / "broken.pdf"
    current.write_bytes(b"pdf")
    broken.write_bytes(b"pdf")
    db = _Db([_document(current), _document(missing), _document(broken)])

    def audit(path, _request_type):
        if path == broken:
            raise ValueError("invalid")
        return {"classification": "current"}

    monkeypatch.setattr(backfill_module, "audit_visura_pdf", audit)
    monkeypatch.setattr(backfill_module, "apply_document_audit", pytest.fail)

    counters = backfill_document_audits(db, batch_id=uuid4(), limit=3)

    assert counters == {
        "selected": 3,
        "missing_file": 1,
        "audit_failed": 1,
        "classification:current": 1,
        "audited": 1,
        "updated": 0,
    }
    assert db.rollbacks == 1
    assert db.commits == 0


def test_backfill_apply_commits_in_chunks_and_force_reprocesses(tmp_path, monkeypatch) -> None:
    paths = [tmp_path / f"{index}.pdf" for index in range(3)]
    for path in paths:
        path.write_bytes(b"pdf")
    documents = [_document(path, "STORICA") for path in paths]
    db = _Db(documents)
    applied = []
    monkeypatch.setattr(
        backfill_module,
        "audit_visura_pdf",
        lambda _path, expected: {"classification": "suppressed", "expected": expected},
    )
    monkeypatch.setattr(backfill_module, "apply_document_audit", lambda document, payload: applied.append((document, payload)))

    counters = backfill_document_audits(db, force=True, dry_run=False, commit_every=2)

    assert counters["updated"] == 3
    assert counters["classification:suppressed"] == 3
    assert len(applied) == 3
    assert db.commits == 2
    assert db.rollbacks == 0

    db = _Db([documents[0]])
    counters = backfill_document_audits(db, force=True, dry_run=False, commit_every=1)
    assert counters["updated"] == 1
    assert db.commits == 1


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [({"limit": 0}, "limit"), ({"commit_every": 0}, "commit_every")],
)
def test_backfill_rejects_invalid_limits(kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        backfill_document_audits(_Db([]), **kwargs)
