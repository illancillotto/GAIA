"""Recover section-rejected AutoSync requests without replacing their SISTER identity."""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.catasto import (
    CatastoBatch,
    CatastoPerpetualSyncItem,
    CatastoRuoloAutoSyncConfig,
    CatastoVisuraRequest,
)
from app.models.catasto_phase1 import CatParticella
from app.modules.elaborazioni.sister_autosync_refill import lock_refill_capacity
from app.modules.ruolo.models import RuoloParticella

_REMOTE_EVIDENCE_FIELDS = (
    "sister_remote_request_id",
    "sister_remote_request_url",
    "sister_remote_state",
    "sister_first_submitted_at",
    "document_id",
    "execution_token",
)


class _SectionOptions(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_section_select = False
        self.values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "select" and attributes.get("name") == "sezione":
            self.in_section_select = True
        elif tag == "option" and self.in_section_select:
            self.values.append((attributes.get("value") or "").strip())

    def handle_endtag(self, tag: str) -> None:
        if tag == "select":
            self.in_section_select = False


def _has_section_evidence(artifact_dir: str | None, section: str, debug_root: Path) -> bool:
    if not artifact_dir:
        return False
    root = debug_root.resolve()
    preview = (Path(artifact_dir) / "final-failed.html").resolve()
    if not preview.is_relative_to(root) or not preview.is_file():
        return False
    try:
        html = preview.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    normalized = unescape(html).upper()
    if not any(
        marker in normalized
        for marker in ("LA SEZIONE È OBBLIGATORIA", "LA SEZIONE E' OBBLIGATORIA")
    ):
        return False
    options = _SectionOptions()
    options.feed(html)
    return options.values.count(section) == 1


def _eligible(
    request: CatastoVisuraRequest, item: CatastoPerpetualSyncItem, section: str, debug_root: Path
) -> bool:
    if (request.status, item.status, request.sezione, item.sezione) != (
        "failed",
        "failed",
        None,
        section,
    ) or not section:
        return False
    if not 0 < request.attempts < 3 or not (request.error_message or "").startswith(
        f"Submit visura non avanzato per richiesta {request.id}:"
    ):
        return False
    if any(getattr(request, field) is not None for field in _REMOTE_EVIDENCE_FIELDS):
        return False
    if request.last_error_code is not None:
        return False
    if (request.comune, request.foglio, request.particella) != (
        item.comune,
        item.foglio,
        item.particella,
    ):
        return False
    return _has_section_evidence(request.artifact_dir, section, debug_root)


def _candidate_statement(batch_id: UUID, request_id: UUID | None):
    statement = (
        select(CatastoVisuraRequest, CatastoPerpetualSyncItem, CatParticella.sezione_catastale)
        .join(
            CatastoPerpetualSyncItem,
            CatastoPerpetualSyncItem.linked_request_id == CatastoVisuraRequest.id,
        )
        .join(RuoloParticella, RuoloParticella.id == CatastoPerpetualSyncItem.ruolo_particella_id)
        .join(CatParticella, CatParticella.id == CatastoPerpetualSyncItem.cat_particella_id)
        .where(
            CatastoVisuraRequest.batch_id == batch_id,
            CatastoVisuraRequest.status == "failed",
            CatastoVisuraRequest.sezione.is_(None),
            CatastoPerpetualSyncItem.status == "failed",
            CatastoPerpetualSyncItem.scope == "ruolo_particella",
            CatastoPerpetualSyncItem.linked_batch_id == batch_id,
            RuoloParticella.cat_particella_match_status == "matched",
            RuoloParticella.cat_particella_id == CatParticella.id,
            CatastoPerpetualSyncItem.sezione == CatParticella.sezione_catastale,
        )
        .order_by(CatastoVisuraRequest.created_at.desc())
        .with_for_update(of=(CatastoVisuraRequest, CatastoPerpetualSyncItem), skip_locked=True)
    )
    return statement.where(CatastoVisuraRequest.id == request_id) if request_id else statement


def _queue_original_request(
    request: CatastoVisuraRequest, item: CatastoPerpetualSyncItem, section: str
) -> None:
    request.sezione = section
    request.status = "pending"
    request.current_operation = f"Retry mirato con sezione catastale {section} verificata"
    request.processed_at = None
    request.retry_not_before = None
    item.status = "queued"
    item.retry_after = None


def _recover_candidates(
    db: Session,
    batch_id: UUID,
    request_id: UUID | None,
    capacity: int,
    debug_root: Path,
    apply: bool,
) -> list[UUID]:
    recovered: list[UUID] = []
    for request, item, section in db.execute(_candidate_statement(batch_id, request_id)):
        if not _eligible(request, item, section, debug_root):
            continue
        recovered.append(request.id)
        if apply:
            _queue_original_request(request, item, section)
        if len(recovered) == capacity:
            break
    return recovered


def recover_required_sections(
    db: Session,
    batch_id: UUID,
    *,
    limit: int,
    debug_root: Path,
    apply: bool = False,
    request_id: UUID | None = None,
) -> list[UUID]:
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    try:
        batch = db.get(CatastoBatch, batch_id, with_for_update=True)
        if batch is None or batch.batch_kind != "perpetual_sync" or batch.status != "processing":
            raise ValueError("batch must be a processing perpetual_sync batch")
        batch_size = db.scalar(
            select(CatastoRuoloAutoSyncConfig.batch_size).where(
                CatastoRuoloAutoSyncConfig.user_id == batch.user_id
            )
        )
        if batch_size is None:
            raise ValueError("AutoSync configuration is missing")
        capacity = min(limit, lock_refill_capacity(db, batch, batch_size, datetime.now(UTC)))
        recovered = (
            _recover_candidates(db, batch_id, request_id, capacity, debug_root, apply)
            if capacity
            else []
        )
        if apply:
            db.commit()
        else:
            db.rollback()
        return recovered
    except Exception:
        db.rollback()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch_id", type=UUID)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--request-id", type=UUID)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    debug_root = Path(os.getenv("ELABORAZIONI_DEBUG_ARTIFACTS_PATH", "/data/catasto/debug"))
    with SessionLocal() as db:
        recovered = recover_required_sections(
            db,
            args.batch_id,
            limit=args.limit,
            debug_root=debug_root,
            apply=args.apply,
            request_id=args.request_id,
        )
    print(f"{'queued' if args.apply else 'eligible'}: {len(recovered)}")
    for request_id in recovered:
        print(request_id)


if __name__ == "__main__":
    main()
