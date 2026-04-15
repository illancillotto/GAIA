from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import logging
from typing import Any

from bs4 import BeautifulSoup
import httpx

from app.modules.elaborazioni.bonifica_oristanese.apps.client import BonificaDatatableClient
from app.modules.elaborazioni.bonifica_oristanese.apps.registry import get_bonifica_app
from app.modules.elaborazioni.bonifica_oristanese.parsers import (
    clean_html_text,
    extract_href_id,
    parse_form_fields,
)
from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSessionManager


REFUELS_APP = get_bonifica_app("refuels")
logger = logging.getLogger(__name__)


def _to_int(value: str | None) -> int | None:
    if not value:
        return None
    digits = "".join(char for char in value if char.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


@dataclass(frozen=True)
class BonificaRefuelRow:
    wc_id: int
    vehicle_code: str | None
    operator_name: str | None
    fueled_at_text: str | None
    odometer_km: int | None
    liters: Decimal | None
    total_cost: Decimal | None
    station_name: str | None
    source_issue: str | None = None


@dataclass(frozen=True)
class BonificaVehicleSearchResult:
    vehicle_filter_id: int
    vehicle_code: str


def _to_decimal(value: str | bool | list[str] | None) -> Decimal | None:
    if isinstance(value, bool) or isinstance(value, list) or value is None:
        return None
    normalized = value.strip().replace(",", ".")
    if not normalized:
        return None
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _first_decimal(fields: dict[str, str | list[str] | bool], candidates: tuple[str, ...]) -> Decimal | None:
    for key in candidates:
        value = _to_decimal(fields.get(key))
        if value is not None:
            return value
    return None


def _first_text(fields: dict[str, str | list[str] | bool], candidates: tuple[str, ...]) -> str | None:
    for key in candidates:
        raw_value = fields.get(key)
        if isinstance(raw_value, bool) or isinstance(raw_value, list) or raw_value is None:
            continue
        value = clean_html_text(raw_value)
        if value:
            return value
    return None


def _field_value_from_container(container) -> str | None:
    for selector in ("input", "select", "textarea"):
        field = container.find(selector)
        if field is None:
            continue
        if field.name == "textarea":
            value = field.get_text(strip=False).strip()
            return value or None
        if field.name == "select":
            selected = field.find("option", selected=True)
            if selected is not None:
                return clean_html_text(selected.get_text()) or selected.get("value") or None
            first_option = field.find("option")
            if first_option is not None:
                return clean_html_text(first_option.get_text()) or first_option.get("value") or None
            continue
        value = field.get("value")
        if value:
            return value
        placeholder = field.get("placeholder")
        if placeholder:
            return placeholder

    text = clean_html_text(container.get_text(" ", strip=True))
    return text or None


def _extract_labeled_values(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    result: dict[str, str] = {}

    for label in soup.find_all("label"):
        label_text = clean_html_text(label.get_text())
        if not label_text:
            continue

        target_field = None
        target_id = label.get("for")
        if target_id:
            target_field = soup.find(id=target_id)
        if target_field is None:
            target_field = label.find_next(["input", "select", "textarea"])
        if target_field is None:
            continue

        value = None
        if target_field.name == "textarea":
            value = target_field.get_text(strip=False).strip()
        elif target_field.name == "select":
            selected = target_field.find("option", selected=True)
            value = clean_html_text(selected.get_text()) if selected else ""
        else:
            value = target_field.get("value") or target_field.get("placeholder") or ""

        value = clean_html_text(value)
        if value:
            result[label_text.lower()] = value

    for row in soup.select("tr"):
        header = row.find(["th", "td"])
        cells = row.find_all(["td", "th"])
        if len(cells) < 2 or header is None:
            continue
        label_text = clean_html_text(header.get_text())
        if not label_text:
            continue
        value = _field_value_from_container(cells[-1])
        if value:
            result.setdefault(label_text.lower(), value)

    return result


def _first_decimal_from_labels(labeled_values: dict[str, str], candidates: tuple[str, ...]) -> Decimal | None:
    for label, value in labeled_values.items():
        if any(candidate in label for candidate in candidates):
            parsed = _to_decimal(value)
            if parsed is not None:
                return parsed
    return None


def _first_text_from_labels(labeled_values: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for label, value in labeled_values.items():
        if any(candidate in label for candidate in candidates):
            cleaned = clean_html_text(value)
            if cleaned:
                return cleaned
    return None


class BonificaRefuelsClient(BonificaDatatableClient):
    def __init__(self, session_manager: BonificaOristaneseSessionManager) -> None:
        super().__init__(session_manager)

    async def _search_vehicle(self, vehicle_code: str) -> BonificaVehicleSearchResult | None:
        response = await self.get_http_client().get(
            self.session_manager.resolve_url("/vehicles/search"),
            params={
                "term": vehicle_code,
                "_type": "query",
                "q": vehicle_code,
            },
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []
        normalized_code = clean_html_text(vehicle_code) or vehicle_code

        fallback_match: dict[str, Any] | None = None
        for item in results:
            if not isinstance(item, dict):
                continue
            if item.get("isVehicle") != 1:
                continue
            text = clean_html_text(str(item.get("text") or ""))
            if text and text.upper() == normalized_code.upper():
                filter_id = item.get("id")
                if isinstance(filter_id, int):
                    return BonificaVehicleSearchResult(vehicle_filter_id=filter_id, vehicle_code=text)
            if fallback_match is None:
                fallback_match = item

        if fallback_match is None:
            return None
        filter_id = fallback_match.get("id")
        text = clean_html_text(str(fallback_match.get("text") or normalized_code)) or normalized_code
        if not isinstance(filter_id, int):
            return None
        return BonificaVehicleSearchResult(vehicle_filter_id=filter_id, vehicle_code=text)

    def _parse_refuel_list_rows(self, rows: list[object], *, source_issue: str | None) -> list[BonificaRefuelRow]:
        parsed: list[BonificaRefuelRow] = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 5:
                continue
            wc_id = extract_href_id(row[4], "/vehicles/refuel/edit/")
            if wc_id is None:
                continue
            parsed.append(
                BonificaRefuelRow(
                    wc_id=wc_id,
                    vehicle_code=clean_html_text(row[0]) or None,
                    operator_name=clean_html_text(row[1]) or None,
                    fueled_at_text=clean_html_text(row[2]) or None,
                    odometer_km=_to_int(clean_html_text(row[3])),
                    liters=None,
                    total_cost=None,
                    station_name=None,
                    source_issue=source_issue,
                )
            )
        return parsed

    async def fetch_refuels(
        self,
        *,
        date_from: date,
        date_to: date,
    ) -> tuple[list[BonificaRefuelRow], int]:
        raise NotImplementedError(
            "Usare fetch_refuels_for_vehicle_codes(): la sorgente WhiteCompany richiede "
            "filter_code[] per mezzo e la datatable globale non e una base affidabile per il sync."
        )

    async def fetch_refuels_for_vehicle_codes(
        self,
        *,
        vehicle_codes: list[str],
        date_from: date,
        date_to: date,
    ) -> tuple[list[BonificaRefuelRow], int]:
        parsed: list[BonificaRefuelRow] = []
        seen_wc_ids: set[int] = set()
        total = 0
        source_issue = (
            "Datatable WhiteCompany filtrata per mezzo: disponibili solo mezzo, operatore, data e km; "
            "litri/costo/distributore non sono esposti e il record non e importabile come fuel log completo."
        )

        for vehicle_code in vehicle_codes:
            search_result = await self._search_vehicle(vehicle_code)
            if search_result is None:
                logger.warning(
                    "Bonifica refuels: nessun mezzo White trovato per vehicle_code=%s",
                    vehicle_code,
                )
                continue

            rows, vehicle_total = await self.fetch_all_datatable_rows(
                REFUELS_APP.list_path,
                columns_count=REFUELS_APP.columns_count,
                page_size=250,
                extra_params={
                    "enable_date_filter": 1,
                    "date_start": date_from.isoformat(),
                    "date_end": date_to.isoformat(),
                    "filter_code[]": [search_result.vehicle_filter_id],
                    "filter_validity": "",
                },
            )
            total += vehicle_total
            for row in self._parse_refuel_list_rows(rows, source_issue=source_issue):
                if row.wc_id in seen_wc_ids:
                    continue
                seen_wc_ids.add(row.wc_id)
                parsed.append(row)

        return parsed, total
