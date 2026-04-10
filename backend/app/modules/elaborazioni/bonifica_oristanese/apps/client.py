from __future__ import annotations

from typing import Any

import httpx

from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSessionManager
from app.modules.shared.datatable_helpers import build_datatable_params


class BonificaDatatableClient:
    def __init__(self, session_manager: BonificaOristaneseSessionManager) -> None:
        self.session_manager = session_manager

    def get_http_client(self) -> httpx.AsyncClient:
        return self.session_manager.get_http_client()

    async def fetch_datatable_page(
        self,
        path: str,
        *,
        start: int = 0,
        length: int = 100,
        draw: int = 1,
        columns_count: int = 3,
        search_value: str = "",
        extra_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self.get_http_client().get(
            self.session_manager.resolve_url(path),
            params=build_datatable_params(
                draw=draw,
                start=start,
                length=length,
                columns_count=columns_count,
                search_value=search_value,
                extra_params=extra_params,
            ),
        )
        response.raise_for_status()
        return response.json()

    async def fetch_all_datatable_rows(
        self,
        path: str,
        *,
        page_size: int = 100,
        columns_count: int = 3,
        search_value: str = "",
        extra_params: dict[str, Any] | None = None,
    ) -> tuple[list[Any], int]:
        rows: list[Any] = []
        start = 0
        draw = 1
        total = 0

        while True:
            payload = await self.fetch_datatable_page(
                path,
                start=start,
                length=page_size,
                draw=draw,
                columns_count=columns_count,
                search_value=search_value,
                extra_params=extra_params,
            )
            data = payload.get("data") or []
            total = int(payload.get("recordsTotal") or len(data))
            rows.extend(data)
            if start + page_size >= total:
                break
            start += page_size
            draw += 1

        return rows, total

    async def fetch_detail_html(self, path: str) -> str:
        response = await self.session_manager.fetch_page(path)
        return response.text
