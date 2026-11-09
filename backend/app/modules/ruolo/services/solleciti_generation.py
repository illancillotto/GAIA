"""Generate only missing eligible notices for an exact CF/P.IVA and reference year."""

import hashlib

from sqlalchemy import select, text

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloTributiReminderBatchItem as Item
from app.modules.ruolo.services import year_notice_generation as generation
from app.modules.ruolo.services.poste_dispatch_state import DispatchConflict


def _lock(db, year, tax_code):
    if db.get_bind().dialect.name == "postgresql":
        key = int.from_bytes(
            hashlib.sha256(f"solleciti:{year}:{tax_code}".encode()).digest()[:8], signed=True
        )
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def generate(db, *, year, tax_code, actor_id):
    _lock(db, year, tax_code)
    candidates = generation._candidates(db, year, [tax_code])
    if not candidates:
        raise DispatchConflict("Nessun avviso eleggibile per questo CF/P.IVA e anno")
    existing = list(
        db.scalars(
            select(Item)
            .where(Item.status == "generated", Item.generated_document_path.ilike("%.pdf"))
            .order_by(Item.created_at, Item.id)
        )
    )
    ready = {frozenset(item.avviso_ids_json or []): item.id for item in existing}
    reused = [ready[generation._avvisi(c)] for c in candidates if generation._avvisi(c) in ready]
    missing = [c for c in candidates if generation._avvisi(c) not in ready]
    created = []
    if missing:
        batch = repo.generate_reminder_batch(
            db,
            missing,
            title=f"Solleciti {year} · {tax_code}",
            filters_json={"years": [year], "manager_key": generation.MANAGER_KEY},
            template_path=None,
            notes="Generazione operatore da CF/P.IVA",
            generated_by=actor_id,
        )
        created = repo.list_reminder_batch_items(db, batch.id)
    return {
        "reused": reused,
        "created": [item.id for item in created],
        "problems": [
            {"item_id": item.id, "detail": item.error_detail or "PDF non disponibile"}
            for item in created
            if item.status != "generated"
        ],
    }
