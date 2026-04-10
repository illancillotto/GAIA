from __future__ import annotations

from dataclasses import dataclass

from app.modules.elaborazioni.bonifica_oristanese.apps.client import BonificaDatatableClient
from app.modules.elaborazioni.bonifica_oristanese.apps.registry import get_bonifica_app
from app.modules.elaborazioni.bonifica_oristanese.parsers import clean_html_text, extract_href_id
from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSessionManager


REPORT_TYPES_APP = get_bonifica_app("report_types")


@dataclass(frozen=True)
class BonificaReportTypeRow:
    wc_id: int
    name: str
    areas_csv: str | None


class BonificaReportTypesClient(BonificaDatatableClient):
    def __init__(self, session_manager: BonificaOristaneseSessionManager) -> None:
        super().__init__(session_manager)

    async def fetch_report_types(self) -> tuple[list[BonificaReportTypeRow], int]:
        rows, total = await self.fetch_all_datatable_rows(
            REPORT_TYPES_APP.list_path,
            columns_count=REPORT_TYPES_APP.columns_count,
            page_size=100,
        )
        parsed: list[BonificaReportTypeRow] = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 3:
                continue
            wc_id = extract_href_id(row[2], "/reports/types/edit/")
            if wc_id is None:
                continue
            parsed.append(
                BonificaReportTypeRow(
                    wc_id=wc_id,
                    name=clean_html_text(row[0]),
                    areas_csv=clean_html_text(row[1]) or None,
                )
            )
        return parsed, total
