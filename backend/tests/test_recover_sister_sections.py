from __future__ import annotations

import runpy
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.models.catasto import (
    CatastoBatch,
    CatastoPerpetualSyncItem,
    CatastoRuoloAutoSyncConfig,
    CatastoVisuraRequest,
)
from app.models.catasto_phase1 import CatParticella
from app.modules.ruolo.models import RuoloParticella
from app.scripts.recover_sister_sections import (
    _eligible,
    _has_section_evidence,
    recover_required_sections,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for model in (
            CatastoBatch,
            CatastoVisuraRequest,
            CatastoPerpetualSyncItem,
            CatastoRuoloAutoSyncConfig,
            RuoloParticella,
            CatParticella,
        ):
            connection.execute(CreateTable(model.__table__, include_foreign_key_constraints=[]))
    with Session(engine) as session:
        yield session
    engine.dispose()


def _seed(db: Session, root: Path):
    batch = CatastoBatch(user_id=1, batch_kind="perpetual_sync", status="processing", total_items=2)
    config = CatastoRuoloAutoSyncConfig(user_id=1, batch_size=2)
    source = CatParticella(
        cod_comune_capacitas=1,
        nome_comune="Oristano",
        sezione_catastale="D",
        foglio="2",
        particella="354",
    )
    db.add_all([batch, config, source])
    db.flush()
    role_parcel = RuoloParticella(
        partita_id=uuid4(),
        anno_tributario=2026,
        foglio="2",
        particella="354",
        cat_particella_id=source.id,
        cat_particella_match_status="matched",
    )
    db.add(role_parcel)
    db.flush()
    request = CatastoVisuraRequest(
        batch_id=batch.id,
        user_id=1,
        row_index=1,
        status="failed",
        attempts=1,
        comune="Oristano",
        foglio="2",
        particella="354",
        sezione=None,
    )
    db.add(request)
    db.flush()
    request.error_message = (
        f"Submit visura non avanzato per richiesta {request.id}: classification=current"
    )
    request.artifact_dir = str(root / "requests" / str(batch.id) / str(request.id))
    Path(request.artifact_dir).mkdir(parents=True)
    (Path(request.artifact_dir) / "final-failed.html").write_text(
        '<p>La sezione è obbligatoria</p><select name="sezione">'
        '<option value="A">A</option><option value="D">D</option></select>',
        encoding="utf-8",
    )
    waiting = CatastoVisuraRequest(batch_id=batch.id, user_id=1, row_index=2, status="pending")
    item = CatastoPerpetualSyncItem(
        user_id=1,
        scope="ruolo_particella",
        target_key="target",
        priority=10,
        search_mode="immobile",
        comune="Oristano",
        foglio="2",
        particella="354",
        sezione="D",
        status="failed",
        attempt_count=1,
        linked_batch_id=batch.id,
        linked_request_id=request.id,
        ruolo_particella_id=role_parcel.id,
        cat_particella_id=source.id,
        next_due_at=datetime.now(UTC),
    )
    db.add_all([request, waiting, item])
    db.commit()
    return batch.id, request.id, item.id


def test_dry_run_and_apply_reuse_original_request(db, tmp_path):
    batch_id, request_id, item_id = _seed(db, tmp_path)
    original = db.get(CatastoVisuraRequest, request_id)
    error, artifact_dir = original.error_message, original.artifact_dir

    assert recover_required_sections(db, batch_id, limit=20, debug_root=tmp_path) == [request_id]
    assert (
        recover_required_sections(db, batch_id, limit=20, debug_root=tmp_path, request_id=uuid4())
        == []
    )
    assert recover_required_sections(
        db, batch_id, limit=20, debug_root=tmp_path, request_id=request_id
    ) == [request_id]
    db.expire_all()
    assert db.get(CatastoVisuraRequest, request_id).status == "failed"

    assert recover_required_sections(db, batch_id, limit=20, debug_root=tmp_path, apply=True) == [
        request_id
    ]
    db.expire_all()
    request = db.get(CatastoVisuraRequest, request_id)
    item = db.get(CatastoPerpetualSyncItem, item_id)
    assert (request.status, request.sezione, request.attempts) == ("pending", "D", 1)
    assert (request.error_message, request.artifact_dir) == (error, artifact_dir)
    assert (item.status, item.attempt_count, item.linked_request_id) == ("queued", 1, request_id)
    assert recover_required_sections(db, batch_id, limit=20, debug_root=tmp_path) == []
    assert len(list(db.scalars(select(CatastoVisuraRequest)))) == 2


@pytest.mark.parametrize("limit", [0, 101])
def test_limit_is_bounded(db, tmp_path, limit):
    with pytest.raises(ValueError, match="limit"):
        recover_required_sections(db, uuid4(), limit=limit, debug_root=tmp_path)


def test_batch_and_config_are_required(db, tmp_path):
    with pytest.raises(ValueError, match="processing"):
        recover_required_sections(db, uuid4(), limit=1, debug_root=tmp_path)
    batch_id, _, _ = _seed(db, tmp_path)
    db.query(CatastoRuoloAutoSyncConfig).delete()
    db.commit()
    with pytest.raises(ValueError, match="configuration"):
        recover_required_sections(db, batch_id, limit=1, debug_root=tmp_path)


def test_capacity_and_artifact_checks_skip_candidates(db, tmp_path):
    batch_id, request_id, _ = _seed(db, tmp_path)
    config = db.scalar(select(CatastoRuoloAutoSyncConfig))
    config.batch_size = 1
    db.commit()
    assert recover_required_sections(db, batch_id, limit=1, debug_root=tmp_path) == []
    config.batch_size = 2
    request = db.get(CatastoVisuraRequest, request_id)
    (Path(request.artifact_dir) / "final-failed.html").unlink()
    db.commit()
    assert recover_required_sections(db, batch_id, limit=1, debug_root=tmp_path) == []


def test_database_failure_rolls_back(tmp_path):
    db = MagicMock()
    db.get.side_effect = RuntimeError("database unavailable")
    with pytest.raises(RuntimeError, match="database unavailable"):
        recover_required_sections(db, uuid4(), limit=1, debug_root=tmp_path)
    db.rollback.assert_called_once()


def test_remote_evidence_and_mismatch_fail_closed(db, tmp_path):
    batch_id, request_id, item_id = _seed(db, tmp_path)
    request = db.get(CatastoVisuraRequest, request_id)
    item = db.get(CatastoPerpetualSyncItem, item_id)
    for field, value in (
        ("sister_remote_request_id", "remote"),
        ("sister_remote_request_url", "https://sister/requests"),
        ("sister_remote_state", "pending"),
        ("sister_first_submitted_at", datetime.now(UTC)),
        ("document_id", uuid4()),
        ("execution_token", uuid4()),
        ("last_error_code", "retry_exhausted"),
        ("comune", "Different"),
        ("foglio", "3"),
        ("particella", "355"),
        ("attempts", 3),
        ("error_message", "Different error"),
    ):
        original = getattr(request, field)
        setattr(request, field, value)
        assert not _eligible(request, item, "D", tmp_path)
        setattr(request, field, original)
    assert not _eligible(request, item, "A", tmp_path)
    assert recover_required_sections(db, batch_id, limit=1, debug_root=tmp_path) == [request_id]


def test_section_artifact_must_be_local_and_explicit(db, tmp_path, monkeypatch):
    _, request_id, item_id = _seed(db, tmp_path)
    request = db.get(CatastoVisuraRequest, request_id)
    item = db.get(CatastoPerpetualSyncItem, item_id)
    assert not _has_section_evidence(None, "D", tmp_path)
    assert not _has_section_evidence(request.artifact_dir, "D", tmp_path / "other")
    html_path = Path(request.artifact_dir) / "final-failed.html"
    html_path.write_text('<select name="sezione"><option value="D">D</option></select>')
    assert not _eligible(request, item, "D", tmp_path)
    html_path.write_text("La sezione è obbligatoria")
    assert not _eligible(request, item, "D", tmp_path)
    html_path.write_text(
        'La sezione è obbligatoria<select name="sezione">'
        '<option value="D">D</option><option value="D">D</option></select>'
    )
    assert not _eligible(request, item, "D", tmp_path)
    original_read = Path.read_text

    for error in (OSError("unreadable"), UnicodeError("invalid encoding")):

        def unreadable(path, *args, failure=error, **kwargs):
            if path == html_path:
                raise failure
            return original_read(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", unreadable)
        assert not _has_section_evidence(request.artifact_dir, "D", tmp_path)


def test_cli_dry_run(db, tmp_path, monkeypatch, capsys):
    batch_id, request_id, _ = _seed(db, tmp_path)
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: db)
    monkeypatch.setenv("ELABORAZIONI_DEBUG_ARTIFACTS_PATH", str(tmp_path))
    monkeypatch.setattr(
        sys,
        "argv",
        ["recover_sister_sections", str(batch_id), "--limit", "1", "--request-id", str(request_id)],
    )
    script = Path(__file__).resolve().parents[1] / "app/scripts/recover_sister_sections.py"
    runpy.run_path(str(script), run_name="__main__")
    assert capsys.readouterr().out == f"eligible: 1\n{request_id}\n"
