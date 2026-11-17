"""Anomaly checks must not deserialize the retained Capacitas source payloads."""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.catasto_phase1 import CatAnomalia
from app.modules.catasto.models.domande_irrigue import (
    CatDomandaIrrigua,
    CatDomandaIrriguaParticella,
)
from app.modules.catasto.services import domande_irrigue as service


@pytest.fixture
def database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.mark.parametrize("anno,expected_domande", [(None, 3), (2026, 2)])
def test_scan_preserves_anomalies_without_fetching_raw_json(database, anno, expected_domande):
    raw = {"retained_source": [{"text": "x" * 100_000}]}
    with Session(database) as db:
        for number, day, surface in [("100", 20, 60), ("101", 32, 50)]:
            domanda = CatDomandaIrrigua(
                anno=2026,
                domanda_numero=number,
                stato="Attiva",
                data_ins=datetime(2026, 4 if day == 20 else 5, 20 if day == 20 else 2),
                autorinnovo=False,
                raw_payload_json=raw,
            )
            db.add(domanda)
            db.flush()
            db.add(
                CatDomandaIrriguaParticella(
                    domanda_id=domanda.id,
                    foglio="10",
                    particella="88",
                    part_com="179",
                    coltura="Mais",
                    sup_cat_mq=Decimal("100"),
                    sup_irr_mq=Decimal(surface),
                    raw_payload_json=raw,
                )
            )
        db.add(CatDomandaIrrigua(anno=2025, autorinnovo=True, raw_payload_json=raw))
        db.add(
            CatAnomalia(
                tipo=service.DIR_ANOMALIA_SUPERFICIE_COLTURA,
                anno_campagna=2026,
                status="aperta",
                severita="error",
                descrizione="Previous parcel group",
                dati_json={"group_key": "previous-group"},
            )
        )
        db.commit()

    statements = []

    def reject_source_payload(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)
            assert "raw_payload_json" not in statement
            assert "geometry" not in statement

    def reject_source_entity(session, instance):
        assert not isinstance(instance, (CatDomandaIrrigua, CatDomandaIrriguaParticella))

    event.listen(database, "before_cursor_execute", reject_source_payload)
    event.listen(Session, "loaded_as_persistent", reject_source_entity)
    try:
        with Session(database) as db:
            summary = service.scan_domande_irrigue_anomalies(db, anno=anno)
            assert summary == service.DomandeIrrigueAnomalySummary(expected_domande, 2, 2, 0, 1)
            db.commit()
        with Session(database) as db:
            repeated = service.scan_domande_irrigue_anomalies(db, anno=anno)
            assert repeated == service.DomandeIrrigueAnomalySummary(expected_domande, 2, 0, 2, 0)
            db.commit()
            surface = db.scalar(
                select(CatAnomalia).where(
                    CatAnomalia.tipo == service.DIR_ANOMALIA_SUPERFICIE_COLTURA,
                    CatAnomalia.status == "aperta",
                )
            )
            assert surface.dati_json["sup_irrigata_mq"] == "110.00"
    finally:
        event.remove(database, "before_cursor_execute", reject_source_payload)
        event.remove(Session, "loaded_as_persistent", reject_source_entity)
    assert any("cat_domande_irrigue" in statement for statement in statements)
    assert any("cat_domanda_irrigua_particelle" in statement for statement in statements)
    with Session(database) as db:
        assert db.scalars(select(CatDomandaIrrigua.raw_payload_json)).all() == [raw] * 3
        assert db.scalars(select(CatDomandaIrriguaParticella.raw_payload_json)).all() == [raw] * 2


def test_unlinked_import_and_partial_identifiers_remain_supported(database):
    with Session(database) as db:
        summary = service.persist_capacitas_domande_irrigue_batch(
            db,
            {"domande": [{"anno": 2026, "domanda": "unlinked", "external_row_id": "unlinked"}]},
        )
        assert summary.domande_inserted == 1
        assert summary.linked_utenze == summary.linked_occupancies == 0
        assert service._find_utenza(db, anno=2026, cco="1001", com="179", fra=None) is None
        assert (
            service._find_occupancy(db, cco="1001", com="179", fra="16", pvc=None, ccs=None) is None
        )
        assert service._string_variants("ABC") == ["ABC"]
