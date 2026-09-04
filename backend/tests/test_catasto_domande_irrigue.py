from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path
import sys
from uuid import UUID

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.capacitas import CapacitasDomandeIrrigueSyncJob
from app.models.catasto_phase1 import (
    CatAnomalia,
    CatComune,
    CatConsorzioOccupancy,
    CatConsorzioUnit,
    CatConsorzioUnitSegment,
    CatImportBatch,
    CatParticella,
    CatUtenzaIrrigua,
)
from app.modules.catasto.models.domande_irrigue import CatDomandaIrrigua, CatDomandaIrriguaParticella
from app.modules.catasto.services import domande_irrigue as domande_irrigue_service
from app.modules.catasto.services.domande_irrigue import (
    DIR_ANOMALIA_DOMANDA_FUORI_TERMINE,
    DIR_ANOMALIA_SUPERFICIE_COLTURA,
    DIR_ANOMALIA_SUPERFICIE_TOTALE,
    persist_capacitas_domande_irrigue_batch,
    scan_domande_irrigue_anomalies,
    sync_domande_irrigue_from_anagrafica_rows,
)
from app.modules.elaborazioni.capacitas.apps.involture.client import CapacitasSessionExpiredError
from app.modules.elaborazioni.capacitas.apps.involture.domande_irrigue import (
    CapacitasDomandaIrriguaDetailRow,
    CapacitasDomandaIrriguaRow,
    CapacitasDomandeIrrigueBatchResult,
    CapacitasDomandeIrrigueResult,
)
from app.modules.elaborazioni.capacitas.models import (
    CapacitasAnagrafica,
    CapacitasDomandeIrrigueAnagraficaSearch,
    CapacitasDomandeIrrigueSyncJobCreateRequest,
    CapacitasSearchResult,
)
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita
from app.services import elaborazioni_capacitas_domande_irrigue as domande_irrigue_job_service
from app.services.elaborazioni_capacitas_domande_irrigue import (
    create_domande_irrigue_sync_job,
    delete_domande_irrigue_sync_job,
    expire_stale_domande_irrigue_sync_jobs,
    get_domande_irrigue_sync_job,
    list_domande_irrigue_sync_jobs,
    prepare_domande_irrigue_sync_jobs_for_recovery,
    run_domande_irrigue_sync_job,
    serialize_domande_irrigue_sync_job,
)

_ROUTES_MODULE_PATH = Path(__file__).resolve().parents[1] / "app/modules/catasto/routes/domande_irrigue.py"
_ROUTES_SPEC = importlib.util.spec_from_file_location("catasto_domande_irrigue_routes_test", _ROUTES_MODULE_PATH)
assert _ROUTES_SPEC is not None and _ROUTES_SPEC.loader is not None
domande_irrigue_routes = importlib.util.module_from_spec(_ROUTES_SPEC)
sys.modules[_ROUTES_SPEC.name] = domande_irrigue_routes
_ROUTES_SPEC.loader.exec_module(domande_irrigue_routes)


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_persist_domande_irrigue_links_context_and_replaces_details() -> None:
    db = TestingSessionLocal()
    try:
        context = _seed_context(db)
        result = _capacitas_result(
            domanda_id="dom-1",
            domanda_numero="5410",
            data_ins="07/05/2026 09:16:27",
            sup_irr="60",
        )

        summary = persist_capacitas_domande_irrigue_batch(db, result, run_anomaly_checks=False)
        db.commit()

        assert summary.source_items == 1
        assert summary.domande_inserted == 1
        assert summary.domande_updated == 0
        assert summary.particelle_inserted == 1
        assert summary.linked_utenze == 1
        assert summary.linked_occupancies == 1
        assert summary.linked_particelle == 1
        domanda = db.execute(select(CatDomandaIrrigua)).scalar_one()
        assert domanda.utenza_id == context["utenza"].id
        assert domanda.occupancy_id == context["occupancy"].id
        assert domanda.subject_id == context["subject_id"]
        assert domanda.cco == "000001001"
        assert domanda.com == "179"
        assert domanda.pvc == "097"
        assert domanda.fra == "16"
        assert domanda.ccs == "00000"
        assert domanda.autorinnovo is True
        assert domanda.tot_sup_bonus_mq == Decimal("2.00")
        assert domanda.data_ins == datetime(2026, 5, 7, 9, 16, 27)
        detail = db.execute(select(CatDomandaIrriguaParticella)).scalar_one()
        assert detail.unit_id == context["unit"].id
        assert detail.segment_id == context["segment"].id
        assert detail.particella_id == context["particella"].id
        assert detail.occupancy_id == context["occupancy"].id
        assert detail.sup_irr_mq == Decimal("60.00")
        assert detail.ruolo_irr == Decimal("12.50")

        updated = _capacitas_result(
            domanda_id="dom-1",
            domanda_numero="5410",
            data_ins="08/05/2026",
            sup_irr="70",
            detail_id="part-2",
        )
        update_summary = persist_capacitas_domande_irrigue_batch(db, updated, run_anomaly_checks=False)
        db.commit()

        assert update_summary.domande_inserted == 0
        assert update_summary.domande_updated == 1
        assert update_summary.particelle_inserted == 1
        assert db.scalar(select(func.count()).select_from(CatDomandaIrrigua)) == 1
        assert db.scalar(select(func.count()).select_from(CatDomandaIrriguaParticella)) == 1
        refreshed_detail = db.execute(select(CatDomandaIrriguaParticella)).scalar_one()
        assert refreshed_detail.external_id == "part-2"
        assert refreshed_detail.sup_irr_mq == Decimal("70.00")
    finally:
        db.close()


def test_domande_irrigue_models_are_exported_by_catasto_registry() -> None:
    from app.modules.catasto.models import CatDomandaIrrigua as ExportedDomanda
    from app.modules.catasto.models import CatDomandaIrriguaParticella as ExportedParticella
    from app.modules.catasto.models import registry
    from app.modules.catasto import services as services_package

    assert ExportedDomanda is CatDomandaIrrigua
    assert ExportedParticella is CatDomandaIrriguaParticella
    assert "CatDomandaIrrigua" in registry.__all__
    assert "CatDomandaIrriguaParticella" in registry.__all__
    assert services_package.__all__ == []


def test_scan_domande_irrigue_anomalies_same_crop_and_late_deadline_are_idempotent() -> None:
    db = TestingSessionLocal()
    try:
        context = _seed_context(db)
        _add_domanda_with_detail(db, context, domanda_numero="100", data_ins=datetime(2026, 4, 20), sup_irr=60, crop="Mais")
        _add_domanda_with_detail(db, context, domanda_numero="101", data_ins=datetime(2026, 5, 2), sup_irr=50, crop="Mais")
        db.commit()

        summary = scan_domande_irrigue_anomalies(db, anno=2026)
        db.commit()

        assert summary.scanned_domande == 2
        assert summary.scanned_particelle == 2
        assert summary.opened == 2
        assert summary.updated == 0
        types = set(db.scalars(select(CatAnomalia.tipo)).all())
        assert types == {DIR_ANOMALIA_SUPERFICIE_COLTURA, DIR_ANOMALIA_DOMANDA_FUORI_TERMINE}
        surface = db.execute(
            select(CatAnomalia).where(CatAnomalia.tipo == DIR_ANOMALIA_SUPERFICIE_COLTURA)
        ).scalar_one()
        assert surface.severita == "error"
        assert surface.particella_id == context["particella"].id
        assert surface.dati_json["sup_irrigata_mq"] == "110.00"
        deadline = db.execute(
            select(CatAnomalia).where(CatAnomalia.tipo == DIR_ANOMALIA_DOMANDA_FUORI_TERMINE)
        ).scalar_one()
        db.add(
            CatAnomalia(
                particella_id=None,
                utenza_id=deadline.utenza_id,
                anno_campagna=deadline.anno_campagna,
                tipo=deadline.tipo,
                severita=deadline.severita,
                descrizione=deadline.descrizione,
                dati_json=deadline.dati_json,
                status="aperta",
            )
        )
        db.commit()

        repeated = scan_domande_irrigue_anomalies(db, anno=2026)
        db.commit()

        assert repeated.opened == 0
        assert repeated.updated == 2
        assert repeated.closed == 0
        assert db.scalar(select(func.count()).select_from(CatAnomalia)) == 2
    finally:
        db.close()


def test_scan_domande_irrigue_warns_total_for_multiple_crops_and_ignores_inactive_versions() -> None:
    db = TestingSessionLocal()
    try:
        context = _seed_context(db)
        _add_domanda_with_detail(db, context, domanda_numero="200", sup_irr=80, crop="Mais")
        _add_domanda_with_detail(db, context, domanda_numero="201", sup_irr=40, crop="Medica")
        _add_domanda_with_detail(db, context, domanda_numero="202", sup_irr=500, crop="Mais", stato="Rettificata")
        db.commit()

        summary = scan_domande_irrigue_anomalies(db, anno=2026)
        db.commit()

        assert summary.opened == 1
        anomaly = db.execute(select(CatAnomalia)).scalar_one()
        assert anomaly.tipo == DIR_ANOMALIA_SUPERFICIE_TOTALE
        assert anomaly.severita == "warning"
        assert anomaly.dati_json["sup_irrigata_mq"] == "120.00"
        assert anomaly.dati_json["colture"] == ["mais", "medica"]
    finally:
        db.close()


def test_scan_domande_irrigue_surface_checks_are_scoped_by_year_and_close_stale() -> None:
    db = TestingSessionLocal()
    try:
        context = _seed_context(db)
        _add_domanda_with_detail(db, context, domanda_numero="250", anno=2025, sup_irr=60, crop="Mais")
        _add_domanda_with_detail(db, context, domanda_numero="251", anno=2026, sup_irr=60, crop="Mais")
        stale = CatAnomalia(
            particella_id=context["particella"].id,
            utenza_id=context["utenza"].id,
            anno_campagna=2026,
            tipo=DIR_ANOMALIA_SUPERFICIE_COLTURA,
            severita="error",
            descrizione="Vecchia anomalia superficie.",
            dati_json={"group_key": "2026|stale|mais"},
            status="aperta",
        )
        db.add(stale)
        db.commit()

        summary = scan_domande_irrigue_anomalies(db)
        db.commit()

        db.refresh(stale)
        assert summary.scanned_domande == 2
        assert summary.opened == 0
        assert summary.updated == 0
        assert summary.closed == 1
        assert stale.status == "chiusa"
        assert db.scalar(select(func.count()).select_from(CatAnomalia).where(CatAnomalia.status == "aperta")) == 0
    finally:
        db.close()


def test_scan_domande_irrigue_uses_extended_deadline_for_special_crops() -> None:
    db = TestingSessionLocal()
    try:
        context = _seed_context(db)
        _add_domanda_with_detail(db, context, domanda_numero="300", data_ins=datetime(2026, 6, 15), crop="Carciofo")
        _add_domanda_with_detail(db, context, domanda_numero="301", data_ins=datetime(2026, 7, 1), crop="Oliveto")
        _add_domanda_with_detail(db, context, domanda_numero="302", data_ins=datetime(2026, 6, 20), crop="Agrumeto")
        _add_domanda_with_detail(
            db,
            context,
            domanda_numero="303",
            data_ins=datetime(2026, 12, 1),
            crop="Mais",
            autorinnovo=True,
        )
        db.commit()

        summary = scan_domande_irrigue_anomalies(db, anno=2026)
        db.commit()

        assert summary.opened == 1
        anomaly = db.execute(select(CatAnomalia)).scalar_one()
        assert anomaly.tipo == DIR_ANOMALIA_DOMANDA_FUORI_TERMINE
        assert anomaly.dati_json["domanda_numero"] == "301"
        assert anomaly.dati_json["deadline"] == "2026-06-30"
    finally:
        db.close()


def test_persist_domande_irrigue_runs_anomaly_scan_and_handles_unlinked_details() -> None:
    db = TestingSessionLocal()
    try:
        context = _seed_context(db)
        _add_unlinked_particella(db)
        result = _capacitas_result(
            domanda_id="dom-unlinked",
            domanda_numero="900",
            data_ins="02/05/2026",
            sup_irr="150",
            autorinnovo="0",
        )
        detail = result.details_by_domanda_id["dom-unlinked"][0]
        detail.particella = "30"

        summary = persist_capacitas_domande_irrigue_batch(db, result)
        db.commit()

        assert summary.anomalies_opened == 2
        assert summary.anomalies_closed == 0
        stored_detail = db.execute(select(CatDomandaIrriguaParticella)).scalar_one()
        assert stored_detail.unit_id is None
        assert stored_detail.segment_id is None
        assert stored_detail.particella_id is not None
        assert stored_detail.occupancy_id == context["occupancy"].id
        assert {item.tipo for item in db.scalars(select(CatAnomalia)).all()} == {
            DIR_ANOMALIA_DOMANDA_FUORI_TERMINE,
            DIR_ANOMALIA_SUPERFICIE_COLTURA,
        }
    finally:
        db.close()


def test_persist_domande_irrigue_handles_dict_payloads_missing_context_and_sub_segments() -> None:
    db = TestingSessionLocal()
    try:
        context = _seed_context(db)
        _add_sub_unit(db, context)
        malformed = {
            "source_row_id": "src-bad",
            "domande": [
                {
                    "anno": "bad",
                    "domanda": None,
                    "tot_sup_cat": "not-a-number",
                    "details_by_domanda_id": "ignored",
                }
            ],
            "details_by_domanda_id": {"": "not-a-list"},
        }

        malformed_summary = persist_capacitas_domande_irrigue_batch(db, malformed)
        db.commit()

        assert malformed_summary.domande_inserted == 0
        assert malformed_summary.domande_seen == 0
        assert malformed_summary.invalid_year_rows == (
            {
                "external_id": None,
                "domanda_numero": None,
                "anno": "bad",
                "reason": "Anno Capacitas assente o fuori intervallo 1900-2100",
            },
        )
        assert malformed_summary.particelle_inserted == 0
        assert db.scalar(
            select(func.count()).select_from(CatDomandaIrrigua).where(CatDomandaIrrigua.source_row_id == "src-bad")
        ) == 0

        dict_result = {
            "source_row_id": "src-sub",
            "source_idxana": "idx-sub",
            "source_patrimonio": "",
            "patrimonio_has_domanda_hint": False,
            "cco": "000001001",
            "com": "179",
            "pvc": "097",
            "fra": "16",
            "ccs": "00000",
            "domande": [
                {
                    "external_row_id": "dom-sub",
                    "anno": "2026",
                    "domanda": "901",
                    "cco": "000001001",
                    "com": "179",
                    "pvc": "097",
                    "fra": "16",
                    "ccs": "00000",
                    "data_ins": datetime(2026, 4, 10),
                }
            ],
            "details_by_domanda_id": {
                "dom-sub": [
                    {
                        "external_row_id": "part-sub",
                        "foglio": "10",
                        "particella": "31",
                        "sub": "1",
                        "sup_cat": "100",
                        "sup_irr": "10",
                        "coltura": "Mais",
                        "part_com": "179",
                        "part_cco": "000001001",
                        "part_fra": "16",
                        "part_pvc": "097",
                        "part_ccs": "99999",
                    },
                    {"external_row_id": "part-empty"},
                ]
            },
        }

        dict_summary = persist_capacitas_domande_irrigue_batch(db, dict_result)
        db.commit()

        assert dict_summary.domande_inserted == 1
        assert dict_summary.particelle_inserted == 2
        sub_detail = db.execute(
            select(CatDomandaIrriguaParticella).where(CatDomandaIrriguaParticella.external_id == "part-sub")
        ).scalar_one()
        assert sub_detail.unit_id == context["sub_unit"].id
        assert sub_detail.segment_id == context["sub_segment"].id
        assert sub_detail.occupancy_id == context["occupancy"].id
        empty_detail = db.execute(
            select(CatDomandaIrriguaParticella).where(CatDomandaIrriguaParticella.external_id == "part-empty")
        ).scalar_one()
        assert empty_detail.unit_id is None
        assert empty_detail.particella_id is None
    finally:
        db.close()


def test_scan_domande_irrigue_groups_unlinked_rows_and_service_helpers() -> None:
    db = TestingSessionLocal()
    try:
        context = _seed_context(db)
        first = _add_domanda_with_unlinked_detail(db, domanda_numero="u1", sup_cat=None, sup_irr=80, utenza_id=None)
        second = _add_domanda_with_unlinked_detail(
            db,
            domanda_numero="u2",
            sup_cat=Decimal("100.00"),
            sup_irr=40,
            utenza_id=context["utenza"].id,
        )
        db.commit()

        summary = scan_domande_irrigue_anomalies(db, anno=2026)
        db.commit()

        assert summary.opened == 1
        anomaly = db.execute(select(CatAnomalia)).scalar_one()
        assert anomaly.tipo == DIR_ANOMALIA_SUPERFICIE_COLTURA
        assert anomaly.utenza_id == context["utenza"].id
        assert anomaly.dati_json["group_key"] == "2026|179|99|99||mais"
        assert {str(first.id), str(second.id)} == set(anomaly.dati_json["domanda_particella_ids"])

        assert persist_capacitas_domande_irrigue_batch(db, {"domande": "not-a-list"}).domande_seen == 0
        assert domande_irrigue_service._payload(object()) == {}
        assert domande_irrigue_service._string_variants(None) == []
        assert domande_irrigue_service._to_int(None) is None
        assert domande_irrigue_service._to_int("abc") is None
        assert domande_irrigue_service._to_decimal(None) is None
        assert domande_irrigue_service._to_decimal("abc") is None
        assert domande_irrigue_service._to_datetime(datetime(2026, 1, 1)) == datetime(2026, 1, 1)
        assert domande_irrigue_service._to_datetime(None) is None
        assert domande_irrigue_service._to_datetime("31-12-2026") is None
        assert domande_irrigue_service._normalize_com("ABC") == "ABC"
        assert domande_irrigue_service._normalize_ccs(None) is None
        assert domande_irrigue_service._jsonable([Decimal("1.50")]) == ["1.50"]
        assert domande_irrigue_service._find_utenza(db, anno=2026, cco=None, com="179", fra="16") is None
        assert (
            domande_irrigue_service._find_occupancy(
                db,
                cco=None,
                com="179",
                pvc="097",
                fra="16",
                ccs="00000",
            )
            is None
        )
        assert domande_irrigue_service._detail_rows_for_domanda({}, {}) == []
        assert domande_irrigue_service._first_not_blank(None, " ") is None
        assert (
            domande_irrigue_service._find_existing_domanda(
                db,
                external_id=None,
                anno=2026,
                domanda_numero=None,
                cco="000001001",
                com="179",
                pvc="097",
                fra="16",
                ccs="00000",
            )
            is None
        )
        ambiguous_unit = CatConsorzioUnit(
            cod_comune_capacitas=179,
            source_cod_comune_capacitas=179,
            foglio="10",
            particella="88",
            is_active=True,
        )
        db.add(ambiguous_unit)
        db.flush()
        db.add_all(
            [
                CatConsorzioUnitSegment(unit=ambiguous_unit, segment_type="a", is_current=False),
                CatConsorzioUnitSegment(unit=ambiguous_unit, segment_type="b", is_current=False),
            ]
        )
        db.flush()
        assert domande_irrigue_service._single_current_segment_id(ambiguous_unit) is None
    finally:
        db.close()


def test_sync_domande_irrigue_from_anagrafica_rows_fetches_and_persists() -> None:
    db = TestingSessionLocal()
    try:
        _seed_context(db)
        scraper = _FakeDomandeScraper(
            _capacitas_batch(
                _capacitas_result(
                    domanda_id="dom-sync",
                    domanda_numero="777",
                    data_ins="20/04/2026",
                    sup_irr="20",
                )
            )
        )

        summary = asyncio.run(
            sync_domande_irrigue_from_anagrafica_rows(
                db,
                scraper,
                rows=[object()],
                include_details=True,
                continue_on_error=False,
                run_anomaly_checks=False,
            )
        )
        db.commit()

        assert scraper.calls == [
            {
                "rows": 1,
                "include_details": True,
                "continue_on_error": False,
            }
        ]
        assert summary.domande_inserted == 1
        assert db.execute(select(CatDomandaIrrigua.domanda_numero)).scalar_one() == "777"
    finally:
        db.close()


def test_domande_irrigue_sync_job_runs_searches_persists_and_tracks_recovery() -> None:
    db = TestingSessionLocal()
    try:
        _seed_context(db)
        payload = CapacitasDomandeIrrigueSyncJobCreateRequest(
            credential_id=7,
            searches=[
                CapacitasDomandeIrrigueAnagraficaSearch(q="ok"),
                CapacitasDomandeIrrigueAnagraficaSearch(q="expired", tipo_ricerca=2),
                CapacitasDomandeIrrigueAnagraficaSearch(q="bad"),
            ],
            deduplicate_contexts=True,
            throttle_ms=1,
        )
        job = create_domande_irrigue_sync_job(db, requested_by_user_id=42, credential_id=7, payload=payload)
        assert serialize_domande_irrigue_sync_job(job).id == job.id
        assert list_domande_irrigue_sync_jobs(db)[0].id == job.id
        assert get_domande_irrigue_sync_job(db, job.id).id == job.id

        client = _FakeAnagraficaClient(
            {
                "ok": [_ana_row(row_id="src-a", cco="000001001"), _ana_row(row_id="src-dup", cco="000001001")],
                "expired": [_ana_row(row_id="src-b", cco="000001002")],
            },
            expired_once={"expired"},
            failing={"bad"},
        )
        valid_result = _capacitas_result(
            domanda_id="dom-job",
            domanda_numero="910",
            data_ins="02/05/2026",
            sup_irr="120",
            autorinnovo="0",
        )
        valid_result.domande.append(CapacitasDomandaIrriguaRow(ID="dom-invalid", Anno="0", Domanda="911"))
        scraper = _JobDomandeScraper(
            {
                "000001001": _capacitas_batch(valid_result),
                "000001002": _capacitas_batch(
                    CapacitasDomandeIrrigueResult(
                        cco="000001002",
                        com="179",
                        pvc="097",
                        fra="16",
                        ccs="00000",
                        source_row_id="src-b",
                        source_denominazione="Errore Demo",
                        error="Contesto non importabile",
                    )
                ),
            }
        )

        asyncio.run(run_domande_irrigue_sync_job(db, client, scraper, job))

        assert client.relogin_calls == 1
        assert [call["q"] for call in client.calls] == ["ok", "expired", "expired", "bad"]
        assert [call["cco"] for call in scraper.calls] == ["000001001", "000001002"]
        result = job.result_json
        assert isinstance(result, dict)
        assert job.status == "completed_with_errors"
        assert result["source_rows"] == 3
        assert result["skipped_duplicate_contexts"] == 1
        assert result["total_rows"] == 2
        assert result["processed_rows"] == 2
        assert result["failed_items"] == 2
        assert result["invalid_year_rows"] == 1
        assert result["recent_invalid_year_rows"][0]["external_id"] == "dom-invalid"
        assert result["domande_inserted"] == 1
        assert result["particelle_inserted"] == 1
        assert result["anomalies_opened"] == 2
        assert result["anomalies_closed"] == 0
        assert db.scalar(select(func.count()).select_from(CatDomandaIrrigua)) == 1

        stale = CapacitasDomandeIrrigueSyncJob(
            status="processing",
            mode="anagrafica_search",
            payload_json={"auto_resume": True},
            result_json={"current_label": "bloccato"},
            updated_at=datetime(2026, 1, 1),
        )
        recoverable = CapacitasDomandeIrrigueSyncJob(
            status="pending",
            mode="anagrafica_search",
            payload_json={"auto_resume": True},
        )
        non_recoverable = CapacitasDomandeIrrigueSyncJob(
            status="pending",
            mode="anagrafica_search",
            payload_json={"auto_resume": False},
        )
        db.add_all([stale, recoverable, non_recoverable])
        db.commit()

        assert domande_irrigue_job_service._normalize_job_datetime(None) is None
        assert domande_irrigue_job_service._normalize_job_datetime(datetime(2026, 1, 1)).tzinfo is not None
        assert (
            domande_irrigue_job_service._normalize_job_datetime(datetime(2026, 1, 1, tzinfo=timezone.utc))
            == datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
        domande_irrigue_job_service._finalize_anomaly_scan(
            db,
            job,
            CapacitasDomandeIrrigueSyncJobCreateRequest(
                searches=[CapacitasDomandeIrrigueAnagraficaSearch(q="noop")],
                run_anomaly_checks=False,
            ),
        )
        recent_payload: dict[str, object] = {}
        domande_irrigue_job_service._append_recent_item(recent_payload, {"status": "checked", "error": None})
        assert recent_payload["recent_items"] == [{"status": "checked"}]
        overflow_payload = {"recent_items": [{"i": i} for i in range(101)]}
        domande_irrigue_job_service._append_recent_item(overflow_payload, {"i": 101})
        assert len(overflow_payload["recent_items"]) == 100
        assert overflow_payload["recent_items"][0] == {"i": 2}
        invalid_payload: dict[str, object] = {}
        for index in range(102):
            domande_irrigue_job_service._append_invalid_year_item(invalid_payload, {"i": index, "empty": None})
        assert len(invalid_payload["recent_invalid_year_rows"]) == 100
        assert invalid_payload["recent_invalid_year_rows"][0] == {"i": 2}

        expire_stale_domande_irrigue_sync_jobs(db)
        db.refresh(stale)
        assert stale.status == "failed"
        assert stale.result_json["current_label"] is None

        recovered_ids = prepare_domande_irrigue_sync_jobs_for_recovery(db)
        assert recoverable.id in recovered_ids
        assert non_recoverable.id not in recovered_ids
        db.refresh(recoverable)
        assert recoverable.status == "queued_resume"
        assert recoverable.result_json["resume_reason"] == "backend_restart"

        job.status = "succeeded"
        db.commit()
        delete_domande_irrigue_sync_job(db, job)
        assert get_domande_irrigue_sync_job(db, job.id) is None
    finally:
        db.close()


def test_domande_irrigue_sync_job_loads_role_cf_and_preserves_source_tax_ids() -> None:
    db = TestingSessionLocal()
    try:
        context = _seed_context(db)
        db.add_all(
            [
                CatUtenzaIrrigua(
                    batch=context["batch"],
                    anno_campagna=2025,
                    cco="role-1",
                    cod_comune_capacitas=179,
                    cod_frazione=16,
                    foglio="10",
                    particella="20",
                    denominazione="Ruolo PG",
                    codice_fiscale="12345678901",
                ),
                CatUtenzaIrrigua(
                    batch=context["batch"],
                    anno_campagna=2025,
                    cco="role-2",
                    cod_comune_capacitas=179,
                    cod_frazione=16,
                    foglio="10",
                    particella="20",
                    denominazione="Ruolo PF",
                    codice_fiscale=" mddmgv77a51g113q ",
                ),
                CatUtenzaIrrigua(
                    batch=context["batch"],
                    anno_campagna=2025,
                    cco="role-invalid",
                    cod_comune_capacitas=179,
                    cod_frazione=16,
                    foglio="10",
                    particella="20",
                    denominazione="Ruolo Ignorato",
                    codice_fiscale="NAN",
                ),
            ]
        )
        db.commit()
        payload = CapacitasDomandeIrrigueSyncJobCreateRequest(
            credential_id=7,
            role_anno_campagna=2025,
            role_cf_limit=2,
            run_anomaly_checks=False,
            throttle_ms=0,
        )
        job = create_domande_irrigue_sync_job(db, requested_by_user_id=42, credential_id=7, payload=payload)
        assert job.mode == "role_cf_search"

        client = _FakeAnagraficaClient(
            {
                "12345678901": [_ana_row(row_id="src-role-pg", cco="000001001")],
                "MDDMGV77A51G113Q": [_ana_row(row_id="src-role-pf", cco="000001001")],
            }
        )
        scraper = _JobDomandeScraper(
            {
                "000001001": _capacitas_batch(
                    _capacitas_result(
                        domanda_id="dom-role",
                        domanda_numero="920",
                        data_ins="20/04/2026",
                        sup_irr="20",
                    )
                ),
            }
        )

        asyncio.run(run_domande_irrigue_sync_job(db, client, scraper, job))

        assert [call["q"] for call in client.calls] == ["12345678901", "MDDMGV77A51G113Q"]
        assert [call["cco"] for call in scraper.calls] == ["000001001"]
        result = job.result_json
        assert isinstance(result, dict)
        assert job.status == "succeeded"
        assert result["mode"] == "role_cf_search"
        assert result["role_anno_campagna"] == 2025
        assert result["role_cf_limit"] == 2
        assert result["total_searches"] == 2
        assert result["source_rows"] == 2
        assert result["skipped_duplicate_contexts"] == 1
        assert result["total_rows"] == 1
        assert result["recent_items"][0]["source_search_codice_fiscali"] == [
            "12345678901",
            "MDDMGV77A51G113Q",
        ]
        domanda = db.execute(select(CatDomandaIrrigua).where(CatDomandaIrrigua.domanda_numero == "920")).scalar_one()
        assert domanda.raw_payload_json["source"]["source_search_codici_fiscali"] == [
            "12345678901",
            "MDDMGV77A51G113Q",
        ]
        assert domanda.raw_payload_json["source"]["source_search_codice_fiscale"] == "12345678901"

        duplicated_searches = domande_irrigue_job_service._deduplicate_searches(
            [
                CapacitasDomandeIrrigueAnagraficaSearch(q=" abc12345678 "),
                CapacitasDomandeIrrigueAnagraficaSearch(q="ABC12345678"),
            ]
        )
        assert [item.q for item in duplicated_searches] == [" abc12345678 "]
        empty_metadata_row = CapacitasAnagrafica(cco="1", com="2", pvc="3", fraz="4", sche="0")
        metadata_row = CapacitasAnagrafica(
            cco="1",
            com="2",
            pvc="3",
            fraz="4",
            sche="0",
            source_search_q="MDDMGV77A51G113Q",
            source_search_tipo=1,
            source_search_codice_fiscale="MDDMGV77A51G113Q",
            source_search_codici_fiscali=["MDDMGV77A51G113Q"],
        )
        assert domande_irrigue_job_service._deduplicate_rows([empty_metadata_row, metadata_row]) == [
            empty_metadata_row
        ]
        assert empty_metadata_row.source_search_q == "MDDMGV77A51G113Q"
        assert empty_metadata_row.source_search_tipo == 1
        assert empty_metadata_row.source_search_codice_fiscale == "MDDMGV77A51G113Q"
    finally:
        db.close()


def test_domande_irrigue_sync_job_marks_failed_on_search_or_row_error() -> None:
    db = TestingSessionLocal()
    try:
        search_error_job = create_domande_irrigue_sync_job(
            db,
            requested_by_user_id=None,
            credential_id=None,
            payload=CapacitasDomandeIrrigueSyncJobCreateRequest(
                searches=[CapacitasDomandeIrrigueAnagraficaSearch(q="bad")],
                continue_on_error=False,
            ),
        )
        with pytest.raises(RuntimeError):
            asyncio.run(
                run_domande_irrigue_sync_job(
                    db,
                    _FakeAnagraficaClient({}, failing={"bad"}),
                    _RaisingDomandeScraper(),
                    search_error_job,
                )
            )
        db.refresh(search_error_job)
        assert search_error_job.status == "failed"
        assert "Errore ricerca" in search_error_job.error_detail

        row_error_job = create_domande_irrigue_sync_job(
            db,
            requested_by_user_id=None,
            credential_id=None,
            payload=CapacitasDomandeIrrigueSyncJobCreateRequest(
                searches=[CapacitasDomandeIrrigueAnagraficaSearch(q="ok")],
                continue_on_error=False,
            ),
        )
        with pytest.raises(ValueError):
            asyncio.run(
                run_domande_irrigue_sync_job(
                    db,
                    _FakeAnagraficaClient({"ok": [_ana_row(row_id="src-a", cco="000001001")]}),
                    _RaisingDomandeScraper(),
                    row_error_job,
                )
            )
        db.refresh(row_error_job)
        assert row_error_job.status == "failed"
        assert row_error_job.error_detail == "Errore riga"
    finally:
        db.close()


def test_catasto_domande_irrigue_routes_list_detail_summary_and_ruolo_reconciliation() -> None:
    db = TestingSessionLocal()
    try:
        context = _seed_context(db)
        _add_domanda_with_detail(db, context, domanda_numero="5013", sup_irr=100, crop="Mais")
        _add_domanda_with_detail(db, context, domanda_numero="99", sup_irr=20, crop="Medica")
        _seed_ruolo_particella(db, context, domanda="05013", crop="Mais", sup_ha=Decimal("0.0100"), cat_particella_id=context["particella"].id)
        _seed_ruolo_particella(db, context, domanda="5013", crop="Medica", sup_ha=Decimal("0.0100"), cat_particella_id=context["particella"].id)
        _seed_ruolo_particella(db, context, domanda="99", crop="Medica", sup_ha=Decimal("0.5000"), cat_particella_id=None)
        _seed_ruolo_particella(db, context, domanda="404", crop=None, sup_ha=None, cat_particella_id=context["particella"].id)
        db.commit()

        listed = domande_irrigue_routes.list_domande_irrigue(
            db=db,
            _=object(),
            anno=2026,
            stato="Aperta",
            subject_id=None,
            utenza_id=None,
            cco="000001001",
            search="5013",
            limit=10,
            offset=0,
        )
        assert listed.total == 1
        assert listed.items[0].domanda_numero == "5013"
        assert listed.items[0].particelle[0].coltura == "Mais"

        subject_listed = domande_irrigue_routes.list_domande_irrigue(
            db=db,
            _=object(),
            anno=2026,
            stato=None,
            subject_id=context["subject_id"],
            utenza_id=None,
            cco=None,
            search=None,
            limit=10,
            offset=0,
        )
        assert subject_listed.total == 2
        unrelated_subject_listed = domande_irrigue_routes.list_domande_irrigue(
            db=db,
            _=object(),
            anno=2026,
            stato=None,
            subject_id=UUID("22222222-2222-2222-2222-222222222222"),
            utenza_id=None,
            cco=None,
            search=None,
            limit=10,
            offset=0,
        )
        assert unrelated_subject_listed.total == 0
        utenza_listed = domande_irrigue_routes.list_domande_irrigue(
            db=db,
            _=object(),
            anno=2026,
            stato=None,
            subject_id=context["subject_id"],
            utenza_id=context["utenza"].id,
            cco=None,
            search=None,
            limit=10,
            offset=0,
        )
        assert utenza_listed.total == 2
        unrelated_utenza_listed = domande_irrigue_routes.list_domande_irrigue(
            db=db,
            _=object(),
            anno=2026,
            stato=None,
            subject_id=context["subject_id"],
            utenza_id=UUID("33333333-3333-3333-3333-333333333333"),
            cco=None,
            search=None,
            limit=10,
            offset=0,
        )
        assert unrelated_utenza_listed.total == 0

        detail = domande_irrigue_routes.get_domanda_irrigua(listed.items[0].id, db=db, _=object())
        assert detail.domanda_numero == "5013"
        with pytest.raises(Exception) as exc_info:
            domande_irrigue_routes.get_domanda_irrigua(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), db=db, _=object())
        assert getattr(exc_info.value, "status_code", None) == 404

        summary = domande_irrigue_routes.get_domande_irrigue_summary(db=db, _=object(), anno=2026)
        assert summary.total_domande == 2
        assert summary.total_particelle == 2
        assert summary.linked_utenze == 1
        assert summary.by_anno[0].key == "2026"
        assert summary.by_stato[0].key == "Aperta"

        reconciliation = domande_irrigue_routes.reconcile_domande_irrigue_ruolo(db=db, _=object(), anno=2026, limit=10)
        assert reconciliation.total_ruolo_rows == 4
        assert reconciliation.matched_rows == 1
        assert reconciliation.missing_rows == 1
        assert reconciliation.crop_mismatch_rows == 1
        assert reconciliation.surface_mismatch_rows == 1
        assert {item.issue for item in reconciliation.items} == {
            None,
            "coltura_mismatch",
            "superficie_mismatch",
            "domanda_non_trovata",
        }
        blank_role = RuoloParticella(
            partita_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            anno_tributario=2026,
            domanda_irrigua=" ",
            foglio="1",
            particella="1",
        )
        assert domande_irrigue_routes._find_domanda_particella_for_ruolo(db, blank_role) is None

        unfiltered = domande_irrigue_routes.list_domande_irrigue(
            db=db,
            _=object(),
            anno=None,
            stato=None,
            subject_id=None,
            utenza_id=None,
            cco=None,
            search=None,
            limit=10,
            offset=0,
        )
        assert unfiltered.total == 2
    finally:
        db.close()


class _FakeDomandeScraper:
    def __init__(self, result: CapacitasDomandeIrrigueBatchResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def fetch_for_anagrafica_rows(
        self,
        rows: list[object],
        *,
        include_details: bool,
        continue_on_error: bool,
    ) -> CapacitasDomandeIrrigueBatchResult:
        self.calls.append(
            {
                "rows": len(rows),
                "include_details": include_details,
                "continue_on_error": continue_on_error,
            }
        )
        return self.result


class _FakeAnagraficaClient:
    def __init__(
        self,
        rows_by_query: dict[str, list[CapacitasAnagrafica]],
        *,
        expired_once: set[str] | None = None,
        failing: set[str] | None = None,
    ) -> None:
        self.rows_by_query = rows_by_query
        self.expired_once = expired_once or set()
        self.failing = failing or set()
        self.calls: list[dict[str, object]] = []
        self.relogin_calls = 0
        self._expired_seen: set[str] = set()

    async def search_anagrafica(
        self,
        q: str,
        tipo: int = 1,
        solo_con_beni: bool = False,
    ) -> CapacitasSearchResult:
        self.calls.append({"q": q, "tipo": tipo, "solo_con_beni": solo_con_beni})
        if q in self.expired_once and q not in self._expired_seen:
            self._expired_seen.add(q)
            raise CapacitasSessionExpiredError("Sessione scaduta")
        if q in self.failing:
            raise RuntimeError(f"Errore ricerca {q}")
        rows = self.rows_by_query.get(q, [])
        return CapacitasSearchResult(total=len(rows), rows=rows)

    async def relogin(self) -> None:
        self.relogin_calls += 1


class _JobDomandeScraper:
    def __init__(self, results_by_cco: dict[str, CapacitasDomandeIrrigueBatchResult]) -> None:
        self.results_by_cco = results_by_cco
        self.calls: list[dict[str, object]] = []

    async def fetch_for_anagrafica_rows(
        self,
        rows: list[CapacitasAnagrafica],
        *,
        include_details: bool,
        continue_on_error: bool,
    ) -> CapacitasDomandeIrrigueBatchResult:
        row = rows[0]
        self.calls.append(
            {
                "cco": row.cco,
                "include_details": include_details,
                "continue_on_error": continue_on_error,
            }
        )
        result = self.results_by_cco[row.cco or ""]
        for item in result.items:
            item.source_row_id = row.id
            item.source_idxana = row.id_ana
            item.source_denominazione = row.denominazione
            item.source_patrimonio = row.patrimonio
            item.source_codice_fiscale = row.codice_fiscale
            item.source_partita_iva = row.partita_iva
            item.source_search_q = row.source_search_q
            item.source_search_tipo = row.source_search_tipo
            item.source_search_codice_fiscale = row.source_search_codice_fiscale
            item.source_search_codici_fiscali = list(row.source_search_codici_fiscali)
        return result


class _RaisingDomandeScraper:
    async def fetch_for_anagrafica_rows(
        self,
        rows: list[CapacitasAnagrafica],
        *,
        include_details: bool,
        continue_on_error: bool,
    ) -> CapacitasDomandeIrrigueBatchResult:
        raise ValueError("Errore riga")


def _seed_context(db: Session) -> dict[str, object]:
    comune = CatComune(nome_comune="SAN VERO MILIS", codice_catastale="I384", cod_comune_capacitas=179)
    batch = CatImportBatch(filename="capacitas.xlsx", tipo="capacitas", anno_campagna=2026)
    particella = CatParticella(
        comune=comune,
        cod_comune_capacitas=179,
        codice_catastale="I384",
        nome_comune="SAN VERO MILIS",
        foglio="10",
        particella="20",
        superficie_mq=Decimal("100.00"),
        is_current=True,
    )
    utenza = CatUtenzaIrrigua(
        batch=batch,
        anno_campagna=2026,
        cco="1001",
        cod_comune_capacitas=179,
        cod_frazione=16,
        foglio="10",
        particella="20",
        sup_catastale_mq=Decimal("100.00"),
        denominazione="Utente Demo",
    )
    subject_id = UUID("11111111-1111-1111-1111-111111111111")
    unit = CatConsorzioUnit(
        particella_record=particella,
        cod_comune_capacitas=179,
        source_cod_comune_capacitas=179,
        foglio="10",
        particella="20",
        is_active=True,
    )
    segment = CatConsorzioUnitSegment(unit=unit, segment_type="full", is_current=True)
    occupancy = CatConsorzioOccupancy(
        unit=unit,
        subject_id=subject_id,
        utenza_record=utenza,
        cco="1001",
        com="179",
        pvc="97",
        fra="16",
        ccs="0",
        is_current=True,
    )
    db.add_all([comune, batch, particella, utenza, unit, segment, occupancy])
    db.flush()
    return {
        "comune": comune,
        "batch": batch,
        "particella": particella,
        "utenza": utenza,
        "unit": unit,
        "segment": segment,
        "occupancy": occupancy,
        "subject_id": subject_id,
    }


def _seed_ruolo_particella(
    db: Session,
    context: dict[str, object],
    *,
    domanda: str,
    crop: str | None,
    sup_ha: Decimal | None,
    cat_particella_id: object | None,
) -> RuoloParticella:
    job = RuoloImportJob(anno_tributario=2026, filename=f"ruolo-{domanda}.txt", status="completed")
    db.add(job)
    db.flush()
    avviso = RuoloAvviso(import_job_id=job.id, codice_cnc=f"cnc-{domanda}", anno_tributario=2026)
    db.add(avviso)
    db.flush()
    partita = RuoloPartita(avviso_id=avviso.id, codice_partita=f"partita-{domanda}", comune_nome="SAN VERO MILIS")
    db.add(partita)
    db.flush()
    row = RuoloParticella(
        partita_id=partita.id,
        anno_tributario=2026,
        domanda_irrigua=domanda,
        foglio="10",
        particella="20",
        subalterno=None,
        sup_irrigata_ha=sup_ha,
        coltura=crop,
        cat_particella_id=cat_particella_id,
    )
    db.add(row)
    db.flush()
    return row


def _ana_row(*, row_id: str, cco: str) -> CapacitasAnagrafica:
    return CapacitasAnagrafica(
        id=row_id,
        id_ana=f"idx-{row_id}",
        patrimonio="T--------D",
        pvc="097",
        com="179",
        cco=cco,
        fraz="16",
        sche="00000",
        comune="SAN VERO MILIS",
        denominazione=f"Utente {row_id}",
        codice_fiscale="MDDMGV77A51G113Q",
    )


def _add_unlinked_particella(db: Session) -> CatParticella:
    particella = CatParticella(
        cod_comune_capacitas=179,
        codice_catastale="I384",
        nome_comune="SAN VERO MILIS",
        foglio="10",
        particella="30",
        superficie_mq=Decimal("100.00"),
        is_current=True,
    )
    db.add(particella)
    db.flush()
    return particella


def _add_sub_unit(db: Session, context: dict[str, object]) -> None:
    particella = CatParticella(
        cod_comune_capacitas=179,
        codice_catastale="I384",
        nome_comune="SAN VERO MILIS",
        foglio="10",
        particella="31",
        subalterno="1",
        superficie_mq=Decimal("100.00"),
        is_current=True,
    )
    unit = CatConsorzioUnit(
        particella_record=particella,
        cod_comune_capacitas=179,
        source_cod_comune_capacitas=179,
        foglio="10",
        particella="31",
        subalterno="1",
        is_active=True,
    )
    segment = CatConsorzioUnitSegment(unit=unit, segment_type="sub", is_current=False)
    db.add_all([particella, unit, segment])
    db.flush()
    context["sub_particella"] = particella
    context["sub_unit"] = unit
    context["sub_segment"] = segment


def _capacitas_batch(*items: CapacitasDomandeIrrigueResult) -> CapacitasDomandeIrrigueBatchResult:
    return CapacitasDomandeIrrigueBatchResult(
        source_total=len(items),
        checked_records=len(items),
        records_with_domande=len(items),
        items=list(items),
    )


def _capacitas_result(
    *,
    domanda_id: str,
    domanda_numero: str,
    data_ins: str,
    sup_irr: str,
    detail_id: str = "part-1",
    autorinnovo: str = "1",
) -> CapacitasDomandeIrrigueResult:
    row = CapacitasDomandaIrriguaRow.model_validate(
        {
            "ID": domanda_id,
            "Autorinnovo": autorinnovo,
            "Stato": "Aperta",
            "StatoCodice": "1",
            "Anno": "2026",
            "Cco": "000001001",
            "Domanda": domanda_numero,
            "DataIns": data_ins,
            "Tipo": "I Coltura",
            "TipoCodice": "1",
            "TipoSchedaCodice": "0",
            "Pvc": "097",
            "Com": "179",
            "Fra": "16",
            "Ccs": "00000",
            "RuoloIrr": "10,50",
            "TotSupCat": "100",
            "TotSupIrr": sup_irr,
            "TotSupServita": "0",
            "TotSupRichiesta": "0",
            "TotSupMalus": "1",
            "TotSupBonus": "2",
            "DataAgg": "08/05/2026",
            "DataRett": "",
            "DataSosp": "",
            "DataChius": "",
            "Comune": "SAN VERO MILIS",
            "IDXAna": "idx-1",
            "strNote": "nota",
        }
    )
    detail = CapacitasDomandaIrriguaDetailRow.model_validate(
        {
            "IDDomanda": domanda_id,
            "ID": detail_id,
            "Localita": "localita",
            "Comizio": "comizio",
            "Foglio": "10",
            "Partic": "20",
            "Sub": "",
            "SupCat": "100",
            "SupIrr": sup_irr,
            "Coltura": "Mais",
            "PartPvc": "097",
            "PartCom": "179",
            "PartCco": "000001001",
            "PartFra": "16",
            "PartCcs": "00000",
            "RuoloBon": "0",
            "RuoloIrr": "12,50",
            "RuoloVar": "0",
        }
    )
    return CapacitasDomandeIrrigueResult(
        cco="000001001",
        com="179",
        pvc="097",
        fra="16",
        ccs="00000",
        source_row_id="src-1",
        source_idxana="idx-1",
        source_denominazione="Utente Demo",
        source_patrimonio="ABCD",
        patrimonio_has_domanda_hint=True,
        total_domande=1,
        domande=[row],
        details_by_domanda_id={domanda_id: [detail]},
    )


def _add_domanda_with_detail(
    db: Session,
    context: dict[str, object],
    *,
    domanda_numero: str,
    anno: int = 2026,
    sup_irr: int = 10,
    crop: str = "Mais",
    stato: str = "Aperta",
    data_ins: datetime | None = None,
    autorinnovo: bool = False,
) -> None:
    domanda = CatDomandaIrrigua(
        anno=anno,
        domanda_numero=domanda_numero,
        cco="000001001",
        com="179",
        pvc="097",
        fra="16",
        ccs="00000",
        stato=stato,
        autorinnovo=autorinnovo,
        data_ins=data_ins or datetime(anno, 4, 20),
        subject_id=context["subject_id"],
        utenza_id=context["utenza"].id,
        occupancy_id=context["occupancy"].id,
        raw_payload_json={"domanda": domanda_numero},
    )
    db.add(domanda)
    db.flush()
    db.add(
        CatDomandaIrriguaParticella(
            domanda_id=domanda.id,
            particella_id=context["particella"].id,
            unit_id=context["unit"].id,
            occupancy_id=context["occupancy"].id,
            utenza_id=context["utenza"].id,
            foglio="10",
            particella="20",
            sup_cat_mq=Decimal("100.00"),
            sup_irr_mq=Decimal(str(sup_irr)),
            coltura=crop,
            part_com="179",
            raw_payload_json={"detail": domanda_numero},
        )
    )


def _add_domanda_with_unlinked_detail(
    db: Session,
    *,
    domanda_numero: str,
    sup_cat: Decimal | None,
    sup_irr: int,
    utenza_id: object | None,
) -> CatDomandaIrriguaParticella:
    domanda = CatDomandaIrrigua(
        anno=2026,
        domanda_numero=domanda_numero,
        cco="000001001",
        com="179",
        pvc="097",
        fra="16",
        ccs="00000",
        stato="Aperta",
        data_ins=datetime(2026, 4, 20),
        utenza_id=utenza_id,
        raw_payload_json={"domanda": domanda_numero},
    )
    db.add(domanda)
    db.flush()
    detail = CatDomandaIrriguaParticella(
        domanda_id=domanda.id,
        utenza_id=utenza_id,
        foglio="99",
        particella="99",
        sup_cat_mq=sup_cat,
        sup_irr_mq=Decimal(str(sup_irr)),
        coltura="Mais",
        part_com="179",
        raw_payload_json={"detail": domanda_numero},
    )
    db.add(detail)
    db.flush()
    return detail
