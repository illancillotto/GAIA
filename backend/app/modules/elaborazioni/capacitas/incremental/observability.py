"""Read-only comparisons and outbox metrics; no personal data in log output."""

from collections import Counter

from sqlalchemy import select

from app.modules.elaborazioni.capacitas.incremental.diff import classify
from app.modules.elaborazioni.capacitas.incremental.models import (
    IncrementalChange,
    IncrementalCycle,
    IncrementalHead,
)
from app.modules.elaborazioni.capacitas.incremental.normalize import (
    SnapshotInvalid,
    canonical_row,
    digest,
)
from app.modules.utenze.models import AnagraficaPaymentNotice


def compare_notice(notice, new: dict, old) -> tuple[str, str]:
    current = canonical_row(notice.raw_row_json or {})
    different = any(current.get(key) != value for key, value in new.items())
    if not different:
        return "matched", "none"
    kind = classify(old.rows.get(notice.source_notice_id), new)[0] if old else "new"
    return "divergent", "unexplained_unchanged" if kind == "unchanged" else "none"


def shadow_observation(db, cycle) -> dict:
    """Candidates for verification, not empirical live false-negative/positive rates."""
    head = db.get(IncrementalHead, 1)
    old = db.get(IncrementalCycle, head.cycle_id) if head.cycle_id else None
    prior_hashes = (
        old.report.get("ordinary_sync_comparison", {}).get("heavy_signatures", {}) if old else {}
    )
    counts = Counter()
    hashes = {}
    query = select(AnagraficaPaymentNotice).where(AnagraficaPaymentNotice.source_system == "incass")
    for notice in db.scalars(query.execution_options(yield_per=500)):
        key = notice.source_notice_id
        new = cycle.rows.get(key)
        if new is None:
            continue
        hashes[key] = digest(notice.raw_detail_json)
        if key in prior_hashes and hashes[key] != prior_hashes[key]:
            if old.rows.get(key) == new:
                counts["heavy_changed_without_excel_change"] += 1
        try:
            status, issue = compare_notice(notice, new, old)
            counts[status] += 1
            counts[issue] += 1
        except SnapshotInvalid:
            counts["invalid_registry_rows"] += 1
    return {
        **dict.fromkeys(
            (
                "matched",
                "divergent",
                "unexplained_unchanged",
                "invalid_registry_rows",
                "heavy_changed_without_excel_change",
            ),
            0,
        ),
        **{key: value for key, value in counts.items() if key != "none"},
        "heavy_signatures": hashes,
        "proof": "stored_rows_only_not_live_recall",
    }


def outbox_counts(db, cycle_id: str) -> dict:
    return dict(
        Counter(
            db.scalars(
                select(IncrementalChange.status).where(IncrementalChange.cycle_id == cycle_id)
            )
        )
    )
