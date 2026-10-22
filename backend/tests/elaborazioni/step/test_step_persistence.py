from __future__ import annotations

import copy
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from step_fixtures import add_avviso, scheda, summary, tributo

from app.modules.elaborazioni.step.models import (
    StepDocumento,
    StepObservation,
    StepPagamento,
    StepRuoloLink,
    StepTributo,
)
from app.modules.elaborazioni.step.persistence import (
    StoredPdf,
    needs_detail,
    persist_scheda,
    summary_key,
    upsert_summary,
)
from app.modules.elaborazioni.step.ruolo_link import link_documents, relink_all

NOW = datetime(2026, 10, 21, tzinfo=UTC)


def store(_contribuente, entry: dict) -> StoredPdf:
    return StoredPdf(
        status="downloaded", path="14215/aa/x.pdf", sha256="x", bytes=3, original_filename="Doc.pdf"
    )


def test_summary_key_requires_identity() -> None:
    assert summary_key(summary()) == ("14215", "RSSMRA80A01G113X")
    with pytest.raises(ValueError, match="codice"):
        summary_key({"COD_ENT": "14215"})


def test_upsert_summary_detects_changes_and_detail_needs(db) -> None:
    first = upsert_summary(db, summary(), job_id=None, now=NOW)
    assert first.created and first.summary_changed
    assert first.contribuente.importo == Decimal("1405.12")
    assert needs_detail(first.contribuente)

    persist_scheda(db, scheda(), job_id=None, now=NOW, pdf_store=store)
    same = upsert_summary(db, summary(), job_id=None, now=NOW)
    assert not same.created and not same.summary_changed
    assert not needs_detail(same.contribuente)

    accrued = upsert_summary(
        db, summary(RESIDUO="1.405,15", IMPORTO_AGGIORNATO="1.405,15"), job_id=None, now=NOW
    )
    assert accrued.summary_changed and accrued.contribuente.residuo == Decimal("1405.15")
    assert not needs_detail(accrued.contribuente)

    changed = upsert_summary(db, summary(PAGATO="10,00"), job_id=None, now=NOW)
    assert changed.summary_changed
    assert needs_detail(changed.contribuente)


def test_persist_scheda_writes_snapshot_and_history(db) -> None:
    result = persist_scheda(db, scheda(), job_id=None, now=NOW, pdf_store=store)
    db.commit()

    assert (
        result.changed and result.documents == 1 and result.tributi == 1 and result.pagamenti == 2
    )
    contribuente = result.contribuente
    assert contribuente.anagrafica_json == {
        "Codice fiscale": "RSSMRA80A01G113X",
        "Denominazione": "ROSSI MARIO",
    }
    assert contribuente.sections_json[0] == {
        "section": "Documenti Emessi",
        "fields": ["NUM_DOC", "NUM_TRIB"],
        "rows": scheda()["sections"][0]["rows"],
    }
    documento = db.scalar(select(StepDocumento))
    assert documento.section == "Documenti Emessi"
    assert documento.data_notifica.isoformat() == "2024-11-16"
    assert documento.pdf_status == "downloaded" and documento.pdf_path == "14215/aa/x.pdf"
    tributo_row = db.scalar(select(StepTributo))
    assert tributo_row.codice_cnc == "020190006018040" and tributo_row.anno_rif == 2019
    pagamenti = db.scalars(select(StepPagamento).order_by(StepPagamento.position)).all()
    assert pagamenti[0].documento_id == documento.id and pagamenti[0].importo == Decimal("1869.26")
    assert (
        pagamenti[1].documento_id is None
        and pagamenti[1].annullato
        and pagamenti[1].data_pagamento is None
    )
    assert db.scalar(select(StepObservation)).kind == "scheda"

    unchanged = persist_scheda(db, scheda(), job_id=None, now=NOW, pdf_store=store)
    assert not unchanged.changed and unchanged.document_ids == ()

    updated = scheda(
        tributi=[tributo("20241421500000003", "Avv. N. 020190006018040 Not.", IMP_CAR="60,00")]
    )
    rewritten = persist_scheda(db, updated, job_id=None, now=NOW, pdf_store=store)
    db.commit()
    assert rewritten.changed
    assert db.scalar(select(StepTributo)).imp_carico == Decimal("60.00")
    assert len(db.scalars(select(StepObservation)).all()) == 2


def test_persist_scheda_rejects_inconsistent_schede(db) -> None:
    wrong_person = scheda()
    wrong_person["anagrafica"]["Codice fiscale"] = "OTHER"
    with pytest.raises(ValueError, match="contribuente diverso"):
        persist_scheda(db, wrong_person, job_id=None, now=NOW, pdf_store=store)

    partial = scheda()
    partial["documents"][0]["document"]["NUM_TRIB"] = "2"
    with pytest.raises(ValueError, match="Tributi incompleti"):
        persist_scheda(db, partial, job_id=None, now=NOW, pdf_store=store)


def _links(db) -> dict[str, StepRuoloLink]:
    return {link.reference_key: link for link in db.scalars(select(StepRuoloLink)).all()}


def test_links_are_exact_and_fail_closed(db) -> None:
    linked_id = add_avviso(db, "020190006018040", 2019)
    add_avviso(db, "020200000000010", 2020)
    narrowed_id = add_avviso(db, "020200000000010", 2021)
    add_avviso(db, "020210000000020", 2018)
    add_avviso(db, "020210000000020", 2017)
    num_doc = "20241421500000003"
    rows = [
        tributo(num_doc, "Avv. N. 020190006018040 Not. 31/01/2021", "2019", IMP_CAR="50,00"),
        tributo(
            num_doc, "Avv. N. 020190006018040 Not. 31/01/2021", "2019", IMP_CAR="3,00", PRG="2"
        ),
        tributo(num_doc, "Avv. N. 020200000000010 Not.", "2021"),
        tributo(num_doc, "Avv. N. 020210000000020 Not.", "2021"),
        tributo(num_doc, "Avv. N. 020219999999990 Not.", "2021"),
        tributo(num_doc, "Quota scarichi - Avv. PG13319 not.", "2023", IMP_CAR=None),
        tributo(num_doc, "Avv. N. 020200000000030 Not.", "2019"),
        tributo(num_doc, "Avv. N. 020200000000030 Not.", "2020"),
        tributo(num_doc, None, "anno"),
    ]
    result = persist_scheda(db, scheda(tributi=rows), job_id=None, now=NOW, pdf_store=store)
    counts = link_documents(db, list(result.document_ids), now=NOW)
    db.commit()

    links = _links(db)
    assert counts == {"linked": 2, "not_found": 2, "ambiguous": 1, "unrecognized": 2}
    assert links["020190006018040"].ruolo_avviso_id == linked_id
    assert links["020190006018040"].tributi_count == 2
    assert links["020190006018040"].imp_carico == Decimal("53.00")
    assert links["020200000000010"].ruolo_avviso_id == narrowed_id
    assert links["020210000000020"].status == "ambiguous"
    assert len(links["020210000000020"].candidate_avviso_ids) == 2
    assert links["020219999999990"].status == "not_found"
    assert (
        links["020200000000030"].status == "not_found" and links["020200000000030"].anno_rif is None
    )
    assert links["Quota scarichi - Avv. PG13319 not."].status == "unrecognized"
    assert links["(assente)"].status == "unrecognized"
    assert link_documents(db, [], now=NOW) == dict.fromkeys(counts, 0)


def test_relink_all_reparses_stored_raw_rows(db) -> None:
    avviso_id = add_avviso(db, "020190006018040", 2019)
    persist_scheda(db, scheda(), job_id=None, now=NOW, pdf_store=store)
    stored = db.scalar(select(StepTributo))
    stored.codice_cnc = None
    stored.raw_json = copy.deepcopy(stored.raw_json)
    db.commit()

    assert relink_all(db, now=NOW, batch_size=1) == {
        "linked": 1,
        "not_found": 0,
        "ambiguous": 0,
        "unrecognized": 0,
    }
    assert db.scalar(select(StepTributo)).codice_cnc == "020190006018040"
    assert db.scalar(select(StepRuoloLink)).ruolo_avviso_id == avviso_id


def test_links_without_recognized_codes_skip_the_avviso_lookup(db) -> None:
    rows = [tributo("20241421500000003", "Quota scarichi - Avv. PG1346 not.", "2023")]
    result = persist_scheda(db, scheda(tributi=rows), job_id=None, now=NOW, pdf_store=store)
    assert link_documents(db, list(result.document_ids), now=NOW)["unrecognized"] == 1
