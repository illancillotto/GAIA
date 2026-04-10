from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.elaborazioni.bonifica_oristanese.apps.client import BonificaDatatableClient
from app.modules.elaborazioni.bonifica_oristanese.apps.registry import get_bonifica_app
from app.modules.elaborazioni.bonifica_oristanese.parsers import clean_html_text
from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSessionManager


REPORTS_APP = get_bonifica_app("reports")


@dataclass(frozen=True)
class BonificaReportRow:
    external_code: str
    report_type_name: str
    urgent: bool
    description: str | None
    reporter_name: str | None
    area_code: str | None
    created_at_text: str | None
    latitude_text: str | None
    longitude_text: str | None
    archived: bool
    status_text: str | None
    assigned_responsibles: str | None


class BonificaReportsClient(BonificaDatatableClient):
    def __init__(self, session_manager: BonificaOristaneseSessionManager) -> None:
        super().__init__(session_manager)

    async def fetch_reports(
        self,
        *,
        date_from: date,
        date_to: date,
    ) -> tuple[list[BonificaReportRow], int]:
        rows, total = await self.fetch_all_datatable_rows(
            REPORTS_APP.list_path,
            columns_count=REPORTS_APP.columns_count,
            page_size=250,
            extra_params={
                "enable_date_filter": 1,
                "date_start": date_from.isoformat(),
                "date_end": date_to.isoformat(),
                "show_archived": 1,
                "export_details": "detailed",
            },
        )
        parsed: list[BonificaReportRow] = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 19:
                continue
            external_code = clean_html_text(row[0])
            if not external_code:
                continue
            parsed.append(
                BonificaReportRow(
                    external_code=external_code,
                    report_type_name=clean_html_text(row[1]),
                    urgent=clean_html_text(row[2]).lower() == "si",
                    description=clean_html_text(row[3]) or None,
                    reporter_name=clean_html_text(row[4]) or None,
                    area_code=clean_html_text(row[5]) or None,
                    created_at_text=clean_html_text(row[6]) or None,
                    latitude_text=clean_html_text(row[7]) or None,
                    longitude_text=clean_html_text(row[8]) or None,
                    archived=clean_html_text(row[15]).lower() == "si",
                    status_text=clean_html_text(row[17]) or None,
                    assigned_responsibles=clean_html_text(row[18]) or None,
                )
            )
        return parsed, total
