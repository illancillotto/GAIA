from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.elaborazioni.bonifica_oristanese.apps.client import BonificaDatatableClient
from app.modules.elaborazioni.bonifica_oristanese.apps.registry import get_bonifica_app
from app.modules.elaborazioni.bonifica_oristanese.parsers import clean_html_text, extract_href_id
from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSessionManager


TAKEN_CHARGE_APP = get_bonifica_app("taken_charge")


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
class BonificaTakenChargeRow:
    wc_id: int
    vehicle_code: str | None
    operator_name: str | None
    started_at_text: str | None
    km_start: int | None
    ended_at_text: str | None
    km_end: int | None


class BonificaTakenChargeClient(BonificaDatatableClient):
    def __init__(self, session_manager: BonificaOristaneseSessionManager) -> None:
        super().__init__(session_manager)

    async def fetch_taken_charge(
        self,
        *,
        date_from: date,
        date_to: date,
    ) -> tuple[list[BonificaTakenChargeRow], int]:
        rows, total = await self.fetch_all_datatable_rows(
            TAKEN_CHARGE_APP.list_path,
            columns_count=TAKEN_CHARGE_APP.columns_count,
            page_size=250,
            extra_params={
                "enable_date_filter": 1,
                "date_start": date_from.isoformat(),
                "date_end": date_to.isoformat(),
            },
        )

        parsed: list[BonificaTakenChargeRow] = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 7:
                continue
            wc_id = extract_href_id(row[6], "/vehicles/taken-charge/edit/")
            if wc_id is None:
                continue
            parsed.append(
                BonificaTakenChargeRow(
                    wc_id=wc_id,
                    vehicle_code=clean_html_text(row[0]) or None,
                    operator_name=clean_html_text(row[1]) or None,
                    started_at_text=clean_html_text(row[2]) or None,
                    km_start=_to_int(clean_html_text(row[3])),
                    ended_at_text=clean_html_text(row[4]) or None,
                    km_end=_to_int(clean_html_text(row[5])),
                )
            )

        return parsed, total
