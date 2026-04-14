from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.core.config import settings
from app.modules.elaborazioni.bonifica_oristanese.apps.client import BonificaDatatableClient
from app.modules.elaborazioni.bonifica_oristanese.apps.registry import get_bonifica_app
from app.modules.elaborazioni.bonifica_oristanese.parsers import (
    clean_html_text,
    extract_href_id,
    parse_form_fields,
)
from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSessionManager


USERS_APP = get_bonifica_app("users")


def _field_text(fields: dict[str, str | list[str] | bool], *keys: str) -> str | None:
    for key in keys:
        value = fields.get(key)
        if isinstance(value, list):
            if value:
                cleaned = clean_html_text(value[0])
                if cleaned:
                    return cleaned
            continue
        if isinstance(value, bool) or value is None:
            continue
        cleaned = clean_html_text(value)
        if cleaned:
            return cleaned
    return None


@dataclass(frozen=True)
class BonificaUserRow:
    wc_id: int
    username: str | None
    email: str | None
    user_type: str | None
    business_name: str | None
    first_name: str | None
    last_name: str | None
    tax: str | None
    contact_phone: str | None
    contact_mobile: str | None
    enabled: bool
    role: str | None


class BonificaUsersClient(BonificaDatatableClient):
    def __init__(self, session_manager: BonificaOristaneseSessionManager) -> None:
        super().__init__(session_manager)

    async def _parse_user_row(self, row: object) -> BonificaUserRow | None:
        if not isinstance(row, list) or len(row) < 5:
            return None
        wc_id = extract_href_id(row[4], "/users/")
        if wc_id is None:
            return None

        html = await self.fetch_detail_html(USERS_APP.detail_path_template.format(id=wc_id))
        fields = parse_form_fields(html)
        return BonificaUserRow(
            wc_id=wc_id,
            username=_field_text(fields, "username"),
            email=_field_text(fields, "email"),
            user_type=_field_text(fields, "user_type", "type"),
            business_name=_field_text(fields, "business_name"),
            first_name=_field_text(fields, "first_name"),
            last_name=_field_text(fields, "last_name"),
            tax=_field_text(fields, "tax"),
            contact_phone=_field_text(fields, "contact_phone"),
            contact_mobile=_field_text(fields, "contact_mobile"),
            enabled=bool(fields.get("enabled")),
            role=_field_text(fields, "roles", "role") or clean_html_text(row[1]) or None,
        )

    async def _fetch_users(
        self,
        *,
        filter_role: str,
        exclude_role: str | None = None,
    ) -> tuple[list[BonificaUserRow], int]:
        rows, total = await self.fetch_all_datatable_rows(
            USERS_APP.list_path,
            columns_count=USERS_APP.columns_count,
            page_size=250,
            extra_params={
                "filter_role": filter_role,
                "filter_enabled": "",
            },
        )

        detail_concurrency = max(settings.wc_sync_user_detail_concurrency, 1)
        semaphore = asyncio.Semaphore(detail_concurrency)

        async def parse_with_limit(row: object) -> BonificaUserRow | None:
            async with semaphore:
                return await self._parse_user_row(row)

        parsed = [
            parsed_row
            for parsed_row in await asyncio.gather(*(parse_with_limit(row) for row in rows))
            if parsed_row is not None
        ]

        if exclude_role:
            normalized_exclude_role = exclude_role.strip().lower()
            parsed = [
                row
                for row in parsed
                if (row.role or "").strip().lower() != normalized_exclude_role
            ]

        return parsed, total

    async def fetch_users(self) -> tuple[list[BonificaUserRow], int]:
        return await self._fetch_users(filter_role="", exclude_role="consorziato")

    async def fetch_consorziati(self) -> tuple[list[BonificaUserRow], int]:
        return await self._fetch_users(filter_role="Consorziato")
