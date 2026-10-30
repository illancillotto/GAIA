"""Every notice of a year with its PDF: ready ones stay, failed ones are retried, missing ones are made.

The year's notices are the reminder candidates of the GAIA rules, the same list as the
Tributi wizard. A notice counts as ready once a generated (or draft) batch item covers all
its avvisi, so running the tool twice never prints a second copy.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloAvviso, RuoloTributiReminderBatchItem
from app.modules.ruolo.services import notice_candidates
from app.modules.ruolo.services import notice_pdf_regeneration as regeneration

MANAGER_KEY = "gaia"
READY = regeneration.REGENERABLE | {"draft"}


def _candidates(db: Session, year: int, tax_codes: list[str] | None = None) -> list[dict]:
    collected = repo._collect_reminder_candidates(
        db,
        years=[year],
        anno_from=None,
        anno_to=None,
        q=None,
        comune=None,
        codice_fiscale=tax_codes,
        manager_key=MANAGER_KEY,
    )
    return notice_candidates.batch_candidates(db, collected, [])


def _avvisi(candidate: dict) -> frozenset[str]:
    return frozenset(str(avviso["id"]) for avviso in candidate["avvisi"])


class _Items:
    """Batch items by state; the latest failed item of a notice is the one to retry."""

    def __init__(self, db: Session):
        items = db.scalars(
            select(RuoloTributiReminderBatchItem).order_by(
                RuoloTributiReminderBatchItem.created_at, RuoloTributiReminderBatchItem.id
            )
        ).all()
        self.ready = {
            avviso
            for item in items
            if item.status in READY
            for avviso in item.avviso_ids_json or []
        }
        self.failed = {
            frozenset(item.avviso_ids_json or []): item
            for item in items
            if regeneration._retryable(item)
        }

    def state(self, candidate: dict) -> tuple[str, RuoloTributiReminderBatchItem | None]:
        avvisi = _avvisi(candidate)
        if avvisi <= self.ready:
            return "ready", None
        failed = self.failed.get(avvisi)
        return ("failed", failed) if failed else ("missing", None)


def year_status(db: Session, year: int) -> dict:
    items = _Items(db)
    status = {"year": year, "total": 0, "ready": 0, "failed": [], "missing": []}
    for candidate in _candidates(db, year):
        state, item = items.state(candidate)
        status["total"] += 1
        if state == "ready":
            status["ready"] += 1
        elif state == "failed":
            status["failed"].append(
                {"item_id": item.id, "label": item.display_name or item.codice_fiscale}
            )
        else:
            label = candidate.get("display_name") or candidate["codice_fiscale"]
            status["missing"].append({"label": label, "avviso_ids": sorted(_avvisi(candidate))})
    return status


def generate_missing(db: Session, year: int, avviso_ids: list[UUID], *, actor_id: int):
    """One batch for the requested notices that are still missing; None when none is left."""
    requested = {str(value) for value in avviso_ids}
    registered = db.scalars(
        select(RuoloAvviso.codice_fiscale_raw).where(RuoloAvviso.id.in_(avviso_ids))
    )
    tax_codes = sorted({code for code in map(repo._normalise_tax_code, registered) if code})
    items = _Items(db)
    missing = [
        candidate
        for candidate in (_candidates(db, year, tax_codes) if tax_codes else [])
        if _avvisi(candidate) <= requested and items.state(candidate)[0] == "missing"
    ]
    if not missing:
        return None
    return repo.generate_reminder_batch(
        db,
        missing,
        title=f"Solleciti {year}",
        filters_json={"years": [year], "manager_key": MANAGER_KEY},
        template_path=None,
        notes=f"Generato da «Avvisi da sollecitare» per l'anno {year}.",
        generated_by=actor_id,
    )
