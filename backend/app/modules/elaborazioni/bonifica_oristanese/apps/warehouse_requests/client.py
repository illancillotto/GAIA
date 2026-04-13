from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import zlib

from app.modules.elaborazioni.bonifica_oristanese.apps.client import BonificaDatatableClient
from app.modules.elaborazioni.bonifica_oristanese.apps.registry import get_bonifica_app
from app.modules.elaborazioni.bonifica_oristanese.parsers import clean_html_text
from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSessionManager
from app.modules.operazioni.services.parsing import parse_italian_datetime


WAREHOUSE_APP = get_bonifica_app("warehouse_requests")


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
class BonificaWarehouseRequestRow:
    wc_id: int
    wc_report_id: int | None
    report_type: str | None
    reported_by: str | None
    requested_by: str | None
    report_date: datetime | None
    request_date: datetime | None
    archived: bool
    status_active: bool


class BonificaWarehouseRequestsClient(BonificaDatatableClient):
    def __init__(self, session_manager: BonificaOristaneseSessionManager) -> None:
        super().__init__(session_manager)

    async def fetch_warehouse_requests(
        self,
        *,
        date_from: date,
        date_to: date,
    ) -> tuple[list[BonificaWarehouseRequestRow], int]:
        rows, total = await self.fetch_all_datatable_rows(
            WAREHOUSE_APP.list_path,
            columns_count=WAREHOUSE_APP.columns_count,
            page_size=250,
            extra_params={
                "enable_date_filter": 1,
                "date_start": date_from.isoformat(),
                "date_end": date_to.isoformat(),
                "show_archived": "all",
                "show_status": "all",
            },
        )

        parsed: list[BonificaWarehouseRequestRow] = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 6:
                continue
            report_ref = clean_html_text(row[0]) or None
            row_key = "|".join(
                [
                    clean_html_text(row[0]),
                    clean_html_text(row[1]),
                    clean_html_text(row[2]),
                    clean_html_text(row[3]),
                    clean_html_text(row[4]),
                    clean_html_text(row[5]),
                ]
            )
            request_date = parse_italian_datetime(clean_html_text(row[5]) or None)
            parsed.append(
                BonificaWarehouseRequestRow(
                    wc_id=zlib.crc32(row_key.encode("utf-8")) & 0x7FFFFFFF,
                    wc_report_id=_to_int(report_ref),
                    report_type=clean_html_text(row[1]) or None,
                    reported_by=clean_html_text(row[2]) or None,
                    requested_by=clean_html_text(row[3]) or None,
                    report_date=parse_italian_datetime(clean_html_text(row[4]) or None),
                    request_date=request_date,
                    archived=False,
                    status_active=True,
                )
            )

        return parsed, total
