"""Final integration contracts across migrations, accounting and the outbox."""

from decimal import Decimal
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file

from app.modules.communications import ruolo_source
from app.modules.elaborazioni.step.models import (
    StepContribuente,
    StepCredential,
    StepDocumento,
    StepRuoloLink,
    StepSyncJob,
)
from app.modules.ruolo import tributi_repositories as accounting
from app.modules.ruolo.models import (
    RuoloAvviso,
    RuoloTributiAvvisoStatus,
    RuoloTributiCalculationPolicy,
    RuoloTributiNote,
    RuoloTributiPayment,
    RuoloTributiYearManager,
)
from app.modules.utenze.models import AnagraficaPaymentNotice

from .conftest import approved, metadata

REAL_ACCOUNTING = accounting.get_tributi_avviso


def test_sqlite_migration_roundtrip_preserves_parents_and_seeds_only_drafts():
    """Keep the non-PG migration path compatible with the isolated API test DB."""
    parent = metadata()
    for table in list(parent.tables.values()):
        if table.name.startswith("communication_"):
            parent.remove(table)
    engine = sa.create_engine("sqlite://")
    folder = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    current = load_python_file(str(folder), "20261103_1200_communications.py")
    try:
        with engine.begin() as connection:
            parent.create_all(connection)
            original = set(sa.inspect(connection).get_table_names())
            with Operations.context(MigrationContext.configure(connection)):
                current.upgrade()
                assert connection.scalar(sa.text("SELECT paused FROM communication_controls")) == 1
                assert connection.execute(
                    sa.text(
                        "SELECT channel, version, status FROM communication_templates ORDER BY channel"
                    )
                ).all() == [("email", 1, "draft"), ("pec", 1, "draft")]
                assert len(set(sa.inspect(connection).get_table_names()) - original) == 11
                current.downgrade()
                assert set(sa.inspect(connection).get_table_names()) == original
                current.upgrade()
                assert (
                    connection.scalar(sa.text("SELECT count(*) FROM communication_templates")) == 2
                )
    finally:
        engine.dispose()


def test_real_accounting_payment_blocks_an_already_reviewed_dispatch(api, monkeypatch):
    """A persisted payment must veto dispatch through the real Ruolo repository."""
    source = metadata()
    for model in (
        RuoloTributiAvvisoStatus,
        RuoloTributiCalculationPolicy,
        RuoloTributiNote,
        RuoloTributiYearManager,
        AnagraficaPaymentNotice,
        StepCredential,
        StepSyncJob,
        StepContribuente,
        StepDocumento,
        StepRuoloLink,
    ):
        model.__table__.to_metadata(source)
    source.create_all(api.engine)
    monkeypatch.setattr(ruolo_source.repo, "get_tributi_avviso", REAL_ACCOUNTING)
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        avviso_id = UUID(item.avviso_ids_json[0])
        db.get(RuoloAvviso, avviso_id).importo_totale_euro = Decimal("10.00")
        db.commit()
    # The real default keeps 2021 with STEP: only an explicit reviewed override
    # permits internal GAIA processing. No production manager is changed here.
    response = api.client.get(f"/communications/ruolo/candidates/{api.source_id}/eligibility")
    assert response.status_code == 409
    assert "gestione_esterna" in response.json()["detail"]
    with api.session() as db:
        accounting.upsert_year_manager(
            db,
            manager_key="gaia",
            manager_label="Synthetic GAIA review",
            year_from=2021,
            year_to=2021,
            calculation_policy="internal_gaia",
            is_active=True,
            notes="Synthetic only",
            updated_by=1,
        )
        db.commit()
    message = approved(api)
    with api.session() as db:
        db.add(RuoloTributiPayment(avviso_id=avviso_id, amount=Decimal("10.00"), source="manual"))
        db.commit()
    base = f"/communications/messages/{message['id']}"
    response = api.client.post(f"{base}/dispatch", json={"expected_version": 1})
    assert response.status_code == 409
    assert "non eleggibile" in response.json()["detail"]
    assert api.client.get(base).json()["state"] == "approved"
    assert api.client.get("/communications/jobs").json() == []
