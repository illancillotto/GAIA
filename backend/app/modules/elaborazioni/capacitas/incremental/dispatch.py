"""Transactional, targeted active application through canonical inCASS/Ruolo services."""

from datetime import datetime

from sqlalchemy import func, select, union_all

from app.modules.elaborazioni.capacitas.apps import get_capacitas_app
from app.modules.elaborazioni.capacitas.apps.incass.parsers import parse_incass_search_result
from app.modules.elaborazioni.capacitas.incremental.journal import pending_changes
from app.modules.elaborazioni.capacitas.incremental.models import (
    IncrementalChange,
    IncrementalCycle,
    IncrementalHead,
)
from app.modules.elaborazioni.capacitas.incremental.normalize import (
    MONEY,
    SnapshotInvalid,
    canonical_row,
)
from app.modules.elaborazioni.capacitas.recovery_identity import audit_recovery_subjects
from app.modules.elaborazioni.capacitas.recovery_ruolo import reconcile_subject_ruolo
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPaymentNotice, AnagraficaPerson
from app.services.elaborazioni_capacitas_incass import _run_incass_retryable, _upsert_payment_notice


def resolve_owner(db, row: dict, existing):
    identifier = row.get("CodFisc")
    if not identifier:
        raise SnapshotInvalid("missing_tax_identifier")
    candidate_ids = identity_candidates(db, identifier)
    if not candidate_ids:
        raise SnapshotInvalid("ambiguous_tax_identity")
    records, _ = audit_recovery_subjects(db, candidate_ids)
    matches = [record for record in records if identifier in record.identifiers]
    if len(matches) != 1 or matches[0].requires_review:
        raise SnapshotInvalid("ambiguous_tax_identity")
    owner = matches[0]
    if existing and existing.subject_id != owner.subject_id:
        raise SnapshotInvalid("notice_owner_changed")
    return owner


def identity_candidates(db, identifier: str) -> list:
    candidates = union_all(
        select(AnagraficaPerson.subject_id).where(
            func.upper(func.trim(AnagraficaPerson.codice_fiscale)) == identifier
        ),
        select(AnagraficaCompany.subject_id).where(
            func.upper(func.trim(AnagraficaCompany.codice_fiscale)) == identifier
        ),
        select(AnagraficaCompany.subject_id).where(
            func.upper(func.trim(AnagraficaCompany.partita_iva)) == identifier
        ),
    ).subquery()
    return list(db.scalars(select(candidates.c.subject_id).distinct()))


def check_drift(existing, change, acquired_at: datetime) -> None:
    if existing is None:
        if change.kind != "new":
            raise SnapshotInvalid("notice_missing_from_database")
        return
    current = canonical_row(existing.raw_row_json or {})
    keys = change.new.keys()
    relevant = {key: current.get(key) for key in keys}
    if relevant == change.new:
        return  # An ordinary sync has already observed the same row.
    if existing.synced_at and existing.synced_at.timestamp() > acquired_at.timestamp():
        raise SnapshotInvalid("newer_ordinary_sync")
    if relevant != change.old:
        raise SnapshotInvalid("database_row_drift")


def notice_row(raw: dict):
    # Canonical parser expects Italian amounts. Do not send decimal-dot text to it.
    payload = {
        key: value.replace(".", ",") if key in MONEY and value else value
        for key, value in raw.items()
    }
    return parse_incass_search_result(
        [payload], base_url=get_capacitas_app("incass").base_url
    ).rows[0]


async def recover_payload(client, row, existing):
    detail = await _run_incass_retryable(
        client, lambda: client.fetch_notice_detail(row.avviso), label="incremental_detail"
    )
    partitario = await _run_incass_retryable(
        client, lambda: client.fetch_notice_partitario(row.avviso), label="incremental_partitario"
    )
    if partitario is None or not partitario.partite:
        raise SnapshotInvalid("partitario_unavailable")
    if detail.avviso != row.avviso or partitario.avviso != row.avviso:
        raise SnapshotInvalid("heavy_notice_mismatch")
    payload = dict(existing.raw_detail_json or {}) if existing else {}
    payload.update(detail.model_dump(mode="json"))
    payload["partitario"] = partitario.model_dump(mode="json")
    return detail, payload


async def apply_change(db, client, change, config):
    if change.action == "review":
        raise SnapshotInvalid("requires_review")
    cycle = db.get(IncrementalCycle, change.cycle_id)
    existing = db.scalar(
        select(AnagraficaPaymentNotice)
        .where(
            AnagraficaPaymentNotice.source_system == "incass",
            AnagraficaPaymentNotice.source_notice_id == change.notice_key,
        )
        .with_for_update()
    )
    owner = resolve_owner(db, change.new, existing)
    check_drift(existing, change, cycle.acquired_at)
    if existing is None and not config.allow_new:
        raise SnapshotInvalid("new_notice_bootstrap_disabled")
    row = notice_row(change.new)
    heavy = needs_recovery(change, existing)
    recovered = await recover_payload(client, row, existing) if heavy else None
    _upsert_payment_notice(
        db,
        subject_id=owner.subject_id,
        identifier=row.codice_fiscale,
        display_name=owner.display_name,
        row=row,
        detail_info_html=None,
        detail_info_text=None,
        pdf_links_json=[],
        detail_payload=None,
        existing=existing,
        preserve_heavy_fields=True,
    )
    db.flush()
    if recovered:
        store_recovery(db, change.notice_key, recovered)
    reconciliation = reconcile_subject_ruolo(db, owner.subject_id)
    change.result = {
        "subject_id": str(owner.subject_id),
        "heavy": heavy,
        "reconciliation": reconciliation,
    }
    change.status = "succeeded"
    db.commit()  # Receipt and domain update are indivisible; replay cannot apply twice.


def needs_recovery(change, existing) -> bool:
    if change.action in {"recover", "audit"}:
        return True
    if existing is None:
        return True
    partitario = (existing.raw_detail_json or {}).get("partitario") or {}
    return not partitario.get("partite")


def store_recovery(db, key, recovered) -> None:
    existing = db.scalar(
        select(AnagraficaPaymentNotice).where(
            AnagraficaPaymentNotice.source_system == "incass",
            AnagraficaPaymentNotice.source_notice_id == key,
        )
    )
    detail, payload = recovered
    existing.raw_detail_json = payload
    existing.detail_info_html = detail.info_html or existing.detail_info_html
    existing.detail_info_text = detail.info_text or existing.detail_info_text
    links = {item["url"]: item for item in existing.pdf_links_json or []}
    links.update({item.url: item.model_dump(mode="json") for item in detail.pdf_links})
    existing.pdf_links_json = list(links.values()) or None


def record_failure(db, change_id: str, config, exc: Exception) -> None:
    db.rollback()
    change = db.get(IncrementalChange, change_id)
    change.attempts += 1
    permanent = isinstance(exc, SnapshotInvalid)
    change.status = "dead" if permanent or change.attempts >= config.max_attempts else "pending"
    reason = str(exc) if permanent else type(exc).__name__
    change.result = {"reason": reason, "fallback": "legacy_autosync_unchanged"}
    db.commit()


async def drain(db, client, config) -> int:
    if config.mode != "active":
        return 0
    completed = 0
    for change in pending_changes(db, config.max_jobs):
        change_id = change.id
        try:
            await apply_change(db, client, change, config)
            completed += 1
        except Exception as exc:
            record_failure(db, change_id, config, exc)
    _finish_audits(db)
    return completed


def _finish_audits(db) -> None:
    head = db.get(IncrementalHead, 1)
    cycles = db.scalars(
        select(IncrementalCycle).where(IncrementalCycle.status == "validated")
    ).all()
    for cycle in cycles:
        if not cycle.report.get("full_audit") or cycle.mode != "active":
            continue
        unfinished = db.scalar(
            select(IncrementalChange.id)
            .where(IncrementalChange.cycle_id == cycle.id, IncrementalChange.status != "succeeded")
            .limit(1)
        )
        if unfinished is None and cycle.acquired_at.timestamp() > head.full_audit_at.timestamp():
            head.full_audit_at = cycle.acquired_at
    db.commit()
