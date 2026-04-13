from __future__ import annotations

from dataclasses import dataclass

from bs4 import BeautifulSoup

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


def _extract_entries(html: str) -> list["BonificaOrgChartEntryRow"]:
    soup = BeautifulSoup(html, "html.parser")
    entries: list[BonificaOrgChartEntryRow] = []
    seen: set[tuple[str, int, str]] = set()

    for select in soup.find_all("select"):
        field_name = (select.get("name") or "").strip()
        if not field_name:
            continue
        normalized_name = field_name.lower()
        if not (
            select.has_attr("multiple")
            or field_name.endswith("[]")
            or any(token in normalized_name for token in ("referent", "user", "employee", "operator", "area"))
        ):
            continue

        for option in select.find_all("option", selected=True):
            wc_id = _parse_numeric(option.get("value"))
            label = clean_html_text(option.get_text())
            if wc_id is None or not label:
                continue

            operator_wc_id = (
                wc_id if any(token in normalized_name for token in ("referent", "user", "employee", "operator")) else None
            )
            area_wc_id = (
                wc_id if "area" in normalized_name and "chart" not in normalized_name else None
            )
            role = _entry_role(field_name)
            dedupe_key = (field_name, wc_id, label)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            entries.append(
                BonificaOrgChartEntryRow(
                    wc_id=wc_id,
                    label=label,
                    role=role,
                    operator_wc_id=operator_wc_id,
                    area_wc_id=area_wc_id,
                    source_field=field_name,
                    sort_order=len(entries),
                )
            )

    for field in soup.find_all("input"):
        field_name = (field.get("name") or "").strip()
        if not field_name:
            continue
        normalized_name = field_name.lower()
        input_type = (field.get("type") or "").lower()
        if input_type not in {"checkbox", "radio", "hidden"}:
            continue
        if input_type in {"checkbox", "radio"} and not field.has_attr("checked"):
            continue
        if not (
            field_name.endswith("[]")
            or any(token in normalized_name for token in ("referent", "user", "employee", "operator", "area"))
        ):
            continue

        wc_id = _parse_numeric(field.get("value"))
        if wc_id is None:
            continue

        label = ""
        field_id = field.get("id")
        if field_id:
            explicit_label = soup.find("label", attrs={"for": field_id})
            if explicit_label is not None:
                label = clean_html_text(explicit_label.get_text())
        if not label:
            parent_label = field.find_parent("label")
            if parent_label is not None:
                label = clean_html_text(parent_label.get_text())
        if not label:
            label = clean_html_text(field.get("data-label") or field.get("title") or "")
        if not label:
            continue

        operator_wc_id = (
            wc_id if any(token in normalized_name for token in ("referent", "user", "employee", "operator")) else None
        )
        area_wc_id = wc_id if "area" in normalized_name and "chart" not in normalized_name else None
        role = _entry_role(field_name)
        dedupe_key = (field_name, wc_id, label)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        entries.append(
            BonificaOrgChartEntryRow(
                wc_id=wc_id,
                label=label,
                role=role,
                operator_wc_id=operator_wc_id,
                area_wc_id=area_wc_id,
                source_field=field_name,
                sort_order=len(entries),
            )
        )

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
            entries = _extract_entries(html)
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
