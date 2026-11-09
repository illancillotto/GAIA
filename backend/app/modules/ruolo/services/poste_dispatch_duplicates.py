"""Account-wide evidence of duplicate notices; never logs into Poste or deletes drafts."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.posta_online import PostaOnlineCredential, PostaOnlineRegisteredMailSyncJob
from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem, PosteDispatchLot
from app.modules.ruolo.services.poste_dispatch_recipient import shipment_name
from app.modules.ruolo.services.poste_dispatch_state import transition

SNAPSHOT_MAX_AGE = timedelta(minutes=30)


def _name(value: str) -> str:
    return " ".join(value.upper().split())


def _account(username: str | None) -> str:
    return (username or "").strip().casefold()


def _snapshot_time(snapshot: dict) -> datetime | None:
    try:
        value = datetime.fromisoformat(snapshot["checked_at"])
    except (KeyError, TypeError, ValueError):
        return None
    return value if value.tzinfo is not None else None


def _latest_snapshots(lots: list[PosteDispatchLot]) -> dict:
    latest = {}
    for lot in lots:
        snapshot = lot.portal_snapshot or {}
        checked = _snapshot_time(snapshot)
        account = _account(lot.poste_username)
        if not account or checked is None:
            continue
        previous = latest.get(account)
        if previous is None or checked > previous[0]:
            latest[account] = (checked, snapshot)
    return latest


def _account_coverage(usernames, lots, snapshots, now: datetime) -> list[dict]:
    accounts = {_account(username) for username in usernames}
    accounts.update(_account(lot.poste_username) for lot in lots)
    result = []
    for account in sorted(accounts):
        checked, snapshot = snapshots.get(account, (None, {}))
        full = "drafts" in snapshot
        fresh = checked is not None and timedelta(0) <= now - checked <= SNAPSHOT_MAX_AGE
        result.append(
            {
                "poste_username": account or None,
                "checked_at": checked.isoformat() if checked else None,
                "full_drafts_snapshot": full,
                "fresh": fresh,
                "verified": full and fresh,
            }
        )
    return result


def _item_evidence(item, lot) -> dict:
    return {
        "item_id": str(item.id),
        "lot_id": str(item.lot_id),
        "batch_item_id": str(item.batch_item_id),
        "notice_number": item.notice_number,
        "poste_username": _account(lot.poste_username) or None,
        "credential_id": lot.credential_id,
        "status": item.status,
        "draft_id": item.poste_draft_id,
        "upload_job_id": item.upload_job_id,
        "uploaded_by": item.upload_requested_by_username,
    }


def _group():
    return {"items": [], "portal_drafts": []}


def _groups(items, lots, snapshots) -> dict:
    groups = defaultdict(_group)
    for item in items:
        evidence = _item_evidence(item, lots[item.lot_id])
        groups[("notice", _name(shipment_name(item.notice_number, item.recipient)))][
            "items"
        ].append(evidence)
        groups[("source", str(item.batch_item_id))]["items"].append(evidence)
    for account, (checked, snapshot) in snapshots.items():
        for row in snapshot.get("drafts", snapshot.get("foreign_drafts", [])):
            name = _name(row["name"])
            if name.startswith("GAIA "):
                groups[("notice", name)]["portal_drafts"].append(
                    {
                        "poste_username": account,
                        "draft_id": row["draft_id"],
                        "checked_at": checked.isoformat(),
                    }
                )
    return groups


def _finding(match, group) -> dict | None:
    accounts = {row["poste_username"] for row in group["items"] + group["portal_drafts"]}
    portal_counts = defaultdict(int)
    for row in group["portal_drafts"]:
        portal_counts[row["poste_username"]] += 1
    reasons = []
    if len(group["items"]) > 1:
        reasons.append("multiple_active_items")
    if len(accounts) > 1:
        reasons.append("cross_account_conflict")
    if any(count > 1 for count in portal_counts.values()):
        reasons.append("multiple_portal_drafts")
    if not reasons:
        return None
    return {"match_by": match[0], "key": match[1], "reasons": reasons, **group}


def duplicate_report(db: Session, *, now: datetime | None = None) -> dict:
    """A zero finding count is not a live all-account certification: see coverage."""
    now = now or datetime.now(UTC)
    lots = list(db.scalars(select(PosteDispatchLot)))
    snapshots = _latest_snapshots(lots)
    usernames = list(db.scalars(select(PostaOnlineCredential.username)))
    coverage = _account_coverage(usernames, lots, snapshots, now)
    items = list(
        db.scalars(select(PosteDispatchItem).where(PosteDispatchItem.status != "cancelled"))
    )
    groups = _groups(items, {lot.id: lot for lot in lots}, snapshots)
    findings = []
    for match, group in sorted(groups.items()):
        finding = _finding(match, group)
        if finding is not None:
            findings.append(finding)
    return {
        "checked_at": now.isoformat(),
        "accounts": coverage,
        "coverage_complete": bool(coverage) and all(row["verified"] for row in coverage),
        "scope": "GAIA notice names and source items; latest stored draft observations and outbox history",
        "findings": findings,
        "total": len(findings),
    }


def allow_upload(
    db: Session, item: PosteDispatchItem, *, job: PostaOnlineRegisteredMailSyncJob, username: str
) -> bool:
    """Choose and persist one outcome after the caller validates account and operator."""
    findings = duplicate_report(db)["findings"]
    conflicts = [f for f in findings if any(r["item_id"] == str(item.id) for r in f["items"])]
    valid_keys = (
        item.active_key == item.shipment_name == shipment_name(item.notice_number, item.recipient)
        and item.active_source_key == str(item.batch_item_id)
        and item.artifact_sha256 == item.recipient.get("heir_pdf_sha256", item.artifact_sha256)
    )
    if valid_keys and not conflicts:
        item.upload_requested_by_user_id = job.requested_by_user_id
        item.upload_requested_by_username = username
        item.upload_job_id = job.id
        item.error_detail = None
        transition(db, item, "draft_creating", "draft_submitting", job_id=job.id)
        return True
    item.error_detail = (
        "Caricamento bloccato: conflitto duplicati o prenotazione globale non valida"
    )
    item.address_review = {
        "reason": item.error_detail,
        "duplicate_check": True,
        "no_automatic_retry": True,
    }
    transition(
        db,
        item,
        "address_review",
        "duplicate_upload_blocked",
        job_id=job.id,
        detail={"valid_reservation": valid_keys, "conflicts": conflicts},
    )
    return False
