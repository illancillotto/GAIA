from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pytest
from openpyxl import Workbook

from app.modules.ruolo.services import notice_import_step as step
from app.modules.ruolo.services.notice_import_step import PARSER_VERSION, parse_report


def _xlsx() -> bytes:
    stream = BytesIO()
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Practice", "State", "Event"])
    sheet.append(["P-001", "ACTIVE", "E-001"])
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def test_parse_step_xlsx_requires_explicit_mapping_and_preserves_original():
    snapshot = parse_report(
        _xlsx(),
        filename="step.xlsx",
        mapping={"practice_id": "Practice", "status": "State", "event_id": "Event"},
    )
    assert snapshot.summary == {"filename": "step.xlsx", "parser_version": PARSER_VERSION, "rows": 1, "unlinked_rows": 1}
    assert snapshot.rows[0]["source_key"] == "E-001"
    assert snapshot.rows[0]["payload"]["original"] == {"Practice": "P-001", "State": "ACTIVE", "Event": "E-001"}
    assert snapshot.rows[0]["anomalies"] == ["step_da_verificare"]


def test_parse_step_csv_rejects_missing_contract_mapping():
    with pytest.raises(ValueError, match="Mapping STEP obbligatorio"):
        parse_report(b"Practice,State\nP-001,ACTIVE\n", filename="step.csv", mapping={"practice_id": "Practice"})


def test_parse_step_rejects_unknown_format():
    with pytest.raises(ValueError, match="Formato STEP"):
        parse_report(b"x", filename="step.pdf", mapping={"practice_id": "Practice", "status": "State"})


def test_parse_step_csv_and_missing_values_are_anomalies():
    snapshot = parse_report(
        b"Practice,State,When\n, ,2024-01-02\n",
        filename="step.csv",
        mapping={"practice_id": "Practice", "status": "State", "event_date": "When"},
    )
    assert snapshot.rows[0]["anomalies"] == [
        "step_da_verificare",
        "pratica_step_assente",
        "stato_step_assente",
    ]


def test_parse_step_rejects_empty_csv_and_invalid_utf8():
    with pytest.raises(ValueError, match="Intestazione CSV"):
        parse_report(b"\n", filename="step.csv", mapping={"practice_id": "P", "status": "S"})
    with pytest.raises(ValueError, match="UTF-8"):
        parse_report(b"Header\n\xff", filename="step.csv", mapping={"practice_id": "P", "status": "S"})


def test_parse_step_rejects_empty_report_and_size_limit(monkeypatch):
    monkeypatch.setattr(step, "MAX_BYTES", 0)
    with pytest.raises(ValueError, match="12 MiB"):
        parse_report(b"x", filename="step.csv", mapping={"practice_id": "P", "status": "S"})
    monkeypatch.setattr(step, "MAX_BYTES", 12 * 1024 * 1024)
    with pytest.raises(ValueError, match="Report STEP vuoto"):
        parse_report(b"Practice,State\n", filename="step.csv", mapping={"practice_id": "Practice", "status": "State"})
    monkeypatch.setattr(step, "MAX_ROWS", 0)
    with pytest.raises(ValueError, match="oltre il limite"):
        parse_report(b"Practice,State\nP,S\n", filename="step.csv", mapping={"practice_id": "Practice", "status": "State"})


def test_parse_step_rejects_invalid_xlsx_and_bad_headers():
    with pytest.raises(ValueError, match="non valida"):
        parse_report(b"not-xlsx", filename="step.xlsx", mapping={"practice_id": "P", "status": "S"})
    stream = BytesIO()
    workbook = Workbook()
    workbook.active.append(["Practice", None])
    workbook.save(stream)
    workbook.close()
    with pytest.raises(ValueError, match="Intestazione Excel"):
        parse_report(stream.getvalue(), filename="step.xlsx", mapping={"practice_id": "Practice", "status": "State"})


def test_parse_step_json_serializes_dates_and_rejects_decompressed_archive(monkeypatch):
    class Item:
        file_size = 65 * 1024 * 1024

    class Archive:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def infolist(self):
            return [Item()]

    monkeypatch.setattr(step, "ZipFile", lambda *_args, **_kwargs: Archive())
    with pytest.raises(ValueError, match="64 MiB"):
        parse_report(b"x", filename="step.xlsx", mapping={"practice_id": "P", "status": "S"})
    snapshot = parse_report(
        b"Practice,State,When\nP,S,2024-01-02\n",
        filename="step.csv",
        mapping={"practice_id": "Practice", "status": "State", "event_date": "When"},
    )
    assert snapshot.rows[0]["payload"]["event_date"] == "2024-01-02"
    assert step._jsonable(datetime(2024, 1, 2)) == "2024-01-02T00:00:00"
