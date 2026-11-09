"""Read-only operator view: canonical notice -> reference year -> Poste account.

Generation batches remain immutable history. Cancelled attempts do not assign an
account; multiple surviving attempts are exposed as conflicts, never hidden.
"""

from collections import Counter

from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloTributiReminderBatchItem as Item
from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem, PosteDispatchLot
from app.modules.ruolo.services.reminder_batch_overview import sendable
from app.modules.ruolo.services.reminder_batch_poste import dispatches_by_notice
from app.modules.ruolo.services.tributi_reminder_service import notice_total_amount

STAGES = {
    "sent": "sent",
    "draft_created": "draft",
    "draft_priced": "draft",
    "address_review": "review",
    "draft_error": "review",
    "draft_uncertain": "review",
    "draft_missing": "review",
}


def _items(db: Session):
    number = Item.payload_json["notice_number"].as_string()
    ranked = select(
        Item.id,
        func.row_number()
        .over(
            partition_by=func.coalesce(
                Item.payload_json["heir_delivery"]["reference"].as_string(),
                func.nullif(number, ""),
                cast(Item.id, String),
            ),
            order_by=(Item.created_at.desc(), Item.id.desc()),
        )
        .label("rank"),
    ).subquery()
    return list(
        db.scalars(select(Item).join(ranked, ranked.c.id == Item.id).where(ranked.c.rank == 1))
    )


def _assignments(db: Session):
    rows = db.execute(
        select(
            func.coalesce(
                PosteDispatchItem.recipient["heir_reference"].as_string(),
                PosteDispatchItem.notice_number,
            ).label("delivery_reference"),
            PosteDispatchItem.status,
            PosteDispatchLot.id.label("lot_id"),
            PosteDispatchLot.credential_id,
            PosteDispatchLot.poste_username,
        )
        .join(PosteDispatchLot, PosteDispatchLot.id == PosteDispatchItem.lot_id)
        .where(PosteDispatchItem.status != "cancelled")
    ).mappings()
    result = {}
    for row in rows:
        result.setdefault(row["delivery_reference"], []).append(dict(row))
    return result


def _ownership(attempts: list[dict]) -> dict:
    if not attempts:
        return {
            "account_key": "none",
            "account_label": "Da assegnare",
            "lot_id": None,
            "stage": "available",
        }
    if len(attempts) > 1:
        return {
            "account_key": "conflict",
            "account_label": "Conflitti da verificare",
            "lot_id": None,
            "stage": "conflict",
        }
    row = attempts[0]
    return {
        "account_key": str(row["credential_id"] or "legacy"),
        "account_label": row["poste_username"] or "Account storico da associare",
        "lot_id": row["lot_id"],
        "stage": STAGES.get(row["status"], "processing"),
    }


def _document(item):
    return {
        "item_id": item.id,
        "batch_id": item.batch_id,
        "codice_fiscale": item.codice_fiscale,
        "label": item.display_name or item.codice_fiscale,
        "years": sorted(set(item.years_json or [])),
        "document_status": item.status,
        "amount": float(notice_total_amount(item.payload_json or {})),
        "download_url": f"/ruolo/tributi/solleciti/items/{item.id}/download"
        if sendable(item)
        else None,
    }


def _row(item, assignments, history):
    payload = item.payload_json or {}
    number = payload.get("notice_number")
    reference = payload.get("heir_delivery", {}).get("reference", number)
    ownership = _ownership(assignments.get(reference, []))
    document = _document(item)
    ready = document["download_url"] is not None
    if ownership["stage"] == "available" and not ready:
        ownership["stage"] = "review"
    return {
        **document,
        "notice_number": number,
        "can_prepare": ready and ownership["stage"] == "available" and bool(number),
        "poste_dispatches": history.get(reference, []),
        **ownership,
    }


def _groups(rows):
    groups = {}
    for row in rows:
        key = (tuple(row["years"]), row["account_key"])
        group = groups.setdefault(
            key,
            {
                "years": row["years"],
                "account_key": row["account_key"],
                "account_label": row["account_label"],
                "total": 0,
                "stages": Counter(),
            },
        )
        group["total"] += 1
        group["stages"][row["stage"]] += 1
    return sorted(groups.values(), key=lambda g: (g["years"], g["account_label"]))


def workspace(db: Session, filters: dict) -> dict:
    items = _items(db)
    assignments, history = _assignments(db), dispatches_by_notice(db, items)
    rows = [_row(item, assignments, history) for item in items]
    term = filters["q"].strip().casefold()
    searched = [
        r
        for r in rows
        if term in f"{r['label']} {r['codice_fiscale']} {r['notice_number']}".casefold()
    ]
    selected = [
        r
        for r in searched
        if (filters["year"] is None or filters["year"] in r["years"])
        and filters["account"] in ("all", r["account_key"])
        and filters["stage"] in ("all", r["stage"])
    ]
    selected.sort(key=lambda r: (r["years"], r["account_label"], r["label"], str(r["item_id"])))
    start = (filters["page"] - 1) * filters["page_size"]
    return {
        "groups": _groups(searched),
        "items": selected[start : start + filters["page_size"]],
        "total": len(selected),
        "page": filters["page"],
        "page_size": filters["page_size"],
    }
