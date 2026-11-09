"""Per-notice deterministic plans; missing never means delete."""

from collections import Counter
from datetime import datetime, timedelta

from app.modules.elaborazioni.capacitas.incremental.models import IncrementalChange
from app.modules.elaborazioni.capacitas.incremental.normalize import SnapshotInvalid, digest

IDENTITY = frozenset({"CodFisc", "Avviso", "Anno", "ID", "TipAna"})
STRUCTURAL = frozenset({"Carico", "Sgravio", "Annullato", "Rateizzato"})


def validate_collection(artifacts: dict, expected: list, old, config) -> dict:
    if not expected or set(expected) != set(artifacts):
        raise SnapshotInvalid("incomplete_scope")
    rows = {}
    for year in expected:
        artifact = artifacts[year]
        validate_artifact(artifact, year, old, config)
        current = artifact["rows"]
        if rows.keys() & current.keys():
            raise SnapshotInvalid("ambiguous_cross_year_notice")
        rows.update(current)
    if old and set(expected) != set(old.expected):
        raise SnapshotInvalid("scope_changed")
    missing = len(old.rows.keys() - rows.keys()) if old else 0
    if old and missing / max(1, len(old.rows)) > config.missing_fraction:
        raise SnapshotInvalid("abnormal_missing_fraction")
    return rows


def validate_artifact(artifact, year, old, config) -> None:
    if not artifact.get("drive_id"):
        raise SnapshotInvalid("archive_unavailable")
    previous = old.artifacts.get(year) if old else None
    if old and previous is None:
        raise SnapshotInvalid("scope_changed")
    if previous and previous["schema"] != artifact["schema"]:
        raise SnapshotInvalid("schema_changed")
    if not artifact["rows"]:
        if year not in config.empty_years:
            raise SnapshotInvalid("unproven_empty")
        if previous and previous["rows"]:
            raise SnapshotInvalid("unexpected_empty")


def classify(old: dict | None, new: dict | None) -> tuple[str, str, dict]:
    if new is None:
        return "missing", "review", {}
    if old is None:
        return "new", "recover", {}
    fields = {
        key: [old.get(key), new.get(key)]
        for key in old.keys() | new.keys()
        if old.get(key) != new.get(key)
    }
    if not fields:
        return "unchanged", "none", {}
    if IDENTITY & fields.keys():
        return "ambiguous", "review", fields
    action = "recover" if STRUCTURAL & fields.keys() else "summary"
    return "changed", action, fields


def make_plan(cycle, old, head, config, now: datetime) -> tuple[list, dict]:
    if not config.bootstrap_keys <= cycle.rows.keys():
        raise SnapshotInvalid("bootstrap_notice_not_in_snapshot")
    if old is None:
        changes = [bootstrap_change(cycle, key) for key in sorted(config.bootstrap_keys)]
        return changes, {
            "baseline": True,
            "counts": {"unchanged": len(cycle.rows)},
            "planned": len(changes),
        }
    previous = old.rows
    full, sample = audit_selection(cycle, previous, head, config, now)
    changes, counts = [], Counter()
    for key in sorted(previous.keys() | cycle.rows.keys()):
        before, after = previous.get(key), cycle.rows.get(key)
        kind, action, fields = classify(before, after)
        counts[kind] += 1
        if key in config.bootstrap_keys:
            changes.append(bootstrap_change(cycle, key))
            continue
        if kind == "unchanged":
            if not full and key not in sample:
                continue
            action = "audit"
        changes.append(
            IncrementalChange(
                id=digest([cycle.id, key]),
                cycle_id=cycle.id,
                notice_key=key,
                kind=kind,
                action=action,
                status="pending" if cycle.mode == "active" else "shadow",
                old=before,
                new=after,
                fields=fields,
            )
        )
    return changes, {
        "baseline": False,
        "counts": dict(counts),
        "planned": len(changes),
        "sampled": len(sample),
        "full_audit": full,
        "unchanged_notices_without_refresh": counts["unchanged"] - len(sample) if not full else 0,
        "hypothetical_full_refresh_requests_avoided": 2 * (counts["unchanged"] - len(sample))
        if not full
        else 0,
        "estimate_basis": "counterfactual detail+partitario for every unchanged notice; legacy light already avoids both; not measured HTTP; excludes exports/PDFs",
    }


def bootstrap_change(cycle, key: str):
    return IncrementalChange(
        id=digest([cycle.id, key]),
        cycle_id=cycle.id,
        notice_key=key,
        kind="new",
        action="recover",
        status="pending" if cycle.mode == "active" else "shadow",
        old=None,
        new=cycle.rows[key],
        fields={"bootstrap": [None, "explicit_allowlist"]},
    )


def audit_selection(cycle, previous, head, config, now):
    """Rotate the stable daily sample; overdue full audits supersede sampling."""
    full = bool(
        config.full_audit_days
        and now.timestamp() - head.full_audit_at.timestamp()
        >= timedelta(days=config.full_audit_days).total_seconds()
    )
    unchanged = [key for key in sorted(cycle.rows) if previous.get(key) == cycle.rows[key]]
    sample = set(sorted(unchanged, key=lambda key: digest([cycle.id, key]))[: config.sample_size])
    return full, sample
