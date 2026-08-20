from __future__ import annotations

import builtins
from datetime import UTC, datetime, timedelta
from enum import Enum
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from uuid import uuid4

import pandas as pd
import pytest
from pydantic import ValidationError
from sqlalchemy.orm import DeclarativeBase

from app.schemas.catasto import CatastoCredentialTestRequest, CatastoSingleVisuraCreateRequest
import app.services.elaborazioni_batches as batches


class ScalarRows:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeDb:
    def __init__(self, *, scalar_values=(), scalars_values=()) -> None:
        self.scalar_values = list(scalar_values)
        self.scalars_values = list(scalars_values)
        self.commits = 0
        self.refreshes: list[object] = []

    def scalar(self, _statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, _statement):
        values = self.scalars_values.pop(0) if self.scalars_values else []
        return ScalarRows(values)

    def commit(self):
        self.commits += 1

    def refresh(self, value):
        self.refreshes.append(value)


def test_catasto_model_strenum_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    class FreshBase(DeclarativeBase):
        pass

    database_module = ModuleType("app.core.database")
    database_module.Base = FreshBase
    enum_without_strenum = SimpleNamespace(Enum=Enum)
    original_import = builtins.__import__

    def fallback_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "enum" and "StrEnum" in fromlist:
            return enum_without_strenum
        if name == "app.core.database":
            return database_module
        return original_import(name, globals, locals, fromlist, level)

    module_path = Path(__file__).resolve().parents[1] / "app" / "models" / "catasto.py"
    spec = importlib.util.spec_from_file_location("catasto_strenum_fallback", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    monkeypatch.setattr(builtins, "__import__", fallback_import)
    spec.loader.exec_module(module)
    assert issubclass(module.StrEnum, str)
    assert module.CatastoBatchStatus.PENDING.value == "pending"


def test_catasto_credential_test_schema_validator_edges() -> None:
    assert CatastoCredentialTestRequest().credential_id is None
    credential_id = uuid4()
    assert CatastoCredentialTestRequest(credential_id=credential_id).credential_id == credential_id
    with pytest.raises(ValidationError, match="either credential_id"):
        CatastoCredentialTestRequest(
            credential_id=credential_id,
            sister_username="user",
            sister_password="secret",
        )
    with pytest.raises(ValidationError, match="Both sister_username"):
        CatastoCredentialTestRequest(credential_id=credential_id, sister_username="user")


@pytest.mark.parametrize(
    "payload",
    [
        {"search_mode": "soggetto"},
        {"search_mode": "soggetto", "subject_id": "invalid", "subject_kind": "PF"},
        {"search_mode": "soggetto", "subject_id": "ABC", "subject_kind": "PNF"},
        {"search_mode": "unknown"},
        {"search_mode": "immobile"},
    ],
)
def test_single_visura_schema_rejects_invalid_payloads(payload) -> None:
    with pytest.raises(ValidationError):
        CatastoSingleVisuraCreateRequest(**payload)


def test_single_visura_schema_normalizes_subjects_and_immobile() -> None:
    pf = CatastoSingleVisuraCreateRequest(search_mode="soggetto", subject_id=" rssmra80a01h501u ")
    pnf = CatastoSingleVisuraCreateRequest(search_mode="soggetto", subject_id="01234567890")
    explicit = CatastoSingleVisuraCreateRequest(
        search_mode="soggetto",
        subject_id="RSSMRA80A01H501U",
        subject_kind="PF",
    )
    immobile = CatastoSingleVisuraCreateRequest(
        comune="Oristano",
        catasto="Terreni",
        foglio="1",
        particella="2",
    )
    assert (pf.subject_kind, pnf.subject_kind, explicit.subject_kind) == ("PF", "PNF", "PF")
    assert immobile.search_mode == "immobile"


def _request(status, **values):
    defaults = {
        "status": status,
        "error_message": None,
        "current_operation": None,
        "processed_at": None,
        "created_at": datetime.now(UTC),
        "execution_token": None,
        "retry_not_before": None,
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def _batch(status="processing", **values):
    defaults = {
        "id": uuid4(),
        "user_id": 1,
        "status": status,
        "credential_id": None,
        "created_at": datetime.now(UTC),
        "started_at": None,
        "completed_at": None,
        "current_operation": None,
        "failed_items": 0,
        "total_items": 0,
        "completed_items": 0,
        "skipped_items": 0,
        "not_found_items": 0,
        "report_json_path": None,
        "report_md_path": None,
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def test_normalize_released_batches_covers_empty_active_and_released(monkeypatch: pytest.MonkeyPatch) -> None:
    empty = _batch()
    active = _batch()
    unchanged = _batch()
    released = _batch()
    released_request = _request("pending", error_message=batches.RELEASE_REQUESTED_MESSAGE)
    request_map = {
        empty.id: [],
        active.id: [_request("processing")],
        unchanged.id: [_request("pending", error_message="other")],
        released.id: [released_request],
    }
    monkeypatch.setattr(batches, "get_batch_requests", lambda _db, batch_id: request_map[batch_id])
    db = FakeDb(scalars_values=[[empty, active, unchanged, released]])
    assert batches.normalize_released_processing_batches(db) == 1
    assert released.status == "cancelled" and released_request.status == "skipped"
    assert db.commits == 1

    db = FakeDb(scalars_values=[[empty]])
    assert batches.normalize_released_processing_batches(db, user_id=1) == 0
    assert db.commits == 0


class FakeResume:
    def replace(self, **_kwargs):
        return self

    def __le__(self, _other):
        return True

    def __add__(self, _other):
        return self

    def astimezone(self, _zone):
        return datetime(2026, 1, 2, 8, tzinfo=UTC)


class InconsistentLocalNow:
    def __init__(self):
        self.hours = iter((6, 0))

    @property
    def hour(self):
        return next(self.hours)

    def replace(self, **_kwargs):
        return FakeResume()


class InconsistentUtcNow:
    def astimezone(self, _zone):
        return InconsistentLocalNow()


def test_time_and_operation_window_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    assert batches._as_utc(None) is None
    assert batches._as_utc(datetime(2026, 1, 1)).tzinfo is UTC
    assert batches._as_utc(datetime(2026, 1, 1, tzinfo=UTC)).tzinfo is UTC

    monkeypatch.setattr(batches.settings, "elaborazioni_operation_timezone", "invalid")
    monkeypatch.setattr(batches.settings, "elaborazioni_operation_window_enabled", False)
    disabled = batches._get_operation_window_snapshot(datetime(2026, 1, 1, tzinfo=UTC))
    assert not disabled["enabled"] and disabled["timezone"] == "Europe/Rome"

    monkeypatch.setattr(batches.settings, "elaborazioni_operation_timezone", "UTC")
    monkeypatch.setattr(batches.settings, "elaborazioni_operation_window_enabled", True)
    monkeypatch.setattr(batches.settings, "elaborazioni_operation_start_hour", 8)
    monkeypatch.setattr(batches.settings, "elaborazioni_operation_end_hour", 18)
    assert batches._get_operation_window_snapshot(datetime(2026, 1, 1, 12, tzinfo=UTC))["is_within_window"]
    assert not batches._get_operation_window_snapshot(datetime(2026, 1, 1, 20, tzinfo=UTC))["is_within_window"]

    monkeypatch.setattr(batches.settings, "elaborazioni_operation_start_hour", 22)
    monkeypatch.setattr(batches.settings, "elaborazioni_operation_end_hour", 5)
    assert batches._get_operation_window_snapshot(datetime(2026, 1, 1, 23, tzinfo=UTC))["is_within_window"]

    monkeypatch.setattr(batches.settings, "elaborazioni_operation_start_hour", 8)
    monkeypatch.setattr(batches.settings, "elaborazioni_operation_end_hour", 18)
    snapshot = batches._get_operation_window_snapshot(InconsistentUtcNow())
    assert not snapshot["is_within_window"]


def test_upload_parsing_and_normalization_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    assert batches.clean_cell(123) == "123"
    assert batches.infer_subject_kind("ABC") == "PF"
    assert batches.infer_subject_kind("123") == "PNF"
    assert batches._normalize_tipo_visura("") == "Sintetica"
    assert batches._normalize_subject_kind("persona giuridica", "") == "PNF"
    assert batches._normalize_subject_kind("persona fisica", "") == "PF"

    with pytest.raises(batches.BatchValidationError, match="Unsupported"):
        batches.load_upload_records("rows.txt", b"x")
    with pytest.raises(batches.BatchValidationError, match="empty"):
        batches.load_upload_records("rows.csv", b"")
    with pytest.raises(batches.BatchValidationError, match="does not contain"):
        batches.load_upload_records("rows.csv", b"comune\n")
    with pytest.raises(batches.BatchValidationError, match="Duplicate"):
        batches.load_upload_records("rows.csv", b"Comune,Citta\nOristano,Oristano\n")

    monkeypatch.setattr(batches.pd, "read_excel", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad")))
    with pytest.raises(batches.BatchValidationError, match="could not be parsed"):
        batches.load_upload_records("rows.xlsx", b"bad")


def test_validate_records_missing_subject_and_invalid_immobile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(batches, "get_catasto_comuni_lookup", lambda _db: {})
    monkeypatch.setattr(batches, "_build_comune_code_lookup", lambda _db: {})
    monkeypatch.setattr(batches, "_normalize_subject_kind", lambda *_args: "UNKNOWN")
    records = [
        {"search_mode": "soggetto", "subject_id": ""},
        {
            "search_mode": "immobile",
            "comune": "missing",
            "catasto": "bad",
            "foglio": "x",
            "particella": "x",
            "subalterno": "x",
            "tipo_visura": "bad",
        },
        {"search_mode": "immobile"},
    ]
    with pytest.raises(batches.BatchValidationError) as exc_info:
        batches.validate_visure_records(FakeDb(), records)
    errors = exc_info.value.errors
    assert len(errors) == 3
    assert any("subject_id" in message for message in errors[0]["errors"])


def test_validate_record_resolves_comune_by_code(monkeypatch: pytest.MonkeyPatch) -> None:
    comune = SimpleNamespace(nome="Oristano", codice_sister="G113#ORISTANO")
    monkeypatch.setattr(batches, "get_catasto_comuni_lookup", lambda _db: {})
    monkeypatch.setattr(batches, "_build_comune_code_lookup", lambda _db: {"G113": comune})
    rows = batches.validate_visure_records(
        FakeDb(),
        [{"comune": "G113", "catasto": "Terreni", "foglio": "1", "particella": "2"}],
    )
    assert rows[0].comune == "Oristano"


def test_create_single_subject_batch_name(monkeypatch: pytest.MonkeyPatch) -> None:
    row = batches.ValidatedVisuraRow(
        row_index=1,
        search_mode="soggetto",
        comune=None,
        comune_codice=None,
        catasto=None,
        sezione=None,
        foglio=None,
        particella=None,
        subalterno=None,
        tipo_visura="Sintetica",
        subject_kind=None,
        subject_id="ABC",
    )
    created = _batch("pending")
    names: list[str] = []
    monkeypatch.setattr(batches, "validate_visure_records", lambda *_args: [row])
    monkeypatch.setattr(
        batches,
        "create_batch_from_validated_rows",
        lambda _db, _user, _rows, name, *_args, **_kwargs: (names.append(name) or created, []),
    )
    monkeypatch.setattr(batches, "start_batch", lambda _db, _user, _id: created)
    payload = SimpleNamespace(model_dump=lambda: {})
    assert batches.create_single_visura_batch(FakeDb(), 1, payload) is created
    assert names == ["Visura soggetto PF ABC"]


def test_expiration_query_and_lookup_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    no_reference = _batch("pending", created_at=None)
    old = _batch("pending", created_at=datetime.now(UTC) - timedelta(days=1))
    nonpending = _request("completed")
    monkeypatch.setattr(batches, "normalize_released_processing_batches", lambda *_args: 0)
    monkeypatch.setattr(batches, "get_batch_requests", lambda _db, batch_id: [nonpending] if batch_id == old.id else [])
    db = FakeDb(scalars_values=[[no_reference, old]])
    assert batches.expire_stale_pending_batches(db) == 1
    assert old.status == "failed" and nonpending.status == "completed"

    monkeypatch.setattr(batches, "expire_stale_pending_batches", lambda *_args: 0)
    db = FakeDb(scalars_values=[[]])
    assert batches.list_batches_for_user(db, 1, status="failed") == []
    with pytest.raises(batches.BatchNotFoundError):
        batches.get_batch_for_user(FakeDb(scalar_values=[None]), 1, uuid4())
    with pytest.raises(batches.RequestNotFoundError):
        batches.get_request_for_user(FakeDb(scalar_values=[None]), 1, uuid4())
    with pytest.raises(batches.BatchConflictError):
        batches.ensure_no_processing_batch(FakeDb(scalar_values=[SimpleNamespace(id=uuid4())]), 1, uuid4())


def test_start_cancel_release_and_retry_conflicts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(batches, "expire_stale_pending_batches", lambda *_args: 0)
    monkeypatch.setattr(batches, "ensure_no_processing_batch", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(batches, "get_batch_requests", lambda *_args: [])

    selected = _batch("pending", credential_id=uuid4())
    monkeypatch.setattr(batches, "get_batch_for_user", lambda *_args: selected)
    monkeypatch.setattr(batches, "get_credential_for_user", lambda *_args: None)
    with pytest.raises(batches.BatchConflictError, match="not active"):
        batches.start_batch(FakeDb(), 1, selected.id)

    unpinned = _batch("pending")
    monkeypatch.setattr(batches, "get_batch_for_user", lambda *_args: unpinned)
    monkeypatch.setattr(
        batches,
        "require_credentials_for_user",
        lambda *_args: (_ for _ in ()).throw(batches.ElaborazioneCredentialNotFoundError("missing")),
    )
    with pytest.raises(batches.BatchConflictError, match="missing"):
        batches.start_batch(FakeDb(), 1, unpinned.id)

    invalid = _batch("completed")
    monkeypatch.setattr(batches, "get_batch_for_user", lambda *_args: invalid)
    monkeypatch.setattr(batches, "require_credentials_for_user", lambda *_args: object())
    with pytest.raises(batches.BatchConflictError, match="cannot be started"):
        batches.start_batch(FakeDb(), 1, invalid.id)
    with pytest.raises(batches.BatchConflictError, match="cannot be cancelled"):
        batches.cancel_batch(FakeDb(), 1, invalid.id)

    assert batches.release_processing_batches_for_user(FakeDb(scalars_values=[[]]), 1) == (0, [])
    processing = _batch("processing")
    monkeypatch.setattr(batches, "get_batch_for_user", lambda *_args: processing)
    with pytest.raises(batches.BatchConflictError, match="while batch is processing"):
        batches.retry_failed_batch(FakeDb(), 1, processing.id)


def test_runtime_metrics_handles_missing_old_dates_and_timezone_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(UTC)
    requests = [
        _request("pending", created_at=None, processed_at=None),
        _request("completed", created_at=now - timedelta(minutes=1), processed_at=now),
        _request("failed", created_at=now - timedelta(days=9), processed_at=now - timedelta(days=8)),
    ]
    batch_rows = [
        _batch("processing", started_at=None, completed_at=None),
        _batch("completed", started_at=now - timedelta(minutes=5), completed_at=now),
    ]
    monkeypatch.setattr(batches, "list_batches_for_user", lambda *_args: batch_rows)
    monkeypatch.setattr(batches, "sync_batch_counters", lambda *_args: False)
    monkeypatch.setattr(
        batches,
        "_get_operation_window_snapshot",
        lambda _now: {"timezone": "Invalid/Timezone", "enabled": False},
    )
    metrics = batches.get_runtime_metrics_for_user(FakeDb(scalars_values=[requests]), 1)
    assert metrics["totals"]["processed_requests"] == 2
    assert len(metrics["recent_daily"]) == 1


def test_empty_lookup_terminal_requests_and_empty_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    empty_code = SimpleNamespace(codice_sister="")
    monkeypatch.setattr(batches, "get_catasto_comuni_lookup", lambda _db: {"empty": empty_code})
    assert batches._build_comune_code_lookup(FakeDb()) == {}

    monkeypatch.setattr(batches, "expire_stale_pending_batches", lambda *_args: 0)
    cancellable = _batch("failed")
    completed_request = _request("completed")
    monkeypatch.setattr(batches, "get_batch_for_user", lambda *_args: cancellable)
    monkeypatch.setattr(batches, "get_batch_requests", lambda *_args: [completed_request])
    batches.cancel_batch(FakeDb(), 1, cancellable.id)
    assert completed_request.status == "completed"

    processing = _batch("processing")
    db = FakeDb(scalars_values=[[processing]])
    monkeypatch.setattr(batches, "get_batch_requests", lambda *_args: [completed_request])
    count, released_ids = batches.release_processing_batches_for_user(db, 1)
    assert count == 1 and released_ids == [processing.id]
    assert completed_request.status == "completed"

    monkeypatch.setattr(batches, "list_batches_for_user", lambda *_args: [])
    monkeypatch.setattr(
        batches,
        "_get_operation_window_snapshot",
        lambda _now: {"timezone": "UTC", "enabled": False},
    )
    metrics = batches.get_runtime_metrics_for_user(FakeDb(scalars_values=[[]]), 1)
    assert metrics["totals"]["success_rate"] is None
    assert metrics["totals"]["latest_processed_at"] is None
