from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import chain

from bs4 import BeautifulSoup, Tag

from app.modules.elaborazioni.bonifica_oristanese.apps.client import BonificaDatatableClient
from app.modules.elaborazioni.bonifica_oristanese.apps.registry import get_bonifica_app
from app.modules.elaborazioni.bonifica_oristanese.parsers import clean_html_text, extract_href_id
from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSessionManager

ORG_AREA_APP = get_bonifica_app("organizational_chart_areas")
ORG_USER_APP = get_bonifica_app("organizational_chart_users")


def _entry_role(field_name: str) -> str:
    normalized = field_name.replace("[]", "").replace("_", " ").replace("-", " ").strip()
    return normalized or "entry"


def _parse_numeric(value: str | None) -> int | None:
    if not value:
        return None
    value = value.strip()
    return int(value) if value.isdigit() else None


_DATASOURCE_RE = re.compile(r"datasource\s*=\s*(\{.*?\});", re.DOTALL)


def _extract_datasource_entries(html: str, chart_type: str) -> list[BonificaOrgChartEntryRow]:
    match = _DATASOURCE_RE.search(html)
    if match is None:
        return []

    try:
        datasource = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    entries: list[BonificaOrgChartEntryRow] = []

    def walk(node: dict, *, parent_wc_id: int | None, depth: int) -> None:
        wc_id = node.get("id")
        if not isinstance(wc_id, int):
            return
        label = clean_html_text(node.get("name"))
        role = clean_html_text(node.get("title"))
        source_parts = ["datasource_node", f"chart={chart_type}", f"depth={depth}"]
        if parent_wc_id is not None:
            source_parts.append(f"parent={parent_wc_id}")
        entries.append(
            BonificaOrgChartEntryRow(
                wc_id=wc_id,
                label=label or None,
                role=role or None,
                operator_wc_id=wc_id if chart_type == "user" else None,
                area_wc_id=wc_id if chart_type == "area" else None,
                source_field="|".join(source_parts),
                sort_order=len(entries),
            )
        )
        for child in node.get("children") or []:
            if isinstance(child, dict):
                walk(child, parent_wc_id=wc_id, depth=depth + 1)

    walk(datasource, parent_wc_id=None, depth=0)
    return entries


_OPERATOR_TOKENS = ("referent", "user", "employee", "operator")
_ENTRY_TOKENS = (*_OPERATOR_TOKENS, "area")

# (field_name, wc_id, label) candidate read from a form control.
_FormCandidate = tuple[str, int | None, str]


def _field_name(tag: Tag) -> str:
    return (tag.get("name") or "").strip()


def _name_qualifies(field_name: str) -> bool:
    normalized_name = field_name.lower()
    return field_name.endswith("[]") or any(token in normalized_name for token in _ENTRY_TOKENS)


def _input_is_submitted(field: Tag) -> bool:
    input_type = (field.get("type") or "").lower()
    if input_type == "hidden":
        return True
    return input_type in {"checkbox", "radio"} and field.has_attr("checked")


def _input_label(soup: BeautifulSoup, field: Tag) -> str:
    field_id = field.get("id")
    if field_id:
        explicit_label = soup.find("label", attrs={"for": field_id})
        if explicit_label is not None:
            label = clean_html_text(explicit_label.get_text())
            if label:
                return label
    parent_label = field.find_parent("label")
    if parent_label is not None:
        label = clean_html_text(parent_label.get_text())
        if label:
            return label
    return clean_html_text(field.get("data-label") or field.get("title") or "")


def _select_candidates(soup: BeautifulSoup) -> Iterator[_FormCandidate]:
    for select in soup.find_all("select"):
        field_name = _field_name(select)
        if not field_name or not (select.has_attr("multiple") or _name_qualifies(field_name)):
            continue
        for option in select.find_all("option", selected=True):
            wc_id = _parse_numeric(option.get("value"))
            yield field_name, wc_id, clean_html_text(option.get_text())


def _input_candidates(soup: BeautifulSoup) -> Iterator[_FormCandidate]:
    for field in soup.find_all("input"):
        field_name = _field_name(field)
        if not field_name or not _input_is_submitted(field) or not _name_qualifies(field_name):
            continue
        wc_id = _parse_numeric(field.get("value"))
        if wc_id is None:
            continue
        yield field_name, wc_id, _input_label(soup, field)


def _form_entry(
    field_name: str, wc_id: int, label: str, sort_order: int
) -> BonificaOrgChartEntryRow:
    normalized_name = field_name.lower()
    is_operator = any(token in normalized_name for token in _OPERATOR_TOKENS)
    is_area = "area" in normalized_name and "chart" not in normalized_name
    return BonificaOrgChartEntryRow(
        wc_id=wc_id,
        label=label,
        role=_entry_role(field_name),
        operator_wc_id=wc_id if is_operator else None,
        area_wc_id=wc_id if is_area else None,
        source_field=field_name,
        sort_order=sort_order,
    )


def _extract_entries(html: str) -> list[BonificaOrgChartEntryRow]:
    datasource_entries = _extract_datasource_entries(html, chart_type="user")
    if datasource_entries:
        return datasource_entries

    soup = BeautifulSoup(html, "html.parser")
    entries: list[BonificaOrgChartEntryRow] = []
    seen: set[tuple[str, int, str]] = set()

    # Selected options are emitted before submitted inputs; dedupe and sort_order span both.
    for field_name, wc_id, label in chain(_select_candidates(soup), _input_candidates(soup)):
        if wc_id is None or not label:
            continue
        dedupe_key = (field_name, wc_id, label)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        entries.append(_form_entry(field_name, wc_id, label, len(entries)))

    return entries


@dataclass(frozen=True)
class BonificaOrgChartEntryRow:
    wc_id: int
    label: str | None
    role: str | None
    operator_wc_id: int | None
    area_wc_id: int | None
    source_field: str | None
    sort_order: int


@dataclass(frozen=True)
class BonificaOrgChartRow:
    wc_id: int
    chart_type: str
    name: str
    entries: list[BonificaOrgChartEntryRow]


class BonificaOrgChartsClient(BonificaDatatableClient):
    def __init__(self, session_manager: BonificaOristaneseSessionManager) -> None:
        super().__init__(session_manager)

    async def _fetch_chart_rows(self, *, app_key: str, chart_type: str) -> tuple[list[BonificaOrgChartRow], int]:
        app_definition = get_bonifica_app(app_key)
        rows, total = await self.fetch_all_datatable_rows(
            app_definition.list_path,
            columns_count=app_definition.columns_count,
            page_size=100,
        )
        parsed: list[BonificaOrgChartRow] = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 2:
                continue
            wc_id = extract_href_id(row[-1], "/edit/")
            if wc_id is None:
                continue

            html = await self.fetch_detail_html(app_definition.detail_path_template.format(id=wc_id))
            entries = _extract_datasource_entries(html, chart_type=chart_type) or _extract_entries(html)
            parsed.append(
                BonificaOrgChartRow(
                    wc_id=wc_id,
                    chart_type=chart_type,
                    name=clean_html_text(row[0]) or f"Org chart {chart_type} {wc_id}",
                    entries=entries,
                )
            )
        return parsed, total

    async def fetch_org_charts(self) -> tuple[list[BonificaOrgChartRow], int]:
        area_rows, area_total = await self._fetch_chart_rows(
            app_key="organizational_chart_areas",
            chart_type="area",
        )
        user_rows, user_total = await self._fetch_chart_rows(
            app_key="organizational_chart_users",
            chart_type="user",
        )
        return area_rows + user_rows, area_total + user_total
