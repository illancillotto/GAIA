from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import audit_ruolo_incass_alignment as _MODULE


class _MappingResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def mappings(self) -> "_MappingResult":
        return self

    def all(self) -> list[dict[str, object]]:
        return self._rows


class _FakeDb:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.closed = False
        self.executed_params: dict[str, object] | None = None

    def execute(self, statement: object, params: dict[str, object]) -> _MappingResult:
        assert statement is _MODULE.ALIGNMENT_SQL
        self.executed_params = params
        return _MappingResult(self.rows)

    def close(self) -> None:
        self.closed = True


def _row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "anno": 2024,
        "incass_source_rows": 10,
        "incass_without_subject": 0,
        "incass_without_detail": 0,
        "incass_without_partite": 2,
        "incass_materializable_rows": 8,
        "ruolo_rows": 8,
        "ruolo_without_partite": 0,
        "materializable_missing_in_ruolo": 0,
        "ruolo_without_source": 0,
    }
    base.update(overrides)
    return base


def test_fetch_alignment_rows_maps_values_and_tracks_drift() -> None:
    db = _FakeDb(
        [
            _row(anno="2023", materializable_missing_in_ruolo="1"),
            _row(anno=2024, ruolo_without_source=None, ruolo_without_partite=0),
        ]
    )

    rows = _MODULE.fetch_alignment_rows(db, from_year=2023, to_year=2024)

    assert db.executed_params == {"from_year": 2023, "to_year": 2024}
    assert rows[0].anno == 2023
    assert rows[0].materializable_missing_in_ruolo == 1
    assert rows[0].has_blocking_drift is True
    assert rows[1].has_blocking_drift is False
    assert "generate_series(CAST(:from_year AS integer), CAST(:to_year AS integer))" in str(_MODULE.ALIGNMENT_SQL)


def test_summary_report_and_json_payload_include_totals() -> None:
    summary = _MODULE.RuoloIncassAlignmentSummary(
        [
            _MODULE.RuoloIncassAlignmentRow.from_mapping(_row(anno=2023, incass_source_rows=3, incass_materializable_rows=2)),
            _MODULE.RuoloIncassAlignmentRow.from_mapping(_row(anno=2024, incass_source_rows=4, incass_materializable_rows=4)),
        ]
    )

    report = _MODULE.format_report(summary)
    payload = summary.as_dict()

    assert "anno | incass | materializzabili" in report
    assert "TOTAL | 7 | 6" in report
    assert "blocking_drift=false" in report
    assert payload["has_blocking_drift"] is False
    assert payload["totals"]["incass_source_rows"] == 7
    assert payload["rows"][0]["anno"] == 2023


def test_parse_args_validates_year_range() -> None:
    args = _MODULE.parse_args(["--from-year", "2024", "--to-year", "2025", "--json", "--fail-on-drift"])

    assert args.from_year == 2024
    assert args.to_year == 2025
    assert args.json is True
    assert args.fail_on_drift is True

    with pytest.raises(SystemExit):
        _MODULE.parse_args(["--from-year", "2025", "--to-year", "2024"])


def test_run_outputs_json_and_fails_on_drift(monkeypatch, capsys) -> None:
    fake_db = _FakeDb([_row(materializable_missing_in_ruolo=2)])
    monkeypatch.setattr(_MODULE, "SessionLocal", lambda: fake_db)

    exit_code = _MODULE.run(["--from-year", "2024", "--to-year", "2024", "--json", "--fail-on-drift"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert fake_db.closed is True
    assert output["has_blocking_drift"] is True
    assert output["totals"]["materializable_missing_in_ruolo"] == 2


def test_run_outputs_text_and_succeeds_without_drift(monkeypatch, capsys) -> None:
    fake_db = _FakeDb([_row()])
    monkeypatch.setattr(_MODULE, "SessionLocal", lambda: fake_db)

    exit_code = _MODULE.run(["--from-year", "2024", "--to-year", "2024"])

    assert exit_code == 0
    assert "blocking_drift=false" in capsys.readouterr().out


def test_main_raises_with_run_exit_code(monkeypatch) -> None:
    monkeypatch.setattr(_MODULE, "run", lambda: 7)

    with pytest.raises(SystemExit) as exc:
        _MODULE.main()

    assert exc.value.code == 7


def test_configure_database_url_for_host_branches(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(_MODULE, "REPO_ROOT", Path("/tmp/gaia-audit-env-that-does-not-exist"))
    _MODULE._configure_database_url_for_host()
    assert "DATABASE_URL" not in _MODULE.os.environ

    monkeypatch.setenv("DATABASE_URL", "not a url")
    _MODULE._configure_database_url_for_host()
    assert _MODULE.os.environ["DATABASE_URL"] == "not a url"

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5433/gaia")
    _MODULE._configure_database_url_for_host()
    assert _MODULE.os.environ["DATABASE_URL"] == "postgresql://user:pass@localhost:5433/gaia"

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@postgres:5432/gaia")

    class DockerPath:
        def __init__(self, value: str) -> None:
            self.value = value

        def exists(self) -> bool:
            return self.value == "/.dockerenv"

    monkeypatch.setattr(_MODULE, "Path", DockerPath)
    _MODULE._configure_database_url_for_host()
    assert _MODULE.os.environ["DATABASE_URL"] == "postgresql://user:pass@postgres:5432/gaia"

    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgresql://user:pass@postgres:5432/gaia\n", encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(_MODULE, "REPO_ROOT", tmp_path)

    class HostPath:
        def __init__(self, value: str) -> None:
            self.value = value

        def exists(self) -> bool:
            return self.value != "/.dockerenv"

        def read_text(self, encoding: str) -> str:
            assert encoding == "utf-8"
            return env_file.read_text(encoding=encoding)

    monkeypatch.setattr(_MODULE, "Path", HostPath)
    _MODULE._configure_database_url_for_host()
    assert "127.0.0.1:5434" in _MODULE.os.environ["DATABASE_URL"]
