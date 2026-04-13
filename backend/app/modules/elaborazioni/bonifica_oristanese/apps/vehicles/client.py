from __future__ import annotations

from dataclasses import dataclass

from app.modules.elaborazioni.bonifica_oristanese.apps.client import BonificaDatatableClient
from app.modules.elaborazioni.bonifica_oristanese.apps.registry import get_bonifica_app
from app.modules.elaborazioni.bonifica_oristanese.parsers import (
    clean_html_text,
    extract_href_id,
    parse_form_fields,
)
from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSessionManager


VEHICLES_APP = get_bonifica_app("vehicles")


def _to_int(value: str | bool | list[str] | None) -> int | None:
    if isinstance(value, bool) or isinstance(value, list) or value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return int(normalized)
    except ValueError:
        return None


def _vehicle_type_label(raw_value: str | bool | list[str] | None) -> str:
    if isinstance(raw_value, bool) or isinstance(raw_value, list) or raw_value is None:
        return "automezzo"
    normalized = raw_value.strip()
    if normalized == "1":
        return "attrezzatura"
    return "automezzo"


@dataclass(frozen=True)
class BonificaVehicleRow:
    wc_id: int
    vehicle_code: str | None
    vehicle_name: str | None
    vehicle_type_label: str
    km_start: int | None
    km_limit: int | None
    override_km_global: bool
    override_ask_km_overflow: bool


class BonificaVehiclesClient(BonificaDatatableClient):
    def __init__(self, session_manager: BonificaOristaneseSessionManager) -> None:
        super().__init__(session_manager)

    async def fetch_vehicles(self) -> tuple[list[BonificaVehicleRow], int]:
        rows, total = await self.fetch_all_datatable_rows(
            VEHICLES_APP.list_path,
            columns_count=VEHICLES_APP.columns_count,
            page_size=100,
        )

        parsed: list[BonificaVehicleRow] = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 3:
                continue
            wc_id = extract_href_id(row[2], "/vehicles/edit/")
            if wc_id is None:
                continue

            html = await self.fetch_detail_html(VEHICLES_APP.detail_path_template.format(id=wc_id))
            fields = parse_form_fields(html)
            parsed.append(
                BonificaVehicleRow(
                    wc_id=wc_id,
                    vehicle_code=clean_html_text(str(fields.get("vehicle_id", "") or row[1])) or None,
                    vehicle_name=clean_html_text(str(fields.get("vehicle_name", "") or row[0])) or None,
                    vehicle_type_label=_vehicle_type_label(fields.get("vehicle_type")),
                    km_start=_to_int(fields.get("vehicle[km][start]")),
                    km_limit=_to_int(fields.get("vehicle[km][limit]")),
                    override_km_global=bool(fields.get("vehicle_override_km_global")),
                    override_ask_km_overflow=bool(fields.get("vehicle_override_ask_km_overflow")),
                )
            )

        return parsed, total
