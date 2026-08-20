from __future__ import annotations

import csv
import json
import runpy
import sys
import uuid
from argparse import Namespace
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.modules.presenze.services import event_summary_export as exporter

from scripts import export_presenze_event_summaries as cli_script


def _collaborator(**overrides):
    values = {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "employee_code": "2110",
        "name": "ACCALAI SANDRO",
        "company_code": "53",
        "company_label": "53 - Consorzio",
        "is_active": True,
        "kint": "10188",
        "kkint": "opaque",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _summary(*, unit: str | None = "3", values: object = None, **overrides):
    payload_values = {
        "spettante": "4,000",
        "residuoprec": "65,000",
        "saldo": "69,000",
        "totale": "69,000",
    } if values is None else values
    attributes = {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "period_start": date(2026, 8, 1),
        "period_end": date(2026, 8, 31),
        "event_code": "10003",
        "description": "Ex Festività",
        "valid_from": date(2026, 1, 1),
        "valid_to": date(2026, 12, 31),
        "unitamisura": unit,
        "owner_user_id": 1,
        "application_user_id": None,
        "source_job_id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
        "created_at": datetime(2026, 8, 19, 10, 0, tzinfo=UTC),
        "updated_at": datetime(2026, 8, 19, 11, 0, tzinfo=UTC),
        "raw_payload_json": {"values": payload_values},
    }
    attributes.update(overrides)
    return SimpleNamespace(**attributes)


def test_build_export_row_keeps_day_values_exact_and_includes_audit_data() -> None:
    row = exporter.build_export_row(
        _collaborator(),
        _summary(values={"spettante": "4,000", "richiesto": "0,462", "saldo": "69,000"}),
    )

    assert row["description"] == "Ex Festività"
    assert row["unit_label"] == "giorni"
    assert row["spettante_raw"] == "4,000"
    assert row["spettante_days"] == "4.000"
    assert row["spettante_minutes"] == ""
    assert row["richiesto_days"] == "0.462"
    assert row["source_job_id"] == "00000000-0000-0000-0000-000000000003"
    assert json.loads(row["raw_payload_json"])["values"]["richiesto"] == "0,462"


def test_build_export_row_converts_hour_values_and_negative_durations() -> None:
    row = exporter.build_export_row(
        _collaborator(),
        _summary(
            unit="2",
            values={"spettante": "38:00", "saldo": "33:19", "totale": "-13:58"},
            valid_from=None,
            valid_to=None,
            source_job_id=None,
            created_at=None,
            updated_at=None,
        ),
    )

    assert row["unit_label"] == "ore"
    assert row["spettante_minutes"] == 2280
    assert row["saldo_minutes"] == 1999
    assert row["totale_minutes"] == -838
    assert row["spettante_days"] == ""
    assert row["valid_from"] == ""
    assert row["source_job_id"] == ""


def test_unknown_or_malformed_values_remain_available_as_raw_text() -> None:
    malformed = exporter.build_export_row(
        _collaborator(),
        _summary(unit="3", values={"saldo": "non numerico"}, raw_payload_json={"values": {"saldo": "non numerico"}}),
    )
    missing = exporter.build_export_row(
        _collaborator(),
        _summary(unit=None, values={}, raw_payload_json=[]),
    )

    assert malformed["saldo_raw"] == "non numerico"
    assert malformed["saldo_days"] == ""
    assert missing["unit_label"] == "non specificata"
    assert missing["saldo_raw"] == ""
    assert exporter._decimal_days("1.500,900") == "1500.900"


def test_write_export_csv_writes_bom_header_and_every_record(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "summary.csv"
    records = [
        (_collaborator(), _summary()),
        (_collaborator(employee_code="2111", name="ATZORI SANDRO"), _summary(unit="2", values={"saldo": "02:12"})),
    ]

    count = exporter.write_export_csv(output, records)

    assert count == 2
    assert output.read_bytes().startswith(b"\xef\xbb\xbf")
    with output.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["description"] == "Ex Festività"
    assert rows[1]["employee_code"] == "2111"
    assert rows[1]["saldo_minutes"] == "132"
    assert tuple(rows[0]) == tuple(exporter.export_fieldnames())


class _FakeExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        return _FakeExecuteResult(self.rows)


def test_load_export_records_applies_all_optional_filters() -> None:
    expected = [(_collaborator(), _summary())]
    db = _FakeSession(expected)

    result = exporter.load_export_records(
        db,
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        employee_codes=["2110"],
        active_only=True,
    )

    assert result == expected
    sql = str(db.statement)
    assert "period_start" in sql
    assert "period_end" in sql
    assert "employee_code" in sql
    assert "is_active" in sql


def test_load_export_records_supports_unfiltered_full_export() -> None:
    db = _FakeSession([])
    assert exporter.load_export_records(db) == []
    assert "WHERE" not in str(db.statement)


def test_cli_helpers_and_custom_database_session(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    args = exporter.parse_args(
        [
            "--output",
            "result.csv",
            "--db-url",
            "sqlite://",
            "--period-start",
            "2026-08-01",
            "--period-end",
            "2026-08-31",
            "--employee-code",
            "2110",
            "--active-only",
        ]
    )
    session_factory, engine = exporter.build_session_factory(args.db_url)
    try:
        assert callable(session_factory)
    finally:
        engine.dispose()

    assert exporter.parse_iso_date(args.period_start) == date(2026, 8, 1)
    assert exporter.parse_iso_date(None) is None
    assert exporter.default_export_filename(datetime(2026, 8, 19, 12, 34, 56, tzinfo=UTC)).endswith("20260819_123456.csv")
    default_session_factory, default_engine = exporter.build_session_factory(None)
    assert callable(default_session_factory)
    assert default_engine is None

    monkeypatch.setattr(exporter, "run_export", lambda parsed: (Path("/tmp/result.csv"), 12))
    assert exporter.main([]) == 0
    assert "Esportate 12 righe" in capsys.readouterr().out


def test_run_export_closes_custom_engine_and_writes_records(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class ContextSession:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    engine = SimpleNamespace(disposed=False)
    engine.dispose = lambda: setattr(engine, "disposed", True)
    session = ContextSession()
    monkeypatch.setattr(exporter, "build_session_factory", lambda _url: (lambda: session, engine))
    monkeypatch.setattr(exporter, "load_export_records", lambda *_args, **_kwargs: [(_collaborator(), _summary())])
    output = tmp_path / "export.csv"
    args = Namespace(
        output=str(output),
        db_url="postgresql://example",
        period_start="2026-08-01",
        period_end="2026-08-31",
        employee_codes=["2110"],
        active_only=True,
    )

    resolved, count = exporter.run_export(args)

    assert resolved == output.resolve()
    assert count == 1
    assert engine.disposed is True


def test_cli_script_bootstraps_backend_path_and_runs_main(monkeypatch: pytest.MonkeyPatch) -> None:
    backend_root = str(Path(cli_script.__file__).resolve().parents[1])
    original_path = list(sys.path)
    monkeypatch.setattr(exporter, "main", lambda: 7)
    try:
        sys.path[:] = [item for item in sys.path if str(Path(item or ".").resolve()) != backend_root]
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(cli_script.__file__, run_name="__main__")
    finally:
        sys.path[:] = original_path
    assert exc_info.value.code == 7
