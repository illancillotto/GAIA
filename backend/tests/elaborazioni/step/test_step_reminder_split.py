from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy import select
from step_fixtures import add_avviso, scheda, tributo

from app.modules.elaborazioni.step.models import StepRuoloLink
from app.modules.elaborazioni.step.persistence import StoredPdf, persist_scheda
from app.modules.elaborazioni.step.ruolo_link import link_documents
from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.services.notice_eligibility import generation_allowed, manager_scope_clause

NOW = datetime(2026, 10, 23, 8, 0, tzinfo=UTC)


def _item(avviso_id, year: int = 2021) -> dict:
    return {"avviso": SimpleNamespace(id=avviso_id, anno_tributario=year)}


def test_2021_avvisi_handed_to_step_stay_with_step(db) -> None:
    assigned = add_avviso(db, "01.02021000000001", 2021)
    revoked = add_avviso(db, "01.02021000000002", 2021)
    free = add_avviso(db, "01.02021000000003", 2021)
    rows = [
        tributo("20241421500000003", "Avv. N. 020210000000010 Not.", anno="2021", PRG="1"),
        tributo(
            "20241421500000003",
            "Avv. N. 020210000000020 Not.",
            anno="2021",
            PRG="2",
            IMP_CARPAG="0,00",
            IMP_DIS="50,00",
        ),
    ]
    result = persist_scheda(
        db,
        scheda(tributi=rows),
        job_id=None,
        now=NOW,
        pdf_store=lambda *_: StoredPdf(status="unavailable", unavailable_reason="test"),
    )
    link_documents(db, list(result.document_ids), now=NOW)
    db.commit()
    linked = set(
        db.scalars(select(StepRuoloLink.ruolo_avviso_id).where(StepRuoloLink.status == "linked"))
    )
    assert linked == {assigned, revoked}

    # Still charged in STEP: not solicited by GAIA; discharged (revocato) or absent: GAIA.
    assert not generation_allowed(db, _item(assigned), True)
    assert generation_allowed(db, _item(revoked), True)
    assert generation_allowed(db, _item(free), True)
    assert not generation_allowed(db, _item(free), False)
    assert "ruolo_step_assigned_avviso_ids" in db.info


def test_gaia_manager_lists_leave_out_avvisi_kept_by_step(db) -> None:
    def listed(policy: str, year_clauses: list) -> set:
        manager = SimpleNamespace(calculation_policy=policy)
        return set(
            db.scalars(select(RuoloAvviso.id).where(manager_scope_clause(db, manager, year_clauses)))
        )

    assigned = add_avviso(db, "01.02021000000001", 2021)
    free = add_avviso(db, "01.02021000000003", 2021)
    reviewed = add_avviso(db, "01.02022000000001", 2022)
    # No STEP links yet: the year range alone decides.
    assert listed("internal_gaia", []) == {assigned, free, reviewed}
    db.info.pop("ruolo_step_assigned_avviso_ids")
    rows = [
        tributo("20241421500000003", "Avv. N. 020210000000010 Not.", anno="2021", PRG="1"),
        tributo("20241421500000003", "Avv. N. 020220000000010 Not.", anno="2022", PRG="2"),
    ]
    result = persist_scheda(
        db,
        scheda(tributi=rows),
        job_id=None,
        now=NOW,
        pdf_store=lambda *_: StoredPdf(status="unavailable", unavailable_reason="test"),
    )
    link_documents(db, list(result.document_ids), now=NOW)
    db.commit()
    assert {assigned, reviewed} <= set(
        db.scalars(select(StepRuoloLink.ruolo_avviso_id).where(StepRuoloLink.status == "linked"))
    )

    year_2021 = [RuoloAvviso.anno_tributario == 2021]
    assert listed("internal_gaia", year_2021) == {free}
    # 2022-2023 are reviewed by GAIA notice by notice: a STEP link does not hide them.
    assert listed("internal_gaia", []) == {free, reviewed}
    assert listed("external_recovery", year_2021) == {assigned, free}
