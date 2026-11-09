"""Final duplicate report, tied to one explicitly requested all-account read pass."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.posta_online import PostaOnlineCredential
from app.models.posta_online import PostaOnlineRegisteredMailSyncJob as Job
from app.modules.ruolo.poste_dispatch_models import PosteDispatchEvent as Event
from app.modules.ruolo.poste_dispatch_models import PosteDispatchLot
from app.modules.ruolo.services.poste_dispatch_final_check import (
    MODE,
    SNAPSHOT_KIND,
    AccountRead,
    account_key,
    get_check,
)

MAX_AGE = timedelta(minutes=30)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _evidence_problem(check, plan, job, evidence, now) -> str | None:
    if evidence is None:
        return "snapshot_missing"
    AccountRead.model_validate(evidence)
    if (
        evidence["final_check_id"] != str(check.id)
        or account_key(evidence["poste_username"]) != account_key(plan["poste_username"])
        or job.credential_id != plan["credential_id"]
        or job.mode != MODE
        or job.payload_json.get("final_check_id") != str(check.id)
        or job.payload_json.get("lot_id") != plan["lot_id"]
        or job.payload_json.get("poste_username") != plan["poste_username"]
    ):
        return "account_or_run_mismatch"
    started = datetime.fromisoformat(evidence["started_at"])
    checked = datetime.fromisoformat(evidence["checked_at"])
    if not (_utc(check.created_at) <= started <= checked <= _utc(job.completed_at) <= now):
        return "invalid_read_interval"
    if now - checked > MAX_AGE:
        return "snapshot_stale"
    return None


def _account_result(check, plan, jobs, snapshots, now) -> dict:
    result = {**plan, "verified": False}
    if plan["unavailable_reason"]:
        return {**result, "status": "unavailable"}
    job = jobs.get(plan["job_id"])
    if job is None:
        return {**result, "status": "missing_job"}
    if job.status != "succeeded" or job.completed_at is None:
        return {**result, "status": job.status, "error": job.error_detail}
    evidence = snapshots.get(job.id)
    try:
        problem = _evidence_problem(check, plan, job, evidence, now)
    except (AttributeError, KeyError, ValueError, TypeError):
        problem = "invalid_snapshot"
    if problem:
        return {**result, "status": problem}
    return {**result, "status": "verified", "verified": True, "snapshot": evidence}


def _accounts(db, check, now) -> list[dict]:
    plans = check.detail["accounts"]
    identities = [plan["job_id"] for plan in plans if plan["job_id"] is not None]
    jobs = {job.id: job for job in db.scalars(select(Job).where(Job.id.in_(identities)))}
    events = db.scalars(
        select(Event)
        .where(Event.kind == SNAPSHOT_KIND, Event.job_id.in_(identities))
        .order_by(Event.created_at)
    )
    snapshots = {event.job_id: event.detail for event in events}
    return [_account_result(check, plan, jobs, snapshots, now) for plan in plans]


def _invalidations(db, check) -> list[str]:
    since = _utc(check.created_at)
    newer_job = db.scalar(
        select(Job.id)
        .where(Job.mode != MODE, or_(Job.created_at >= since, Job.started_at >= since))
        .limit(1)
    )
    newer_event = db.scalar(
        select(Event.id)
        .where(
            Event.created_at >= since,
            or_(Event.item_id.is_not(None), Event.kind.in_(("lot_created", "account_bound"))),
        )
        .limit(1)
    )
    current = {account_key(name) for name in db.scalars(select(PostaOnlineCredential.username))}
    current.update(
        account_key(name) for name in db.scalars(select(PosteDispatchLot.poste_username))
    )
    expected = {account_key(plan["poste_username"]) for plan in check.detail["accounts"]}
    return [
        reason
        for condition, reason in (
            (newer_job is not None, "operations_after_request"),
            (newer_event is not None, "items_changed_after_request"),
            (current != expected, "account_scope_changed"),
        )
        if condition
    ]


def _rows(account) -> list[dict]:
    snapshot = account["snapshot"]
    rows = [
        {"name": row["name"], "shipment_id": row["draft_id"], "source": "draft"}
        for row in snapshot["drafts"]
    ]
    rows.extend(
        {"name": name, "shipment_id": identity, "source": "archive"}
        for name, ids in snapshot["archive"].items()
        for identity in ids
    )
    return rows


def _observations(accounts) -> tuple[dict, int]:
    groups = defaultdict(dict)
    unmatched = 0
    for account in accounts:
        if not account["verified"]:
            continue
        username = account_key(account["poste_username"])
        for index, row in enumerate(_rows(account)):
            name = " ".join(row["name"].upper().split())
            if not name.startswith("GAIA "):
                unmatched += 1
                continue
            # A shipment can move from drafts to archive during the read. Its id counts once.
            key = (
                username,
                row["shipment_id"] if row["shipment_id"] is not None else f"pending:{index}",
            )
            groups[name][key] = {
                **row,
                "name": name,
                "poste_username": username,
                "job_id": account["job_id"],
                "checked_at": account["snapshot"]["checked_at"],
            }
    return {name: list(rows.values()) for name, rows in groups.items()}, unmatched


def _expected_results(expected, observations) -> tuple[list, list]:
    missing, misplaced = [], []
    for item in expected:
        found = observations.get(item["notice_name"], [])
        if not found:
            missing.append(item)
        elif account_key(item["poste_username"]) not in {row["poste_username"] for row in found}:
            misplaced.append(
                {**item, "observed_accounts": sorted({row["poste_username"] for row in found})}
            )
    return missing, misplaced


def _status(complete, duplicates, missing, misplaced) -> str:
    if duplicates:
        return "duplicates_found"
    if not complete:
        return "incomplete"
    if missing or misplaced:
        return "needs_review"
    return "verified_no_duplicates"


def check_report(db: Session, check_id: UUID, *, now: datetime | None = None) -> dict:
    check = get_check(db, check_id)
    now = now or datetime.now(UTC)
    accounts = _accounts(db, check, now)
    invalidations = _invalidations(db, check)
    observations, unmatched = _observations(accounts)
    duplicates = [
        {
            "notice_name": name,
            "occurrences": rows,
            "cross_account": len({r["poste_username"] for r in rows}) > 1,
        }
        for name, rows in sorted(observations.items())
        if len(rows) > 1
    ]
    missing, misplaced = _expected_results(check.detail["expected_items"], observations)
    complete = (
        bool(accounts) and all(account["verified"] for account in accounts) and not invalidations
    )
    return {
        "check_id": str(check.id),
        "requested_at": _utc(check.created_at).isoformat(),
        "checked_at": now.isoformat(),
        "requested_by": check.actor_username,
        "status": _status(complete, duplicates, missing, misplaced),
        "complete": complete,
        "accounts": accounts,
        "invalidations": invalidations,
        "duplicates": duplicates,
        "missing": missing,
        "misplaced": misplaced,
        "unmatched_rows": unmatched,
        "scope": "GAIA shipment names, complete drafts and archive read per account",
    }
