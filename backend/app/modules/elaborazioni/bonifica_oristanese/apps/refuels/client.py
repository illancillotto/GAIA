from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from app.modules.elaborazioni.bonifica_oristanese.apps.client import BonificaDatatableClient
from app.modules.elaborazioni.bonifica_oristanese.apps.registry import get_bonifica_app
from app.modules.elaborazioni.bonifica_oristanese.parsers import (
    clean_html_text,
    extract_href_id,
    parse_form_fields,
)
from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSessionManager


REFUELS_APP = get_bonifica_app("refuels")


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


class BonificaRefuelsClient(BonificaDatatableClient):
    def __init__(self, session_manager: BonificaOristaneseSessionManager) -> None:
        super().__init__(session_manager)

    async def fetch_refuels(
        self,
        *,
        date_from: date,
        date_to: date,
    ) -> tuple[list[BonificaRefuelRow], int]:
        rows, total = await self.fetch_all_datatable_rows(
            REFUELS_APP.list_path,
            columns_count=REFUELS_APP.columns_count,
            page_size=250,
            extra_params={
                "enable_date_filter": 1,
                "date_start": date_from.isoformat(),
                "date_end": date_to.isoformat(),
            },
        )

        parsed: list[BonificaRefuelRow] = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 5:
                continue
            wc_id = extract_href_id(row[4], "/vehicles/refuel/edit/")
            if wc_id is None:
                continue
            html = await self.fetch_detail_html(REFUELS_APP.detail_path_template.format(id=wc_id))
            fields = parse_form_fields(html)
            parsed.append(
                BonificaRefuelRow(
                    wc_id=wc_id,
                    vehicle_code=clean_html_text(row[0]) or None,
                    operator_name=clean_html_text(row[1]) or None,
                    fueled_at_text=clean_html_text(row[2]) or None,
                    odometer_km=_to_int(clean_html_text(row[3])),
                    liters=_first_decimal(
                        fields,
                        (
                            "liters",
                            "liter",
                            "quantity",
                            "amount",
                            "fuel_quantity",
                            "refuel_liters",
                            "vehicle_refuel[liters]",
                            "vehicle_refuel[quantity]",
                            "vehicle[refuel][liters]",
                            "vehicle[refuel][quantity]",
                        ),
                    ),
                    total_cost=_first_decimal(
                        fields,
                        (
                            "total_cost",
                            "cost",
                            "amount_total",
                            "price_total",
                            "vehicle_refuel[total_cost]",
                            "vehicle[refuel][total_cost]",
                        ),
                    ),
                    station_name=_first_text(
                        fields,
                        (
                            "station_name",
                            "station",
                            "supplier",
                            "distributor",
                            "vehicle_refuel[station_name]",
                            "vehicle[refuel][station_name]",
                        ),
                    ),
                )
            )

        return parsed, total
