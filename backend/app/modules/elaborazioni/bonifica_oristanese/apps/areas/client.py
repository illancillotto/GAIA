from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.modules.elaborazioni.bonifica_oristanese.apps.client import BonificaDatatableClient
from app.modules.elaborazioni.bonifica_oristanese.apps.registry import get_bonifica_app
from app.modules.elaborazioni.bonifica_oristanese.parsers import (
    clean_html_text,
    extract_href_id,
    parse_form_fields,
)
from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSessionManager


AREAS_APP = get_bonifica_app("areas")


def _to_decimal(value: str | list[str] | bool | None) -> Decimal | None:
    if isinstance(value, bool) or isinstance(value, list) or value is None:
        return None
    normalized = value.strip().replace(",", ".")
    if not normalized:
        return None
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _to_bool(value: str | list[str] | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, list) or value is None:
        return False
    return value.strip() in {"1", "true", "True", "on"}


@dataclass(frozen=True)
class BonificaAreaRow:
    wc_id: int
    name: str
    color: str | None
    is_district: bool
    description: str | None
    lat: Decimal | None
    lng: Decimal | None
    polygon: str | None


class BonificaAreasClient(BonificaDatatableClient):
    def __init__(self, session_manager: BonificaOristaneseSessionManager) -> None:
        super().__init__(session_manager)

    async def fetch_areas(self) -> tuple[list[BonificaAreaRow], int]:
        rows, total = await self.fetch_all_datatable_rows(
            AREAS_APP.list_path,
            columns_count=AREAS_APP.columns_count,
            page_size=100,
        )
        parsed: list[BonificaAreaRow] = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 2:
                continue
            wc_id = extract_href_id(row[-1], "/areas/edit/")
            if wc_id is None:
                continue

            html = await self.fetch_detail_html(AREAS_APP.detail_path_template.format(id=wc_id))
            fields = parse_form_fields(html)
            parsed.append(
                BonificaAreaRow(
                    wc_id=wc_id,
                    name=clean_html_text(str(fields.get("name", "") or row[0])) or f"Area {wc_id}",
                    color=clean_html_text(str(fields.get("area_color", ""))) or None,
                    is_district=_to_bool(fields.get("area_is_district")),
                    description=clean_html_text(str(fields.get("description", ""))) or None,
                    lat=_to_decimal(fields.get("area_position_lat")),
                    lng=_to_decimal(fields.get("area_position_lng")),
                    polygon=clean_html_text(str(fields.get("area_polygon", ""))) or None,
                )
            )

        return parsed, total
