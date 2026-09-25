from __future__ import annotations

import asyncio
import json
import runpy
import sys
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from scripts import poste_recover_missing_recipients as recovery


def _checkpoint(tmp_path, *, count=437, details=None):
    path = tmp_path / "job-9-scrape-payload.json"
    path.write_text(json.dumps({"archive_ids": list(range(count)), "details": details or []}))
    return path


def _row(**changes):
    values = {
        "recipient_index": 0,
        "recipient_address": None,
        "avviso_id": None,
        "subject_id": None,
        "recovered_payment_id": None,
        "import_job_id": "source-job",
        "annualita_json": [2026],
        "anomaly_key": "missing_recipient",
        "raw_payload_json": {"raw": {"warning": recovery.PLACEHOLDER_WARNING}},
    }
    values.update(changes)
    return SimpleNamespace(**values)


def _db(rows):
    db = MagicMock()
    db.scalars.return_value.all.return_value = rows
    return db


def test_checkpoint_requires_exact_unique_empty_ids(tmp_path):
    path = _checkpoint(tmp_path)
    ids, digest = recovery._checkpoint_ids(path)
    assert len(ids) == 437 and len(digest) == 64
    for payload in (
        {"archive_ids": [1]},
        {"archive_ids": [1] * 437},
        {"archive_ids": list(range(437)), "details": [{}]},
    ):
        path.write_text(json.dumps(payload))
        with pytest.raises(RuntimeError):
            recovery._checkpoint_ids(path)


def test_private_write_and_preflight_backup(tmp_path, monkeypatch):
    target = tmp_path / "private" / "backup.json"
    recovery._write_private_json(target, {"ok": True})
    assert target.stat().st_mode & 0o777 == 0o600
    assert json.loads(target.read_text()) == {"ok": True}
    target = tmp_path / "private" / "snapshot.json"
    row = _row()
    row.__table__ = SimpleNamespace(columns=[SimpleNamespace(name="anomaly_key")])
    db = _db([row])

    @contextmanager
    def factory():
        yield db

    monkeypatch.setattr(recovery, "EXPECTED_COUNT", 1)
    recovery._prepare_backup(factory, ["42"], target, "digest")
    assert json.loads(target.read_text())["rows"] == [{"anomaly_key": "missing_recipient"}]
    recovery._prepare_backup(factory, ["42"], target, "digest")
    with pytest.raises(RuntimeError, match="incompatibile"):
        recovery._prepare_backup(factory, ["42"], target, "other")


def test_placeholder_rejects_ambiguous_or_linked_rows():
    assert recovery._placeholder(_db([_row()]), "42").anomaly_key == "missing_recipient"
    for rows in ([], [_row(), _row()], [_row(avviso_id="linked")], [_row(recipient_address="via")]):
        with pytest.raises(RuntimeError):
            recovery._placeholder(_db(rows), "42")


def test_validation_and_persistence(monkeypatch):
    detail = {
        "source_shipment_id": "42",
        "recipient_name": "Mario",
        "recipient_address": "Via Roma 1",
        "shipment_name": "raccomandata",
    }
    monkeypatch.setattr(
        recovery, "_parse_posta_online_detail_html", lambda *_args, **_kwargs: [detail]
    )
    assert recovery._validated_rows("42", "html") == [detail]
    monkeypatch.setattr(recovery, "_parse_posta_online_detail_html", lambda *_args, **_kwargs: [])
    with pytest.raises(RuntimeError):
        recovery._validated_rows("42", "html")
    monkeypatch.setattr(
        recovery,
        "_parse_posta_online_detail_html",
        lambda *_args, **_kwargs: [{**detail, "recipient_address": None}],
    )
    with pytest.raises(RuntimeError):
        recovery._validated_rows("42", "html")
    with pytest.raises(RuntimeError, match="indici destinatari inattesi"):
        recovery._persist(None, "42", [detail, detail])

    row = _row()
    db = MagicMock()

    @contextmanager
    def begin():
        yield db

    monkeypatch.setattr(recovery, "_placeholder", lambda *_args: row)
    recovery._persist(SimpleNamespace(begin=begin), "42", [detail])
    assert row.recipient_name == "Mario"
    assert row.recipient_address == "Via Roma 1"
    assert row.anomaly_key == "association_not_evaluated"
    assert row.avviso_id is None


def test_two_recipients_use_one_transaction_without_associations(monkeypatch):
    first = {
        "source_shipment_id": "42",
        "recipient_index": 1,
        "recipient_name": "Mario",
        "recipient_address": "Via Roma 1",
    }
    second = {**first, "recipient_index": 2, "recipient_name": "Luigi"}
    placeholder = _row()
    db = MagicMock()

    @contextmanager
    def begin():
        yield db

    monkeypatch.setattr(recovery, "_placeholder", lambda *_args: placeholder)
    recovery._persist(SimpleNamespace(begin=begin), "42", [first, second])
    inserted = db.add.call_args.args[0]
    assert placeholder.recipient_index == 1
    assert placeholder.recipient_name == "Mario"
    assert inserted.recipient_index == 2
    assert inserted.recipient_name == "Luigi"
    assert inserted.import_job_id == "source-job"
    assert inserted.annualita_json == [2026]
    assert inserted.avviso_id is None


def test_recover_stops_after_two_errors_and_resumes(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    recovery._write_private_json(state_path, {"completed_ids": [], "errors": {}})
    credential = SimpleNamespace(username="user")

    @contextmanager
    def factory():
        yield SimpleNamespace()

    monkeypatch.setattr(recovery, "pick_credential", lambda _db: (credential, "secret"))

    class Client:
        def __init__(self, config):
            assert config.max_retries == 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def login(self, username, password):
            assert (username, password) == ("user", "secret")

        async def fetch_detail_html(self, shipment_id):
            if shipment_id != "1":
                raise RuntimeError("HTTP 500")
            return "html"

    persisted = []
    monkeypatch.setattr(recovery, "PostaOnlineBrowserClient", Client)
    monkeypatch.setattr(recovery, "_validated_rows", lambda *_args: [{"recipient_name": "A"}])
    monkeypatch.setattr(
        recovery, "_persist", lambda _factory, shipment_id, _rows: persisted.append(shipment_id)
    )
    asyncio.run(recovery._recover(factory, ["1", "2", "3", "4"], state_path, 4))
    state = json.loads(state_path.read_text())
    assert persisted == ["1"]
    assert state["completed_ids"] == ["1"]
    assert set(state["errors"]) == {"2", "3"}
    asyncio.run(recovery._recover(factory, ["1", "2", "3"], state_path, 1))
    assert persisted == ["1"]


def test_main_preflight_and_guards(tmp_path, monkeypatch, capsys):
    checkpoint = _checkpoint(tmp_path)
    state_path = tmp_path / "state.json"
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    monkeypatch.setattr(recovery, "create_engine", lambda *_args, **_kwargs: object())
    job = SimpleNamespace(status="cancelled")

    @contextmanager
    def factory():
        yield SimpleNamespace(get=lambda *_args: job)

    monkeypatch.setattr(recovery, "sessionmaker", lambda _engine: factory)
    monkeypatch.setattr(recovery, "_prepare_backup", lambda *_args: None)
    monkeypatch.setattr(
        sys,
        "argv",
        ["tool", "--checkpoint", str(checkpoint), "--state", str(state_path), "--preflight-only"],
    )
    recovery.main()
    assert "Preflight riuscito" in capsys.readouterr().out
    assert json.loads(state_path.read_text())["completed_ids"] == []
    recovery.main()
    state_path.write_text(json.dumps({"source_sha256": "wrong"}))
    with pytest.raises(RuntimeError, match="incompatibile"):
        recovery.main()
    state_path.write_text(json.dumps({"source_sha256": recovery._checkpoint_ids(checkpoint)[1]}))
    monkeypatch.setattr(
        sys, "argv", ["tool", "--checkpoint", str(checkpoint), "--state", str(state_path)]
    )
    monkeypatch.setattr(recovery.asyncio, "run", lambda coroutine: coroutine.close())
    recovery.main()
    job.status = "running"
    with pytest.raises(RuntimeError, match="inattivo"):
        recovery.main()
    monkeypatch.setattr(
        sys,
        "argv",
        ["tool", "--checkpoint", str(checkpoint), "--state", str(state_path), "--limit", "0"],
    )
    with pytest.raises(SystemExit):
        recovery.main()


def test_module_entrypoint_help(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool", "--help"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(recovery.__file__, run_name="__main__")
    assert exc.value.code == 0
