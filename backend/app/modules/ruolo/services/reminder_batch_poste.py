"""Read stored Poste attempts by exact notice number, including older batch copies."""

from collections import defaultdict

from sqlalchemy import func, select

from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem, PosteDispatchLot


def dispatches_by_notice(db, items):
    numbers = {(item.payload_json or {}).get("notice_number") for item in items} - {None, ""}
    if not numbers:
        return {}
    dispatch = PosteDispatchItem
    rows = db.execute(
        select(
            dispatch.id,
            dispatch.notice_number,
            dispatch.notice_number.label("delivery_reference"),
            dispatch.status,
            dispatch.poste_draft_id,
            dispatch.poste_status,
            dispatch.draft_created_at,
            dispatch.sent_at,
            dispatch.tracking_number,
            dispatch.upload_requested_by_username,
            dispatch.updated_at,
            PosteDispatchLot.poste_username,
        )
        .join(PosteDispatchLot, PosteDispatchLot.id == dispatch.lot_id)
        .where(dispatch.notice_number.in_(numbers))
        .order_by(dispatch.created_at.desc(), dispatch.id)
    ).mappings()
    result = defaultdict(list)
    for row in rows:
        result[row["delivery_reference"]].append(dict(row))
    return result
