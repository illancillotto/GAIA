"""Read-only AutoSync capacity report using current calendars, never secrets.

Run with PYTHONPATH=backend and the backend environment. Historical calendars
and lease occupancy are not reconstructed: the denominator is scheduled time.
"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, text

from app.models.catasto import CatastoBatch, CatastoCredential, CatastoRuoloAutoSyncConfig
from app.modules.elaborazioni.sister_http_health import init_portale_hourly_health
from app.modules.elaborazioni.telemetry_models import SisterPortalEvent
from app.services.elaborazioni_credential_schedule import credential_is_available

UTC = timezone.utc  # noqa: UP017 - Also executed inside the Python 3.10 worker.


def utc(value):
    return value.replace(tzinfo=value.tzinfo or UTC).astimezone(UTC)


def union_seconds(intervals):
    end = None
    total = 0.0
    for left, right in sorted(intervals):
        if end is not None:
            left = max(left, end)
        total += max((right - left).total_seconds(), 0)
        end = max(end or right, right)
    return total


def scheduled_intervals(profile, start, end):
    cursor = start
    intervals = []
    while cursor < end:
        following = min(cursor.replace(second=0, microsecond=0) + timedelta(minutes=1), end)
        if credential_is_available(
            profile.get("schedule_enabled", False), profile.get("availability_schedule"), cursor
        ):
            intervals.append((cursor, following))
        cursor = following
    return intervals


def event_interval(event):
    at = utc(event.occurred_at)
    if event.cooldown_seconds and event.event_type in {"cooldown", "authentication_gate"}:
        return "cooldown", at, at + timedelta(seconds=event.cooldown_seconds)
    categories = {"login": "login", "authentication_gate": "login", "polling": "remote_poll"}
    category = categories.get(event.event_type)
    return category, at - timedelta(milliseconds=event.duration_ms or 0), at


def remote_wait_intervals(events, end):
    waiting = {}
    intervals = []
    for event in sorted(events, key=lambda item: utc(item.occurred_at)):
        at = utc(event.occurred_at)
        if event.event_type == "polling" and event.outcome == "waiting":
            waiting.setdefault(event.request_id, at)
        elif event.event_type in {"execution_start", "download"} and event.request_id in waiting:
            intervals.append((waiting.pop(event.request_id), at))
    intervals.extend((at, end) for at in waiting.values())
    return intervals


def summarize(profile, events, start, end):
    available = scheduled_intervals(profile, start, end)
    hours = union_seconds(available) / 3600
    durations = {"login": [], "remote_poll": [], "cooldown": []}
    downloads = set()
    for event in events:
        at = utc(event.occurred_at)
        if start <= at < end and event.event_type == "download" and event.outcome == "success":
            downloads.add(event.request_id or event.id)
        category, left, right = event_interval(event)
        if category is not None:
            durations[category].extend(
                (max(left, a), min(right, b)) for a, b in available if left < b and right > a
            )
    remote_wait = remote_wait_intervals(events, end)
    remote_seconds = union_seconds(
        (max(left, a), min(right, b))
        for left, right in remote_wait
        for a, b in available
        if left < b and right > a
    )
    return {
        "pdf": len(downloads),
        "scheduled_hours": round(hours, 3),
        "outside_schedule_hours": round((end - start).total_seconds() / 3600 - hours, 3),
        "pdf_per_scheduled_hour": round(len(downloads) / hours, 3) if hours else None,
        "observed_remote_wait_hours": round(remote_seconds / 3600, 3) if remote_wait else None,
        "observed_hours_within_schedule": {
            name: round(union_seconds(values) / 3600, 3) for name, values in durations.items()
        },
    }


def report(db, user_id, start, end):
    config = db.scalar(
        select(CatastoRuoloAutoSyncConfig).where(CatastoRuoloAutoSyncConfig.user_id == user_id)
    )
    if config is None or not config.enabled or not config.credential_profiles:
        raise ValueError("Serve una campagna attiva con profili AutoSync espliciti")
    profiles = {
        UUID(key): value for key, value in config.credential_profiles.items() if value["enabled"]
    }
    accounts = list(db.scalars(select(CatastoCredential).where(CatastoCredential.id.in_(profiles))))
    if len({account.sister_username for account in accounts}) != len(accounts):
        raise ValueError("Profili duplicati per username: consolidare prima il denominatore")
    rows = []
    for account in accounts:
        events = db.scalars(
            select(SisterPortalEvent)
            .join(CatastoBatch, CatastoBatch.id == SisterPortalEvent.batch_id)
            .where(
                CatastoBatch.user_id == user_id,
                CatastoBatch.batch_kind.in_(["perpetual_sync", "ruolo_autosync"]),
                SisterPortalEvent.credential_id == account.id,
                SisterPortalEvent.occurred_at >= start - timedelta(days=1),
                SisterPortalEvent.occurred_at < end,
            )
        ).all()
        profile = profiles[account.id] if account.active else {"schedule_enabled": True}
        rows.append(
            {
                "label": account.label,
                "active": account.active,
                **summarize(profile, events, start, end),
                "init_portale_hourly": init_portale_hourly_health(
                    events, start, end, _merged_schedule(profile, start, end)
                ),
            }
        )
    return {
        "start_utc": start.isoformat(),
        "end_utc": end.isoformat(),
        "calendar_basis": "current_configuration_not_historical",
        "lease_occupancy": "unknown",
        "note": "Durate unificate per categoria, non sommabili. Attesa remota osservata solo con nuovi eventi waiting; null significa non misurabile.",
        "accounts": rows,
    }


def _merged_schedule(profile, start, end):
    merged = []
    for left, right in scheduled_intervals(profile, start, end):
        if merged and merged[-1][1] == left:
            merged[-1] = (merged[-1][0], right)
        else:
            merged.append((left, right))
    return merged


def main():
    from app.core.database import SessionLocal

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--hours", type=int, default=24, choices=range(1, 169))
    args = parser.parse_args()
    end = datetime.now(UTC)
    with SessionLocal() as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        result = report(db, args.user_id, end - timedelta(hours=args.hours), end)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
