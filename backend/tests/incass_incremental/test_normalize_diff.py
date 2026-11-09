from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook
from pydantic import ValidationError

from app.modules.elaborazioni.capacitas.incremental import diff
from app.modules.elaborazioni.capacitas.incremental import normalize as n
from app.modules.elaborazioni.capacitas.incremental.config import IncrementalSettings
from app.modules.elaborazioni.capacitas.incremental.models import IncrementalCycle, IncrementalHead

from .conftest import NOW, raw_row, workbook


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        (" \u00a0", None),
        ("1.234,50", "1234.50"),
        (1234.5, "1234.50"),
        ("1.234", "1234.00"),
        ("(1.234,50)", "-1234.50"),
        ("€ -12,00", "-12.00"),
        ("-0", "0.00"),
        ("1000.00", "1000.00"),
    ],
)
def test_money(value, expected):
    assert n.money(value) == expected


@pytest.mark.parametrize("value", ["garbage", "NaN", "Infinity", "1,001", "1.2.3", "1e99999"])
def test_invalid_money(value):
    with pytest.raises(n.SnapshotInvalid):
        n.money(value)


@pytest.mark.parametrize(
    "value,expected",
    [
        (date(2026, 11, 9), "2026-11-09"),
        (NOW, "2026-11-09"),
        (datetime(2026, 11, 9, 23, 30, tzinfo=UTC), "2026-11-10"),
        (datetime(2026, 11, 9), "2026-11-09"),
        (None, None),
        ("09/11/2026", "2026-11-09"),
        ("09/11/2026 12:00", "2026-11-09"),
        ("2026-11-09 12:00:00", "2026-11-09"),
        ("2026-11-09", "2026-11-09"),
    ],
)
def test_dates(value, expected):
    assert n.day(value) == expected


def test_invalid_date():
    with pytest.raises(n.SnapshotInvalid, match="invalid_date"):
        n.day("31/02/2026")


@pytest.mark.parametrize(
    "value,field,fmt,expected",
    [
        (12, "ID", "General", "12"),
        (12.0, "ID", "General", "12"),
        (12, "Avviso", "00000", "00012"),
        (123, "CodFisc", "00000000000", "00000000123"),
        (None, "Avviso", "General", None),
        (" 0012 ", "Avviso", "General", "0012"),
        (" abcd ", "CodFisc", "General", "ABCD"),
    ],
)
def test_codes(value, field, fmt, expected):
    assert n.code(value, field, fmt) == expected


@pytest.mark.parametrize(
    "value,field",
    [
        (True, "ID"),
        (1.2, "ID"),
        (10**15, "ID"),
        (12, "Avviso"),
        (12, "CodFisc"),
        (12, "Cap"),
        ("1.2E+12", "Avviso"),
    ],
)
def test_lossy_codes(value, field):
    with pytest.raises(n.SnapshotInvalid):
        n.code(value, field)


def test_semantic_equality_and_hash_order():
    one = raw_row(DataScad="09/11/2026", Denominaz=" SOGGETTO  TEST ")
    two = raw_row(Avviso="020250000000002")
    a, schema = n.decode_workbook(workbook([one, two], footer=True), 2, {})
    one.update(Carico=1000.0, DataScad=datetime(2026, 11, 9), Denominaz="SOGGETTO TEST")
    b, schema2 = n.decode_workbook(
        workbook([two, one], headers=list(reversed(sorted(n.KNOWN)))), 2, {}
    )
    assert a == b and schema == schema2 and n.digest(a) == n.digest(b)
    assert n.canonical_row({**one, "ignored": 1}) == a[one["Avviso"]]
    original = workbook([one, two])
    book = load_workbook(BytesIO(original))
    book.properties.title = "Different metadata, identical notice values"
    book.active.cell(2, 1).number_format = "@"
    changed = BytesIO()
    book.save(changed)
    assert original != changed.getvalue()
    assert n.decode_workbook(changed.getvalue(), 2, {})[0] == a


@pytest.mark.parametrize(
    "kind",
    [
        "zip",
        "empty",
        "sheets",
        "missing",
        "duplicate_header",
        "unknown",
        "formula",
        "error",
        "count",
        "duplicate",
        "key",
        "year",
        "long_key",
        "width",
    ],
)
def test_bad_workbooks(kind):
    content = workbook([raw_row()])
    book = load_workbook(BytesIO(content))
    sheet = book.active
    headers = list(n.KNOWN)
    if kind == "zip":
        content = b"not-a-zip"
    elif kind == "empty":
        sheet.delete_rows(1, 2)
    elif kind == "sheets":
        book.create_sheet()
    elif kind == "missing":
        sheet.cell(1, 1).value = "Unrecognized"
    elif kind == "duplicate_header":
        sheet.cell(1, 2).value = sheet.cell(1, 1).value
    elif kind == "unknown":
        sheet.cell(1, sheet.max_column + 1).value = "Unrecognized"
    elif kind in {"formula", "error"}:
        sheet.cell(2, 1).value = "=1+1" if kind == "formula" else "#VALUE!"
    elif kind == "duplicate":
        sheet.append([c.value for c in sheet[2]])
    elif kind in {"key", "year", "long_key"}:
        field = "Anno" if kind == "year" else "Avviso"
        index = [c.value for c in sheet[1]].index(field) + 1
        sheet.cell(2, index).value = "x" * 129 if kind == "long_key" else None
    elif kind == "width":
        # Dimension mismatch is also checked for workbooks lacking declared dimensions.
        with pytest.raises(n.SnapshotInvalid, match="row_width"):
            n._decode_rows(iter([sheet[2][:-1]]), headers)
        return
    if kind != "zip":
        stream = BytesIO()
        book.save(stream)
        content = stream.getvalue()
    with pytest.raises(n.SnapshotInvalid):
        n.decode_workbook(content, 3 if kind == "count" else 1, {})


def test_header_alias_and_excel_number_format():
    book = load_workbook(BytesIO(workbook([raw_row()])))
    sheet = book.active
    index = sorted(n.KNOWN).index("Avviso") + 1
    sheet.cell(1, index).value = "Numero Avviso"
    sheet.cell(2, index).value = 123
    sheet.cell(2, index).number_format = "000000"
    stream = BytesIO()
    book.save(stream)
    rows, _ = n.decode_workbook(stream.getvalue(), 1, {"Numero Avviso": "Avviso"})
    assert "000123" in rows


@pytest.mark.parametrize(
    "changes,kind,action",
    [
        ({}, "unchanged", "none"),
        ({"Riscosso": "10.00"}, "changed", "summary"),
        ({"StatoPag": "1"}, "changed", "summary"),
        ({"IDLista": "2"}, "changed", "summary"),
        ({"Carico": "99.00"}, "changed", "recover"),
        ({"Sgravio": "99.00"}, "changed", "recover"),
        ({"Annullato": "99.00"}, "changed", "recover"),
        ({"Rateizzato": "99.00"}, "changed", "recover"),
        ({"CodFisc": "OTHER"}, "ambiguous", "review"),
        ({"Anno": "9926"}, "ambiguous", "review"),
    ],
)
def test_classification(changes, kind, action):
    before = n.canonical_row(raw_row())
    after = {**before, **changes}
    result = diff.classify(before, after)
    assert result[:2] == (kind, action)
    for field, value in changes.items():
        assert result[2][field] == [before[field], value]
    assert diff.classify(None, after) == ("new", "recover", {})
    assert diff.classify(before, None) == ("missing", "review", {})


def test_settings_slots_and_active_guards(monkeypatch):
    monkeypatch.setenv("INCASS_INCREMENTAL_MODE", "off")
    assert IncrementalSettings().mode == "off"
    with pytest.raises(ValidationError):
        IncrementalSettings(mode="shadow")
    with pytest.raises(ValidationError):
        IncrementalSettings(mode="active", credential_id=1)
    with pytest.raises(ValidationError, match="bootstrap_keys"):
        IncrementalSettings(max_jobs=1, bootstrap_keys={"a", "b"})
    config = IncrementalSettings(
        mode="active",
        credential_id=1,
        schema_verified=True,
        coverage_verified=True,
        sample_size=2,
        full_audit_days=7,
    )
    assert config.slot(NOW).hour == 7
    assert config.slot(NOW.replace(hour=0)).date() == (NOW - timedelta(days=1)).date()
    # Both DST transition days still identify the correct Europe/Rome daily slot.
    assert config.slot(datetime(2026, 3, 29, 9, tzinfo=UTC)).utcoffset() == timedelta(hours=2)
    assert config.slot(datetime(2026, 10, 25, 9, tzinfo=UTC)).utcoffset() == timedelta(hours=1)


def artifact(rows, schema=None):
    return {"rows": rows, "schema": schema or ["x"], "drive_id": "file"}


def test_collection_and_plan_guards(config):
    row = n.canonical_row(raw_row())
    key = row["Avviso"]
    art = {"2025": artifact({key: row})}
    old = SimpleNamespace(rows={key: row}, expected=["2025"], artifacts=art)
    assert diff.validate_collection(art, ["2025"], old, config) == old.rows
    for artifacts, expected in [
        ({}, []),
        ({}, ["2025"]),
        ({"2025": artifact({})}, ["2025"]),
        ({"2025": {**artifact({key: row}), "drive_id": None}}, ["2025"]),
        ({"2025": artifact({key: row}, ["different"])}, ["2025"]),
        ({"9926": artifact({key: row})}, ["9926"]),
        ({"2025": artifact({key: row}), "2026": artifact({key: row})}, ["2025", "2026"]),
    ]:
        with pytest.raises(n.SnapshotInvalid):
            diff.validate_collection(artifacts, expected, old, config)
    config.empty_years = {"2025"}
    with pytest.raises(n.SnapshotInvalid, match="unexpected_empty"):
        diff.validate_collection({"2025": artifact({})}, ["2025"], old, config)
    assert diff.validate_collection({"2025": artifact({})}, ["2025"], None, config) == {}
    # A changed scope that is empty and explicitly permitted still cannot silently shrink.
    config.empty_years.add("2026")
    with pytest.raises(n.SnapshotInvalid, match="scope_changed"):
        diff.validate_collection(
            {"2025": artifact({key: row}), "2026": artifact({})},
            ["2025", "2026"],
            SimpleNamespace(
                rows=old.rows,
                expected=["2025", "2026", "9926"],
                artifacts={**art, "2026": artifact({})},
            ),
            config,
        )
    config.missing_fraction = 0
    with pytest.raises(n.SnapshotInvalid, match="missing_fraction"):
        diff.validate_collection({"2025": artifact({"other": row})}, ["2025"], old, config)
    with pytest.raises(n.SnapshotInvalid, match="cross_year"):
        diff.validate_collection(
            {"2025": artifact({key: row}), "2026": artifact({key: row})},
            ["2025", "2026"],
            None,
            config,
        )
    cycle = IncrementalCycle(id="c", mode="shadow", rows={key: row})
    head = IncrementalHead(id=1, full_audit_at=NOW)
    assert diff.make_plan(cycle, None, head, config, NOW)[0] == []
    assert diff.make_plan(cycle, old, head, config, NOW)[0] == []
    config.sample_size = 1
    jobs, _report = diff.make_plan(cycle, old, head, config, NOW)
    assert jobs[0].action == "audit" and jobs[0].status == "shadow"
    config.full_audit_days = 1
    cycle.mode = "active"
    assert diff.make_plan(cycle, old, head, config, NOW + timedelta(days=2))[1]["full_audit"]
    config.bootstrap_keys = {key}
    assert diff.make_plan(cycle, None, head, config, NOW)[0][0].fields == {
        "bootstrap": [None, "explicit_allowlist"]
    }
    assert diff.make_plan(cycle, old, head, config, NOW)[0][0].kind == "new"
    cycle.mode = "shadow"
    assert diff.make_plan(cycle, None, head, config, NOW)[0][0].status == "shadow"
    config.bootstrap_keys = {"not-in-snapshot"}
    with pytest.raises(n.SnapshotInvalid, match="bootstrap_notice"):
        diff.make_plan(cycle, old, head, config, NOW)
