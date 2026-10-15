"""Characterization tests for the Bonifica org chart detail parser (R119)."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from app.modules.elaborazioni.bonifica_oristanese.apps.org_charts.client import (
    BonificaOrgChartEntryRow,
    BonificaOrgChartsClient,
    _extract_datasource_entries,
    _extract_entries,
)


def _summary(entries: list[BonificaOrgChartEntryRow]) -> list[tuple[Any, ...]]:
    return [
        (e.wc_id, e.label, e.role, e.operator_wc_id, e.area_wc_id, e.source_field, e.sort_order)
        for e in entries
    ]


def test_select_entries_come_before_input_entries_with_shared_sort_order() -> None:
    html = """
    <form>
      <input type="hidden" name="operators[]" value="7" data-label="Hidden Op">
      <select name="referents[]" multiple>
        <option value="11" selected>Anna</option>
        <option value="12">Not selected</option>
        <option value="13" selected>Bruno</option>
      </select>
      <select name="area_id">
        <option value="21" selected>Area Nord</option>
      </select>
    </form>
    """

    assert _summary(_extract_entries(html)) == [
        (11, "Anna", "referents", 11, None, "referents[]", 0),
        (13, "Bruno", "referents", 13, None, "referents[]", 1),
        (21, "Area Nord", "area id", None, 21, "area_id", 2),
        (7, "Hidden Op", "operators", 7, None, "operators[]", 3),
    ]


def test_select_qualification_requires_name_and_multiple_brackets_or_token() -> None:
    html = """
    <form>
      <select><option value="1" selected>No name</option></select>
      <select name="   "><option value="2" selected>Blank name</option></select>
      <select name="status"><option value="3" selected>Unrelated</option></select>
      <select name="status" multiple><option value="4" selected>Multiple</option></select>
      <select name="tags[]"><option value="5" selected>Brackets</option></select>
      <select name="Employee"><option value="6" selected>Token</option></select>
    </form>
    """

    assert _summary(_extract_entries(html)) == [
        (4, "Multiple", "status", None, None, "status", 0),
        (5, "Brackets", "tags", None, None, "tags[]", 1),
        (6, "Token", "Employee", 6, None, "Employee", 2),
    ]


def test_select_options_need_numeric_value_and_label() -> None:
    html = """
    <form>
      <select name="users[]" multiple>
        <option selected>No value</option>
        <option value="" selected>Empty value</option>
        <option value="abc" selected>Alpha value</option>
        <option value="31" selected>   </option>
        <option value=" 32 " selected>Padded <b>value</b></option>
      </select>
    </form>
    """

    assert _summary(_extract_entries(html)) == [
        (32, "Padded value", "users", 32, None, "users[]", 0),
    ]


def test_input_entries_only_checked_checkbox_radio_or_hidden_with_qualifying_name() -> None:
    html = """
    <form>
      <input type="text" name="users[]" value="1" title="Text">
      <input name="users[]" value="2" title="Untyped">
      <input type="checkbox" name="users[]" value="3" title="Unchecked">
      <input type="CHECKBOX" name="users[]" value="4" title="Checked" checked>
      <input type="radio" name="operator" value="5" title="Radio" checked>
      <input type="radio" name="operator" value="6" title="Radio off">
      <input type="hidden" name="area_ref" value="7" title="Hidden">
      <input type="hidden" name="status" value="8" title="Unrelated" multiple>
      <input type="hidden" value="9" title="No name">
      <input type="hidden" name="  " value="10" title="Blank name">
      <input type="hidden" name="users[]" value="x1" title="Alpha">
      <input type="hidden" name="users[]" title="Missing value">
    </form>
    """

    assert _summary(_extract_entries(html)) == [
        (4, "Checked", "users", 4, None, "users[]", 0),
        (5, "Radio", "operator", 5, None, "operator", 1),
        (7, "Hidden", "area ref", None, 7, "area_ref", 2),
    ]


def test_input_label_resolution_order() -> None:
    html = """
    <form>
      <label for="u1">For label</label>
      <label>Parent label <input id="u1" type="hidden" name="users[]" value="1" title="T1"></label>
      <label for="u2">   </label>
      <label>Parent two <input id="u2" type="hidden" name="users[]" value="2" title="T2"></label>
      <label>Parent three <input id="missing" type="hidden" name="users[]" value="3" title="T3"></label>
      <label><input type="hidden" name="users[]" value="4" data-label="Data four" title="T4"></label>
      <input type="hidden" name="users[]" value="5" data-label="Data five" title="Title five">
      <input type="hidden" name="users[]" value="6" title="Title six">
      <input type="hidden" name="users[]" value="7" data-label="" title="Title seven">
      <input id="u8" type="hidden" name="users[]" value="8">
    </form>
    """

    assert [(e.wc_id, e.label) for e in _extract_entries(html)] == [
        (1, "For label"),
        (2, "Parent two"),
        (3, "Parent three"),
        (4, "Data four"),
        (5, "Data five"),
        (6, "Title six"),
        (7, "Title seven"),
    ]


def test_dedupe_is_shared_across_select_and_input_loops() -> None:
    html = """
    <form>
      <select name="users[]" multiple>
        <option value="1" selected>Anna</option>
      </select>
      <select name="users[]" multiple>
        <option value="1" selected>Anna</option>
        <option value="1" selected>Anna Bis</option>
      </select>
      <input type="hidden" name="users[]" value="1" title="Anna">
      <input type="hidden" name="users[]" value="1" title="Anna Ter">
      <input type="hidden" name="users[]" value="1" title="Anna Ter">
      <input type="hidden" name="operators[]" value="1" title="Anna">
    </form>
    """

    assert _summary(_extract_entries(html)) == [
        (1, "Anna", "users", 1, None, "users[]", 0),
        (1, "Anna Bis", "users", 1, None, "users[]", 1),
        (1, "Anna Ter", "users", 1, None, "users[]", 2),
        (1, "Anna", "operators", 1, None, "operators[]", 3),
    ]


def test_role_and_operator_area_classification() -> None:
    html = """
    <form>
      <select name="employee_area-chart"><option value="1" selected>Select chart</option></select>
      <select name="employee-area"><option value="2" selected>Select both</option></select>
      <select name="[]"><option value="3" selected>Select bare</option></select>
      <input type="hidden" name="area_chart[]" value="4" title="Input chart">
      <input type="hidden" name="referent_area" value="5" title="Input both">
      <input type="hidden" name="[]" value="6" title="Input bare">
    </form>
    """

    assert _summary(_extract_entries(html)) == [
        (1, "Select chart", "employee area chart", 1, None, "employee_area-chart", 0),
        (2, "Select both", "employee area", 2, 2, "employee-area", 1),
        (3, "Select bare", "entry", None, None, "[]", 2),
        (4, "Input chart", "area chart", None, None, "area_chart[]", 3),
        (5, "Input both", "referent area", 5, 5, "referent_area", 4),
        (6, "Input bare", "entry", None, None, "[]", 5),
    ]


def _datasource_html(datasource: object, form: str = "") -> str:
    payload = datasource if isinstance(datasource, str) else json.dumps(datasource)
    return f"<script>var datasource = {payload};</script>{form}"


_FORM = '<input type="hidden" name="users[]" value="99" title="Form user">'


def test_datasource_short_circuits_form_parsing_and_handles_bad_payloads() -> None:
    tree = {
        "id": 1,
        "name": "<b>Root</b>",
        "title": "Boss",
        "children": [
            {"id": 2, "name": "", "title": "", "children": None},
            "skip",
            {"id": "3", "name": "Bad id"},
            {"id": 4, "name": "Leaf", "children": [{"id": 5, "name": "Deep"}]},
        ],
    }

    assert _summary(_extract_entries(_datasource_html(tree, _FORM))) == [
        (1, "Root", "Boss", 1, None, "datasource_node|chart=user|depth=0", 0),
        (2, None, None, 2, None, "datasource_node|chart=user|depth=1|parent=1", 1),
        (4, "Leaf", None, 4, None, "datasource_node|chart=user|depth=1|parent=1", 2),
        (5, "Deep", None, 5, None, "datasource_node|chart=user|depth=2|parent=4", 3),
    ]
    assert _summary(
        _extract_datasource_entries(_datasource_html({"id": 8, "name": "Area"}), "area")
    ) == [
        (8, "Area", None, None, 8, "datasource_node|chart=area|depth=0", 0),
    ]

    form_only = [(99, "Form user", "users", 99, None, "users[]", 0)]
    assert _summary(_extract_entries(_datasource_html("{not json}", _FORM))) == form_only
    assert (
        _summary(_extract_entries(_datasource_html({"id": "1", "name": "Bad root"}, _FORM)))
        == form_only
    )
    assert _summary(_extract_entries(_FORM)) == form_only
    assert _extract_entries("<form></form>") == []


class _DummySessionManager:
    def __init__(
        self, list_payloads: dict[str, dict[str, Any]], detail_pages: dict[str, str]
    ) -> None:
        self.list_payloads = list_payloads
        self.detail_pages = detail_pages
        self.detail_calls: list[str] = []

    def resolve_url(self, path: str) -> str:
        return f"https://bonifica.test{path}"

    def get_http_client(self) -> httpx.AsyncClient:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=self.list_payloads[request.url.path])

        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def fetch_page(self, path: str) -> SimpleNamespace:
        self.detail_calls.append(path)
        return SimpleNamespace(text=self.detail_pages[path])


def test_client_fetch_org_charts_parses_area_and_user_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.core.config.settings.wc_sync_request_delay_ms", 0)
    monkeypatch.setattr("app.core.config.settings.wc_sync_detail_delay_ms", 0)
    session = _DummySessionManager(
        list_payloads={
            "/areas/organizational-charts/list": {
                "recordsTotal": 4,
                "data": [
                    "not-a-row",
                    ["only-one"],
                    ["No link", "<span>none</span>"],
                    ["<b>Aree</b>", '<a href="/areas/organizational-charts/edit/10">Edit</a>'],
                ],
            },
            "/users/organizational-charts/list": {
                "recordsTotal": 1,
                "data": [["", '<a href="/users/organizational-charts/edit/20">Edit</a>']],
            },
        },
        detail_pages={
            "/areas/organizational-charts/edit/10": _datasource_html({"id": 5, "name": "Area Uno"}),
            "/users/organizational-charts/edit/20": _FORM,
        },
    )

    rows, total = asyncio.run(BonificaOrgChartsClient(session).fetch_org_charts())

    assert total == 5
    assert session.detail_calls == [
        "/areas/organizational-charts/edit/10",
        "/users/organizational-charts/edit/20",
    ]
    assert [(r.wc_id, r.chart_type, r.name) for r in rows] == [
        (10, "area", "Aree"),
        (20, "user", "Org chart user 20"),
    ]
    assert _summary(rows[0].entries) == [
        (5, "Area Uno", None, None, 5, "datasource_node|chart=area|depth=0", 0)
    ]
    assert _summary(rows[1].entries) == [(99, "Form user", "users", 99, None, "users[]", 0)]
