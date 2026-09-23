from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from test_worker import _seed_batch, _VisuraFlowResult, worker_module
from test_worker import worker_db as _worker_db

import sister_worker_reliability
from app.models.catasto import CatastoVisuraRequest, CatastoVisuraRequestStatus

worker_db = _worker_db


def test_ade_document_does_not_create_sister_extraction(
    worker_db: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    worker, session_factory, _ = worker_db
    _, batch_id, request_ids = _seed_batch(
        session_factory,
        request_statuses=[CatastoVisuraRequestStatus.PROCESSING.value],
    )
    ade_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        worker_module,
        "persist_ade_status_scan_result",
        lambda _db, **kwargs: ade_calls.append(kwargs),
    )
    monkeypatch.setattr(
        worker_module,
        "parse_historical_visura_pdf",
        lambda _path: {"classification": "active"},
    )

    def reject_sister_extraction(*_args: object) -> None:
        pytest.fail("An AdE scan must not create a SISTER extraction")

    monkeypatch.setattr(
        sister_worker_reliability, "persist_sister_visura", reject_sister_extraction
    )
    pdf_path = tmp_path / "ade.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\nade")
    with session_factory() as db:
        request = db.get(CatastoVisuraRequest, request_ids[0])
        assert request is not None
        request.purpose = worker_module.ADE_SCAN_PURPOSE
        request.target_ruolo_particella_id = uuid.uuid4()
        db.commit()

    result = _VisuraFlowResult()
    result.file_path = pdf_path
    result.file_size = pdf_path.stat().st_size
    worker._request_repository().persist_flow_result(batch_id, request_ids[0], "USER", result)

    assert ade_calls[0]["classification"] == "active"
    assert ade_calls[0]["document_id"] is not None
