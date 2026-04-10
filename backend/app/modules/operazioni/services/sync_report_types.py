from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.elaborazioni.bonifica_oristanese.apps.report_types.client import BonificaReportTypeRow
from app.modules.operazioni.models.reports import FieldReportCategory


@dataclass(frozen=True)
class WhiteReportTypesSyncResult:
    synced: int
    skipped: int
    errors: list[str]


def slugify_white_report_type(title: str) -> str:
    normalized = title.lower().replace("&", " ")
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    tokens = [token for token in re.split(r"\s+", normalized.strip()) if token]
    slug = re.sub(r"_+", "_", "_".join(tokens))
    return slug[:50] or "categoria_white"


def sync_white_report_types(
    *,
    db: Session,
    rows: list[BonificaReportTypeRow],
) -> WhiteReportTypesSyncResult:
    synced = 0
    skipped = 0
    errors: list[str] = []

    for row in rows:
        try:
            category = db.scalar(
                select(FieldReportCategory).where(FieldReportCategory.wc_id == row.wc_id)
            )
            desired_code = slugify_white_report_type(row.name)
            if category is None:
                category = db.scalar(
                    select(FieldReportCategory).where(FieldReportCategory.code == desired_code)
                )
                if category is not None and category.wc_id is None:
                    category.wc_id = row.wc_id

            if category is None:
                category = FieldReportCategory(
                    wc_id=row.wc_id,
                    code=desired_code,
                    name=row.name[:150],
                    description=f"Categoria sincronizzata da White Company: {row.name[:120]}",
                    is_active=True,
                    sort_order=0,
                )
                db.add(category)
                synced += 1
                continue

            changed = False
            if category.name != row.name[:150]:
                category.name = row.name[:150]
                changed = True
            if category.code != desired_code:
                category.code = desired_code
                changed = True
            if category.wc_id != row.wc_id:
                category.wc_id = row.wc_id
                changed = True

            if changed:
                synced += 1
            else:
                skipped += 1
        except Exception as exc:  # pragma: no cover - defensive branch
            errors.append(f"{row.wc_id}: {exc}")

    db.commit()
    return WhiteReportTypesSyncResult(
        synced=synced,
        skipped=skipped,
        errors=errors,
    )
