import asyncio
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.modules.elaborazioni.capacitas.incremental import dispatch as d
from app.modules.elaborazioni.capacitas.incremental.journal import begin_cycle
from app.modules.elaborazioni.capacitas.incremental.models import (
    IncrementalChange,
    IncrementalHead,
)
from app.modules.elaborazioni.capacitas.incremental.normalize import SnapshotInvalid, canonical_row
from app.modules.elaborazioni.capacitas.models import (
    CapacitasInCassNoticeDetail,
    CapacitasInCassNoticePdf,
    CapacitasInCassPartitarioDetail,
    CapacitasInCassPartitarioPartita,
)
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPaymentNotice, AnagraficaSubject
from app.services.elaborazioni_capacitas_incass import _upsert_payment_notice

from .conftest import CF, NOTICE, NOW, raw_row


class HeavyClient:
    def __init__(self):
        self.calls = []
        self.missing = False
        self.mismatch = False

    async def fetch_notice_detail(self, key):
        self.calls.append(("detail", key))
        return CapacitasInCassNoticeDetail(
            avviso=key,
            detail_url="https://fixture/detail",
            info_html="<p>detail</p>",
            info_text="detail",
            pdf_links=[CapacitasInCassNoticePdf(url="https://fixture/new.pdf")],
        )

    async def fetch_notice_partitario(self, key):
        self.calls.append(("partitario", key))
        if self.missing:
            return None
        return CapacitasInCassPartitarioDetail(
            avviso="different" if self.mismatch else key,
            partite=[
                CapacitasInCassPartitarioPartita(
                    codice_partita="1", comune_nome="TEST", importo_0648_euro="1000,00"
                )
            ],
        )


def seed_notice(db, owner, raw=None, heavy=True):
    raw = raw or raw_row()
    row = d.notice_row(canonical_row(raw))
    _upsert_payment_notice(
        db,
        subject_id=owner.id,
        identifier=CF,
        display_name="TEST",
        row=row,
        detail_info_html="original-html",
        detail_info_text="original-text",
        pdf_links_json=[{"url": "https://fixture/original.pdf", "document_id": "kept"}],
        detail_payload={
            "mailing_list": {"preserve": True},
            "partitario": {
                "partite": [
                    {
                        "codice_partita": "1",
                        "comune_nome": "TEST",
                        "importo_0648_euro": "1000,00",
                        "particelle": [],
                    }
                ]
            },
        }
        if heavy
        else None,
    )
    notice = db.scalar(select(AnagraficaPaymentNotice))
    notice.synced_at = NOW - timedelta(days=1)
    db.commit()
    return notice


def change(db, config, before=None, after=None, action="summary", kind="changed", key=NOTICE):
    cycle = begin_cycle(db, config, NOW)
    cycle.status = "validated"
    item = IncrementalChange(
        id=key,
        cycle_id=cycle.id,
        notice_key=key,
        kind=kind,
        action=action,
        status="pending",
        fields={},
        old=canonical_row(before or raw_row()),
        new=canonical_row(after or raw_row(Riscosso="10,00", Differenza="990,00")),
    )
    db.add(item)
    db.commit()
    return item


def active(config):
    return config.model_copy(
        update={"mode": "active", "schema_verified": True, "sample_size": 1, "full_audit_days": 7}
    )


def test_payment_only_uses_canonical_upsert_without_heavy_http(db, config, owner):
    notice = seed_notice(db, owner)
    original = notice.raw_detail_json.copy()
    item = change(db, config)
    client = HeavyClient()
    assert asyncio.run(d.drain(db, client, config)) == 0  # shadow never dispatches
    assert asyncio.run(d.drain(db, client, active(config))) == 1
    assert not client.calls
    assert notice.importo_riscosso == "10,00" and notice.importo_residuo == "990,00"
    assert notice.stato_label == "Parzialmente pagato"
    assert notice.raw_detail_json == original and notice.detail_info_html == "original-html"
    assert notice.pdf_links_json[0]["document_id"] == "kept"
    assert item.result["heavy"] is False
    assert asyncio.run(d.drain(db, client, active(config))) == 0


@pytest.mark.parametrize("new_notice", [False, True])
def test_recovery_targets_only_avviso_and_preserves_other_heavy_fields(
    db, config, owner, new_notice
):
    notice = None if new_notice else seed_notice(db, owner, heavy=False)
    item = change(db, config, kind="new" if new_notice else "changed", action="recover")
    cfg = active(config)
    cfg.allow_new = True
    client = HeavyClient()
    asyncio.run(d.apply_change(db, client, item, cfg))
    assert client.calls == [("detail", NOTICE), ("partitario", NOTICE)]
    notice = db.scalar(select(AnagraficaPaymentNotice))
    assert notice.raw_detail_json["partitario"]["partite"]
    assert notice.detail_info_text == "detail"
    assert len(notice.pdf_links_json) == (1 if new_notice else 2)
    assert item.result["reconciliation"]["notices_reconciled"] == 1


def test_missing_heavy_causes_controlled_recovery_and_no_partial_write(db, config, owner):
    notice = seed_notice(db, owner, heavy=False)
    item = change(db, config)
    client = HeavyClient()
    client.missing = True
    assert asyncio.run(d.drain(db, client, active(config))) == 0
    assert item.status == "dead" and item.result["reason"] == "partitario_unavailable"
    assert notice.importo_riscosso == "0,00" and notice.raw_detail_json is None


def test_heavy_payload_merge_and_mismatch(db, config, owner):
    notice = seed_notice(db, owner)
    client = HeavyClient()
    row = d.notice_row(canonical_row(raw_row()))
    detail, payload = asyncio.run(d.recover_payload(client, row, notice))
    assert payload["mailing_list"] == {"preserve": True}
    detail.info_html = detail.info_text = None
    d.store_recovery(db, NOTICE, (detail, payload))
    assert notice.detail_info_text == "original-text"
    client.mismatch = True
    with pytest.raises(SnapshotInvalid, match="mismatch"):
        asyncio.run(d.recover_payload(client, row, notice))


@pytest.mark.parametrize(
    "problem",
    [
        "review",
        "missing_cf",
        "ambiguous",
        "owner_changed",
        "missing_db",
        "new_disabled",
        "drift",
        "newer",
        "requires_review",
    ],
)
def test_unsafe_changes_are_dead_letter_without_mutation(db, config, owner, problem):
    notice = None if problem in {"missing_db", "new_disabled"} else seed_notice(db, owner)
    after = raw_row(Riscosso="10,00", Differenza="990,00")
    if problem == "missing_cf":
        after["CodFisc"] = None
    if problem == "ambiguous":
        after["CodFisc"] = "UNKNOWN"
    if problem == "owner_changed":
        other = AnagraficaSubject(subject_type="person", source_name_raw="OTHER")
        db.add(other)
        db.flush()
        notice.subject_id = other.id
    if problem == "requires_review":
        owner.requires_review = True
    if problem in {"drift", "newer"}:
        notice.raw_row_json = raw_row(Riscosso="99,00")
        if problem == "newer":
            notice.synced_at = NOW + timedelta(hours=1)
    db.commit()
    item = change(
        db,
        config,
        after=after,
        action="review" if problem == "review" else "summary",
        kind="new" if problem == "new_disabled" else "changed",
    )
    assert asyncio.run(d.drain(db, HeavyClient(), active(config))) == 0
    assert item.status == "dead" and item.result["fallback"] == "legacy_autosync_unchanged"
    if notice:
        assert notice.importo_riscosso == "0,00"


def test_already_observed_row_and_failure_retries(db, config, owner, monkeypatch):
    notice = seed_notice(db, owner, raw_row(Riscosso="10,00", Differenza="990,00"))
    notice.synced_at = NOW + timedelta(hours=1)
    item = change(db, config)
    d.check_drift(notice, item, NOW)
    attempts = []

    async def fail(*args):
        attempts.append(1)
        raise TimeoutError("private upstream URL must not be stored")

    monkeypatch.setattr(d, "apply_change", fail)
    cfg = active(config)
    for expected in range(1, cfg.max_attempts + 1):
        assert asyncio.run(d.drain(db, HeavyClient(), cfg)) == 0
        assert item.attempts == expected
    assert item.status == "dead" and item.result["reason"] == "TimeoutError"
    assert len(attempts) == 3


def test_complete_full_audit_only_after_all_receipts(db, config):
    cycle = begin_cycle(db, config, NOW)
    cycle.status = "validated"
    cycle.report = {"full_audit": True}
    head = db.get(IncrementalHead, 1)
    head.full_audit_at = NOW - timedelta(days=10)
    item = change(db, config, action="audit")
    cycle.mode = "active"
    db.commit()
    d._finish_audits(db)
    assert head.full_audit_at < NOW
    item.status = "succeeded"
    db.commit()
    d._finish_audits(db)
    assert head.full_audit_at == NOW
    d._finish_audits(db)


def test_needs_recovery_variants():
    assert d.needs_recovery(SimpleNamespace(action="summary"), None)
    assert d.needs_recovery(
        SimpleNamespace(action="summary"), SimpleNamespace(raw_detail_json=None)
    )
    assert d.needs_recovery(
        SimpleNamespace(action="summary"), SimpleNamespace(raw_detail_json={"partitario": None})
    )


def test_shared_person_company_fiscal_identity_is_never_guessed(db, owner):
    company = AnagraficaSubject(subject_type="company", source_name_raw="TEST COMPANY")
    db.add(company)
    db.flush()
    db.add(
        AnagraficaCompany(
            subject_id=company.id,
            codice_fiscale=CF,
            partita_iva="00000000001",
            ragione_sociale="TEST COMPANY",
        )
    )
    db.commit()
    with pytest.raises(SnapshotInvalid, match="ambiguous_tax_identity"):
        d.resolve_owner(db, canonical_row(raw_row()), None)
